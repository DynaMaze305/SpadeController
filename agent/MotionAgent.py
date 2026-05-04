import asyncio
import os
import logging

from spade.agent import Agent, Template
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour, OneShotBehaviour
from spade.message import Message

from agent.managers.motion_manager import MotionManager
from agent.motion_models import (
    duration_for_distance,
    duration_for_angle,
    get_ratio,
    update as update_motion_config,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MotionAgent")

# Quiet down SPADE / XMPP internals
for log_name in ["spade", "aioxmpp", "xmpp", "aioopenssl"]:
    logging.getLogger(log_name).setLevel(logging.WARNING)

# Default motion parameters for fallback purpose
STEP_DURATION = 0.5          # seconds
ROTATION_DURATION = 1.0      # seconds
ROTATION_DEG_PER_SEC = 45    # degrees per second
ROTATION_PWM_DEFAULT = 20    # duty cycle for rotations
FORWARD_PWM_LEFT = 0.4       # duty cycle for forward
LEFT_RIGHT_RATIO = 1.01      # right / left motor compensation

# Smooth-stop ramp
SMOOTH_STEPS = 5
SMOOTH_TIME = 0.15           # seconds

# Autonomous recovery: when both IR fire we cut motors and reverse a bit so
# the bot frees itself without any controller-side handshake.
EMERGENCY_RECOVERY_MM = 30
EMERGENCY_RECOVERY_PWM = 10


class MotionAgent(Agent):
    class XMPPCommandListener(CyclicBehaviour):
        async def on_start(self):
            logger.info("[Behaviour] Ready to receive commands.")

        async def run(self):
            """
            Listen for incoming XMPP messages and route them to the queue
            or to the emergency processor.
            """
            msg = await self.receive(timeout=30)
            if not msg:
                return

            logger.info(f"[Behaviour] Received command ({msg.sender}): {msg.body}")

            if msg.get_metadata("emergency"):
                await self.process_command(msg)
            else:
                await self.agent.queue.put(msg)

        async def process_command(self, msg: Message):
            """
            Process IR-emergency notifications from SensorsAgent. Per-side IR
            state is tracked locally; on the transition into both-blocked we
            cut motors and fire the autonomous backward recovery.
            """
            command = msg.body
            side = msg.get_metadata("emergency")  # "left" or "right"

            if not command.startswith("obstacles"):
                return

            state = command.split(' ', 1)[1]
            logger.info(f"[Behaviour] Emergency: {state} (side={side})")

            # manual override clears everything
            if state == "override":
                self.agent.ir_left_blocked = False
                self.agent.ir_right_blocked = False
                self.agent.motion_manager.clear_emergency_stop()
                self.agent.emergency_brake = False
                return

            was_double = self.agent.ir_left_blocked and self.agent.ir_right_blocked

            # apply the IR-level mutation
            if state == "detected":
                if side == "left":
                    self.agent.ir_left_blocked = True
                elif side == "right":
                    self.agent.ir_right_blocked = True
            elif state == "still":
                if side == "left":
                    self.agent.ir_left_blocked = False
                elif side == "right":
                    self.agent.ir_right_blocked = False
            elif state == "clear":
                self.agent.ir_left_blocked = False
                self.agent.ir_right_blocked = False

            is_double = self.agent.ir_left_blocked and self.agent.ir_right_blocked

            # transition into both-blocked: latch motors and back up autonomously
            if is_double and not was_double:
                self.agent.motion_manager.emergency_stop()
                self.agent.emergency_brake = True
                self.agent.add_behaviour(MotionAgent.EmergencyRecovery())

            # transition out of both-blocked: lift the latch
            if not is_double and was_double:
                self.agent.motion_manager.clear_emergency_stop()
                self.agent.emergency_brake = False

    class EmergencyRecovery(OneShotBehaviour):
        """
        Autonomous backward maneuver. Bypasses the latch with emergency_override
        so the bot can move while it is still classified as "in emergency".
        Once it has rolled back, the IR sensors clear and SensorsAgent will
        signal "obstacles clear", which lifts the latch via process_command.
        """
        async def run(self):
            logger.info(f"[Recovery] backing up {EMERGENCY_RECOVERY_MM}mm")
            # tiny delay so the in-flight worker reply gets out first
            await asyncio.sleep(0.1)
            duration = duration_for_distance(EMERGENCY_RECOVERY_MM)
            pwm_left = EMERGENCY_RECOVERY_PWM
            pwm_right = pwm_left * get_ratio(is_backward=True)
            self.agent.motion_manager.backward(
                int(pwm_left), int(pwm_right), emergency_override=True,
            )
            await asyncio.sleep(duration)
            self.agent.motion_manager.stop()
            logger.info("[Recovery] done")

    class Worker(CyclicBehaviour):
        async def on_start(self):
            logger.info("[Behaviour] Ready to work.")

        async def run(self):
            """
            Pull queued commands and execute them, replying with the result.
            """
            msg = await self.agent.queue.get()

            keyboard_signal = msg.get_metadata("source") == "keyboard"
            try:
                response = await self.process_command(msg.body, override_stop=keyboard_signal)
            except RuntimeError as e:
                logger.error(f"[Behaviour] Worker: RuntimeError ({e}) during process message:\n{msg}")
                response = f"Error: {e}"

            reply = Message(to=str(msg.sender))
            reply.set_metadata("performative", "inform")
            reply.body = f"Executed command: {msg.body}\n{response}"
            await self.send(reply)
            logger.info(f"[Behaviour] Sent reply to {msg.sender}")

        # decrementing the motors to 0 instead of an abrupt stop
        async def smooth_stop(self, pwm_left, pwm_right, steps=SMOOTH_STEPS, smoothing_time=SMOOTH_TIME):
            step_time = smoothing_time / steps
            for i in range(steps, 0, -1):
                left = int(abs(pwm_left) * i / steps)
                right = int(abs(pwm_right) * i / steps)
                self.agent.motion_manager.setPWM(left, right)
                await asyncio.sleep(step_time)
            self.agent.motion_manager.stop()

        # rotation by a signed angle in degrees
        async def rotate_by(self, degrees: float, duration: float = None, pwm: int = None, ratio: int = None):
            if pwm is None:
                pwm_left = ROTATION_PWM_DEFAULT
            else:
                pwm_left = pwm

            if ratio is None:
                pwm_right = pwm_left * LEFT_RIGHT_RATIO
            else:
                pwm_right = pwm_left * ratio

            if degrees is None:
                is_positive = duration > 0
                duration = abs(duration)
            else:
                is_positive = degrees > 0
                if duration is None:
                    duration = abs(degrees) / ROTATION_DEG_PER_SEC

            logger.info(
                f"[Behaviour] Rotating deg={degrees} duration={duration:.2f}s "
                f"pwm={pwm_left} ratio={pwm_right/pwm_left:.3f} positive={is_positive}"
            )

            if is_positive:
                self.agent.motion_manager.left(int(pwm_left), int(pwm_right))
            else:
                self.agent.motion_manager.right(int(pwm_left), int(pwm_right))

            smooth_time = min(SMOOTH_TIME, duration / 2)
            await asyncio.sleep(duration - smooth_time)
            await self.smooth_stop(pwm_left, pwm_right, smoothing_time=smooth_time)

        # forward / backward by a signed distance in mm
        async def forward_by(self, distance: float, duration: float = None, pwm: int = None, ratio: int = None):
            if pwm is None:
                pwm_left = FORWARD_PWM_LEFT
            else:
                pwm_left = pwm

            if distance is None:
                is_backward = duration < 0
                duration = abs(duration)
            else:
                is_backward = distance < 0
                if duration is None:
                    duration = duration_for_distance(distance)

            if ratio is None:
                ratio = get_ratio(is_backward)
            pwm_right = pwm_left * ratio

            logger.info(
                f"[Behaviour] Moving dist={distance} duration={duration:.2f}s "
                f"pwm={pwm_left} ratio={pwm_right/pwm_left:.3f} backward={is_backward}"
            )

            if is_backward:
                self.agent.motion_manager.backward(int(pwm_left), int(pwm_right))
            else:
                self.agent.motion_manager.forward(int(pwm_left), int(pwm_right))

            smooth_time = min(SMOOTH_TIME, duration / 2)
            await asyncio.sleep(duration - smooth_time)
            await self.smooth_stop(pwm_left, pwm_right, smoothing_time=smooth_time)

        async def process_command(self, command: str, override_stop: bool = False):
            """
            Parse the message body and execute the corresponding action.
            """
            command = command.strip()

            if command == "forward":
                logger.info("[Behaviour] Moving forward...")
                self.agent.motion_manager.forward(emergency_override=override_stop)
                await asyncio.sleep(STEP_DURATION)
                self.agent.motion_manager.stop(emergency_override=override_stop)

            elif command == "backward":
                logger.info("[Behaviour] Moving backward...")
                self.agent.motion_manager.backward(emergency_override=override_stop)
                await asyncio.sleep(STEP_DURATION)
                self.agent.motion_manager.stop(emergency_override=override_stop)

            elif command == "left":
                logger.info("[Behaviour] Turning left...")
                self.agent.motion_manager.left(emergency_override=override_stop)
                await asyncio.sleep(ROTATION_DURATION)
                self.agent.motion_manager.stop(emergency_override=override_stop)

            elif command == "right":
                logger.info("[Behaviour] Turning right...")
                self.agent.motion_manager.right(emergency_override=override_stop)
                await asyncio.sleep(ROTATION_DURATION)
                self.agent.motion_manager.stop(emergency_override=override_stop)

            elif command.startswith("motor "):
                try:
                    _, left, right = command.split()
                    left_speed = int(left)
                    right_speed = int(right)
                    logger.info(
                        f"[Behaviour] Setting motor speeds to {left_speed} (left) and {right_speed} (right)..."
                    )
                    self.agent.motion_manager.set_motors(left_speed, right_speed, override_stop)
                except (ValueError, IndexError):
                    logger.error("[Behaviour] Invalid motor command format. Use 'motor <left_speed> <right_speed>'")

            # rotation <angle> [duration] [pwm] [ratio]
            elif command.startswith("rotation "):
                try:
                    parts = command.split()
                    angle = float(parts[1])
                    duration = float(parts[2]) if len(parts) > 2 else None
                    pwm = int(parts[3]) if len(parts) > 3 else None
                    ratio = float(parts[4]) if len(parts) > 4 else None

                    if angle == 0:
                        angle = None
                    else:
                        duration = duration_for_angle(angle)

                    if pwm == 0:
                        pwm = None
                    if ratio == 0:
                        ratio = None

                    await self.rotate_by(angle, duration, pwm, ratio)

                except (ValueError, IndexError):
                    logger.error("[Behaviour] Invalid rotation command")

            # move <distance> [duration] [pwm] [ratio]
            elif command.startswith("move "):
                try:
                    parts = command.split()
                    distance = float(parts[1])
                    duration = float(parts[2]) if len(parts) > 2 else None
                    pwm = int(parts[3]) if len(parts) > 3 else None
                    ratio = float(parts[4]) if len(parts) > 4 else None

                    if distance == 0:
                        distance = None
                    else:
                        duration = duration_for_distance(distance)

                    if duration == 0:
                        duration = None
                    if pwm == 0:
                        pwm = None
                    if ratio == 0:
                        ratio = None

                    await self.forward_by(distance, duration, pwm, ratio)

                except (ValueError, IndexError):
                    logger.error("[Behaviour] Invalid move command")

            elif command == "stop":
                logger.info("[Behaviour] Stopping...")
                self.agent.motion_manager.stop(emergency_override=override_stop)

            # calibrate <key> <value> [value]
            elif command.startswith("calibrate "):
                try:
                    parts = command.split()
                    key = parts[1]
                    values = [float(x) for x in parts[2:]]
                    result = update_motion_config(key, values)
                    logger.info(f"[Behaviour] {result}")
                    return result
                except (ValueError, IndexError) as e:
                    logger.error(f"[Behaviour] Invalid calibrate command: {e}")
                    return f"Error: {e}"

            else:
                logger.warning(f"[Behaviour] Unknown command: {command}")

    async def setup(self):
        logger.info("[Agent] MotionAgent starting setup...")
        logger.info(f"[Agent] Will connect as {self.jid}")

        self.motion_manager = MotionManager()
        self.emergency_brake = False
        # per-side IR state, used by process_command to detect both-blocked transitions
        self.ir_left_blocked = False
        self.ir_right_blocked = False
        self.queue = asyncio.Queue()

        template = Template()
        template.set_metadata("performative", "request")
        self.add_behaviour(self.XMPPCommandListener(), template=template)

        worker_template = Template()
        worker_template.set_metadata("never", "match")
        self.add_behaviour(self.Worker(), template=worker_template)

        logger.info("[Agent] Behaviours added, setup complete.")

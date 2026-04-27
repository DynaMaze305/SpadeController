import asyncio
import os
import logging

from spade.agent import Agent, Template
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour, OneShotBehaviour
from spade.message import Message

from agent.managers.motion_manager import MotionManager
from agent.motion_models import duration_for_distance, duration_for_angle

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("MotionAgent")

# Enable SPADE and XMPP specific logging
for log_name in ["spade", "aioxmpp", "xmpp"]:
    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.propagate = True

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


class MotionAgent(Agent):
    class XMPPCommandListener(CyclicBehaviour):
        async def on_start(self):
            logger.info("[Behaviour] Ready to receive commands.")

        async def run(self):
            """
            Listen for incoming XMPP messages and process commands.
            """

            logger.info("[Behaviour] Waiting for messages...")
            msg = await self.receive(timeout=1)
            if msg:
                logger.info(f"[Behaviour] Received command ({msg.sender}):")
                logger.debug(f"\t\t{msg.body}")

                if msg.get_metadata("emergency"):
                    await self.process_command(msg)
                else:
                    await self.agent.queue.put(msg)
            else:
                logger.debug("[Behavior] No message received?!")

        async def process_command(self, msg: Message):
            """
            To process emergency commands.

            Parameter
            ---------
            msg: Message
                The emergency message.
            """
            command = msg.body

            if command.startswith("obstacles"):
                state = command.split(' ', 1)
                logger.info(f"{state}")
                if state[1] == "detected":
                    self.agent.emergency_brake = self.agent.motion_manager.emergency_stop()
                elif state[1] == "clear":
                    self.agent.emergency_brake = not self.agent.motion_manager.clear_emergency_stop()
                elif state[1] == "override":
                    self.agent.motion_manager.clear_emergency_stop()
                    self.agent.emergency_brake = False
                    return "obstacles overrided"

    class Worker(CyclicBehaviour):
        async def on_start(self):
            logger.info("[Behaviour] Ready to work.")

        async def run(self):
            """
            Execution of the waiting instructions.
            """
            msg = await self.agent.queue.get()

            keyboard_signal = msg.get_metadata("source") == "keyboard"
            try:
                response = await self.process_command(msg.body, override_stop=keyboard_signal)
            except RuntimeError as e:
                logger.error(f"[Behaviour] Worker: RuntimeError ({e})during process message:\n{msg}")
                response = f"Error: {e}"

            # Send a confirmation response
            reply = Message(to=str(msg.sender))
            reply.set_metadata("performative", "inform")
            reply.body = f"Executed command: {msg.body}\n{response}"
            await self.send(reply)
            logger.info(f"[Behaviour] Sent reply to {msg.sender}")

        # decrementing the motors to 0 instead of abrupt stop
        async def smooth_stop(self, pwm_left, pwm_right, steps=SMOOTH_STEPS, smoothing_time=SMOOTH_TIME):
            step_time = smoothing_time / steps
            for i in range(steps, 0, -1):
                left = int(abs(pwm_left) * i / steps)
                right = int(abs(pwm_right) * i / steps)
                self.agent.motion_manager.setPWM(left, right)
                await asyncio.sleep(step_time)
            self.agent.motion_manager.stop()

        # Functions that rotates the robot
        # Takes an angle in degrees as a parameter
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

            logger.info(f"[Behaviour] Rotating deg={degrees} duration={duration:.2f}s pwm={pwm_left} ratio={pwm_right/pwm_left:.3f} positive={is_positive}")

            # invert the motors for negative values
            if is_positive:
                self.agent.motion_manager.left(int(pwm_left), int(pwm_right))
            else:
                self.agent.motion_manager.right(int(pwm_left), int(pwm_right))

            # defining a smoothing value , not longer than half the duration
            smooth_time = min(SMOOTH_TIME, duration / 2)
            await asyncio.sleep(duration - smooth_time)

            # calling the modified stop to have a less abrupt stop
            await self.smooth_stop(pwm_left, pwm_right, smoothing_time=smooth_time)

        # Functions that moves the robot forward / backward
        # Takes a distance in mm as parameter
        async def forward_by(self, distance: float, duration : float = None, pwm: int = None, ratio: int = None):
            if pwm is None:
                pwm_left = FORWARD_PWM_LEFT
            else:
                pwm_left = pwm

            if ratio is None:
                pwm_right = pwm_left * LEFT_RIGHT_RATIO
            else:
                pwm_right = pwm_left * ratio

            # calculating the distance if duration is None
            if distance is None:
                is_backward = duration < 0
                duration = abs(duration)
            else:
                is_backward = distance < 0
                if duration is None:
                    duration = duration_for_distance(distance)

            logger.info(f"[Behaviour] Moving dist={distance} duration={duration:.2f}s pwm={pwm_left} ratio={pwm_right/pwm_left:.3f} backward={is_backward}")

            # invert the motors for negative values
            if is_backward:
                self.agent.motion_manager.backward(int(pwm_left), int(pwm_right))
            else:
                self.agent.motion_manager.forward(int(pwm_left), int(pwm_right))

            # defining a smoothing value , not longer than half the duration
            smooth_time = min(SMOOTH_TIME, duration / 2)
            await asyncio.sleep(duration - smooth_time)

            # calling the modified stop to have a less abrupt stop
            await self.smooth_stop(pwm_left, pwm_right, smoothing_time=smooth_time)

        async def process_command(self, command: str, override_stop: bool = False):
            """
            Process the received command and execute corresponding actions on the AlphaBot2.

            Parameters
            ----------
            command: str
                The command string received via XMPP, e.g., "forward", "backward", "left", "right", "motor 100 100", etc.
            override_stop: bool
                Override the emergency break
            """
            command = command.strip()

            if self.agent.emergency_brake and not override_stop and command not in ("stop",):
                logger.warning(f"Command '{command}' blocked — obstacle detected.")
                return

            if command == "forward":
                logger.info("[Behaviour] Moving forward...")
                self.agent.motion_manager.forward(emergency_override = override_stop)
                await asyncio.sleep(STEP_DURATION)
                self.agent.motion_manager.stop(emergency_override = override_stop)
                
            elif command == "backward":
                logger.info("[Behaviour] Moving backward...")
                self.agent.motion_manager.backward(emergency_override = override_stop)
                await asyncio.sleep(STEP_DURATION)
                self.agent.motion_manager.stop(emergency_override = override_stop)
                
            elif command == "left":
                logger.info("[Behaviour] Turning left...")
                self.agent.motion_manager.left(emergency_override = override_stop)
                await asyncio.sleep(ROTATION_DURATION)
                self.agent.motion_manager.stop(emergency_override = override_stop)
                
            elif command == "right":
                logger.info("[Behaviour] Turning right...")
                self.agent.motion_manager.right(emergency_override = override_stop)
                await asyncio.sleep(ROTATION_DURATION)
                self.agent.motion_manager.stop(emergency_override = override_stop)
                
            elif command.startswith("motor "):
                try:
                    _, left, right = command.split()
                    left_speed = int(left)
                    right_speed = int(right)
                    logger.info(f"[Behaviour] Setting motor speeds to {left_speed} (left) and {right_speed} (right)...")
                    self.agent.motion_manager.set_motors(left_speed, right_speed, override_stop)
                except (ValueError, IndexError):
                    logger.error("[Behaviour] Invalid motor command format. Use 'motor <left_speed> <right_speed>'")

            # Command for a specific rotation angle instead of left/right
            elif command.startswith("rotation "):

                # Splitting the incoming command into
                # angle
                # duration
                # pwm
                # ratio
                try:
                    parts = command.split()
                    angle = float(parts[1])
                    duration = float(parts[2]) if len(parts) > 2 else None
                    pwm = int(parts[3]) if len(parts) > 3 else None
                    ratio = float(parts[4]) if len(parts) > 4 else None

                    # calculate the angle from the linearModel
                    if angle == 0:
                        angle = None
                    else:
                        duration = duration_for_angle(angle)

                    # fallback to None (default) if value is 0
                    if pwm == 0:
                        pwm = None
                    if ratio == 0:
                        ratio = None

                    # execute the movement
                    await self.rotate_by(angle, duration, pwm, ratio)

                except (ValueError, IndexError):
                    logger.error("[Behaviour] Invalid rotation command")

            elif command.startswith("move "):
                # Splitting the incoming command into
                # distance
                # duration
                # pwm
                # ratio
                try:
                    parts = command.split()
                    distance = float(parts[1])
                    duration = float(parts[2]) if len(parts) > 2 else None
                    pwm = int(parts[3]) if len(parts) > 3 else None
                    ratio = float(parts[4]) if len(parts) > 4 else None

                    # calculate the distance from the linearModel
                    if distance == 0:
                        distance = None
                    else:
                        duration = duration_for_distance(distance)
                        logger.info("f[Behaviour] Calculated duration: {duration}")

                    # fallback to None (default) if value is 0
                    if duration == 0:
                        duration = None
                    if pwm == 0:
                        pwm = None
                    if ratio == 0:
                        ratio = None

                    # Execute the movement
                    await self.forward_by(distance, duration, pwm, ratio)

                except (ValueError, IndexError):
                    logger.error("[Behaviour] Invalid move command")

            elif command == "stop":
                logger.info("[Behaviour] Stopping...")
                self.agent.motion_manager.stop(emergency_override = override_stop)

            else:
                logger.warning(f"[Behaviour] Unknown command: {command}")

    async def setup(self):
        """
        Setup the agent and add its behaviors.
        """
        logger.info("[Agent] MotionAgent starting setup...")
        logger.info(f"[Agent] Will connect as {self.jid}")

        self.motion_manager = MotionManager()
        self.emergency_brake = False
        self.queue = asyncio.Queue()

        # Add command listener behaviour
        template = Template()
        template.set_metadata("performative", "request")
        self.add_behaviour(self.XMPPCommandListener(), template=template)

        # Add worker
        worker_template = Template()
        worker_template.set_metadata("never", "match")
        self.add_behaviour(self.Worker(), template=worker_template)


        logger.info("[Agent] Behaviours added, setup complete.")
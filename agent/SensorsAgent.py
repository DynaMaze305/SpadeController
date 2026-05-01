import asyncio
import json
import logging
import os
import time

from spade.agent import Agent, Template
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour, OneShotBehaviour
from spade.message import Message

from agent.managers.sensors_manager import SensorsManager
from agent.managers.motion_manager import MotionManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("SensorsAgent")

# Enable SPADE and XMPP specific logging
for log_name in ["spade", "aioxmpp", "xmpp"]:
    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.propagate = True

class SensorsAgent(Agent):
    def __init__(self, motion_jid: str, period_sensors: float, period_emergency: float, jid: str, password: str, verify_security = False):
        """
        Create the SensorsAgent for an AlphaBot2-Pi.

        Parameters
        ----------
        motion_jid: str
            The identifier of the motion agent for emergency brake.
        period_sensors: float
            The interval in second for the measure of the sensors (not the emergency one).
        period_emergency: float
            The interval in second for the measure of the emergency sensors.
        jid : str
            The identifier of the agent in the form username@server
        password : str
            The password to connect to the server
        verify_security : bool
            Whether to verify or not the SSL certificates
        """
        super().__init__(jid, password, verify_security)
        self.motion_jid = motion_jid
        self.period_sensors = period_sensors
        self.period_emergency = period_emergency

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

                await self.agent.queue.put(msg)
            else:
                logger.debug("[Behavior] No message received?!")

    class Worker(CyclicBehaviour):
        async def on_start(self):
            logger.info("[Behaviour] Ready to work.")

        async def run(self):
            msg = await self.agent.queue.get()

            try:
                response = await self.process_msg(msg)
            except RuntimeError as e:
                logger.error(f"[Behaviour] Worker: RuntimeError ({e})during process message:\n{msg}")
                response = f"Error: {e}"

            reply = Message(to=str(msg.sender))
            reply.set_metadata("performative", "inform")
            reply.body = f"Executed command: {msg.body}\n{response}"
            await self.send(reply)
            logger.info(f"[Behaviour] Sent reply to {msg.sender}")

        async def process_msg(self, msg: Message):
            """
            Process the received command and execute corresponding actions on the AlphaBot2.

            Parameter
            ---------
            command: str
                The command string received via XMPP, e.g., "register" "data" "battery" "sensor <sensor_type> <sensor_id>" "sensors <sensor_type> <sensor_id> <sensor_type> <sensor_id> ..."
            """
            command = msg.body.strip()

            if command == "register":
                sender = str(msg.sender.bare)
                if sender not in self.agent.register_list:
                    self.agent.register_list.append(sender)
                    logger.info(f"[Agent] Registered dashboard: {sender}")
                    return "sensors register done"
                return "sensors register already"


            elif command == "data":
                if self.agent.data is not None:
                    return json.dumps({"data": self.agent.data})
                self.agent.queue.put(msg)

            elif command == "battery":
                value = self.agent.sensors_manager.get_battery_level()
                return f"battery {value}"

            elif command.startswith("sensor "):
                parts = command.split()
                if len(parts) != 3:
                    logger.error(f"[Behaviour] Invalid sensor command format: {command}")
                    return f"invalid sensor {command}"
                try:
                    sensor_type = parts[1]
                    sensor_id = int(parts[2])
                    if sensor_type == "digital":
                        if sensor_id in [1,2]:
                            value = self.agent.sensors_manager.get_digital_sensor_value(sensor_id)
                        else:
                            raise ValueError(f"{sensor_type} {sensor_id}")
                    elif sensor_type == "analog":
                        if sensor_id in [0,1,2,3,4,10]:
                            value = self.agent.sensors_manager.get_analog_sensor_value(sensor_id)
                        else:
                            raise ValueError(f"{sensor_type} {sensor_id}")
                    return f"value {sensor_type} {sensor_id} {value}"

                except ValueError as e:
                    logger.error(f"[Behaviour] Invalid sensor id: {e}")
                    return f"invalid sensor {command}"

                except Exception as e:
                    logger.exception(f"[Behaviour] Unexpected error while reading sensor: {e}")

            elif command.startswith("sensors "):
                parts = command.split()

                # Expect: sensors type id type id ...
                if (len(parts) - 1) % 2 != 0:
                    logger.error(f"[Behaviour] Invalid sensors command format: {command}")
                    return f"invalide sensors {command}"

                count = (len(parts) - 1) // 2
                response = "value"

                for i in range(count):
                    base = 1 + 2 * i
                    try:
                        sensor_type = parts[base]
                        sensor_id = int(parts[base + 1])
                        if sensor_type == "digital":
                            if sensor_id in [1,2]:
                                value = self.agent.sensors_manager.get_digital_sensor_value(sensor_id)
                            else:
                                raise ValueError(f"{sensor_type} {sensor_id}")
                        elif sensor_type == "analog":
                            if sensor_id in [0,1,2,3,4,10]:
                                value = self.agent.sensors_manager.get_analog_sensor_value(sensor_id)
                            else:
                                raise ValueError(f"{sensor_type} {sensor_id}")
                        response += f" {sensor_type} {sensor_id} {value}"

                    except ValueError as e:
                        logger.error(f"[Behaviour] Invalid sensor id: {e}")
                        return f"invalid sensor{i} {command}"

                    except Exception as e:
                        logger.exception(f"[Behaviour] Unexpected error while reading sensor: {e}")

                return response

            else:
                logger.warning(f"[Behaviour] Unknown command: {command}")
                return f"error {command}"

    class ReadSensors(PeriodicBehaviour):
        async def on_start(self):
            logger.info(f"[Behaviour] ReadSensors running every {self.period}s.")

        async def run(self):
            # Read digital + analog sensors
            for sensor_type in ["digital", "analog"]:
                for sensor_id in self.agent.data[sensor_type]:
                    if sensor_type == "digital":
                        self.agent.data["digital"][sensor_id] = self.agent.sensors_manager.get_digital_sensor_value(sensor_id)
                    else:
                        self.agent.data["analog"][sensor_id] = self.agent.sensors_manager.get_analog_sensor_value(sensor_id)

            # Battery
            self.agent.data["battery"] = self.agent.sensors_manager.get_battery_level()

            # Motion
            self.agent.data["motion"] = self.agent.motion_manager.read_motion_status()

            logger.debug(f"[Behaviour] Updated sensor data: {self.agent.data}")

            # Broadcast
            self.agent.add_behaviour(self.agent.BroadcastData())

    class ReadEmergencySensors(PeriodicBehaviour):
        def __init__(self, period, start_at = None):
            super().__init__(period, start_at)
            self.emergency_right = False
            self.emergency_left = False

        async def on_start(self):
            logger.info(f"[Behaviour] Emergency sensors every {self.period}s.")

        async def run(self):
            right, left = self.agent.sensors_manager.get_ioa()

            # RIGHT
            if right == 0 and not self.emergency_right:
                self.emergency_right = True
                await self.send_emergency("right")
            elif right == 1 and self.emergency_right:
                self.emergency_right = False
                await self.send_emergency_clear("right")

            # LEFT
            if left == 0 and not self.emergency_left:
                self.emergency_left = True
                await self.send_emergency("left")
            elif left == 1 and self.emergency_left:
                self.emergency_left = False
                await self.send_emergency_clear("left")

        async def send_emergency(self, side: str):
            msg = Message(to=self.agent.motion_jid)
            msg.set_metadata("performative", "request")
            msg.set_metadata("emergency", side)
            msg.body = f"obstacles detected"
            await self.send(msg)
            logger.info(f"[Behaviour] Sent emergency to {msg.to}")

        async def send_emergency_clear(self, side: str):
            msg = Message(to=self.agent.motion_jid)
            msg.set_metadata("performative", "request")
            msg.set_metadata("emergency", side)
            if self.emergency_left or self.emergency_right:
                msg.body = f"obstacles still"
            else:
                msg.body = f"obstacles clear"
            await self.send(msg)
            logger.info(f"[Behaviour] Sent emergency clear to {msg.to}")

    class BroadcastData(OneShotBehaviour):
        async def on_start(self):
            logger.info("[Behaviour] Broadcasting sensors...")

        async def run(self):
            if not self.agent.data:
                logger.debug("[Behaviour] No data to broadcast.")
                return
            payload = json.dumps({
                "type": "data",
                "bot": str(self.agent.jid),
                "ts": time.time(),
                "data": self.agent.data
            })

            for jid in self.agent.register_list:
                msg = Message(to=jid)
                msg.set_metadata("performative", "inform")
                msg.body = payload
                await self.send(msg)

        async def on_end(self):
            logger.info("[Behaviour] Data broadcast complete.")

    async def setup(self):
        logger.info("[Agent] SensorsAgent starting setup...")
        logger.info(f"[Agent] Connecting as {self.jid}")

        self.sensors_manager = SensorsManager()
        self.motion_manager = MotionManager()
        self.register_list = []
        self.data = {
            "digital": {
                1: None,    # Right Infrared
                2: None     # Left  Infrared
            },
            "analog": {
                0: None,    # IR Line most left
                1: None,    # IR Line left
                2: None,    # IR Line center
                3: None,    # IR Line right
                4: None,    # IR Line most right
                10: None,   # Battery measure (divider)
            }
        }

        # Queue for worker
        self.queue = asyncio.Queue()

        # Command listener
        template = Template()
        template.set_metadata("performative", "request")
        self.add_behaviour(self.XMPPCommandListener(), template)

        # Worker
        worker_template = Template()
        worker_template.set_metadata("never", "match")
        self.add_behaviour(self.Worker(), worker_template)

        # Emergency sensors
        logger.info(f"[Agent] Will provide emergency to {self.motion_jid}")
        self.add_behaviour(self.ReadEmergencySensors(period=self.period_emergency), worker_template)

        # Regular sensors
        self.add_behaviour(self.ReadSensors(period=self.period_sensors), worker_template)

        logger.info("[Agent] SensorsAgent setup complete.")

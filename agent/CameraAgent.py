import asyncio
import logging

from spade.agent import Agent, Template
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message

from agent.managers.camera_manager import CameraManager
from rpi_ws281x import Color

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("CameraAgent")

# Enable SPADE and XMPP specific logging
for log_name in ["spade", "aioxmpp", "xmpp"]:
    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.propagate = True

class CameraAgent(Agent):
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

                await self.queue.put(msg)
            else:
                logger.debug("[Behavior] No message received?!")

    class Worker(CyclicBehaviour):
        async def on_start(self):
            logger.info("[Behaviour] Ready to work.")

        async def run(self):
            """
            Execution of the waiting instructions.
            """
            msg = await self.agent.queue.get()

            try:
                response = await self.process_command(msg.body)
            except RuntimeError as e:
                logger.error(f"[Behaviour] Worker: RuntimeError ({e})during process message:\n{msg}")
                response = f"Error: {e}"

            # Send a confirmation response
            reply = Message(to=str(msg.sender))
            reply.set_metadata("performative", "inform")
            reply.body = f"Executed command: {msg.body}\n{response}"
            await self.send(reply)
            logger.info(f"[Behaviour] Sent reply to {msg.sender}")

        async def process_command(self, command:str):
            """
            Process the received command and execute corresponding actions.

            Parameter
            ----------
            command: str
                The command string received via XMPP, e.g., "forward", "backward", "left", "right", "motor 100 100", etc.
            """
            command = command.strip().lower()
            # -----------------------------
            # Streaming commands (Currently in development)
            # -----------------------------
            if command == "start_stream":
                if self.agent.camera_agent.running:
                    logger.warning("[Behaviour] Stream is already running")
                    return
                self.agent.camera_agent.start_stream()
                logger.info("[Behaviour] Camera stream started")
                return "stream started"

            elif command == "stop_stream":
                if not self.agent.camera_agent.running:
                    logger.warning("[Behaviour] Stream is not running")
                    return
                self.agent.camera_agent.stop_stream()
                logger.info("[Behaviour] Camera stream stopped")
                return "stream stopped"

            elif command == "stream_connexion":
                logger.info("[Behaviour] Providing stream connection info")
                return

            elif command == "get_frame":
                frame = self.agent.camera_agent.get_jpeg_frame()
                if frame:
                    logger.info(f"[Behaviour] Retrieved JPEG frame")
                    return f"frame {str(frame)}"
                else:
                    logger.warning("[Behaviour] No frame available, check if stream is running")
            
            # -----------------------------
            # Still capture command
            # -----------------------------
            elif command == "capture_still":
                img_data = self.agent.camera_agent.capture_still()
                logger.info(f"[Behaviour] Captured still image")
                return f"image {str(img_data)}"
            
            # -----------------------------
            # Led commands
            # -----------------------------
            elif command.startswith("led "):
                parts = command.split()
                if len(parts) != 5:
                    logger.error(f"[Behaviour] Invalid LED command format: {command}")
                    return f"invalid led {command}"
                try:
                    led_id = int(parts[1])
                    r = int(parts[2])
                    g = int(parts[3])
                    b = int(parts[4])

                    # clamp or validate RGB
                    for name, value in (("r", r), ("g", g), ("b", b)):
                        if not 0 <= value <= 255:
                            raise ValueError(f"{name} {value}")

                    logger.info(f"[Behaviour] Set LED ({led_id}) to ({r}, {g}, {b})")
                    self.agent.camera_manager.set_led(led_id, Color(r, g, b))

                except ValueError as e:
                    logger.error(f"[Behaviour] Invalid LED parameters: {e} out of range 0-255")
                    return f"invalid led {command} {e}"

                except Exception as e:
                    logger.exception(f"[Behaviour] Unexpected error while setting LED: {e}")
                    return f"error led {command} {e}"

            elif command.startswith("leds "):
                parts = command.split()

                # Expect: leds id r g b id r g b ...
                if (len(parts) - 1) % 4 != 0:
                    logger.error(f"[Behaviour] Invalid LED command format: {command}")
                    return f"invalide led {command}"

                count = (len(parts) - 1) // 4
                cmd = []

                for i in range(count):
                    base = 1 + 4 * i
                    try:
                        led_id = int(parts[base])
                        r = int(parts[base + 1])
                        g = int(parts[base + 2])
                        b = int(parts[base + 3])

                        # Validate RGB
                        for name, value in (("r", r), ("g", g), ("b", b)):
                            if not 0 <= value <= 255:
                                raise ValueError(f"{name} {value}")

                        logger.info(f"[Behaviour] Set LED ({led_id}) to ({r}, {g}, {b})")
                        cmd.append([led_id,r, g,b])

                    except ValueError as e:
                        logger.error(f"[Behaviour] Invalid LED parameters for block {i}: {e}")
                        return f"invalide led{i} {command} {e}"

                    except Exception as e:
                        logger.exception(f"[Behaviour] Unexpected error while setting LED {i}: {e}")
                        return f"error led{i} {command} {e}"

                for led_id, r, g, b in cmd:
                    self.agent.camera_manager.set_led(led_id, Color(r, g, b))


            else:
                logger.warning(f"[Behaviour] Unknown command: {command}")
            return None

    async def setup(self):
        """
        Setup the agent and add its behaviors.
        """
        logger.info("[Agent] CameraAgent starting setup...")
        logger.info(f"[Agent] Will connect as {self.jid}")

        self.camera_manager = CameraManager()

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
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message

import logging
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestCameraReceiver")

# Enable SPADE and XMPP specific logging
for log_name in ["spade", "aioxmpp", "xmpp"]:
    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.propagate = True

class TestCameraReceiver(Agent):
    def __init__(self, camera_jid, jid, password, verify_security=False):
        super().__init__(jid, password, verify_security=verify_security)
        self.tunnel = None
        self.camera_jid = camera_jid
        logger.info(f"[Agent] Initialized with JID: {jid} and camera JID: {camera_jid}")

    class XMPPCommandListener(CyclicBehaviour):
        async def on_start(self):
            logger.info("[Behaviour] XMPPCommandListener started")

        async def run(self):
            logger.debug("[Behaviour] Waiting for XMPP command...")
            msg = await self.receive(timeout=10)
            if msg:
                logger.debug(f"[Behaviour] Received message from {msg.sender}")
                command = msg.body
                request = await self.process_command(command)
                if request:
                    reply = Message(to=str(msg.sender.bare))
                    reply.set_metadata("performative", "request")
                    reply.body = request
                    await self.send(reply)
            else:
                logger.debug("[Behaviour] No message received within timeout")
            
            logger.debug("[Behaviour] Sleep XMPP listener")
        
        async def process_command(self, command):
            command = command.strip()
            if command.startswith("image"):
                logger.info("[Behaviour] Processing 'image' command")
                _, data = command.split(" ", 1)
                filename = f"./agent/camera_receiver.jpg"
                with open(filename, "wb") as f:
                    f.write(base64.b64decode(data))
                logger.info(f"[Behaviour] Image successfully saved at {filename}")
                return None
            
            # -----------------------------
            # STREAMING (Currently in development)
            # -----------------------------
            elif command.startswith("stream"):
                _, response = command.split(" ", 1)
                if response == "started":
                    logger.info(f"[Behaviour] Tunel ssh for stream started")
                    return "stream_connexion"
                elif response == "stopped":
                    self.agent.tunel = None
                    logger.info(f"[Behaviour] Tunel ssh for stream stopped")
                    return None
            
            elif command.startswith("tunel_ssh"):
                _, response = command.split(" ", 1)
                self.agent.tunel = response
                logger.info(f"[Behaviour] Tunel ssh for stream on {response}")
                return None

            else:
                logger.warning(f"[Behaviour] Unknown command: {command}")
            return None
    
    class TestRequestPhoto(OneShotBehaviour):
        async def on_start(self):
            logger.info("[Behaviour] TestRequestPhoto started")

        async def run(self):
            logger.info("[Behaviour] Sending photo request to camera agent")
            msg = Message(to=self.agent.camera_jid)
            msg.set_metadata("performative", "request")
            msg.body = "capture_still"
            await self.send(msg)
            logger.info("[Behaviour] Photo request sent")

    class TestRequestStream(OneShotBehaviour):
        async def on_start(self):
            logger.info("[Behaviour] TestRequestStream started")
        
        async def run(self):
            logger.info("[Behaviour] Sending photo request to camera agent")
            msg = Message(to=self.agent.camera_jid)
            msg.set_metadata("performative", "request")
            msg.body = "start_stream"
            await self.send(msg)
            logger.info("[Behaviour] Photo request sent")


    async def setup(self):
        logger.info("[Agent] CameraAgent is starting...")

        # Add the XMPP command listener behaviour
        self.add_behaviour(self.XMPPCommandListener())

        # Test: Add a behaviour to request a photo from the camera agent after startup
        # self.add_behaviour(self.TestRequestPhoto())

        logger.info("[Agent] CameraAgent setup complete")

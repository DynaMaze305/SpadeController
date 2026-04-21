from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour, OneShotBehaviour
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour, OneShotBehaviour
from spade.message import Message
import asyncio
import os
import time
import logging

import base64
from picamera2 import Picamera2
from io import BytesIO
from PIL import Image


# from agent.alphabotlib.camera import StillCamera
# from agent.alphabotlib.servo import ServoController

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("CameraAgent")

# Enable SPADE and XMPP specific logging
for log_name in ["spade", "aioxmpp", "xmpp"]:
    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.propagate = True

class CameraAgent(Agent):
    def __init__(self, jid: str, password: str, verify_security: bool = False):
        super().__init__(jid=jid, password=password, verify_security=verify_security)
        logger.info("[Agent] Initializing CameraAgent...")
        # self.still = StillCamera()
        # self.servo = ServoController(pin_pan=17, pin_tilt=27)
        self.cam = None
        self.initialized = False

        try:
            logger.info("[Agent] Initializing Picamera2...")
            self.cam = Picamera2()
            self.cam.configure(self.cam.create_still_configuration())
            self.initialized = True
            logger.info("[Agent] Picamera2 initialized successfully.")

        except Exception as e:
            logger.error(f"[Agent] Camera initialization failed: {e}")
            logger.error("[Agent] CameraAgent will run WITHOUT camera support.")
            self.cam = None
            self.initialized = False
        
        logger.info("[Agent] CameraAgent initialization complete.")

    class XMPPCommandListener(CyclicBehaviour):
        async def on_start(self):
            logger.info("[Behaviour] Camera command listener started.")
        
        async def run(self):
            msg = await self.receive(timeout=10)
            logger.info(f"[Behaviour] Received message: {msg}")
            if msg:
                logger.info(f"[Behaviour] Received command: {msg.body}")
                response = await self.process_message(str(msg.body))
                if response is not None:
                    reply = Message(to=msg.sender)
                    reply.set_metadata("performative", "inform")
                    reply.body = str(response)
                    await self.send(reply)
                    logger.info(f"[Behaviour] Sent response: {response}")

        async def process_message(self, command):
            command = command.strip().lower()
            if command == "photo":
                logger.info("[Behaviour] Processing photo command...")
                if self.agent.initialized:
                    try:
                        logger.info("[Behaviour] Capturing photo...")
                        self.agent.cam.start()
                        time.sleep(2)  # Allow camera to warm up
                        img = self.agent.cam.capture_array()
                        self.agent.cam.stop()

                        # Encode image to base64
                        buffer = BytesIO()
                        Image.fromarray(img).save(buffer, format="JPEG")
                        data = buffer.getvalue()

                        filename = f"./agent/photo_{int(time.time())}.jpg"
                        with open(filename, "wb") as f:
                            f.write(data)

                        img_str = base64.b64encode(data).decode()
                        logger.info("[Behaviour] Photo captured and encoded successfully.")
                        return img_str
                    except Exception as e:
                        logger.error(f"[Behaviour] Failed to capture photo: {e}")
                        return "Error capturing photo"
                else:
                    logger.warning("[Behaviour] Camera not initialized, cannot capture photo.")
                    return "Camera not available"
                # return self.still.capture_jpg()

            if command.startswith("pan "):
                angle = int(command.split()[1])
                # self.servo.set_pan(angle)

            if command.startswith("tilt "):
                angle = int(command.split()[1])
                # self.servo.set_tilt(angle)

            if command == "stream":
                return "http://<robot-ip>:8000/stream"
            
            return None
    
    class TESTPeriodicPhoto(PeriodicBehaviour):
        def __init__(self, period=30):
            super().__init__(period)
            self.ctn = 0

        async def on_start(self):
            await asyncio.sleep(2)  # wait for XMPP connection
        
        async def run(self):
            self.ctn += 1
            logger.info(f"[Behaviour] Taking photo {self.ctn}")
            await self.request_photo()

        async def request_photo(self):
            logger.info("[Behaviour] Requesting photo from self for testing...")
            logger.info(f"[Behaviour] self address: {self.agent.jid.bare}")
            msg = Message(to=self.agent.jid.bare)   # Send to self for testing
            msg.set_metadata("performative", "request")
            msg.body = "photo"
            logger.info("#######################################################")
            logger.info(f"[Behaviour] Photo request sent, waiting for response...")
            logger.info(msg)
            await self.send(msg)


    async def setup(self):
        logger.info("[Agent] Setting up CameraAgent...")
        if self.initialized is False:
            logger.error("[Agent] Camera initialization failed.")
            return

        command_listener = self.XMPPCommandListener()
        self.add_behaviour(command_listener)

        self.add_behaviour(self.TESTPeriodicPhoto(period=60), template=None)

        logger.info("[Agent] CameraAgent is ready to receive commands.")


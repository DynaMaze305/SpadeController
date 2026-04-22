from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

import logging

import subprocess

from agent.managers.camera_manager import CameraManager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CameraAgent")

# Enable SPADE and XMPP specific logging
for log_name in ["spade", "aioxmpp", "xmpp"]:
    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.propagate = True

class CameraAgent(Agent):
    def __init__(self, ssh_user, ssh_server, jid, password, verify_security=False):
        super().__init__(jid, password, verify_security=verify_security)
        self.ssh_user = ssh_user
        self.ssh_server = ssh_server
        self.cam = CameraManager()
        self.tunnel = None

    class XMPPCommandListener(CyclicBehaviour):
        async def on_start(self):
            if self.agent.tunnel is None:
                self.agent.tunnel = subprocess.Popen([
                    "ssh", "-N",
                    "-R", "8080:localhost:8000",
                    f"{self.agent.ssh_user}@{self.agent.ssh_server}"
                ])
                logger.info("[Behaviour] SSH tunnel is active")
            logger.info("[Behaviour] XMPPCommandListener started")

        async def run(self):
            logger.info("[Behaviour] Waiting for XMPP command...")
            msg = await self.receive(timeout=10)
            if msg:
                logger.info(f"[Behaviour] Received message from {msg.sender}")
                command = msg.body
                response = await self.process_command(command)
                if response:
                    reply = Message(to=str(msg.sender.bare))
                    reply.set_metadata("performative", "inform")
                    reply.body = response
                    await self.send(reply)
            else:
                logger.info("[Behaviour] No message received within timeout")
        
        async def process_command(self, command):
            command = command.strip().lower()
            # -----------------------------
            # Streaming commands
            # -----------------------------
            if command == "start_stream":
                if self.agent.cam.running:
                    logger.warning("[Behaviour] Stream is already running")
                    return
                self.agent.cam.start_stream()
                logger.info("[Behaviour] Camera stream started")
                return "stream started"

            elif command == "stop_stream":
                if not self.agent.cam.running:
                    logger.warning("[Behaviour] Stream is not running")
                    return
                self.agent.cam.stop_stream()
                logger.info("[Behaviour] Camera stream stopped")
                return "stream stopped"

            elif command == "stream_connexion":
                if self.agent.tunnel is None:
                    logger.warning("[Behaviour] SSH tunnel is not active")
                    return
                logger.info("[Behaviour] Providing stream connection info")
                return f"tunel_ssh http://{self.agent.ssh_server}:8080"

            elif command == "get_frame":
                frame = self.agent.cam.get_jpeg_frame()
                if frame:
                    logger.info(f"[Behaviour] Retrieved JPEG frame")
                    return f"frame {str(frame)}"
                else:
                    logger.warning("[Behaviour] No frame available, check if stream is running")
            
            # -----------------------------
            # Still capture command
            # -----------------------------
            elif command == "capture_still":
                img_data = self.agent.cam.capture_still()
                logger.info(f"[Behaviour] Captured still image")
                return f"image {str(img_data)}"
            else:
                logger.warning(f"[Behaviour] Unknown command: {command}")
            return None

    async def setup(self):
        logger.info("[Agent] CameraAgent is starting...")

        # Add the XMPP command listener behaviour
        self.add_behaviour(self.XMPPCommandListener())

        logger.info("[Agent] CameraAgent setup complete")

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour, OneShotBehaviour
from spade.message import Message
from agent.alphabotlib.AlphaBot2 import AlphaBot2
import asyncio
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("AlphaBotAgent")

# Enable SPADE and XMPP specific logging
for log_name in ["spade", "aioxmpp", "xmpp"]:
    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.propagate = True

class AlphaBotAgent(Agent):
    def __init__(self, nav_recipent, jid, password, verify_security=False):
        super().__init__(jid, password, verify_security=verify_security)
        self.nav_recipent = nav_recipent

    class XMPPCommandListener(CyclicBehaviour):
        STEP_DURATION = 0.5
        ROTATION_DURATION = 0.18
        ROTATION_DEG_PER_SEC = 500

        async def on_start(self):
            logger.info("[Behaviour] Initializing AlphaBot2...")
            self.ab = AlphaBot2()
            logger.info("[Behaviour] Ready to receive commands.")
            
        async def run(self):
            logger.debug("[Behaviour] Waiting for messages...")
            msg = await self.receive(timeout=10)
            if msg:
                logger.info(f"[Behaviour] Received command ({msg.sender}): {msg.body}")
                await self.process_command(msg.body, str(msg.sender))

                # Send a confirmation response
                reply = Message(to=str(msg.sender))
                reply.set_metadata("performative", "inform")
                reply.body = f"Executed command: {msg.body}"
                await self.send(reply)
                logger.info(f"[Behaviour] Sent reply to {msg.sender}")
            else:
                logger.debug("[Behaviour] No message received during timeout.")
        
        async def rotate_by(self, degrees: float):
            duration = abs(degrees) / self.ROTATION_DEG_PER_SEC

            logger.info(f"[Behavior] Rotating {degrees:+.1f} deg (duration={duration:.2f}s)")

            if degrees > 0:
                self.ab.left()
            else:
                self.ab.right()

            await asyncio.sleep(duration)
            self.ab.stop()

        async def process_command(self, command, sender):
            command = command.strip().lower()
            
            if command == "forward":
                logger.info("[Behaviour] Moving forward...")
                self.ab.forward()
                await asyncio.sleep(self.STEP_DURATION)
                self.ab.stop()
                
            elif command == "backward":
                logger.info("[Behaviour] Moving backward...")
                self.ab.backward()
                await asyncio.sleep(self.STEP_DURATION)
                self.ab.stop()
                
            elif command == "left":
                logger.info("[Behaviour] Turning left...")
                self.ab.left()
                await asyncio.sleep(self.ROTATION_DURATION)
                self.ab.stop()
                
            elif command == "right":
                logger.info("[Behaviour] Turning right...")
                self.ab.right()
                await asyncio.sleep(self.ROTATION_DURATION)
                self.ab.stop()
                
            elif command.startswith("motor "):
                try:
                    _, left, right = command.split()
                    left_speed = int(left)
                    right_speed = int(right)
                    logger.info(f"[Behaviour] Setting motor speeds to {left_speed} (left) and {right_speed} (right)...")
                    self.ab.setMotor(left_speed, right_speed)
                    await asyncio.sleep(self.STEP_DURATION)
                    self.ab.stop()
                except (ValueError, IndexError):
                    logger.error("[Behaviour] Invalid motor command format. Use 'motor <left_speed> <right_speed>'")
                    logger.error("[Behavior] Invalid motor command format. Use 'motor <left_speed> <right_speed>'")

            elif command.startswith("rotation "):
                try:
                    angle = float(command.split()[1])
                    await self.rotate_by(angle)
                except (ValueError, IndexError):
                    logger.error("[Behavior] Invalid rotation command. Use 'rotation <degrees>'")

            elif command == "stop":
                logger.info("[Behaviour] Stopping...")
                self.ab.stop()
            
            elif command == "init":
                logger.info("[Behaviour] Start robot.")
                #self.agent.add_behaviour(self.agent.XMPPPathRequest(self.nav_recipent))

            elif command.startswith("instructions "):
                instructions = command.split()
                self.agent.add_behaviour(self.agent.XMPPExecutePath(instructions[1:]))

            else:
                logger.warning(f"[Behaviour] Unknown command: {command}")

    class XMPPPathRequest(OneShotBehaviour):
        def __init__(self, target):
            super().__init__()
            self.target = target
            logger.info("[Behaviour] Ready to request a path.")
        
        async def run(self):
            logger.info("[Behaviour] Sending path request...")
            msg = Message(to=self.target)
            msg.set_metadata("performative", "request")
            msg.body = "request path"

            await self.send(msg)
            logger.info("[Behaviour] Request send.")

    class XMPPExecutePath(PeriodicBehaviour):
            def __init__(self, instructions):
                super().__init__(period=1)
                self.instructions = instructions
                logger.info("[Behaviour] Ready to execute instructions.")

            async def run(self):
                if not self.instructions:
                    logger.info("[Behavior] Path complete.")
                    self.kill()
                    return

                step = self.instructions.pop(0)
                logger.info(f"[Behavior] Dispatching step to listener: {step}")
                msg = Message(to=str(self.agent.jid))
                msg.set_metadata("performative", "inform")
                msg.body = step
                await self.send(msg)


    async def setup(self):
        logger.info("[Agent] AlphaBotAgent starting setup...")
        logger.info(f"[Agent] Will connect as {self.jid} to server {os.environ.get('XMPP_SERVER', 'prosody')}")
        
        # Add command listener behaviour
        command_behaviour = self.XMPPCommandListener()
        self.add_behaviour(command_behaviour)

        # Add first init request
        # init_request = self.XMPPPathRequest(self.nav_recipent)
        # self.add_behaviour(init_request)
        
        logger.info("[Agent] Behaviours added, setup complete.")

import asyncio

async def main():
    xmpp_domain = os.environ.get("XMPP_DOMAIN", "prosody")
    xmpp_username = os.environ.get("XMPP_USERNAME", "alpha-pi-zero-agent")
    xmpp_jid = f"{xmpp_username}@{xmpp_domain}"
    xmpp_password = os.environ.get("XMPP_PASSWORD", "top_secret")

    nav_recipent = os.environ.get("NAV_RECIPENT", "navigator@isc-coordinator.lan")
    
    logger.info("Starting AlphaBot XMPP Agent")
    logger.info(f"XMPP JID: {xmpp_jid}")
    logger.info(f"XMPP Password: {'*' * len(xmpp_password)}")
    
    try:
        agent = AlphaBotAgent(
            nav_recipent=nav_recipent,
            jid=xmpp_jid, 
            password=xmpp_password,
            verify_security=False
        )
        
        logger.info("Agent created, attempting to start...")
        await agent.start(auto_register=True)
        logger.info("Agent started successfully!")
        
        try:
            while agent.is_alive():
                logger.debug("Agent is alive and running...")
                await asyncio.sleep(10)  # Log every 10 seconds that agent is alive
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            await agent.stop()
            logger.info("Agent stopped by user.")
    except Exception as e:
        logger.error(f"Error starting agent: {str(e)}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Critical error in main loop: {str(e)}", exc_info=True)

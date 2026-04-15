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

        async def on_start(self):
            logger.info("[Behavior] Initializing AlphaBot2...")
            self.ab = AlphaBot2()
            logger.info("[Behavior] Ready to receive commands.")
            
        async def run(self):
            logger.debug("[Behavior] Waiting for messages...")
            msg = await self.receive(timeout=10)
            if msg:
                logger.info(f"[Behavior] Received command ({msg.sender}): {msg.body}")
                await self.process_command(msg.body, str(msg.sender))

                # Only ack real commands, not informs (prevents echo loops)
                if msg.get_metadata("performative") != "inform":
                    reply = Message(to=str(msg.sender))
                    reply.set_metadata("performative", "inform")
                    reply.body = f"Executed command: {msg.body}"
                    await self.send(reply)
                    logger.info(f"[Behavior] Sent reply to {msg.sender}")
            else:
                logger.debug("[Behavior] No message received during timeout.")
        
        async def process_command(self, command, sender):
            command = command.strip().lower()
            
            if command == "forward":
                logger.info("[Behavior] Moving forward...")
                self.ab.forward()
                await asyncio.sleep(self.STEP_DURATION)
                self.ab.stop()
                
            elif command == "backward":
                logger.info("[Behavior] Moving backward...")
                self.ab.backward()
                await asyncio.sleep(self.STEP_DURATION)
                self.ab.stop()
                
            elif command == "left":
                logger.info("[Behavior] Turning left...")
                self.ab.left()
                await asyncio.sleep(self.ROTATION_DURATION)
                self.ab.stop()
                
            elif command == "right":
                logger.info("[Behavior] Turning right...")
                self.ab.right()
                await asyncio.sleep(self.ROTATION_DURATION)
                self.ab.stop()
                
            elif command.startswith("motor "):
                try:
                    _, left, right = command.split()
                    left_speed = int(left)
                    right_speed = int(right)
                    logger.info(f"[Behavior] Setting motor speeds to {left_speed} (left) and {right_speed} (right)...")
                    self.ab.setMotor(left_speed, right_speed)
                    await asyncio.sleep(self.STEP_DURATION)
                    self.ab.stop()
                except (ValueError, IndexError):
                    logger.error("[Behavior] Invalid motor command format. Use 'motor <left_speed> <right_speed>'")
                    
            elif command == "stop":
                logger.info("[Behavior] Stopping...")
                self.ab.stop()
            
            elif command == "init":
                logger.info("[Behavior] Start robot.")
                #self.agent.add_behaviour(self.agent.XMPPPathRequest(self.nav_recipent))

            elif command.startswith("instructions "):
                instructions = command.split()
                self.agent.add_behaviour(self.agent.XMPPExecutePath(instructions[1:]))

            else:
                logger.warning(f"[Behavior] Unknown command: {command}")

    class XMPPPathRequest(OneShotBehaviour):
        def __init__(self, target):
            super().__init__()
            self.target = target
            logger.info("[Behavior] Ready to request a path.")
        
        async def run(self):
            logger.info("[Behavior] Sending path request...")
            msg = Message(to=self.target)
            msg.set_metadata("performative", "request")
            msg.body = "request path"

            await self.send(msg)
            logger.info("[Behavior] Request send.")

    class XMPPExecutePath(PeriodicBehaviour):
            def __init__(self, instructions):
                super().__init__(period=1)
                self.instructions = instructions
                logger.info("[Behavior] Ready to execute instructions.")

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
        
        # Add command listener behavior
        command_behavior = self.XMPPCommandListener()
        self.add_behaviour(command_behavior)

        # Add first init request
        init_request = self.XMPPPathRequest(self.nav_recipent)
        self.add_behaviour(init_request)
        
        logger.info("[Agent] Behaviors added, setup complete.")

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

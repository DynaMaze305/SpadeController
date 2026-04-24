import asyncio
import os
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestAgent")

class TestAgent(Agent):
    class ReceiveBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if msg:
                logger.info(f"[TEST]   Received from {msg.sender}:")
                logger.info(f"[TEST]   Body: {msg.body}")
                logger.info(f"[TEST]   Metadata: {msg.metadata}\n")
            else:
                await asyncio.sleep(0.2)

    class SendCommandBehaviour(OneShotBehaviour):
        def __init__(self, target_jid, command):
            super().__init__()
            self.target_jid = target_jid
            self.command = command

        async def run(self):
            logger.info(f"[TEST] Sent command to {self.target_jid}:\n {self.command}")
            msg = Message(to=self.target_jid)
            msg.set_metadata("performative", "request")
            msg.body = self.command
            await self.send(msg)
            logger.info(f"[TEST] Sent command: {self.command}")

    class ConsoleInputBehaviour(CyclicBehaviour):
        async def run(self):
            # Non-blocking input
            cmd = await asyncio.get_event_loop().run_in_executor(None, input, ">>> ")

            cmd = cmd.strip()
            if not cmd:
                return

            logger.info(f"Sent inline command: {cmd}")

            # Expect: "<jid> <command>"
            try:
                jid, command = cmd.split(" ", 1)
            except ValueError:
                logger.error("[CMD] Invalid format. Use: <jid> <command>")
                return

            msg = Message(to=jid)
            msg.set_metadata("performative", "request")
            msg.body = command
            await self.send(msg)

    async def setup(self):
        logger.info(f"[TEST] TestAgent {self.jid} started.")
        self.add_behaviour(self.ReceiveBehaviour())
        # self.add_behaviour(self.ConsoleInputBehaviour())

    async def send_command(self, target_jid, command):
        """Helper to send commands from outside behaviours."""
        behaviour = self.SendCommandBehaviour(target_jid, command)
        self.add_behaviour(behaviour)


async def start_test_agent() -> Agent:
    # Read XMPP credentials and configuration from environment variables
    xmpp_domain = os.environ.get("XMPP_DOMAIN", "prosody")
    xmpp_jid = f"test-agent@{xmpp_domain}"
    xmpp_password = os.environ.get("XMPP_PASSWORD", "top_secret")

    # Log the configuration for debugging purposes (masking the password)
    logger.info("Starting AlphaBot XMPP Agent")
    logger.info(f"XMPP JID: {xmpp_jid}")
    logger.info(f"XMPP Password: {'*' * len(xmpp_password)}")

    try:
        # Create and start the agent
        agent = TestAgent(
            jid=xmpp_jid, 
            password=xmpp_password,
            verify_security=False
        )
        logger.info("TestAgent created, attempting to start...")
        await agent.start(auto_register=True)
        logger.info("TestAgent started successfully!")
        return agent
    except Exception as e:
        logger.error(f"Error starting agent: {str(e)}", exc_info=True)

async def main():

    # Start only the TestAgent
    test = await start_test_agent()
    if test is None:
        logger.error("TestAgent failed to start.")
        return

    await asyncio.sleep(1)

    # Send test commands
    sensors_jid = os.environ.get("SENSORS_AGENT")
    logger.info("[TEST] Launch test SensorsAgent...")
    await test.send_command(sensors_jid ,"register")
    await asyncio.sleep(1)

    await test.send_command(sensors_jid ,"battery")
    await asyncio.sleep(1)

    await test.send_command(sensors_jid ,"sensor digital 1")
    await asyncio.sleep(1)

    await test.send_command(sensors_jid ,"sensors analog 0 digital 1")
    await asyncio.sleep(1)

    logger.info("Test sequence complete. Waiting for messages...")

    try:
        while True:
            await asyncio.sleep(5)
            if test:
                if test.is_alive():
                    logger.info("TestAgent is alive and running...")
                else:
                    logger.error("TestAgent is NOT alive anymore!")
            else:
                raise RuntimeError("No Test agent running!!!")

    except asyncio.CancelledError:
        logger.warning("Main loop cancelled")

    finally:
        logger.info("Stopping test agent...")
        await test.stop()
        logger.info("Test agent stopped cleanly")

if __name__ == "__main__":
    asyncio.run(main())
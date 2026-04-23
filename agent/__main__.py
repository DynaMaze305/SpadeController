import asyncio
import os
import logging

from spade.agent import Agent

from agent.CameraAgent import CameraAgent
from agent.TestCameraReceiver import TestCameraReceiver

from agent.MotionAgent import MotionAgent

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("Main")

# Enable SPADE and XMPP specific logging
for log_name in ["spade", "aioxmpp", "xmpp"]:
    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.propagate = True

async def start_motion_agent() -> Agent:
    # Read XMPP credentials and configuration from environment variables
    xmpp_domain = os.environ.get("XMPP_DOMAIN", "prosody")
    xmpp_username = os.environ.get("XMPP_USERNAME", "alpha-pi-zero-agent")
    xmpp_jid = f"{xmpp_username}@{xmpp_domain}"
    xmpp_password = os.environ.get("XMPP_PASSWORD", "top_secret")
    
    # Log the configuration for debugging purposes (masking the password)
    logger.info("Starting AlphaBot XMPP Agent")
    logger.info(f"XMPP JID: {xmpp_jid}")
    logger.info(f"XMPP Password: {'*' * len(xmpp_password)}")
    
    try:
        # Create and start the agent
        agent = MotionAgent(
            jid=xmpp_jid, 
            password=xmpp_password,
            verify_security=False
        )
        
        logger.info("MotionAgent created, attempting to start...")
        await agent.start(auto_register=True)
        logger.info("MotionAgent started successfully!")
    except Exception as e:
        logger.error(f"Error starting agent: {str(e)}", exc_info=True)
    
    return agent

async def start_camera() -> Agent:
    # Read XMPP credentials and configuration from environment variables
    xmpp_domain = os.environ.get("XMPP_DOMAIN", "prosody") # isc-coordinator.lan
    xmpp_username = os.environ.get("XMPP_CAMERA_USERNAME", "camera-bot-agent") #camera-bot-agent
    xmpp_botname = os.environ.get("XMPP_USERNAME", "alpha-pi-zero-agent") # alphabot23-agent
    xmpp_jid = f"{xmpp_username}-{xmpp_botname}@{xmpp_domain}"
    xmpp_password = os.environ.get("XMPP_PASSWORD", "top_secret")

    ssh_user = os.environ.get("REMOTE_USER", "pi") # hesso
    ssh_server = os.environ.get("REMOTE_HOST", "alpha-pi-zero.local") # alphabot23-agent.local
    
    # Log the configuration for debugging purposes (masking the password)
    logger.info("Starting Camera XMPP Agent")
    logger.info(f"XMPP JID: {xmpp_jid}")
    logger.info(f"XMPP Password: {'*' * len(xmpp_password)}")
    logger.info(f"SSH User: {ssh_user}")
    logger.info(f"SSH Server: {ssh_server}")
    
    try:
        # Create and start the agent
        agent = CameraAgent(
            ssh_user=ssh_user,
            ssh_server=ssh_server,
            jid=xmpp_jid, 
            password=xmpp_password,
            verify_security=False
        )
        
        logger.info("CameraAgent created, attempting to start...")
        await agent.start(auto_register=True)
        logger.info("CameraAgent started successfully!")
    except Exception as e:
        logger.error(f"Error starting agent: {str(e)}", exc_info=True)
    
    return agent

async def start_test_camera() -> Agent:
    # Read XMPP credentials and configuration from environment variables
    xmpp_domain = os.environ.get("XMPP_DOMAIN", "prosody")
    xmpp_username = os.environ.get("XMPP_CAMERA_USERNAME", "camera-bot-agent")
    xmpp_botname = os.environ.get("XMPP_USERNAME", "alpha-pi-zero-agent")
    xmpp_camera_jid = f"{xmpp_username}-{xmpp_botname}@{xmpp_domain}"
    xmpp_password = os.environ.get("XMPP_PASSWORD", "top_secret")
    
    xmpp_test_receiver_jid = f"test-camera-bot-agent@{xmpp_domain}"
    
    # Log the configuration for debugging purposes (masking the password)
    logger.info("Starting Test Camera Receiver XMPP Agent")
    logger.info(f"XMPP camera JID: {xmpp_camera_jid}")
    logger.info(f"XMPP test receiver JID: {xmpp_test_receiver_jid}")
    logger.info(f"XMPP Password: {'*' * len(xmpp_password)}")
    
    try:
        # Create and start the agent
        test_agent = TestCameraReceiver(
            camera_jid=xmpp_camera_jid,
            jid=xmpp_test_receiver_jid,
            password=xmpp_password,
            verify_security=False
        )
        
        logger.info("TestCameraReceiver created, attempting to start...")
        await test_agent.start(auto_register=True)
        logger.info("TestCameraReceiver started successfully!")

    except Exception as e:
        logger.error(f"Error starting agent: {str(e)}", exc_info=True)

    return test_agent


async def main():
    motion_agent = await start_motion_agent()
    # await start_camera()
    # await start_test_camera()

    logger.info("Agents started")

    # Keep the program alive
    while True:
        await asyncio.sleep(1)
        if motion_agent.is_alive():
            logger.debug("MotionAgent is alive and running...")
        
if __name__ == "__main__":
    try:
      asyncio.run(main())
    except Exception as e:
        logger.critical(f"Critical error in main loop: {str(e)}", exc_info=True)
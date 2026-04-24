import asyncio
import os
import logging

from spade.agent import Agent

from agent.CameraAgent import CameraAgent
from agent.TestCameraReceiver import TestCameraReceiver

from agent.MotionAgent import MotionAgent
from agent.SensorsAgent import SensorsAgent

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("Main")

# Enable SPADE and XMPP specific logging
for log_name in ["spade", "aioxmpp", "xmpp"]:
    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.propagate = True

async def start_motion_agent(run_agent: bool) -> Agent:
    # Read XMPP credentials and configuration from environment variables
    xmpp_jid = os.environ.get("MOTION_AGENT", "prosody")
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
        if run_agent:
            logger.info("MotionAgent created, attempting to start...")
            await agent.start(auto_register=True)
            logger.info("MotionAgent started successfully!")
        else:
            logger.info("MotionAgent created, but will not run!")
    except Exception as e:
        logger.error(f"Error starting agent: {str(e)}", exc_info=True)
    
    return agent

async def start_camera_agent(run_agent: bool) -> Agent:
    # Read XMPP credentials and configuration from environment variables
    xmpp_jid = os.environ.get("CAMERA_AGENT", "prosody")
    xmpp_password = os.environ.get("XMPP_PASSWORD", "top_secret")
    
    # Log the configuration for debugging purposes (masking the password)
    logger.info("Starting Camera XMPP Agent")
    logger.info(f"XMPP JID: {xmpp_jid}")
    logger.info(f"XMPP Password: {'*' * len(xmpp_password)}")
    
    try:
        # Create and start the agent
        agent = CameraAgent(
            jid=xmpp_jid, 
            password=xmpp_password,
            verify_security=False
        )
        if run_agent:
            logger.info("CameraAgent created, attempting to start...")
            await agent.start(auto_register=True)
            logger.info("CameraAgent started successfully!")
        else:
            logger.info("CameraAgent created, but will not run!")
    except Exception as e:
        logger.error(f"Error starting agent: {str(e)}", exc_info=True)
    
    return agent

async def start_sensors_agent(run_agent: bool) -> Agent:
    # Read XMPP credentials and configuration from environment variables
    xmpp_jid = os.environ.get("SENSORS_AGENT", "prosody")
    xmpp_password = os.environ.get("XMPP_PASSWORD", "top_secret")

    xmpp_motion_jid = os.environ.get("MOTION_AGENT","prosody")
    
    # Log the configuration for debugging purposes (masking the password)
    logger.info("Starting Sensors XMPP Agent")
    logger.info(f"XMPP JID: {xmpp_jid}")
    logger.info(f"XMPP Password: {'*' * len(xmpp_password)}")
    
    try:
        # Create and start the agent
        agent = SensorsAgent(
            motion_jid=xmpp_motion_jid,
            period_sensors=10,
            period_emergency=1,
            jid=xmpp_jid, 
            password=xmpp_password,
            verify_security=False
        )
        if run_agent:
            logger.info("SensorsAgent created, attempting to start...")
            await agent.start(auto_register=True)
            logger.info("SensorsAgent started successfully!")
        else:
            logger.info("SensorsAgent created, but will not run!")
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
    camera_agent = await start_camera_agent()
    sensors_agent = await start_sensors_agent()

    logger.info("Agents started")

    # Keep the program alive
    while True:
        await asyncio.sleep(60)
        if motion_agent.is_alive():
            logger.info("MotionAgent is alive and running...")
        if camera_agent.is_alive():
            logger.info("CameraAgent is alive and running...")
        if sensors_agent.is_alive():
            logger.info("SensorsAgent is alive and running...")
        
if __name__ == "__main__":
    try:
      asyncio.run(main())
    except Exception as e:
        logger.critical(f"Critical error in main loop: {str(e)}", exc_info=True)
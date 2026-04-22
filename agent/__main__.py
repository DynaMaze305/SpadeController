import asyncio
import os
import logging

from agent.CameraAgent import CameraAgent
from agent.TestCameraReceiver import TestCameraReceiver

from agent.AlphaBotAgent import AlphaBotAgent

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("Main")

# Enable SPADE and XMPP specific logging
for log_name in ["spade", "aioxmpp", "xmpp"]:
    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.propagate = True

async def start_alphabot():
    # Read XMPP credentials and configuration from environment variables
    xmpp_domain = os.environ.get("XMPP_DOMAIN", "prosody")
    xmpp_username = os.environ.get("XMPP_USERNAME", "alpha-pi-zero-agent")
    xmpp_jid = f"{xmpp_username}@{xmpp_domain}"
    xmpp_password = os.environ.get("XMPP_PASSWORD", "top_secret")

    # Navigation recipient (the agent that will receive path requests)
    nav_recipent = os.environ.get("NAV_RECIPIENT", "navigator@isc-coordinator.lan")
    
    # Log the configuration for debugging purposes (masking the password)
    logger.info("Starting AlphaBot XMPP Agent")
    logger.info(f"XMPP JID: {xmpp_jid}")
    logger.info(f"XMPP Password: {'*' * len(xmpp_password)}")
    
    try:
        # Create and start the agent
        agent = AlphaBotAgent(
            nav_recipent=nav_recipent,
            jid=xmpp_jid, 
            password=xmpp_password,
            verify_security=False
        )
        
        logger.info("Agent created, attempting to start...")
        await agent.start(auto_register=True)
        logger.info("Agent started successfully!")
        
        # For debug purpose only as it will block there the code
        # try:
        #     while agent.is_alive():
        #         logger.debug("Agent is alive and running...")
        #         await asyncio.sleep(10)  # Log every 10 seconds that agent is alive
        # except KeyboardInterrupt:
        #     logger.info("Keyboard interrupt received")
        #     await agent.stop()
        #     logger.info("Agent stopped by user.")
    except Exception as e:
        logger.error(f"Error starting agent: {str(e)}", exc_info=True)

async def start_camera():
    # Read XMPP credentials and configuration from environment variables
    xmpp_domain = os.environ.get("XMPP_DOMAIN", "prosody") # isc-coordinator.lan
    xmpp_username = os.environ.get("XMPP_CAMERA_USERNAME", "camera-bot-agent") #camera-bot-agent
    xmpp_botname = os.environ.get("XMPP_USERNAME", "alpha-pi-zero-agent") # isc-alphabot23
    xmpp_jid = f"{xmpp_username}-{xmpp_botname}@{xmpp_domain}"
    xmpp_password = os.environ.get("XMPP_PASSWORD", "top_secret")

    ssh_user = os.environ.get("REMOTE_USER", "pi") # hesso
    ssh_server = os.environ.get("REMOTE_HOST", "alpha-pi-zero.local") # isc-alphabot23.local
    
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
        
        # For debug purpose only as it will block there the code
        # try:
        #     while agent.is_alive():
        #         logger.debug("CameraAgent is alive and running...")
        #         await asyncio.sleep(10)  # Log every 10 seconds that agent is alive
        # except KeyboardInterrupt:
        #     logger.info("Keyboard interrupt received")
        #     await agent.stop()
        #     logger.info("CameraAgent stopped by user.")
    except Exception as e:
        logger.error(f"Error starting agent: {str(e)}", exc_info=True)

async def start_test_camera():
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

        # For debug purpose only as it will block there the code
        # try:
        #     while test_agent.is_alive():
        #         logger.debug("TestCameraReceiver is alive and running...")
        #         await asyncio.sleep(10)  # Log every 10 seconds that agent is alive
        # except KeyboardInterrupt:
        #     logger.info("Keyboard interrupt received")
        #     await test_agent.stop()
        #     logger.info("TestCameraReceiver stopped by user.")
    except Exception as e:
        logger.error(f"Error starting agent: {str(e)}", exc_info=True)




async def main():
    await start_alphabot()
    # await start_camera()
    # await start_test_camera()

    logger.info("Agents started")

    # Keep the program alive
    while True:
        await asyncio.sleep(1)
        
if __name__ == "__main__":
    try:
      asyncio.run(main())
    except Exception as e:
        logger.critical(f"Critical error in main loop: {str(e)}", exc_info=True)
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour, OneShotBehaviour
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour, OneShotBehaviour
from spade.message import Message
import asyncio
import os
import time
import logging

# Import AlphaBot2 library
from agent.alphabotlib.AlphaBot2 import AlphaBot2

# Import rpi_ws281x for LED color
from rpi_ws281x import Color

def Wheel(pos: int) -> Color:
    """
    Generate rainbow colors across 0-255 positions.

    Parameters
    ----------
    pos : int
        The position in the rainbow (0-255).

    Returns
    -------
    Color
        The RGB color for the given position.
    """
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("AlphaBotAgent")

# Enable SPADE and XMPP specific logging
for log_name in ["spade", "aioxmpp", "xmpp"]:
    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.propagate = True

class AlphaBotAgent(Agent):
    """
    Agent to control the AlphaBot2 robot via XMPP commands.
    """
    def __init__(self, nav_recipent: str, jid: str, password: str, verify_security: bool = False):
        """
        Initialize the AlphaBotAgent with XMPP credentials and navigation recipient.

        Parameters
        ----------
        nav_recipent: str
            The JID of the navigation agent to which the path request will be sent.
        jid: str
            The XMPP JID for the agent.
        password: str
            The password for the XMPP account.
        verify_security: bool
            Whether to verify the security of the XMPP connection.

        """
        super().__init__(jid, password, verify_security=verify_security)
        self.nav_recipent = nav_recipent
        self.ab = None

    class XMPPCommandListener(CyclicBehaviour):
        """
        Behavior to listen for XMPP messages and execute commands on the AlphaBot2.
        """
        # Adjustable variable for better control of the movement duration
        STEP_DURATION = 0.5
        ROTATION_DURATION = 0.18
        ROTATION_DEG_PER_SEC = 500

        async def on_start(self):
            """
            Initialize the AlphaBot2 instance if needed when the behavior starts.
            """
            if self.agent.ab is None:
                logger.info("[Behaviour] Initializing AlphaBot2...")
                self.agent.ab = AlphaBot2()
            logger.info("[Behaviour] Ready to receive commands.")
            
        async def run(self):
            """
            Listen for incoming XMPP messages and process commands.
            """
            logger.debug("[Behaviour] Waiting for messages...")
            msg = await self.receive(timeout=10)
            if msg:
                logger.info(f"[Behaviour] Received command ({msg.sender}): {msg.body}")
                await self.process_command(msg.body)
                
                # Send a confirmation response
                reply = Message(to=str(msg.sender))
                reply.set_metadata("performative", "inform")
                reply.body = f"Executed command: {msg.body}"
                await self.send(reply)
                logger.info(f"[Behaviour] Sent reply to {msg.sender}")
            else:
                logger.debug("[Behavior] No message received during timeout.")

        # Functions that rotates the robot
        # Takes an angle in degrees as a parameter
                logger.debug("[Behaviour] No message received during timeout.")

        async def rotate_by(self, degrees: float):
            """
            Rotate the AlphaBot2 by a specified angle in degrees.

            Parameters
            ----------
            degrees: float
                The angle in degrees to rotate. Positive for left, negative for right.
            """
            # Calculates the theoretical Duration of the rotation
            duration = abs(degrees) / self.ROTATION_DEG_PER_SEC

            logger.info(f"[Behavior] Rotating {degrees:+.1f} deg (duration={duration:.2f}s)")

            # Executes the rotation
            if degrees > 0:
                self.ab.left()
            else:
                self.ab.right()

            await asyncio.sleep(duration)
            self.ab.stop()

        
        async def process_command(self, command: str):
            """
            Process the received command and execute corresponding actions on the AlphaBot2.

            Parameters
            ----------
            command: str
                The command string received via XMPP, e.g., "forward", "backward", "left", "right", "motor 100 100", etc.
            """
            command = command.strip().lower()
            
            if command == "forward":
                # Move the AlphaBot2 forward for a short duration.
                logger.info("[Behaviour] Moving forward...")
                self.ab.forward()
                await asyncio.sleep(self.STEP_DURATION)
                self.ab.stop()
                
            elif command == "backward":
                # Move the AlphaBot2 backward for a short duration.
                logger.info("[Behaviour] Moving backward...")
                self.ab.backward()
                await asyncio.sleep(self.STEP_DURATION)
                self.ab.stop()
                
            elif command == "left":
                # Turn the AlphaBot2 left for a short duration.
                logger.info("[Behaviour] Turning left...")
                self.ab.left()
                await asyncio.sleep(self.ROTATION_DURATION)
                self.ab.stop()
                
            elif command == "right":
                # Turn the AlphaBot2 right for a short duration.
                logger.info("[Behaviour] Turning right...")
                self.ab.right()
                await asyncio.sleep(self.ROTATION_DURATION)
                self.ab.stop()
                
            elif command.startswith("motor "):
                # Set custom motor speeds for the AlphaBot2. Command format: 'motor <left_speed> <right_speed>'
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

            # Command for a specific rotation angle instead of left/right
            elif command.startswith("rotation "):
                try:
                    angle = float(command.split()[1])
                    await self.rotate_by(angle)
                except (ValueError, IndexError):
                    logger.error("[Behavior] Invalid rotation command. Use 'rotation <degrees>'")

            elif command == "stop":
                # Stop the AlphaBot2 immediately.
                logger.info("[Behaviour] Stopping...")
                self.agent.ab.stop()

            elif command == "init":
                logger.info("[Behaviour] Start robot.")
                #self.agent.add_behaviour(self.agent.XMPPPathRequest(self.nav_recipent))

            elif command.startswith("instructions "):
                # Execute a series of instructions periodically. Command format: 'instructions <instr1> <instr2> ...'
                instructions = command.split()
                self.agent.add_behaviour(self.agent.XMPPExecutePath(instructions[1:]))

            else:
                logger.warning(f"[Behaviour] Unknown command: {command}")

    class XMPPPathRequest(OneShotBehaviour):
        """
        Behavior to send an initial path request to the navigation agent.
        """
        def __init__(self, target: str):
            """
            Initialize the behavior with the target recipient for the path request.

            Parameters
            ----------
            target: str
                The JID of the navigation agent to which the path request will be sent.
            """
            super().__init__()
            self.target = target
            logger.info("[Behaviour] Ready to request a path.")
        
        async def run(self):
            """
            Send a path request message to the navigation agent.
            """
            logger.info("[Behaviour] Sending path request...")
            msg = Message(to=self.target)
            msg.set_metadata("performative", "request")
            msg.body = "request path"

            await self.send(msg)
            logger.info("[Behaviour] Request send.")

    class XMPPExecutePath(PeriodicBehaviour):
        """
        Behavior to execute a series of instructions received from the navigation agent.
        """
        def __init__(self, instructions: list[str], period: float = 1):
            """
            Initialize the behavior with the list of instructions to execute and the execution period.

            Parameters
            ----------
            instructions: list[str]
                A list of instructions to execute, e.g., ["forward", "left", "forward", "right"].
            period: float
                The time interval (in seconds) between executing each instruction.
            """
            super().__init__(period=period)
            self.instructions = instructions
            logger.info("[Behavior] Ready to execute instructions.")

        async def run(self):
            """ Execute the next instruction in the list. """
            logger.info("[Behaviour] Executing instruction...")
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

    class TESTPeriodicSensors(PeriodicBehaviour):
        def __init__(self, period):
            super().__init__(period=period)
            if self.agent.ab is None:
                logger.info("[Behavior] Initializing AlphaBot2...")
                self.agent.ab = AlphaBot2()
            logger.info(f"[Behavior] Ready to test sensors every {period} secondes.")

        async def run(self):
            logger.info("[Behavior] Reading sensors...")
            analog_data = self.agent.ab.get_analog_values()
            for i, d in enumerate(analog_data):
                logger.info(f"[Sensor] Analog chanel {i}; {d}")
            
            battery_level = self.agent.ab.get_battery_level()
            logger.info(f"[Sensor] Battery level; {battery_level}")

    async def setup(self):
        """
        Setup the agent and add its behaviors.
        """
        logger.info("[Agent] AlphaBotAgent starting setup...")
        logger.info(f"[Agent] Will connect as {self.jid} to server {os.environ.get('XMPP_SERVER', 'prosody')}")
        
        # Add command listener behaviour
        command_behaviour = self.XMPPCommandListener()
        self.add_behaviour(command_behaviour)

        # Add first init request
        # init_request = self.XMPPPathRequest(self.nav_recipent)
        # self.add_behaviour(init_request)
        
        logger.info("[Agent] Behaviors added, setup complete.")

async def main():
    # Read XMPP credentials and configuration from environment variables
    xmpp_domain = os.environ.get("XMPP_DOMAIN", "prosody")
    xmpp_username = os.environ.get("XMPP_USERNAME", "alpha-pi-zero-agent")
    xmpp_jid = f"{xmpp_username}@{xmpp_domain}"
    xmpp_password = os.environ.get("XMPP_PASSWORD", "top_secret")

    # Navigation recipient (the agent that will receive path requests)
    nav_recipent = os.environ.get("NAV_RECIPENT", "navigator@isc-coordinator.lan")
    
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

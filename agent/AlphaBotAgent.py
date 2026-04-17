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
                logger.debug("[Behaviour] No message received during timeout.")
        
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
                self.agent.ab.forward()
                await asyncio.sleep(2)
                self.agent.ab.stop()
                
            elif command == "backward":
                # Move the AlphaBot2 backward for a short duration.
                logger.info("[Behaviour] Moving backward...")
                self.agent.ab.backward()
                await asyncio.sleep(2)
                self.agent.ab.stop()
                
            elif command == "left":
                # Turn the AlphaBot2 left for a short duration.
                logger.info("[Behaviour] Turning left...")
                self.agent.ab.left()
                await asyncio.sleep(2)
                self.agent.ab.stop()
                
            elif command == "right":
                # Turn the AlphaBot2 right for a short duration.
                logger.info("[Behaviour] Turning right...")
                self.agent.ab.right()
                await asyncio.sleep(2)
                self.agent.ab.stop()
                
            elif command.startswith("motor "):
                # Set custom motor speeds for the AlphaBot2. Command format: 'motor <left_speed> <right_speed>'
                try:
                    _, left, right = command.split()
                    left_speed = int(left)
                    right_speed = int(right)
                    logger.info(f"[Behaviour] Setting motor speeds to {left_speed} (left) and {right_speed} (right)...")
                    self.agent.ab.setMotor(left_speed, right_speed)
                    await asyncio.sleep(2)
                    self.agent.ab.stop()
                except (ValueError, IndexError):
                    logger.error("[Behaviour] Invalid motor command format. Use 'motor <left_speed> <right_speed>'")
                    
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
            # TODO: implement execution logic
            if len(self.instructions) <= 0:
                logger.info("[Behaviour] No more instructions to execute.")
                self.kill()
                return
            i = self.instructions.pop(0)
            logger.info(f"[Behaviour] Next instruction: {i}")
            await self.agent.XMPPCommandListener.process_command(self, i)

    class TESTPeriodicSensors(PeriodicBehaviour):
        def __init__(self, period):
            super().__init__(period=period)
            self.ctn = 0
        
        async def on_start(self):
            if self.agent.ab is None:
                logger.info("[Behavior] Initializing AlphaBot2...")
                self.agent.ab = AlphaBot2()
            logger.info(f"[Behavior] Ready to test sensors every {self.period} secondes.")

        async def run(self):
            logger.info("[Behavior] Reading sensors...")
            analog_data = self.agent.ab.get_analog_values()
            for i, d in enumerate(analog_data):
                logger.info(f"[Sensor] Analog channel {i}; {d}")
            for i in range(4):
                self.agent.ab.set_led(i, Wheel(((i + self.ctn) * 256 // 4) % 256))
            self.ctn += 1
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
        init_request = self.XMPPPathRequest(self.nav_recipent)
        self.add_behaviour(init_request)

        # Add periodic sensor reading behaviour (for testing)
        sensor_behaviour = self.TESTPeriodicSensors(period=10)  # Read sensors every 30 seconds
        self.add_behaviour(sensor_behaviour)

        # To test battery level reading (for testing)
        # forward_behaviour = self.XMPPExecutePath(instructions=["forward"]*10 + ["backward"]*10 + ["stop"], period=2)
        # self.add_behaviour(forward_behaviour)
        
        logger.info("[Agent] Behaviors added, setup complete.")
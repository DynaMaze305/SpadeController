# Import necessary libraries for GPIO control (Raspberry Pi)
import RPi.GPIO as GPIO

class MotionManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self,ain1: int = 12,ain2: int = 13,ena: int = 6,bin1: int = 20,bin2: int = 21,enb: int = 26):
        """
        Initialize the AlphaBot2 with motor control pins, sensors, camera, and LED strip.

        Parameters
        ----------
        ain1: int
            GPIO pin for motor A input 1 (default: 12)
        ain2: int
            GPIO pin for motor A input 2 (default: 13)
        ena: int
            GPIO pin for motor A enable (default: 6)
        bin1: int
            GPIO pin for motor B input 1 (default: 20)
        bin2: int
            GPIO pin for motor B input 2 (default: 21)
        enb: int
            GPIO pin for motor B enable (default: 26)
        """
        if hasattr(self, "_initialized"):
            return
        self.AIN1 = ain1
        self.AIN2 = ain2
        self.BIN1 = bin1
        self.BIN2 = bin2
        self.ENA = ena
        self.ENB = enb

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.AIN1,GPIO.OUT)
        GPIO.setup(self.AIN2,GPIO.OUT)
        GPIO.setup(self.BIN1,GPIO.OUT)
        GPIO.setup(self.BIN2,GPIO.OUT)
        GPIO.setup(self.ENA,GPIO.OUT)
        GPIO.setup(self.ENB,GPIO.OUT)
        self.PWMA = GPIO.PWM(self.ENA,500)
        self.PWMB = GPIO.PWM(self.ENB,500)
        self.PWMA.start(0)
        self.PWMB.start(0)

        self._initialized = True
        self._last_pwm_left = 0
        self._last_pwm_right = 0

    def setPWMA(self, value: int):
        """Set the duty cycle for motor A."""
        self._last_pwm_right = value
        self.PWMA.ChangeDutyCycle(value)

    def setPWMB(self, value: int):
        """Set the duty cycle for motor B."""
        self._last_pwm_left = value
        self.PWMB.ChangeDutyCycle(value)

    def setPWM(self, pa: int, pb: int):
        """Set the duty cycle for the motors."""
        pa = max(0, min(pa, 100))
        pb = max(0, min(pb, 100))
        self.setPWMA(pa)
        self.setPWMB(pb)

    def forward(self, pa: int = 100, pb: int = 100):
        """Move the robot forward."""
        self.setPWM(pa, pb)
        GPIO.output(self.AIN1,GPIO.LOW)
        GPIO.output(self.AIN2,GPIO.HIGH)
        GPIO.output(self.BIN1,GPIO.LOW)
        GPIO.output(self.BIN2,GPIO.HIGH)

    def stop(self, pa: int = 0, pb: int = 0):
        """Stop the robot."""
        self.setPWM(pa, pb)
        GPIO.output(self.AIN1,GPIO.LOW)
        GPIO.output(self.AIN2,GPIO.LOW)
        GPIO.output(self.BIN1,GPIO.LOW)
        GPIO.output(self.BIN2,GPIO.LOW)

    def backward(self, pa: int = 100, pb: int = 100):
        """Move the robot backward."""
        self.setPWM(pa, pb)
        GPIO.output(self.AIN1,GPIO.HIGH)
        GPIO.output(self.AIN2,GPIO.LOW)
        GPIO.output(self.BIN1,GPIO.HIGH)
        GPIO.output(self.BIN2,GPIO.LOW)

    def left(self, pa: int = 50, pb: int = 50):
        """Turn the robot itself on the left."""
        self.setPWM(pa, pb)
        GPIO.output(self.AIN1,GPIO.HIGH)
        GPIO.output(self.AIN2,GPIO.LOW)
        GPIO.output(self.BIN1,GPIO.LOW)
        GPIO.output(self.BIN2,GPIO.HIGH)

    def right(self, pa: int = 50, pb: int = 50):
        """Turn the robot itself on the right."""
        self.setPWM(pa, pb)
        GPIO.output(self.AIN1,GPIO.LOW)
        GPIO.output(self.AIN2,GPIO.HIGH)
        GPIO.output(self.BIN1,GPIO.HIGH)
        GPIO.output(self.BIN2,GPIO.LOW)

    def setMotor(self, left, right):
        """Set the speed and direction of both motors."""
        if((right >= 0) and (right <= 100)):
            GPIO.output(self.AIN1,GPIO.HIGH)
            GPIO.output(self.AIN2,GPIO.LOW)
            self.PWMA.ChangeDutyCycle(right)
        elif((right < 0) and (right >= -100)):
            GPIO.output(self.AIN1,GPIO.LOW)
            GPIO.output(self.AIN2,GPIO.HIGH)
            self.PWMA.ChangeDutyCycle(0 - right)
        if((left >= 0) and (left <= 100)):
            GPIO.output(self.BIN1,GPIO.HIGH)
            GPIO.output(self.BIN2,GPIO.LOW)
            self.PWMB.ChangeDutyCycle(left)
        elif((left < 0) and (left >= -100)):
            GPIO.output(self.BIN1,GPIO.LOW)
            GPIO.output(self.BIN2,GPIO.HIGH)
            self.PWMB.ChangeDutyCycle(0 - left)

    def read_motion_status(self) -> dict:
        """
        Return a dictionary describing the robot's current motion state.
        Includes direction and PWM values for both motors.

        Return
        ------
        dict
            A dictionary encoding the motion data
            {
                [left|right]_motor: {
                    "direction": str,
                    "pwm": int
                }
            }
        """
        # Read GPIO pin states
        ain1 = GPIO.input(self.AIN1)
        ain2 = GPIO.input(self.AIN2)
        bin1 = GPIO.input(self.BIN1)
        bin2 = GPIO.input(self.BIN2)

        # Determine direction of each motor
        def decode_direction(p1, p2):
            if p1 == GPIO.LOW and p2 == GPIO.LOW:
                return "stopped"
            if p1 == GPIO.LOW and p2 == GPIO.HIGH:
                return "forward"
            if p1 == GPIO.HIGH and p2 == GPIO.LOW:
                return "backward"
            return "unknown"

        left_dir = decode_direction(bin1, bin2)
        right_dir = decode_direction(ain1, ain2)

        # Read PWM duty cycles
        status = {
            "left_motor": {
                "direction": left_dir,
                "pwm": self._last_pwm_left
            },
            "right_motor": {
                "direction": right_dir,
                "pwm": self._last_pwm_right
            }
        }

        return status

# Import necessary libraries for GPIO control (Raspberry Pi)
import RPi.GPIO as GPIO

# Import threading for safety
import threading

class MotionManager:
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        # Thread‑safe singleton creation
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self,ain1: int = 12,ain2: int = 13,ena: int = 6,bin1: int = 20,bin2: int = 21,enb: int = 26):
        """
        Initialize the AlphaBot2 with motor control pins, sensors, camera, and LED strip.

        Motor A is considered as the left  motor of the AlphaBot2
        Motor B is considered as the right motor of the AlphaBot2

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

        # Motor pins
        self.AIN1 = ain1
        self.AIN2 = ain2
        self.BIN1 = bin1
        self.BIN2 = bin2
        self.ENA = ena
        self.ENB = enb

        # GPIO setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for pin in (self.AIN1, self.AIN2, self.BIN1, self.BIN2, self.ENA, self.ENB):
            GPIO.setup(pin, GPIO.OUT)

        self.PWMA = GPIO.PWM(self.ENA, 500)
        self.PWMB = GPIO.PWM(self.ENB, 500)
        self.PWMA.start(0)
        self.PWMB.start(0)

        # Internal state
        self._last_pwm_left = 0
        self._last_pwm_right = 0
        self._emergency_stop = False
        self._lock = threading.Lock()

        self._initialized = True

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------
    def _check_emergency(self, emergency_override: bool = False):
        if self._emergency_stop and not emergency_override:
            raise RuntimeError("MotionManager emergency stop active")

    def _safe_pwm(self, value: int) -> int:
        return max(0, min(value, 100))

    # ---------------------------------------------------------
    # Emergency stop
    # ---------------------------------------------------------
    def emergency_stop(self) -> bool:
        """Immediately stop all motion and lock out future movement."""
        with self._lock:
            if self._emergency_stop:
                return False

            self._emergency_stop = True
            self._stop_unlocked()
            return True

    def clear_emergency_stop(self) -> bool:
        """Re-enable motion after an emergency stop."""
        with self._lock:
            self._emergency_stop = False
            return True

    # ---------------------------------------------------------
    # PWM control
    # ---------------------------------------------------------
    def setPWMA(self, value: int, emergency_override: bool = False):
        """Set the duty cycle for motor A (left)."""
        with self._lock:
            self._check_emergency(emergency_override)
            value = self._safe_pwm(value)
            self._last_pwm_left= value
            self.PWMA.ChangeDutyCycle(value)

    def setPWMB(self, value: int, emergency_override: bool = False):
        """Set the duty cycle for motor B (right)."""
        with self._lock:
            self._check_emergency(emergency_override)
            value = self._safe_pwm(value)
            self._last_pwm_right = value
            self.PWMB.ChangeDutyCycle(value)

    def setPWM(self, pa: int, pb: int, emergency_override: bool = False):
        """Set the duty cycle for the motors."""
        with self._lock:
            self._check_emergency(emergency_override)
            pa = self._safe_pwm(pa)
            pb = self._safe_pwm(pb)
            self._last_pwm_left = pa
            self._last_pwm_right = pb
            self.PWMA.ChangeDutyCycle(pa)
            self.PWMB.ChangeDutyCycle(pb)
    
    def _setPWM_internal_only(self, pa: int, pb: int, emergency_override: bool = False):
        """
        Set the duty cycle for the motors.

        Note:
        - Only internal to MotionManager, otherwise break thread safety.
        """
        self._check_emergency(emergency_override)
        pa = self._safe_pwm(pa)
        pb = self._safe_pwm(pb)
        self._last_pwm_left = pa
        self._last_pwm_right = pb
        self.PWMA.ChangeDutyCycle(pa)
        self.PWMB.ChangeDutyCycle(pb)

    # ---------------------------------------------------------
    # Motion commands
    # ---------------------------------------------------------
    def forward(self, pa: int = 100, pb: int = 100, emergency_override: bool = False):
        """Move the robot forward."""
        with self._lock:
            self._check_emergency(emergency_override)
            self._setPWM_internal_only(pa, pb)
            GPIO.output(self.AIN1, GPIO.LOW)
            GPIO.output(self.AIN2, GPIO.HIGH)
            GPIO.output(self.BIN1, GPIO.LOW)
            GPIO.output(self.BIN2, GPIO.HIGH)

    def stop(self):
        """Stop the robot."""
        with self._lock:
            self._check_emergency(True)
            self._stop_unlocked()

    def backward(self, pa: int = 100, pb: int = 100, emergency_override: bool = False):
        """Move the robot backward."""
        with self._lock:
            self._check_emergency(emergency_override)
            self._setPWM_internal_only(pa, pb)
            GPIO.output(self.AIN1, GPIO.HIGH)
            GPIO.output(self.AIN2, GPIO.LOW)
            GPIO.output(self.BIN1, GPIO.HIGH)
            GPIO.output(self.BIN2, GPIO.LOW)

    def left(self, pa: int = 50, pb: int = 50, emergency_override: bool = False):
        """Turn the robot itself on the left."""
        with self._lock:
            self._check_emergency(emergency_override)
            self._setPWM_internal_only(pa, pb)
            GPIO.output(self.AIN1, GPIO.HIGH)
            GPIO.output(self.AIN2, GPIO.LOW)
            GPIO.output(self.BIN1, GPIO.LOW)
            GPIO.output(self.BIN2, GPIO.HIGH)

    def right(self, pa: int = 50, pb: int = 50, emergency_override: bool = False):
        """Turn the robot itself on the right."""
        with self._lock:
            self._check_emergency(emergency_override)
            self._setPWM_internal_only(pa, pb)
            GPIO.output(self.AIN1, GPIO.LOW)
            GPIO.output(self.AIN2, GPIO.HIGH)
            GPIO.output(self.BIN1, GPIO.HIGH)
            GPIO.output(self.BIN2, GPIO.LOW)

    def _stop_unlocked(self):
        """Stop motors without checking emergency state (internal use)."""
        self.PWMA.ChangeDutyCycle(0)
        self.PWMB.ChangeDutyCycle(0)
        GPIO.output(self.AIN1, GPIO.LOW)
        GPIO.output(self.AIN2, GPIO.LOW)
        GPIO.output(self.BIN1, GPIO.LOW)
        GPIO.output(self.BIN2, GPIO.LOW)
        self._last_pwm_left = 0
        self._last_pwm_right = 0

    # ---------------------------------------------------------
    # Status
    # ---------------------------------------------------------
    def read_motion_status(self) -> dict:
        """
        Return a dictionary describing the robot's current motion state.
        Includes direction and PWM values for both motors.

        Return
        ------
        dict
            A dictionary encoding the motion data
            {
                "[left|right]_motor": {
                    "direction": str,
                    "pwm": int
                },
                "emergency_stop": bool
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

        return {
            "left_motor": {
                "direction": decode_direction(bin1, bin2),
                "pwm": self._last_pwm_left
            },
            "right_motor": {
                "direction": decode_direction(ain1, ain2),
                "pwm": self._last_pwm_right
            },
            "emergency_stop": self._emergency_stop
        }

    # ---------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------
    def shutdown(self):
        """Stop motors and clean up GPIO."""
        with self._lock:
            self._stop_unlocked()
            GPIO.cleanup()

import logging
import time
import threading
import subprocess
import RPi.GPIO as GPIO

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("SensorsAgent")

class BuzzerManager:
    _instance = None
    _instance_lock = threading.Lock()

    BUZZER_PIN = 4          # AlphaBot2-Pi default buzzer pin
    PWM_FREQUENCY = 1000    # Base PWM frequency (Hz)

    def __new__(cls, *args, **kwargs):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self._lock = threading.Lock()
        self._initialized = True

        # GPIO setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.BUZZER_PIN, GPIO.OUT)

        # PWM setup (start silent)
        self._pwm = GPIO.PWM(self.BUZZER_PIN, self.PWM_FREQUENCY)
        self._pwm.start(0)  # duty cycle 0 = silent

    # ---------------------------------------------------------
    # Play a sequence of tones
    # ---------------------------------------------------------
    def play_sound(self, sounds: list[tuple[int, float]]):
        """
        Play a list of (frequency, duration) tuples.
        Frequency = Hz, duration = seconds.
        """
        with self._lock:
            for freq, duration in sounds:
                if freq <= 0:
                    # Silence
                    self._pwm.ChangeDutyCycle(0)
                else:
                    self._pwm.ChangeFrequency(freq)
                    self._pwm.ChangeDutyCycle(50)  # 50% duty cycle

                time.sleep(duration)

            # Stop sound at end
            self._pwm.ChangeDutyCycle(0)

    # ---------------------------------------------------------
    # Play an MP3 file using system player
    # ---------------------------------------------------------
    def play_track(self, mp3_file: str):
        """
        Play an MP3 file using omxplayer or mpg123.
        Blocks until finished.
        """
        with self._lock:
            try:
                subprocess.run(
                    ["omxplayer", "-o", "local", mp3_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except FileNotFoundError:
                logger.error("[BUZZER] Error playing music")
                sounds = [
                    (1000, 0.2),
                    (1500, 0.2),
                    (2000, 0.2),
                    (0, 0.1),      # silence
                    (2000, 0.3)
                ]

                for freq, duration in sounds:
                    if freq <= 0:
                        # Silence
                        self._pwm.ChangeDutyCycle(0)
                    else:
                        self._pwm.ChangeFrequency(freq)
                        self._pwm.ChangeDutyCycle(50)  # 50% duty cycle

                    time.sleep(duration)

                # Stop sound at end
                self._pwm.ChangeDutyCycle(0)

    # ---------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------
    def cleanup(self):
        self._pwm.stop()
        GPIO.cleanup()

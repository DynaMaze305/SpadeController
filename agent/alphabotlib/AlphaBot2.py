import time

# Import necessary libraries for GPIO control (Raspberry Pi)
import RPi.GPIO as GPIO

# Additional imports for line sensor and LED strip
from TRSensors import TRSensor
from rpi_ws281x import Adafruit_NeoPixel, Color

# Additional imports for camera
# import base64
# from picamera2 import Picamera2
# from io import BytesIO

# Additional imports for analog sensors
from AnalogSensors import AnalogSensors

class AlphaBot2(object):
    """
    Class to control the AlphaBot2 robot with added sensors and camera functionality.
    """
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
        self.AIN1 = ain1
        self.AIN2 = ain2
        self.BIN1 = bin1
        self.BIN2 = bin2
        self.ENA = ena
        self.ENB = enb
        self.PA  = 50
        self.PB  = 50

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
        self.PWMA.start(self.PA)
        self.PWMB.start(self.PB)
        self.stop()

        # Add infrared obstacle avoidance sensors
        self.DR = 16
        self.DL = 19
        GPIO.setup(self.DR,GPIO.IN,GPIO.PUD_UP)
        GPIO.setup(self.DL,GPIO.IN,GPIO.PUD_UP)

        # Add line sensor
        self.tr_sensor = TRSensor(5)

        # LED strip configuration:
        self.LED_COUNT = 4       # Number of LED pixels.
        LED_PIN        = 18      # GPIO pin connected to the pixels (must support PWM!).
        LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
        LED_DMA        = 5       # DMA channel to use for generating signal (try 5)
        LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
        LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
        LED_CHANNEL    = 0

        self.strip = Adafruit_NeoPixel(self.LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)

        self.strip.begin()
        self.strip.setPixelColor(0, Color(0, 0, 0))       #Red
        self.strip.setPixelColor(1, Color(0, 0, 0))       #Green
        self.strip.setPixelColor(2, Color(0, 0, 0))       #Blue
        self.strip.setPixelColor(3, Color(0, 0, 0))       #Yellow
        self.strip.show()

        # Configure camera
        # self.picam = Picamera2()
        # config = self.picam.create_still_configuration()
        # self.picam.configure(config)

        # Add analog sensors
        self.analog_sensors = AnalogSensors()

    def forward(self):
        """Move the robot forward."""
        self.PWMA.ChangeDutyCycle(self.PA)
        self.PWMB.ChangeDutyCycle(self.PB)
        GPIO.output(self.AIN1,GPIO.LOW)
        GPIO.output(self.AIN2,GPIO.HIGH)
        GPIO.output(self.BIN1,GPIO.LOW)
        GPIO.output(self.BIN2,GPIO.HIGH)

    def stop(self):
        """Stop the robot."""
        self.PWMA.ChangeDutyCycle(0)
        self.PWMB.ChangeDutyCycle(0)
        GPIO.output(self.AIN1,GPIO.LOW)
        GPIO.output(self.AIN2,GPIO.LOW)
        GPIO.output(self.BIN1,GPIO.LOW)
        GPIO.output(self.BIN2,GPIO.LOW)

    def backward(self):
        """Move the robot backward."""
        self.PWMA.ChangeDutyCycle(self.PA)
        self.PWMB.ChangeDutyCycle(self.PB)
        GPIO.output(self.AIN1,GPIO.HIGH)
        GPIO.output(self.AIN2,GPIO.LOW)
        GPIO.output(self.BIN1,GPIO.HIGH)
        GPIO.output(self.BIN2,GPIO.LOW)

    def left(self):
        """Turn the robot itself on the left."""
        self.PWMA.ChangeDutyCycle(30)
        self.PWMB.ChangeDutyCycle(30)
        GPIO.output(self.AIN1,GPIO.HIGH)
        GPIO.output(self.AIN2,GPIO.LOW)
        GPIO.output(self.BIN1,GPIO.LOW)
        GPIO.output(self.BIN2,GPIO.HIGH)

    def right(self):
        """Turn the robot itself on the right."""
        self.PWMA.ChangeDutyCycle(30)
        self.PWMB.ChangeDutyCycle(30)
        GPIO.output(self.AIN1,GPIO.LOW)
        GPIO.output(self.AIN2,GPIO.HIGH)
        GPIO.output(self.BIN1,GPIO.HIGH)
        GPIO.output(self.BIN2,GPIO.LOW)
        
    def setPWMA(self,value):
        """Set the duty cycle for motor A."""
        self.PA = value
        self.PWMA.ChangeDutyCycle(self.PA)

    def setPWMB(self,value):
        """Set the duty cycle for motor B."""
        self.PB = value
        self.PWMB.ChangeDutyCycle(self.PB)	
        
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

    def get_ioa(self) -> tuple(int, int):
        """
        Read the status of the infrared obstacle avoidance sensors.

        Returns
        -------
        tuple(int, int)
            A tuple containing the status of the right (DR) and left (DL) sensors, where 0 indicates an obstacle detected and 1 indicates no obstacle.
        """
        DR_status = GPIO.input(self.DR)
        DL_status = GPIO.input(self.DL)
        return DR_status, DL_status

    def get_tr_value(self) -> int:
        """
        Read the value from the line sensor.

        Returns
        -------
        int
            The value read from the line sensor.
        """
        return self.tr_sensor.AnalogRead()

    def get_analog_values(self) -> list(int):
        """
        Read values from the analog sensors.

        Returns
        -------
        list(int)
            A list of the values read from the analog sensors.
        """
        data = []
        for i in range(10):
            data.append(self.analog_sensors.read_channel(i))
        return data

    def set_led(self, led_id: int, color: Color):
        """
        Set the color of a specific LED on the strip.

        Parameters
        ----------
        led_id : int
            The ID of the LED to set.
        color : Color
            The color to set the LED to.
        """
        strip.setPixelColor(led_id%self.LED_COUNT, color)
        strip.show()

    # def get_photo(self):
    #     """
    #     Capture a photo using the camera.
        
    #     Returns:
    #     --------
    #     str
    #         A base64-encoded string of the captured JPEG image.
        
    #     Notes:
    #     - This method assumes that the camera is properly configured and connected to the Raspberry Pi. If using a different camera module, additional configuration may be required.
    #     """
    #     self.picam.start()
    #     time.sleep(2) # Adjust time

    #     buffer = BytesIO()
    #     self.picam.capture_file(buffer, format="jpeg")
    #     self.picam.stop()

    #     buffer.seek(0)
    #     jpeg_bytes = buffer.read()

    #     # Encode to base64 for XMPP
    #     return base64.b64encode(jpeg_bytes).decode()

    def get_battery_level(self) -> float:
        """
        Read the battery level from the analog sensors.

        Returns
        -------
        float
            The battery level as a percentage (0-100%).
        """
        return self.analog_sensors.get_battery_level()

if __name__=='__main__':
    # Example usage of the AlphaBot2 class
    Ab = AlphaBot2()
    Ab.forward()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup()

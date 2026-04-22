import time

# Import necessary libraries for GPIO control (Raspberry Pi)
import RPi.GPIO as GPIO

class SensorsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, dr=16, dl=19, cs=5, clk=25, addr=24, data=23, vref=3.3, adc_bit=10):
        if hasattr(self, "_initialized"):
            return
        self.DR = dr
        self.DL = dl
        self.CS = cs
        self.CLK = clk
        self.ADDR = addr
        self.DATA = data
        self.VREF = vref
        self.BITS = adc_bit

        GPIO.setup(self.DR,GPIO.IN,GPIO.PUD_UP)
        GPIO.setup(self.DL,GPIO.IN,GPIO.PUD_UP)

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.CS, GPIO.OUT)
        GPIO.setup(self.CLK, GPIO.OUT)
        GPIO.setup(self.ADDR, GPIO.OUT)
        GPIO.setup(self.DATA, GPIO.IN, GPIO.PUD_UP)

        GPIO.output(self.CS, GPIO.HIGH)
        GPIO.output(self.CLK, GPIO.LOW)

    def get_ioa_right(self) -> int:
        return GPIO.input(self.DR)

    def get_ioa_left(self) -> int:
        return GPIO.input(self.DL)

    def get_ioa(self) -> tuple[int, int]:
        return self.get_ioa_right(), self.get_ioa_left()

    def get_analog_sensor_value(self, channel: int) -> int:
        """
        Read the value from a specific analog sensor channel.

        Parameters
        ----------
        channel : int
            The channel number of the analog sensor to read (0-10).
            0: IR line sensor most left
            1: IR line sensor left
            2: IR line sensor center
            3: IR line sensor right
            4: IR line sensor most right
            10: Battery level

        Returns
        -------
        int
            The value read from the specified analog sensor channel.
        """
        return self._read_channel(channel)

    def get_battery_level(self, max_voltage: float = 7.2, min_voltage: float = 6.0, divider_ratio: float = 2.0) -> float:
        """
        Get the battery level as a percentage.

        The battery is two 1CR14500 3.6V in series, so the nominal voltage is 7.2V (3.6V * 2).
        The minimum voltage is around 6.0V (3.0V per cell) when the battery is considered empty.

        Parameters
        ----------
        max_voltage : float, optional
            The voltage corresponding to 100% battery.
        min_voltage : float, optional
            The voltage corresponding to 0% battery.
        divider_ratio : float, optional
            The ratio of the voltage divider used to step down the battery voltage to the ADC input.

        Returns
        -------
        float
            The battery level as a percentage (0-100%).

        Notes
        -----
        - This code assumes that the battery is a 2S Li-ion pack (7.4V nominal, 8.4V fully charged, 6.72V empty)
        - The connexion is based (channel 10, voltage divider) on https://www.waveshare.com/w/upload/7/72/AlphaBot2-Pi-Schematic.pdf
        - The reference voltage (VREF) of the ADC is 3.3V, according the schematic, so the maximum measurable voltage with a 1:2 divider is around 6.6V, which is not sufficient for a 2S Li-ion pack. If the battery voltage exceeds this, the code will clamp the percentage to 100%.
        """
        if max_voltage <= min_voltage:
            raise ValueError("max_voltage must be greater than min_voltage")

        # Adjust max_voltage based on the voltage divider to ensure we don't report over 100% if the battery is fully charged
        if self.VREF * divider_ratio <= max_voltage:
            max_voltage = self.VREF * divider_ratio

        # Channel 10 is connected to the battery voltage divider on AlphaBot2
        battery_value = self._read_channel(10)

        # Convert raw ADC value to voltage
        battery_voltage = (battery_value / (2**self.BITS - 1)) * self.VREF
        battery_voltage *= divider_ratio
        
        # Convert voltage to percentage
        battery_level = (battery_voltage - min_voltage) / (max_voltage - min_voltage)
        battery_level = max(0.0, min(100.0, battery_level * 100))  # Clamp to 0-100%
        return battery_level

    def _read_channel(self, channel: int) -> int:
        """
        Read a raw 10-bit ADC value (0–1023) from the specified TLC chips channel.

        This code was taken from the original TRSensor class and adapted to be more general and reusable. The TLC chips requires a specific sequence of operations to read a channel, which is seemingly implemented working in TRSensor.

        Parameters
        ----------
        channel : int
            The ADC channel to read (0–10).

        Returns
        -------
        int
            The raw ADC value read from the TLC chips (0–1023).

        Raises
        ------
        ValueError
            If the channel is not within the valid range.
        """
        if channel < 0 or channel > 10:
            raise ValueError("Channel must be between 0 and 10")
        value = [0,0]
        # Read the same channel twice to get the result (first read starts conversion, second read gets result)
        for j, ch in enumerate([channel, channel]):
            GPIO.output(self.CS, GPIO.LOW)
            for i in range(0,8):
                #sent 8-bit Address
                if i<4:
                    if(((ch) >> (3 - i)) & 0x01):
                        GPIO.output(self.ADDR,GPIO.HIGH)
                    else:
                        GPIO.output(self.ADDR,GPIO.LOW)
                else:
                    GPIO.output(self.ADDR,GPIO.LOW)		
                #read MSB 4-bit data
                value[j] <<= 1
                if(GPIO.input(self.DATA)):
                    value[j] |= 0x01
                GPIO.output(self.CLK,GPIO.HIGH)
                GPIO.output(self.CLK,GPIO.LOW)
            for i in range(0,4):
                #read LSB 8-bit data
                value[j] <<= 1
                if(GPIO.input(self.DATA)):
                    value[j] |= 0x01
                GPIO.output(self.CLK,GPIO.HIGH)
                GPIO.output(self.CLK,GPIO.LOW)
            time.sleep(0.0001)
            GPIO.output(self.CS,GPIO.HIGH)
        for i in range(0,2):
            value[i] >>= 2
        return value[1]  # Return the second read which contains the result of the conversion
#!/usr/bin/python
# -*- coding:utf-8 -*-
import RPi.GPIO as GPIO
import time


# ------------------------------------------------------------
# This class provides an interface for reading analog values from the ADC used on the AlphaBot2-P.
# On schematic, the chip is labeled as TLC1543, but it is actually a TLC2543C, which has the same pinout and behavior.
# The code is adapted from the original TRSensor class to be more general and reusable for any ADC channel.
# The TLC2543C is a 10-bit ADC that uses GPIO bit-banging to communicate, and this class abstracts that communication to allow easy reading of analog values and battery voltage on the AlphaBot2-P.
# ------------------------------------------------------------
class AnalogSensors:
    """
        Interface for reading analog values from the ADC used on the AlphaBot2-P.

        This class provides low-level access to the 10-bit analog-to-digital
        converter through GPIO bit-banging. It allows reading any of the 11 ADC
        channels (0–10), converting raw ADC values to voltages, and retrieving the
        robot's battery voltage using the built-in voltage divider on the AlphaBot2.

        Implemented with assistance from AI (Copilot)

        Parameters
        ----------
        cs : int, optional
            GPIO pin connected to CS (chip select). Default is 5.
        clk : int, optional
            GPIO pin connected to CLK (clock). Default is 25.
        addr : int, optional
            GPIO pin connected to ADDR (address input). Default is 24.
        data : int, optional
            GPIO pin connected to DATA OUT. Default is 23.
        vref : float, optional
            Reference voltage for the ADC. On AlphaBot2 this is 3.3V.

        Methods
        -------
        read_channel(channel)
            Reads a raw 10-bit ADC value (0–1023) from the specified channel.
        read_voltage(channel)
            Returns the measured voltage at the ADC pin based on Vref.
        get_battery_voltage(channel=6, divider_ratio=11.0)
            Returns the robot's battery voltage using the onboard voltage divider.

        Notes
        -----
        - The chips uses a 4-bit channel address and outputs a 10-bit result.
        - The AlphaBot2-P connects its battery through a ~1:11 voltage divider
        to ADC channel 6, allowing safe measurement of Li-ion battery packs.
        - All GPIO operations use BCM numbering.
    """
    def __init__(self, cs=5, clk=25, addr=24, data=23, vref=3.3):
        """
        Initialize the GPIO pins for communicating with the ADC.

        Parameters:
        -----------
        cs : int, optional
            GPIO pin connected to CS (chip select). Default is 5.
        clk : int, optional
            GPIO pin connected to CLK (clock). Default is 25.
        addr : int, optional
            GPIO pin connected to ADDR (address input). Default is 24.
        data : int, optional
            GPIO pin connected to DATA OUT. Default is 23.
        vref : float, optional
            Reference voltage for the ADC. On AlphaBot2 this is 3.3V.
        """
        self.CS = cs
        self.CLK = clk
        self.ADDR = addr
        self.DATA = data
        self.VREF = vref

        self.BITS = 10  # chip is a 10-bit ADC

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.CS, GPIO.OUT)
        GPIO.setup(self.CLK, GPIO.OUT)
        GPIO.setup(self.ADDR, GPIO.OUT)
        GPIO.setup(self.DATA, GPIO.IN, GPIO.PUD_UP)

        GPIO.output(self.CS, GPIO.HIGH)
        GPIO.output(self.CLK, GPIO.LOW)

    def read_channel(self, channel: int) -> int:
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

    ##############################################################
        # The following code is not working, but I keep it here for reference.
        # The chips is a bit tricky to read because it requires sending the channel address and then reading the result in a specific sequence.
        # The code below is a simplified version that may not work correctly without proper timing and sequencing.
        # def clock_pulse(self):
        #     """
        #     Generate a clock pulse on the CLK pin.
        #     """
        #     GPIO.output(self.CLK, GPIO.HIGH)
        #     # Short delay to meet timing
        #     time.sleep(1e-6)
        #     GPIO.output(self.CLK, GPIO.LOW)
        #     time.sleep(1e-6)

        # def select_channel(self, channel: int):
        #     """
        #     Send 4-bit address (channel) to ADC.

        #     Parameters
        #     ----------
        #     channel : int
        #         The ADC channel to select (0–10).
        #     """
        #     # CS low to start
        #     GPIO.output(self.CS, GPIO.LOW)
        #     # Send 4 bits MSB first
        #     for bit in [3, 2, 1, 0]:
        #         GPIO.output(self.ADDR, GPIO.HIGH if (channel >> bit) & 0x1 else GPIO.LOW)
        #         self.clock_pulse()
        #     # After address, chips starts conversion automatically

        # def read_conversion(self) -> int:
        #     """
        #     Read 10-bit conversion result from chips.
        #     Data is shifted out MSB first on DOUT.

        #     Returns
        #     -------
        #     int
        #          The raw ADC value read from the chips (0–1023).
        #     """
        #     value = 0
        #     for _ in range(self.BITS):
        #         self.clock_pulse()
        #         bit = GPIO.input(self.DATA)
        #         value = (value << 1) | bit
        #     return value

        # def read_channel(self, channel: int) -> int:
        #     """
        #     Read a raw 10-bit ADC value (0–1023) from the specified channel.

        #     Parameters
        #     ----------
        #     channel : int
        #         The ADC channel to read (0–10).

        #     Returns
        #     -------
        #     int
        #         The raw ADC value.

        #     Raises
        #     ------
        #     ValueError
        #         If the channel is not within the valid range.
        #     """
        #     # Dummy cycle to start conversion
        #     self.select_channel(channel)
        #     # Wait for conversion (datasheet: ~26 clock cycles; we just delay)
        #     time.sleep(0.001)

        #     # Now send same channel again and read previous result
        #     self.select_channel(channel)
        #     value = self.read_conversion()

        #     # CS high to end
        #     GPIO.output(self.CS, GPIO.HIGH)
        #     return value
    ##############################################################

    # ------------------------------------------------------------
    # Battery voltage helper (AlphaBot2)
    # ------------------------------------------------------------
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
        """
        if max_voltage <= min_voltage:
            raise ValueError("max_voltage must be greater than min_voltage")

        # Adjust max_voltage based on the voltage divider to ensure we don't report over 100% if the battery is fully charged
        if self.VREF * divider_ratio <= max_voltage:
            max_voltage = self.VREF * divider_ratio

        # Channel 10 is connected to the battery voltage divider on AlphaBot2
        battery_value = self.read_channel(10)

        # Convert raw ADC value to voltage
        battery_voltage = (battery_value / (2**self.BITS - 1)) * self.VREF
        battery_voltage *= divider_ratio
        
        # Convert voltage to percentage
        battery_level = (battery_voltage - min_voltage) / (max_voltage - min_voltage)
        battery_level = max(0.0, min(100.0, battery_level * 100))  # Clamp to 0-100%
        return battery_level
        

#!/usr/bin/python
# -*- coding:utf-8 -*-
import RPi.GPIO as GPIO
import time

class AnalogSensors:
    """
        Interface for reading analog values from the TLC1543 ADC used on the AlphaBot2-P.

        This class provides low-level access to the TLC1543 10-bit analog-to-digital
        converter through GPIO bit-banging. It allows reading any of the 11 ADC
        channels (0–10), converting raw ADC values to voltages, and retrieving the
        robot's battery voltage using the built-in voltage divider on the AlphaBot2.

        AI generated (Copilot)

        Parameters
        ----------
        cs : int, optional
            GPIO pin connected to TLC1543 CS (chip select). Default is 5.
        clk : int, optional
            GPIO pin connected to TLC1543 CLK (clock). Default is 25.
        addr : int, optional
            GPIO pin connected to TLC1543 ADDR (address input). Default is 24.
        data : int, optional
            GPIO pin connected to TLC1543 DATA OUT. Default is 23.
        vref : float, optional
            Reference voltage for the ADC. On AlphaBot2 this is 3.3V.

        Methods
        -------
        read_channel(channel)
            Reads a raw 10-bit ADC value (0–1023) from the specified TLC1543 channel.
        read_voltage(channel)
            Returns the measured voltage at the ADC pin based on Vref.
        get_battery_voltage(channel=6, divider_ratio=11.0)
            Returns the robot's battery voltage using the onboard voltage divider.

        Notes
        -----
        - The TLC1543 uses a 4-bit channel address and outputs a 10-bit result.
        - The AlphaBot2-P connects its battery through a ~1:11 voltage divider
        to ADC channel 6, allowing safe measurement of Li-ion battery packs.
        - All GPIO operations use BCM numbering.
    """
    def __init__(self, cs=5, clk=25, addr=24, data=23, vref=3.3):
        """
        Initialize the GPIO pins for communicating with the TLC1543 ADC.

        Parameters:
        -----------
        cs : int, optional
            GPIO pin connected to TLC1543 CS (chip select). Default is 5.
        clk : int, optional
            GPIO pin connected to TLC1543 CLK (clock). Default is 25.
        addr : int, optional
            GPIO pin connected to TLC1543 ADDR (address input). Default is 24.
        data : int, optional
            GPIO pin connected to TLC1543 DATA OUT. Default is 23.
        vref : float, optional
            Reference voltage for the ADC. On AlphaBot2 this is 3.3V.
        """
        self.CS = cs
        self.CLK = clk
        self.ADDR = addr
        self.DATA = data
        self.VREF = vref  # TLC1543 reference voltage (3.3V on AlphaBot2)

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.CS, GPIO.OUT)
        GPIO.setup(self.CLK, GPIO.OUT)
        GPIO.setup(self.ADDR, GPIO.OUT)
        GPIO.setup(self.DATA, GPIO.IN, GPIO.PUD_UP)

        GPIO.output(self.CS, GPIO.HIGH)
        GPIO.output(self.CLK, GPIO.LOW)

    # ------------------------------------------------------------
    # Read a single TLC1543 analog channel (0–10)
    # ------------------------------------------------------------
    def read_channel(self, channel: int) -> int:
        """
        Read a raw 10-bit ADC value (0–1023) from the specified TLC1543 channel.

        Parameters
        ----------
        channel : int
            The ADC channel to read (0–10).

        Returns
        -------
        int
            The raw ADC value.

        Raises
        ------
        ValueError
            If the channel is not within the valid range.
        """

        if channel < 0 or channel > 10:
            raise ValueError("TLC1543 channel must be 0–10")

        # Start conversion
        GPIO.output(self.CS, GPIO.LOW)

        # Send 4-bit channel address
        for i in [3, 2, 1, 0]:
            bit = (channel >> i) & 1
            GPIO.output(self.ADDR, bit)
            time.sleep(0.000002)
            GPIO.output(self.CLK, GPIO.HIGH)
            time.sleep(0.000002)
            GPIO.output(self.CLK, GPIO.LOW)

        # Read 10-bit result
        value = 0
        for _ in range(10):
            GPIO.output(self.CLK, GPIO.HIGH)
            time.sleep(0.000002)
            GPIO.output(self.CLK, GPIO.LOW)
            value = (value << 1) | GPIO.input(self.DATA)

        GPIO.output(self.CS, GPIO.HIGH)
        return value  # 0–1023

    # ------------------------------------------------------------
    # Convert ADC reading to voltage
    # ------------------------------------------------------------
    def read_voltage(self, channel: int) -> float:
        """
        Read the voltage from the specified ADC channel.

        Parameters
        ----------
        channel : int
            The ADC channel to read (0–10).

        Returns
        -------
        float
            The voltage reading.
        """
        raw = self.read_channel(channel)
        return raw * self.VREF / 1023.0

    # ------------------------------------------------------------
    # Battery voltage helper (AlphaBot2 uses ~1:11 divider)
    # ------------------------------------------------------------
    def get_battery_voltage(self, channel: int=6, divider_ratio: float=11.0) -> float:
        """
        Get the battery voltage from the specified ADC channel.

        Parameters
        ----------
        channel : int, optional
            The ADC channel to read (0–10). Default is 6.
        divider_ratio : float, optional
            The voltage divider ratio. Default is 11.0.

        Returns
        -------
        float
            The battery voltage.
        """
        adc_voltage = self.read_voltage(channel)
        battery_voltage = adc_voltage * divider_ratio
        return battery_voltage

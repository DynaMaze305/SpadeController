Here’s a clean, readable Markdown document you can drop into your repository. It explains the purpose, structure, and usage of your `AnalogSensors` class without overwhelming the reader.

---

# `AnalogSensors` — ADC Interface for AlphaBot2

The `AnalogSensors` class provides a lightweight Python interface for reading analog values from the TLC-series ADC used on the **AlphaBot2** robot platform. It handles GPIO setup, channel reading, and includes a helper for estimating the robot’s battery level.

---

## Features

- Communicates with the ADC using GPIO bit‑banging  
- Reads **10‑bit** analog values (0–1023)  
- Supports all ADC channels (0–10)  
- Provides a **battery level percentage** helper using the AlphaBot2’s voltage divider  
- Designed to be reusable beyond the original TRSensor implementation  

---

## Initialization

```python
sensors = AnalogSensors(
    cs=5,
    clk=25,
    addr=24,
    data=23,
    vref=3.3
)
```

### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `cs` | int | 5 | Chip Select pin |
| `clk` | int | 25 | Clock pin |
| `addr` | int | 24 | Address pin |
| `data` | int | 23 | Data output pin |
| `vref` | float | 3.3 | ADC reference voltage |

The class configures the GPIO pins in BCM mode and prepares the ADC for communication.

---

## Reading an ADC Channel

```python
value = sensors.read_channel(3)
```

Reads a **raw 10‑bit value** from the specified ADC channel.

### Behavior

- Valid channels: **0–10**
- Performs two reads:
  - First read triggers conversion
  - Second read retrieves the result
- Returns an integer between **0 and 1023**

### Raises

- `ValueError` if the channel is outside the valid range

---

## ADC Channel Mapping (AlphaBot2)

The AlphaBot2 uses a TLC-series 10‑bit ADC with **11 channels (0–10)**.  
Most channels are connected to the line‑tracking sensors, while channel **10** is reserved for battery monitoring.

| Channel | Connected To | Description |
|---------|--------------|-------------|
| **0** | IR1 | Left‑most IR reflectance sensor |
| **1** | IR2 | IR reflectance sensor |
| **2** | IR3 | IR reflectance sensor |
| **3** | IR4 | IR reflectance sensor |
| **4** | IR5 | Right‑most IR reflectance sensor |
| **5** | - | No used |
| **6** | - | No used |
| **7** | - | No used |
| **8** | - | No used |
| **9** | - | No used |
| **10** | Battery Voltage Divider | Reads scaled battery voltage for charge estimation |

### Notes

- Channels **0–7** correspond to the 8‑element line sensor array.  
- Channels **8** and **9** exist on the ADC but are not wired on the AlphaBot2 board.  
- Channel **10** is wired through a **2:1 voltage divider**, allowing safe measurement of the ~7.4 V battery pack using a 3.3 V ADC.

---

## Battery Level Helper

The AlphaBot2 includes a voltage divider connected to ADC **channel 10**, allowing the robot to estimate battery charge.

```python
level = sensors.get_battery_level()
print(f"Battery: {level:.1f}%")
```

### How it works

1. Reads ADC channel 10  
2. Converts the raw value to voltage using `vref` (3.3 V)  
3. Applies the voltage divider ratio  
4. Maps the voltage to a percentage between `min_voltage` and `max_voltage`  

### Parameters

| Name | Default | Meaning |
|------|---------|---------|
| `max_voltage` | 7.2 V | Voltage at 100% battery |
| `min_voltage` | 6.0 V | Voltage at 0% battery |
| `divider_ratio` | 2.0 | Divider scaling factor |

### Notes

- AlphaBot2 uses a **2S Li‑ion pack** (nominal 7.4 V)  
- Fully charged voltage may exceed the default `max_voltage`
    - This is due to the `vref` and divider composition limiting the max measure.
    - If `max_voltage` exceeds `divider_ratio` * `vref` = 6.6 V, then it is replaced.
- The method clamps the result to **0–100%**

---

## Example Usage

```python
from analog_sensors import AnalogSensors

sensors = AnalogSensors()

# Read line sensor channel
line_value = sensors.read_channel(2)
print("Line sensor:", line_value)

# Read battery level
battery = sensors.get_battery_level()
print(f"Battery level: {battery:.2f}%")
```

---

## Hardware Reference

The implementation follows the ADC wiring and battery voltage divider described in the AlphaBot2‑Pi schematic:

- Channel **10** → battery voltage divider  
- ADC reference voltage: **3.3 V**  
- ADC resolution: **10 bits**

import os, time, csv
import spidev

# ---------- ENV CALIBRATION ----------
GAIN = float(os.getenv("GAIN", "50.0"))  # OP07 gain
SHUNT_MV_PER_A = float(os.getenv("SHUNT_MV_PER_A", "0.5"))  # mV per A at shunt
V_DIV_TOP = float(os.getenv("V_DIV_TOP_OHMS", "1000000"))   # ohms
V_DIV_BOTTOM = float(os.getenv("V_DIV_BOTTOM_OHMS", "33000"))  # ohms
SAMPLE_PERIOD = float(os.getenv("SAMPLE_PERIOD_S", "0.5"))
LOG_PATH = os.getenv("LOG_PATH", "/data/log.csv")

# MCP3008 runs from 3.3V; set ADC reference to 3.3V
VREF = 3.3

# ---------- MCP3008 SPI SETUP ----------
spi = spidev.SpiDev()
spi.open(0, 0)                 # bus 0, CE0
spi.max_speed_hz = 1350000     # 1.35 MHz is safe
spi.mode = 0

def read_mcp3008(ch: int) -> int:
    """Return 10-bit ADC value from channel 0..7."""
    if not (0 <= ch <= 7):
        raise ValueError("MCP3008 channel must be 0-7")
    # Protocol: start bit, single-ended, channel bits, null
    resp = spi.xfer2([1, (8 + ch) << 4, 0])
    # resp = [junk, high bits, low bits]; 10-bit value in last 2 bytes
    value = ((resp[1] & 0x03) << 8) | resp[2]
    return value

def adc_to_volts(counts: int) -> float:
    return counts * (VREF / 1023.0)

def main():
    # Create log file if new
    new_file = not os.path.exists(LOG_PATH)
    f = open(LOG_PATH, "a", newline="")
    w = csv.writer(f)
    if new_file:
        w.writerow(["time_s", "voltage_V", "current_A", "power_W",
                    "adc_v_V", "adc_i_V", "raw_v", "raw_i"])

    t0 = time.time()
    while True:
        raw_i = read_mcp3008(0)      # CH0: OP07 amplified shunt
        raw_v = read_mcp3008(1)      # CH1: divider voltage

        adc_i_v = adc_to_volts(raw_i)
        adc_v_v = adc_to_volts(raw_v)

        # Undo op-amp gain to get shunt mV
        shunt_volts = adc_i_v / GAIN
        # Current (A) from shunt mV-per-amp
        current_a = (shunt_volts * 1000.0) / SHUNT_MV_PER_A

        # Undo divider to get actual bus voltage
        v_ratio = (V_DIV_TOP + V_DIV_BOTTOM) / V_DIV_BOTTOM
        bus_v = adc_v_v * v_ratio

        power_w = bus_v * current_a

        w.writerow([round(time.time()-t0, 3),
                    round(bus_v, 3), round(current_a, 3),
                    round(power_w, 3),
                    round(adc_v_v, 4), round(adc_i_v, 4),
                    raw_v, raw_i])
        f.flush()
        time.sleep(SAMPLE_PERIOD)

if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            spi.close()
        except Exception:
            pass

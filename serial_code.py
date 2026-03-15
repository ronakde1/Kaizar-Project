import serial
import time

# ------------------- CONFIG -------------------
# Replace with your Arduino's COM port and baud rate
arduino_port = "/dev/tty.usbserial-10"  # Linux/Mac
# arduino_port = "COM3"        # Windows example
baud_rate = 9600
timeout = 2  # seconds
# ---------------------------------------------

# Open serial connection
ser = serial.Serial(arduino_port, baud_rate, timeout=timeout)
time.sleep(2)  # wait for Arduino to initialize

# Array to store data
data_array = []

try:
    while True:
        line = ser.readline().decode('utf-8').strip()  # read a line from serial
        if line:
            try:
                # Split the CSV string into values
                dist_str, temp_str, loud_str = line.split(',')
                temperature = float(temp_str)
                distance = float(dist_str)
                loud = int(loud_str)

                # Append as a tuple (temperature, distance, loud)
                data_array.append((temperature, distance, loud))
                
                print(f"Read: Temp={temperature}, Distance={distance}, Loud={loud}")
            
            except ValueError:
                # Skip any malformed lines
                print(f"Malformed line: {line}")
except KeyboardInterrupt:
    print("Stopped by user")

finally:
    ser.close()
    print("Final data array:", data_array)
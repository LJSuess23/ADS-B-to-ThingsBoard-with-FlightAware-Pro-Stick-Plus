# ADS-B-to-ThingsBoard-with-FlightAware-Pro-Stick-Plus
This project turns live aircraft broadcasts (ADS-B) into a real-time IoT data stream.
Using a Raspberry Pi and a 1090 MHz ADS-B SDR receiver, aircraft data is captured by an 1090MHz antenna, processed locally in Python, and sent via MQTT to an ThingsBoard dashboard.
Built for the university module “Funksysteme für IoT”

I.Aircraft continuously broadcast ADS-B messages on 1090 MHz
II.An SDR stick captures the raw RF data
III. dump1090-fa decodes the signals into usable aircraft data
IV. Python Code: filters aircraft, prioritizes relevant targets and assigns them to fixed slots
V. Selected aircraft are published as MQTT telemetry
VI. ThingsBoard runs inside Docker containers and visualizes the data live

Hardware-List:
ADS-B Receiver: [https://www.berrybase.de/flightaware-pro-stick-plus-usb-sdr-ads-b-receiver
1090MHz-Antenna: https://shorturl.at/QgZZZ #long Amazon-link :D
Microcontroller: Raspberry PI 3,4 or 5

What you need in Software:
Linux (Ubuntu / Raspberry Pi OS)
dump1090-fa
Python 3
Mosquitto (MQTT Broker)
Docker & Docker Compose
ThingsBoard (running in Docker)

# clone repository
git clone https://github.com/LJSuess23/ADS-B-to-ThingsBoard-with-FlightAware-Pro-Stick-Plus.git
cd ADS-B-to-ThingsBoard-with-FlightAware-Pro-Stick-Plus

# start IoT backend (ThingsBoard, MQTT, DB)
docker compose up -d #or just start it in Docker Desktop

# start ADS-B decoder
sudo systemctl start dump1090-fa #from the FlightAware Stick, recommend to read the tutorial https://de.flightaware.com/adsb/prostick/setup/

# run the IoT publisher
python3 adsb_slots_to_tb.py

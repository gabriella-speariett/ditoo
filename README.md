# Divoom Ditoo Weather Display

A Python daemon to control a [Divoom Ditoo](https://divoom.com/) pixel art display device, showing animated GIFs based on current weather conditions, time of day, and a rotating default gallery.

## Features

- **Weather-Aware Display**: Fetches current weather and displays contextual GIFs (rain, clouds, sun, snow, etc.)
- **Time-Based Animations**: Shows special GIFs during sunrise and sunset windows
- **Smart Polling**: Only fetches weather during configurable active hours (e.g., 6am–10pm)
- **Notifications**: Plays a sound alert when weather changes significantly
- **Low-Power Sleep Mode**: Respects sleep windows to avoid unnecessary updates
- **Bluetooth Connectivity**: Communicates with Ditoo device via RFCOMM Bluetooth protocol

## Requirements

- Python 3.13+
- Divoom Ditoo device
- Bluetooth connectivity to your device
- Linux, for other operating systems, you will have to adapt the bluetooth connection & sound playback code

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ditoo
```

2. Create a virtual environment and install dependencies, ideally with `uv`

## Configuration

Edit `config.toml` with your settings:

```toml
# Divoom device Bluetooth MAC address
mac = "B1:21:81:22:B8:E1"

# Location for weather data (coordinates for your location)
latitude = 0
longitude = 0

# Timezone for time-based logic
timezone = "Europe/London"

# Weather polling interval in seconds (e.g., 900 = 15 minutes)
weather_poll_interval = 900

# How long to display weather GIFs after a weather poll (seconds)
weather_showcase_duration = 120

# Sleep window (no weather polling outside these hours)
sleep_start_hour = 23
sleep_end_hour = 6

# Weather configuration (see src/weather/config.py for more options)
hot_threshold_c = 30
cold_threshold_c = 0

# Notification sound path
notification_sound_path = "assets/sounds/notify.wav"
```

### Finding Your Device's MAC Address

On Linux, you can use `bluetoothctl` to scan for devices:
```bash
bluetoothctl scan on
# Look for "Divoom-Ditoo" in the output and note its MAC address (format: XX:XX:XX:XX:XX:XX) to use in the config.
```

## Usage

Place the `ditoo.service` file in `/etc/systemd/system/` and ensure the path to the Python script is correct. Then enable and start the service:

```bash
sudo systemctl enable ditoo.service
sudo systemctl start ditoo.service
```

Then you can follow the logs with:
```bash
sudo journalctl -u ditoo.service -f
```

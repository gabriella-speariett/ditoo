import json
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


class WeatherFetchError(Exception):
    pass


@dataclass
class WeatherSnapshot:
    """Weather snapshot for the closest 15-minute interval."""

    fetched_at: datetime
    weathercode: int
    temperature_c: float
    precipitation_mm: float
    windspeed_kmh: float


def fetch_weather(latitude: float, longitude: float) -> dict:
    """Fetch weather for the closest 15-minute interval.

    Returns:
        dict - raw weather data from the API
    """
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            f"&minutely_15=temperature_2m,weather_code,wind_gusts_10m,precipitation"
            f"&timezone=auto"
        )

        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        return data

    except Exception as e:
        raise WeatherFetchError(f"Failed to fetch weather: {e}") from e


def parse_weather_data(data: dict) -> WeatherSnapshot:
    """Parse weather data from API response and return a WeatherSnapshot."""
    # Get current time in local timezone
    tz_name = data.get("timezone", "UTC")
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    # Parse minutely_15 times and values
    times_str = data["minutely_15"]["time"]
    temps = data["minutely_15"]["temperature_2m"]
    codes = data["minutely_15"]["weather_code"]
    wind_gusts = data["minutely_15"]["wind_gusts_10m"]
    precip = data["minutely_15"]["precipitation"]

    # Find closest 15-minute interval
    closest_idx = 0
    min_diff = float("inf")

    for i, time_str in enumerate(times_str):
        interval_time = datetime.fromisoformat(time_str).replace(tzinfo=tz)
        diff = abs((interval_time - now).total_seconds())
        if diff < min_diff:
            min_diff = diff
            closest_idx = i

    return WeatherSnapshot(
        fetched_at=now,
        weathercode=int(codes[closest_idx]),
        temperature_c=float(temps[closest_idx]),
        precipitation_mm=float(precip[closest_idx]),
        windspeed_kmh=float(wind_gusts[closest_idx]),
    )


def get_sun_times(latitude: float, longitude: float) -> tuple[datetime, datetime]:
    """Fetch sunrise and sunset for today.

    Returns:
        (sunrise, sunset) as timezone-aware datetimes
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        f"&daily=sunrise,sunset"
        f"&timezone=auto"
    )

    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))

    sunrise_timestamp = data["daily"]["sunrise"][0]
    sunset_timestamp = data["daily"]["sunset"][0]

    tz_name = data.get("timezone", "UTC")
    tz = ZoneInfo(tz_name)

    sunrise = datetime.fromisoformat(sunrise_timestamp).replace(tzinfo=tz)
    sunset = datetime.fromisoformat(sunset_timestamp).replace(tzinfo=tz)

    return sunrise, sunset

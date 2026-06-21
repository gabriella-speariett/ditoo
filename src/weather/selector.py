from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from .config import Config
from .weather import WeatherSnapshot

if TYPE_CHECKING:
    from typing import Literal


@dataclass
class SelectionContext:
    snapshot: WeatherSnapshot
    now: datetime
    sunrise: datetime
    sunset: datetime
    config: Config


def is_in_sleep_window(now: datetime, config: Config) -> bool:
    """Check if current time is in sleep window (accounts for midnight wrapping)."""
    if config.sleep_start_hour <= config.sleep_end_hour:
        return config.sleep_start_hour <= now.hour < config.sleep_end_hour
    else:
        return now.hour >= config.sleep_start_hour or now.hour < config.sleep_end_hour


def is_daytime(now: datetime, sunrise: datetime, sunset: datetime) -> bool:
    """Check if current time is between sunrise and sunset."""
    return sunrise < now < sunset


def in_horizon_window(
    now: datetime, sunrise: datetime, sunset: datetime, window_seconds: int = 2700
) -> Literal["sunrise", "sunset"] | None:
    """Check if we are close to a sunrise or sunset. Return 'sunrise', 'sunset', or None"""
    window = timedelta(seconds=window_seconds)

    if sunrise - window <= now <= sunrise + window:
        return "sunrise"
    if sunset - window <= now <= sunset + window:
        return "sunset"

    return None


def get_season(now: datetime) -> Literal["spring", "summer", "autumn", "winter"]:
    """Return season name for the current date."""
    match month := now.month:
        case 12 | 1 | 2:
            return "winter"
        case 3 | 4 | 5:
            return "spring"
        case 6 | 7 | 8:
            return "summer"
        case 9 | 10 | 11:
            return "autumn"
        case _:
            raise ValueError(f"Invalid month: {month}")


def select_gif(ctx: SelectionContext) -> Path:
    """
    Select GIF directory or file based on weather, time of day, and season.
    Returns a Path to either a directory (caller picks random .GIF)
    or a file Path (to use directly).
    """
    config = ctx.config
    snapshot = ctx.snapshot
    now = ctx.now
    wmo = snapshot.weathercode

    assets = config.assets_root

    if assets is None or not assets.exists():
        raise ValueError("Assets root is not set or does not exist")

    if is_in_sleep_window(now, config):
        return assets / "night.GIF"

    horizon = in_horizon_window(now, ctx.sunrise, ctx.sunset, config.horizon_window)
    if horizon == "sunrise":
        return assets / "horizons" / "sunrise"
    elif horizon == "sunset":
        return assets / "horizons" / "sunset"

    if 95 <= wmo <= 99:
        return assets / "storm"

    day_or_night = "day" if is_daytime(now, ctx.sunrise, ctx.sunset) else "night"

    if snapshot.precipitation_mm > 4.0:
        return assets / "rain" / day_or_night / "heavy"

    if snapshot.precipitation_mm > 0.0:
        return assets / "rain" / day_or_night / "light"

    temp = snapshot.temperature_c
    if temp >= config.very_hot_threshold_c:
        return assets / "sun" / "boiling"

    if temp >= config.hot_threshold_c:
        return assets / "sun" / "warm"

    if temp <= config.freezing_threshold_c:
        return assets / "cold" / "freezing"

    if temp <= config.cold_threshold_c:
        return assets / "cold" / "cold"

    season = get_season(now)
    return assets / "seasons" / season


def pick_random_gif(path: Path) -> Path:
    """If path is a file, return it. If dir, pick a uniformly random .GIF from it."""
    if path.is_file():
        return path

    gifs = list(path.glob("*.GIF")) + list(path.glob("*.gif"))
    if not gifs:
        raise ValueError(f"No GIFs found in {path}")

    return random.choice(gifs)

import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import NoReturn
from zoneinfo import ZoneInfo

from src.ditoo import Divoom
from src.logging import logger
from src.weather.config import load_config
from src.weather.selector import SelectionContext, pick_random_gif, select_gif
from src.weather.weather import fetch_weather, get_sun_times, parse_weather_data


def get_poll_minutes(interval: int) -> list[int]:
    """Get the minute marks when polling should occur based on interval.

    E.g., 900s (15min) interval -> [0, 15, 30, 45]
    E.g., 1800s (30min) interval -> [0, 30]
    """
    minutes_between_polls = interval // 60
    return [i * minutes_between_polls for i in range(60 // minutes_between_polls)]


def needs_refresh(last_fetch: datetime | None, interval: int, now: datetime) -> bool:
    """Check if we should poll at the current minute mark.

    Polls are triggered when the current minute matches an aligned time
    (determined by interval) AND we haven't already polled this minute.
    """
    if last_fetch is None:
        return True

    poll_minutes = get_poll_minutes(interval)
    current_minute = now.minute

    if current_minute not in poll_minutes:
        return False

    # Only poll once per minute even if loop runs multiple times
    return (now - last_fetch).total_seconds() >= 60


def pick_default_gif(
    assets_root: Path,
    now: datetime,
    sunrise: datetime,
    sunset: datetime,
    horizon_window: int = 2700,
) -> Path:
    """Pick sunrise/sunset gif if in window, otherwise pick random default."""
    sunrise_window_start = sunrise - timedelta(seconds=horizon_window)
    sunrise_window_end = sunrise + timedelta(seconds=horizon_window)

    sunset_window_start = sunset - timedelta(seconds=horizon_window)
    sunset_window_end = sunset + timedelta(seconds=horizon_window)

    if sunrise_window_start <= now <= sunrise_window_end:
        logger.info("In sunrise window, selecting sunrise gif")
        return assets_root / "horizons" / "sunrise"

    if sunset_window_start <= now <= sunset_window_end:
        logger.info("In sunset window, selecting sunset gif")
        return assets_root / "horizons" / "sunset"

    default_folder = assets_root / "default"
    if not default_folder.exists():
        raise FileNotFoundError(f"Default assets folder not found: {default_folder}")

    return pick_random_gif(default_folder)


def is_weather_poll_window(now: datetime, config) -> bool:
    """Check if current hour is between 6am and 10pm."""
    return config.sleep_end_hour <= now.hour < 22


def play_notification(sound_path: Path) -> None:
    if not sound_path.exists():
        logger.warning(f"Notification sound not found: {sound_path}")
        return
    try:
        subprocess.run(
            ["aplay", str(sound_path)],
            check=False,
            timeout=5,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        logger.debug(f"Could not play notification sound: {e}")


def run() -> NoReturn:
    config = load_config()
    logger.info(f"Starting daemon with MAC {config.mac}")
    logger.info(f"Location: {config.latitude}, {config.longitude}")
    logger.info(f"Sleep window: {config.sleep_start_hour}:00-{config.sleep_end_hour}:00")

    last_weather_poll: datetime | None = None
    weather_showcase_start: datetime | None = None
    weather_showcase_gif: Path | None = None

    current_default_gif: Path | None = None
    last_default_gif_pick: datetime | None = None
    default_gif_refresh_interval = 60  # Refresh default GIF every 60 seconds
    last_gif_path: Path | None = None

    sunrise, sunset = get_sun_times(config.latitude, config.longitude)

    local_tz = ZoneInfo(config.timezone)
    assets_root = config.assets_root

    if assets_root is None or not assets_root.exists():
        raise ValueError("Assets root is not set or does not exist")

    sound_path = Path(config.notification_sound_path)

    with Divoom(config.mac) as divoom:
        while True:
            now = datetime.now(tz=local_tz)

            # Weather polling: only during 6am-10pm window, at aligned minute marks
            if is_weather_poll_window(now, config) and needs_refresh(
                last_weather_poll, config.weather_poll_interval, now
            ):
                weather_showcase_start = now
                weather_data = fetch_weather(config.latitude, config.longitude)
                last_weather_poll = now
                logger.info(f"Weather polled at {now.strftime('%H:%M')}")
                snapshot = parse_weather_data(weather_data)

                ctx = SelectionContext(
                    snapshot=snapshot,
                    now=now,
                    sunrise=sunrise,
                    sunset=sunset,
                    config=config,
                )
                current_default_gif = None
                last_default_gif_pick = None
                weather_showcase_gif = pick_random_gif(select_gif(ctx))
                logger.info("Starting weather showcase")
                play_notification(sound_path)

            # Check if weather showcase should end
            if weather_showcase_start is not None:
                if (
                    now - weather_showcase_start
                ).total_seconds() >= config.weather_showcase_duration:
                    weather_showcase_start = None
                    weather_showcase_gif = None
                    logger.info("Weather showcase ended, reverting to default GIF")

            # Determine which GIF to display
            if weather_showcase_gif is None:
                # Refresh default GIF periodically or if not set
                if current_default_gif is None or (
                    last_default_gif_pick is not None
                    and (now - last_default_gif_pick).total_seconds()
                    >= default_gif_refresh_interval
                ):
                    current_default_gif = pick_default_gif(assets_root, now, sunrise, sunset)
                    last_default_gif_pick = now

            gif_to_display = weather_showcase_gif if weather_showcase_start else current_default_gif

            if gif_to_display:
                if gif_to_display != last_gif_path:
                    divoom.send_gif(gif_to_display)
                    last_gif_path = gif_to_display
                    logger.info(f"Display updated: {gif_to_display.name}")

            time.sleep(10)


if __name__ == "__main__":
    run()

import tomllib
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE.parent
PROJECT_ROOT = SRC.parent
ASSETS = PROJECT_ROOT / "assets"


@dataclass
class Config:
    mac: str
    latitude: float
    longitude: float
    timezone: str
    weather_poll_interval: int = 1800
    daily_refresh_interval: int = 86400
    weather_showcase_duration: int = 120
    horizon_window: int = 2700
    sleep_start_hour: int = 23
    sleep_end_hour: int = 6
    hot_threshold_c: float = 24.0
    very_hot_threshold_c: float = 28.0
    cold_threshold_c: float = 5.0
    freezing_threshold_c: float = 2.0
    notification_sound_path: Path = ASSETS / "sounds" / "notify.wav"
    assets_root: Path = ASSETS


def load_config(path: Path = Path("config.toml")) -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    return Config(**data)

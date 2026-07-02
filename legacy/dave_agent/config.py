from pathlib import Path
import tomllib


THINK_LEVELS = ["none", "minimal", "low", "medium", "high", "xhigh", "max"]


def load_config(path="dave.toml"):
    config_path = Path(path)
    if not config_path.exists():
        config_path = Path(__file__).resolve().parents[1] / path

    config = tomllib.loads(config_path.read_text())
    if config.get("think") == "":
        config["think"] = None
    return config

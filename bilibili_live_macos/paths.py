"""macOS 专用运行时目录。"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR_NAME = "data"


def data_root() -> Path:
    return PROJECT_ROOT / DATA_DIR_NAME


def config_file() -> Path:
    return data_root() / "config.json"


def accounts_file() -> Path:
    return data_root() / "accounts.json"


def log_file() -> Path:
    return data_root() / "logs" / "bilibili_live_macos.log"


def qr_dir() -> Path:
    return data_root() / "qr"


def cache_dir() -> Path:
    return data_root() / "cache"


def ensure_runtime_dirs() -> None:
    for path in (data_root(), log_file().parent, qr_dir(), cache_dir()):
        path.mkdir(parents=True, exist_ok=True)

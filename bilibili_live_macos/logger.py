"""轻量文件日志。"""

from datetime import datetime
from pathlib import Path

from . import obs_bridge as bridge
from .paths import log_file, ensure_runtime_dirs


class Logger:
    def __init__(self) -> None:
        ensure_runtime_dirs()
        self.path: Path = log_file()

    def _write(self, level: str, message: str) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{now} [{level}] {message}\n"
        try:
            with self.path.open("a", encoding="utf-8") as file:
                file.write(line)
        except OSError:
            pass

    def info(self, message: str) -> None:
        self._write("INFO", message)
        bridge.log(0, message)

    def warning(self, message: str) -> None:
        self._write("WARN", message)
        bridge.log(2, message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)
        bridge.log(3, message)

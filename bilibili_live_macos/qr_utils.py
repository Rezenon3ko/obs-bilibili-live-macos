"""二维码图片生成与打开。"""

from datetime import datetime
import subprocess
from pathlib import Path
from typing import Optional

import qrcode

from .paths import qr_dir


def make_qr_image(content: str, prefix: str) -> Path:
    qr_dir().mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = qr_dir() / f"{prefix}_{stamp}.png"

    maker = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    maker.add_data(content)
    maker.make(fit=True)
    image = maker.make_image(fill_color="black", back_color="white")
    image.save(path)
    return path


def open_image(path: Path) -> None:
    try:
        subprocess.Popen(
            ["open", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return


class QrPreview:
    """可关闭的 Quick Look 预览窗口。"""

    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None

    def open(self, path: Path) -> None:
        self.close()
        try:
            self._process = subprocess.Popen(
                ["qlmanage", "-p", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            self._process = None

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

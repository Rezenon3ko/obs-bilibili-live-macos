"""二维码登录状态机。"""

from pathlib import Path
from typing import Callable, Optional

from ..api.auth_api import BiliAccountApi
from ..qr_utils import make_qr_image, open_image
from .account_store import AccountStore


POLL_INTERVAL_SECONDS = 1.5


class LoginFlow:
    """管理一次二维码登录从生成到持久化的完整过程。"""

    def __init__(
        self,
        api: BiliAccountApi,
        account_store: AccountStore,
        open_qr: Optional[Callable[[Path], None]] = None,
        close_qr: Optional[Callable[[], None]] = None,
    ) -> None:
        self.api = api
        self.account_store = account_store
        self.open_qr_callback = open_qr
        self.close_qr_callback = close_qr
        self.state = "idle"
        self.message = "未开始登录"
        self.qr_key: Optional[str] = None
        self.qr_path: Optional[Path] = None
        self._elapsed = 0.0

    @property
    def is_active(self) -> bool:
        return self.state in {"waiting", "scanned"}

    def show_current_qr(self) -> None:
        if self.qr_path is not None:
            self._open_qr_image()

    def begin(self) -> bool:
        self._discard_qr_image()
        ticket = self.api.create_ticket()
        if not ticket.ok:
            self.state = "error"
            self.message = ticket.message
            return False

        self.qr_key = ticket.qr_key
        self.qr_path = self._write_qr_image(ticket.qr_content)
        self.state = "waiting"
        self.message = "二维码已生成，请使用 B 站 App 扫码"
        self._elapsed = 0.0
        self._open_qr_image()
        return True

    def tick(self, delta_seconds: float) -> None:
        if not self.is_active:
            return

        self._elapsed += float(delta_seconds)
        if self._elapsed < POLL_INTERVAL_SECONDS:
            return

        self._elapsed = 0.0
        if not self.qr_key:
            self.state = "error"
            self.message = "登录状态异常，请重新获取二维码"
            return

        result = self.api.check_ticket(self.qr_key)
        self.state = result.state
        self.message = result.message

        if result.state == "scanned":
            return

        if result.state == "success" and result.cookies:
            self._finish_success(result.cookies)
            return

        if result.state in {"expired", "error"}:
            self.qr_key = None
            self._discard_qr_image()

    def status_text(self) -> str:
        return self.message

    def _finish_success(self, cookies) -> None:
        profile = self.api.fetch_profile()
        if "_error" in profile:
            self.qr_key = None
            self._discard_qr_image()
            self.state = "error"
            self.message = f"登录成功但获取账号信息失败：{profile['_error']}"
            return

        self.account_store.save(cookies, profile)
        self.qr_key = None
        self._discard_qr_image()
        self.state = "success"
        self.message = f"登录成功：{profile.get('uname') or profile.get('mid') or '未知用户'}"

    def _discard_qr_image(self) -> None:
        if self.close_qr_callback is not None:
            self.close_qr_callback()
        if self.qr_path is None:
            return
        try:
            self.qr_path.unlink()
        except OSError:
            pass
        self.qr_path = None

    def _write_qr_image(self, content: str) -> Path:
        return make_qr_image(content, "login")

    def _open_qr_image(self) -> None:
        if self.qr_path is None:
            return
        if self.open_qr_callback is not None:
            self.open_qr_callback(self.qr_path)
        else:
            open_image(self.qr_path)

"""账号凭据的本地持久化。"""

from datetime import datetime
from typing import Any, Dict, Optional

from ..config_store import ConfigStore


class AccountStore:
    """保存当前登录账号的 Cookie 和简单资料。"""

    def __init__(self, store: ConfigStore) -> None:
        self.store = store

    def current(self) -> Dict[str, Any]:
        data = self.store.read()
        account = data.get("account") or {}
        return account if isinstance(account, dict) else {}

    def save(self, cookies: Dict[str, str], profile: Dict[str, Any]) -> Dict[str, Any]:
        account = {
            "uid": str(profile.get("mid") or cookies.get("DedeUserID") or ""),
            "uname": profile.get("uname") or "",
            "cookies": cookies,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.store.set("account", account)
        return account

    def clear(self) -> None:
        data = self.store.read()
        data.pop("account", None)
        self.store.write(data)

    def is_logged_in(self) -> bool:
        account = self.current()
        return bool(account.get("uid") and account.get("cookies"))

    def cookies(self) -> Dict[str, str]:
        cookies = self.current().get("cookies") or {}
        return cookies if isinstance(cookies, dict) else {}

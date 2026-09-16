"""B 站账号登录与身份信息接口。"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlsplit

import requests


_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_PASSPORT_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://passport.bilibili.com",
    "Referer": "https://passport.bilibili.com/login",
}

_API_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.bilibili.com/",
}

GENERATE_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"


@dataclass
class LoginTicket:
    ok: bool
    message: str = ""
    qr_content: str = ""
    qr_key: str = ""


@dataclass
class LoginPoll:
    ok: bool
    state: str = "idle"
    message: str = ""
    cookies: Optional[Dict[str, str]] = None


class BiliAccountApi:
    """负责二维码登录和当前账号信息查询。"""

    def __init__(self) -> None:
        self.session = requests.Session()

    def create_ticket(self) -> LoginTicket:
        try:
            response = self.session.get(
                GENERATE_URL,
                headers=_PASSPORT_HEADERS,
                timeout=10,
            )
            payload = response.json()
        except requests.RequestException as exc:
            return LoginTicket(ok=False, message=f"网络请求失败：{exc}")
        except ValueError:
            return LoginTicket(ok=False, message="二维码接口返回了无效 JSON")

        if payload.get("code") != 0:
            return LoginTicket(
                ok=False,
                message=str(payload.get("message") or "获取二维码失败"),
            )

        data = payload.get("data") or {}
        qr_content = data.get("url") or ""
        qr_key = data.get("qrcode_key") or ""
        if not qr_content or not qr_key:
            return LoginTicket(ok=False, message="二维码数据不完整")

        return LoginTicket(
            ok=True,
            qr_content=qr_content,
            qr_key=qr_key,
        )

    def check_ticket(self, qr_key: str) -> LoginPoll:
        try:
            response = self.session.get(
                POLL_URL,
                params={"qrcode_key": qr_key},
                headers=_PASSPORT_HEADERS,
                timeout=10,
            )
            payload = response.json()
        except requests.RequestException as exc:
            return LoginPoll(ok=False, state="error", message=f"网络请求失败：{exc}")
        except ValueError:
            return LoginPoll(ok=False, state="error", message="登录状态接口返回了无效 JSON")

        data = payload.get("data") or {}
        code = int(data.get("code", -1))
        if code == 0:
            cookies = self._extract_cookies(data.get("url") or "")
            self._import_cookies(cookies)
            self._fill_browser_cookies()
            return LoginPoll(
                ok=True,
                state="success",
                message="扫码登录成功",
                cookies=self.current_cookies(),
            )

        if code == 86038:
            return LoginPoll(ok=False, state="expired", message="二维码已失效，请重新获取")
        if code == 86090:
            return LoginPoll(ok=True, state="scanned", message="已扫码，请在手机上确认")
        if code == 86101:
            return LoginPoll(ok=True, state="waiting", message="等待扫码")

        return LoginPoll(
            ok=False,
            state="error",
            message=str(payload.get("message") or f"登录失败（{code}）"),
        )

    def fetch_profile(self) -> Dict[str, Any]:
        try:
            response = self.session.get(NAV_URL, headers=_API_HEADERS, timeout=10)
            payload = response.json()
        except requests.RequestException as exc:
            return {"_error": f"网络请求失败：{exc}"}
        except ValueError:
            return {"_error": "账号信息接口返回了无效 JSON"}

        if payload.get("code") != 0:
            return {"_error": str(payload.get("message") or "获取账号信息失败")}

        data = payload.get("data") or {}
        if not data.get("isLogin"):
            return {"_error": "当前账号未登录或已失效"}
        return data

    def set_cookies(self, cookies: Dict[str, str]) -> None:
        self._import_cookies(cookies)

    def current_cookies(self) -> Dict[str, str]:
        return dict(self.session.cookies.get_dict())

    @staticmethod
    def _extract_cookies(url: str) -> Dict[str, str]:
        parsed = urlsplit(url)
        return {key: value for key, value in parse_qsl(parsed.query)}

    def _import_cookies(self, cookies: Dict[str, str]) -> None:
        for key, value in cookies.items():
            self.session.cookies.set(
                key,
                value,
                domain=".bilibili.com",
                path="/",
            )

    def _fill_browser_cookies(self) -> None:
        try:
            self.session.get(
                "https://www.bilibili.com/video/",
                headers=_API_HEADERS,
                timeout=10,
            )
        except requests.RequestException:
            # 补充浏览器指纹 Cookie 失败不应影响已经拿到的登录 Cookie。
            return

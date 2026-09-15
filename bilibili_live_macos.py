"""BiliLiveMac OBS 脚本入口。

这个文件只负责把 OBS 生命周期转发给应用层，不写业务逻辑。
"""

from pathlib import Path
import importlib
import sys

import obspython as obs


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

MODULE_NAMES = (
    "bilibili_live_mac.paths",
    "bilibili_live_mac.config_store",
    "bilibili_live_mac.obs_bridge",
    "bilibili_live_mac.logger",
    "bilibili_live_mac.qr_utils",
    "bilibili_live_mac.api.auth_api",
    "bilibili_live_mac.api.live_api",
    "bilibili_live_mac.services.account_store",
    "bilibili_live_mac.services.login_flow",
    "bilibili_live_mac.services.room_service",
    "bilibili_live_mac.services.stream_flow",
    "bilibili_live_mac.services.stream_service",
    "bilibili_live_mac.app",
)


def _load_app():
    """加载或重载本地模块，避免 OBS 复用旧的 Python 模块缓存。"""
    modules = [importlib.import_module(name) for name in MODULE_NAMES]
    for module in modules:
        importlib.reload(module)

    from bilibili_live_mac.app import BiliLiveMacApp
    return BiliLiveMacApp()


_app = _load_app()
_POLL_INTERVAL_MS = 1000
_POLL_COUNT = 0


def _poll_timer():
    global _POLL_COUNT
    _POLL_COUNT += 1
    if _POLL_COUNT == 1:
        _app.logger.info("登录轮询定时器首次触发")
    _app.handle_tick(1.0)


def _install_poll_timer():
    try:
        obs.timer_add(_poll_timer, _POLL_INTERVAL_MS)
    except Exception as exc:
        _app.logger.error(f"启动登录轮询定时器失败：{exc}")
        return
    _app.logger.info("登录轮询定时器已启动")


def script_defaults(settings):
    _app.handle_defaults(settings)


def script_load(settings):
    _app.handle_load(settings)
    _install_poll_timer()


def script_update(settings):
    _app.handle_update(settings)


def script_properties():
    return _app.build_properties()


def script_tick(seconds):
    _app.handle_tick(seconds)


def script_unload():
    try:
        obs.timer_remove(_poll_timer)
    except Exception:
        pass
    _app.handle_unload()


def script_description():
    return _app.describe()

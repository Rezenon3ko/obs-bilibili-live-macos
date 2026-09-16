"""BiliLiveMac 应用层。"""

from . import obs_bridge as bridge
from .api.auth_api import BiliAccountApi
from .api.live_api import BiliLiveApi
from .config_store import ConfigStore
from .logger import Logger
from .paths import accounts_file, config_file, ensure_runtime_dirs
from .qr_utils import QrPreview, make_qr_image
from .services.account_store import AccountStore
from .services.login_flow import LoginFlow
from .services.room_service import RoomService
from .services.stream_flow import StreamFlow
from .services.stream_service import StreamService


class BiliLiveMacApp:
    def __init__(self) -> None:
        self.settings = None
        self.logger = Logger()
        self.config = ConfigStore(config_file())
        self.account_store = AccountStore(ConfigStore(accounts_file()))
        self.account_api = BiliAccountApi()
        self._login_qr_preview = QrPreview()
        self.login_flow = LoginFlow(
            self.account_api,
            self.account_store,
            self._show_login_qr,
            self._close_login_qr,
        )
        self.live_api = BiliLiveApi(self.account_api.session)
        self.room_service = RoomService(self.live_api)
        self.stream_service = StreamService(self.live_api)
        self._face_qr_preview = QrPreview()
        self._face_auth_path = None
        self.stream_flow = StreamFlow(
            self.stream_service,
            self._show_face_auth_qr,
            self._close_face_auth_qr,
        )
        self._room_area_prop = None
        self._room_title_prop = None
        self._loaded = False
        self._last_login_state = None

    def _ensure_ready(self, settings=None) -> None:
        ensure_runtime_dirs()
        if settings is not None:
            self.settings = settings

    def handle_defaults(self, settings) -> None:
        self._ensure_ready(settings)
        bridge.set_string(settings, "room_status", "登录后自动获取直播间状态")
        bridge.set_string(settings, "stream_status", "登录后自动获取直播间状态")
        self.logger.info("script_defaults")

    def handle_load(self, settings) -> None:
        self._ensure_ready(settings)
        self._loaded = True
        self._restore_account_session()
        self._auto_refresh_room_if_logged_in()
        self.logger.info("script_load")

    def handle_update(self, settings) -> None:
        self._ensure_ready(settings)
        self.logger.info("script_update")

    def build_properties(self):
        self._ensure_ready(self.settings)
        props = bridge.create_properties()

        account_props = bridge.create_properties()
        bridge.add_group(
            props,
            "account_group",
            "账号",
            account_props,
        )
        bridge.add_info_text(account_props, "account_status", "登录状态")
        bridge.add_button(
            account_props,
            "account_login_qr",
            "二维码登录",
            self._on_login_qr,
        )
        bridge.add_button(
            account_props,
            "account_refresh",
            "更新账号信息",
            self._on_update_account,
        )
        bridge.add_button(
            account_props,
            "account_logout",
            "退出登录",
            self._on_logout,
        )

        room_props = bridge.create_properties()
        bridge.add_group(
            props,
            "room_group",
            "直播间",
            room_props,
        )
        bridge.add_info_text(room_props, "room_status", "房间状态")
        self._room_title_prop = bridge.add_text(room_props, "room_title", "直播标题")
        bridge.set_modified_callback(self._room_title_prop)
        bridge.add_button(
            room_props,
            "room_save_title",
            "保存标题",
            self._on_room_save_title,
        )
        self._room_area_prop = bridge.add_list(
            room_props,
            "room_area",
            "直播分区",
        )
        bridge.set_modified_callback(self._room_area_prop)
        bridge.add_button(
            room_props,
            "room_save_area",
            "保存分区",
            self._on_room_save_area,
        )

        stream_props = bridge.create_properties()
        bridge.add_group(
            props,
            "stream_group",
            "直播控制",
            stream_props,
        )
        bridge.add_info_text(stream_props, "stream_status", "推流状态")
        bridge.add_button(
            stream_props,
            "stream_start",
            "开始直播",
            self._on_stream_start,
        )
        bridge.add_button(
            stream_props,
            "stream_stop",
            "结束直播",
            self._on_stream_stop,
        )
        self._render_cached_room_state()
        self._sync_account_status()
        return props

    def handle_tick(self, seconds: float) -> None:
        if self._loaded:
            was_logged_in = self.account_store.is_logged_in()
            self.login_flow.tick(seconds)
            self._sync_login_status_after_tick()
            self.stream_flow.tick(seconds)
            self._sync_stream_status()
            if not was_logged_in and self.account_store.is_logged_in():
                self.logger.info("扫码登录成功，请在 OBS 面板点击“更新账号信息”")
                self._sync_account_status()

    def handle_unload(self) -> None:
        self._face_qr_preview.close()
        self._login_qr_preview.close()
        self.logger.info("script_unload")
        self._loaded = False

    def describe(self) -> str:
        return (
            "BilibiliLiveMacOS\n"
            "使用：二维码登录 → 更新账号信息 → 修改标题/分区 → 开始直播"
        )

    def _on_login_qr(self, *args):
        if self.account_store.is_logged_in():
            self._auto_refresh_room_if_logged_in()
            self._sync_account_status()
            return True
        if self.login_flow.is_active:
            self.login_flow.show_current_qr()
        else:
            self._last_login_state = None
            self.login_flow.begin()
        self._sync_account_status()
        return True

    def _on_logout(self, *args):
        self.account_store.clear()
        self._login_qr_preview.close()
        self.login_flow = LoginFlow(
            self.account_api,
            self.account_store,
            self._show_login_qr,
            self._close_login_qr,
        )
        self.room_service = RoomService(self.live_api)
        self.stream_service = StreamService(self.live_api)
        self._face_qr_preview.close()
        self.stream_flow = StreamFlow(
            self.stream_service,
            self._show_face_auth_qr,
            self._close_face_auth_qr,
        )
        self._reset_room_ui()
        self._sync_account_status()
        self.logger.info("退出登录")
        return True

    def _on_update_account(self, *args):
        self._sync_account_status()
        self._auto_refresh_room_if_logged_in()
        self._sync_account_status()
        self.logger.info("更新账号信息")
        return True

    def _on_room_save_title(self, *args):
        if not self.account_store.is_logged_in():
            self._set_room_status("请先登录账号")
            return True
        title = bridge.get_string(self.settings, "room_title", "").strip()
        result = self.room_service.save_title(title)
        if result.get("ok"):
            self._refresh_room_after_change()
            bridge.set_string(self.settings, "room_title", title)
        else:
            self._set_room_status(result.get("message") or "保存标题失败")
        return True

    def _on_room_save_area(self, *args):
        if not self.account_store.is_logged_in():
            self._set_room_status("请先登录账号")
            return True
        area_id = bridge.get_string(self.settings, "room_area", "")
        result = self.room_service.save_area(area_id)
        if result.get("ok"):
            self._refresh_room_after_change()
        else:
            self._set_room_status(result.get("message") or "保存分区失败")
        return True

    def _on_stream_start(self, *args):
        if not self._ensure_room_ready():
            return True
        area_id = bridge.get_string(self.settings, "room_area", "")
        self.stream_flow.request_start(area_id)
        self._sync_stream_status()
        return True

    def _on_stream_stop(self, *args):
        if not self._ensure_room_ready():
            return True
        self.stream_flow.request_stop()
        self._sync_stream_status()
        return True

    def _show_login_qr(self, path):
        self._login_qr_preview.open(path)

    def _close_login_qr(self):
        self._login_qr_preview.close()

    def _show_face_auth_qr(self):
        account = self.account_store.current()
        uid = account.get("uid") or ""
        if not uid:
            self._set_stream_status("需要人脸认证，但未找到登录账号")
            return False

        url = (
            "https://www.bilibili.com/blackboard/live/face-auth-middle.html"
            f"?source_event=400&mid={uid}"
        )
        try:
            path = make_qr_image(url, "face_auth")
            self._face_auth_path = path
            self._face_qr_preview.open(path)
        except Exception as exc:
            self._set_stream_status(f"生成人脸认证二维码失败：{exc}")
            return False
        return True

    def _close_face_auth_qr(self):
        self._face_qr_preview.close()
        if self._face_auth_path is not None:
            try:
                self._face_auth_path.unlink()
            except OSError:
                pass
            self._face_auth_path = None

    def _apply_room_result(self, result) -> None:
        if not result.get("ok"):
            self._set_room_status(result.get("message") or "获取直播间状态失败")
            return

        if not result.get("has_room"):
            self._set_room_status(result.get("message") or "当前账号还没有开通直播间")
            bridge.set_string(self.settings, "room_title", "")
            self._fill_room_areas([], "")
            self.stream_service.set_room_id(None)
            self._set_stream_status("当前账号没有直播间")
            return

        self._set_room_status(result.get("message") or "直播间信息已刷新")
        bridge.set_string(self.settings, "room_title", result.get("title") or "")
        self.stream_service.set_room_id(int(self.room_service.room_id or 0))
        self._set_stream_status("房间信息已就绪，可一键开播")
        self._fill_room_areas(
            self.room_service.area_options(),
            str(result.get("area_id") or ""),
        )

    def _fill_room_areas(self, options, selected_value) -> None:
        if self.settings is not None:
            bridge.set_string(self.settings, "room_area", selected_value)
        if self._room_area_prop is None:
            return
        bridge.list_clear(self._room_area_prop)
        if not options:
            bridge.list_add_string(self._room_area_prop, "暂无可选分区", "")
        for option in options:
            bridge.list_add_string(
                self._room_area_prop,
                option.get("label") or "",
                option.get("value") or "",
            )

    def _set_room_status(self, message: str) -> None:
        if self.settings is not None:
            bridge.set_string(self.settings, "room_status", message)

    def _set_stream_status(self, message: str) -> None:
        if self.settings is not None:
            bridge.set_string(self.settings, "stream_status", message)

    def _sync_stream_status(self) -> None:
        self._set_stream_status(self.stream_flow.message)

    def _auto_refresh_room_if_logged_in(self) -> None:
        if not self.account_store.is_logged_in():
            return
        result = self.room_service.refresh()
        self._apply_room_result(result)

    def _refresh_room_after_change(self) -> None:
        if not self.account_store.is_logged_in():
            return
        result = self.room_service.refresh()
        self._apply_room_result(result)

    def _reset_room_ui(self) -> None:
        self._set_room_status("登录后自动获取直播间状态")
        self.stream_flow.state = "idle"
        self.stream_flow.message = "登录后自动获取直播间状态"
        self._sync_stream_status()
        bridge.set_string(self.settings, "room_title", "")
        self._fill_room_areas([], "")

    def _render_cached_room_state(self) -> None:
        if not self.account_store.is_logged_in() or not self.room_service.room_id:
            return

        info = self.room_service.room_info
        room_id = self.room_service.room_id
        uname = info.get("uname") or ""
        title = info.get("title") or ""
        area_id = str(info.get("area_id") or "")
        live_status = int(info.get("live_status") or 0)
        live_text = {0: "未开播", 1: "直播中", 2: "轮播中"}.get(live_status, "未知状态")
        area_name = info.get("area_name") or ""
        parent_name = info.get("parent_area_name") or ""
        area_text = f"{parent_name} / {area_name}" if area_name else "未知"

        self._set_room_status(
            f"房间 {room_id}｜{uname}｜{live_text}｜分区：{area_text}"
        )
        bridge.set_string(self.settings, "room_title", title)
        self._fill_room_areas(self.room_service.area_options(), area_id)

    def _ensure_room_ready(self) -> bool:
        if not self.account_store.is_logged_in():
            self._set_stream_status("请先登录账号")
            return False
        if not self.room_service.room_id:
            self._set_stream_status("直播间状态尚未就绪，请稍候或重新登录")
            return False
        return True

    def _restore_account_session(self) -> None:
        cookies = self.account_store.cookies()
        if cookies:
            self.account_api.set_cookies(cookies)

    def _sync_account_status(self) -> None:
        if self.settings is None:
            return
        if self.account_store.is_logged_in():
            account = self.account_store.current()
            text = f"已登录：{account.get('uname') or account.get('uid') or '未知用户'}"
        else:
            text = self.login_flow.status_text()
        bridge.set_string(self.settings, "account_status", text)

    def _sync_login_status_after_tick(self) -> None:
        state = self.login_flow.state
        if state in {"waiting", "scanned", "success", "expired", "error"}:
            if state != self._last_login_state:
                self.logger.info(f"登录状态变化：{state} {self.login_flow.message}")
                self._last_login_state = state
            self._sync_account_status()


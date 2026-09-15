"""一键开播/下播状态机。"""

import time
from typing import Any, Callable, Dict, Optional

from .stream_service import StreamService


FACE_AUTH_CODE = 60024
FACE_AUTH_TIMEOUT_SECONDS = 180
FACE_AUTH_POLL_INTERVAL = 2.0
OBS_RESTART_DELAY_SECONDS = 2.0


class StreamFlow:
    def __init__(
        self,
        stream_service: StreamService,
        face_auth_provider: Optional[Callable[[], None]] = None,
        face_auth_closer: Optional[Callable[[], None]] = None,
    ) -> None:
        self.stream_service = stream_service
        self.face_auth_provider = face_auth_provider
        self.face_auth_closer = face_auth_closer
        self.state = "idle"
        self.message = "未开始直播"
        self._pending_area_id = ""
        self._elapsed = 0.0
        self._face_qr_opened = False
        self._wait_started_at = 0.0
        self._restart_at = 0.0

    @property
    def is_busy(self) -> bool:
        return self.state in {"starting", "waiting_face", "restarting_obs", "stopping"}

    def request_start(self, area_id: str) -> bool:
        if self.is_busy:
            return False
        self._pending_area_id = str(area_id or "")
        self._face_qr_opened = False
        self.state = "starting"
        self.message = "正在获取推流地址并开播..."
        self._attempt_start(self._pending_area_id)
        return True

    def request_stop(self) -> bool:
        self.state = "stopping"
        self.message = "正在停止直播..."

        if self.stream_service.obs_active():
            self.stream_service.stop_obs()

        self._close_face_auth()
        result = self.stream_service.stop()
        if result.get("ok"):
            self.state = "stopped"
            self.message = "已结束直播并停止 OBS 推流"
        else:
            self.state = "error"
            self.message = result.get("message") or "结束直播失败"
        return True

    def tick(self, delta_seconds: float) -> None:
        if self.state == "waiting_face":
            self._elapsed += float(delta_seconds)
            if time.time() - self._wait_started_at > FACE_AUTH_TIMEOUT_SECONDS:
                self.state = "error"
                self.message = "人脸认证超时，请重新点击开始直播"
                self._close_face_auth()
                return
            if self._elapsed >= FACE_AUTH_POLL_INTERVAL:
                self._elapsed = 0.0
                self._attempt_start(self._pending_area_id)
            return

        if self.state == "restarting_obs":
            if time.time() >= self._restart_at:
                self.stream_service.start_obs()
                self.state = "started"
                self.message = "已开播并重启 OBS 推流"
            return

    def _attempt_start(self, area_id: str) -> None:
        result = self.stream_service.start(area_id)
        if result.get("ok"):
            self._close_face_auth()
            self._finish_start(result)
            return

        if result.get("code") == FACE_AUTH_CODE:
            self.state = "waiting_face"
            self.message = "需要人脸认证，请扫码；认证成功后会自动开播"
            self._elapsed = 0.0
            self._wait_started_at = time.time()
            if not self._face_qr_opened and self.face_auth_provider is not None:
                self._face_qr_opened = bool(self.face_auth_provider())
            return

        self.state = "error"
        self.message = result.get("message") or "开播失败"
        self._close_face_auth()

    def _finish_start(self, result: Dict[str, Any]) -> None:
        applied = self.stream_service.apply_to_obs(
            result.get("addr") or "",
            result.get("code") or "",
        )
        if not applied.get("ok"):
            self.state = "error"
            self.message = applied.get("message") or "写入 OBS 推流设置失败"
            return

        if self.stream_service.obs_active():
            self.stream_service.stop_obs()
            self.state = "restarting_obs"
            self.message = "OBS 正在推流，已停止，稍后自动重启推流"
            self._restart_at = time.time() + OBS_RESTART_DELAY_SECONDS
            return

        self.stream_service.start_obs()
        self.state = "started"
        self.message = "已开播并启动 OBS 推流"

    def _close_face_auth(self) -> None:
        if self.face_auth_closer is not None:
            self.face_auth_closer()

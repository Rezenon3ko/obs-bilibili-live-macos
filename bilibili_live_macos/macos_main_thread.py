"""macOS 主线程调度工具。

OBS 的属性面板只能在主线程安全更新，但脚本里的网络请求需要放到后台线程。
这个模块通过 Core Foundation 的 CFRunLoopTimer 把回调投递回主线程，避免从
``script_tick`` 或后台线程直接操作 OBS 属性对象导致崩溃。
"""

import ctypes
from typing import Callable, List, Tuple


_CF = ctypes.CDLL(
    "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
)

_CF.CFAbsoluteTimeGetCurrent.restype = ctypes.c_double

_CFRunLoopRef = ctypes.c_void_p
_CFRunLoopTimerRef = ctypes.c_void_p
_CFRunLoopTimerCallBack = ctypes.CFUNCTYPE(
    None,
    ctypes.c_void_p,
    ctypes.c_void_p,
)


class _CFRunLoopTimerContext(ctypes.Structure):
    _fields_ = [
        ("version", ctypes.c_long),
        ("info", ctypes.c_void_p),
        ("retain", ctypes.c_void_p),
        ("release", ctypes.c_void_p),
        ("copyDescription", ctypes.c_void_p),
    ]


_CF.CFRunLoopGetMain.restype = _CFRunLoopRef
_CF.CFRunLoopTimerCreate.argtypes = [
    ctypes.c_void_p,
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_long,
    ctypes.c_long,
    _CFRunLoopTimerCallBack,
    ctypes.POINTER(_CFRunLoopTimerContext),
]
_CF.CFRunLoopTimerCreate.restype = _CFRunLoopTimerRef
_CF.CFRunLoopAddTimer.argtypes = [
    _CFRunLoopRef,
    _CFRunLoopTimerRef,
    ctypes.c_void_p,
]
_CF.CFRunLoopTimerInvalidate.argtypes = [_CFRunLoopTimerRef]

_kCFRunLoopCommonModes = ctypes.c_void_p.in_dll(
    _CF,
    "kCFRunLoopCommonModes",
)

_active_timers: List[Tuple[_CFRunLoopTimerCallBack, _CFRunLoopTimerRef]] = []


def schedule_on_main_thread(
    callback: Callable[[], None],
    delay_seconds: float = 0.05,
) -> None:
    """把一个无参回调调度到 macOS 主线程执行。"""

    holder = {"callback": callback}

    @_CFRunLoopTimerCallBack
    def _timer_fired(timer, info):
        try:
            holder["callback"]()
        finally:
            _CF.CFRunLoopTimerInvalidate(timer)
            _active_timers[:] = [
                entry for entry in _active_timers if entry[0] is not _timer_fired
            ]

    context = _CFRunLoopTimerContext()
    context.version = 0

    timer = _CF.CFRunLoopTimerCreate(
        None,
        _CF.CFAbsoluteTimeGetCurrent() + max(0.0, float(delay_seconds)),
        0,
        0,
        0,
        _timer_fired,
        ctypes.byref(context),
    )
    if not timer:
        raise RuntimeError("无法创建主线程调度定时器")

    _active_timers.append((_timer_fired, timer))
    _CF.CFRunLoopAddTimer(
        _CF.CFRunLoopGetMain(),
        timer,
        _kCFRunLoopCommonModes,
    )

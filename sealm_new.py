from __future__ import annotations
 
import importlib.util
import multiprocessing
import queue
import sys
import time
import traceback
import types
import tkinter as tk
import ctypes
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

import cv2
import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_DIR = Path(__file__).resolve().parent / "ldplayer-auto"
EMULATOR_DIR = REPO_DIR / "emulator"
EMULATOR_INIT = EMULATOR_DIR / "__init__.py"
LDPLAYER_DIR = r"D:/LDPlayer/LDPlayer9"
AUTO_TEMPLATE = Path("images/auto.png")
NOT_AUTO_TEMPLATE = Path("images/not_auto.png")
MAP_IMAGES_DIR = Path("images")
MAP_IMAGE_GLOB = "map_*.png"
LOG_BOSS_FILE = Path("logboss.txt")
LOADING_TEMPLATE = Path("images/loading.png")
DONE_LOADING_TEMPLATE = Path("images/done_loading.png")
BOSS_DONE_TEMPLATE = Path("images/boss_done.png")
BOSS_RANK_TEMPLATE = Path("images/boss_rank.png")
CHANNEL_TEMPLATE = Path("images/channel.png")
HOME_TEMPLATE = Path("images/home.png")
CONFIRM_HOME_TEMPLATE = Path("images/confirm_home.png")
FEVER_TEMPLATE = Path("images/faver.png")
LOGIN_TEMPLATE = Path("images/login.png")
STARTGAME_TEMPLATE = Path("images/startgame.png")
DISCONNECT_TEMPLATE = Path("images/disconnect.png")
QUEST_DONE_TEMPLATE = Path("images/quest_done.png")
CONFIRM_QUEST_TEMPLATE = Path("images/confirm_quest.png")
CONFIRM_CHANNEL_TEMPLATE = Path("images/confirm_channel.png")
TAB_CHANNEL_TEMPLATE = Path("images/tab_channel.png")
MAP_TEMPLATE = Path("images/map.png")
MAP_6X_TEMPLATE = Path("images/map6x.png")
MAP_LIST_TEMPLATE = Path("images/map_list.png")
MAP_CREEP_TEMPLATE = Path("images/map_creep.png")
INSTANCE_MOVE_TEMPLATE = Path("images/intance_move.png")
INSTANCE_MOVE_BOSS_TEMPLATE = Path("images/intance_move_boss.png")
MENU_TEMPLATE = Path("images/menu.png")
ICON_DISMAN_TEMPLATE = Path("images/icon_disman.png")
ICON_FIELD_BOSS_TEMPLATE = Path("images/icon_fielboss.png")
DISMAN_TAB_TEMPLATE = Path("images/disman_tab.png")
SELECT_ALL_TEMPLATE = Path("images/select_all.png")
DISMANTLE_BUTTON_TEMPLATE = Path("images/dismant_bt.png")
DISMANTLE_CONFIRM_TEMPLATE = Path("images/disman_com.png")
BOSS_CHOICE_TEMPLATES = {
    1: Path("images/boss1_choice.png"),
    2: Path("images/boss2_choice.png"),
    3: Path("images/boss3_choice.png"),
    4: Path("images/boss4_choice.png"),
    5: Path("images/boss5_choice.png"),
    6: Path("images/boss6_choice.png"),
}
BACK1_TEMPLATE = Path("images/back1.png")
BACK2_TEMPLATE = Path("images/back2.png")
DUNGEON_ENTER_TEMPLATE = Path("images/dungeon_enter.png")
DUNGEON_INSTANCE_TEMPLATE = Path("images/dungeon_intance.png")
DUNGEON_LEAVE_TEMPLATE = Path("images/dungeon_leave.png")
DUNGEON_RETRY_TEMPLATE = Path("images/dungeon_retry.png")
BOSS_ICON_TEMPLATES = {
    1: Path("images/icon_boss1.png"),
    2: Path("images/icon_boss2.png"),
    3: Path("images/icon_boss3.png"),
    4: Path("images/icon_boss4.png"),
    5: Path("images/icon_boss5.png"),
    6: Path("images/icon_boss6.png"),
}
TEMPLATE_CACHE: dict[tuple[str, int], np.ndarray] = {}


def ensure_pkg_resources_stub() -> None:
    if "pkg_resources" in sys.modules:
        return

    pkg_resources = types.ModuleType("pkg_resources")

    class _PkgInfo:
        version = "cloned-local"

    def _require(_name: str):
        return [_PkgInfo()]

    pkg_resources.require = _require  # type: ignore[attr-defined]
    sys.modules["pkg_resources"] = pkg_resources


def load_module(module_name: str, module_path: Path, *, is_package: bool = False):
    if not module_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {module_path}")

    kwargs = {}
    if is_package:
        kwargs["submodule_search_locations"] = [str(module_path.parent)]

    spec = importlib.util.spec_from_file_location(module_name, module_path, **kwargs)
    if spec is None or spec.loader is None:
        raise ImportError(f"Không thể tạo module spec cho {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_runtime_modules():
    ensure_pkg_resources_stub()
    cloned_emulator = load_module("cloned_emulator", EMULATOR_INIT, is_package=True)
    cloned_keys = load_module("cloned_emulator.keys", EMULATOR_DIR / "keys.py")
    return cloned_emulator, cloned_keys


def create_ldplayer():
    cloned_emulator, cloned_keys = load_runtime_modules()
    ld = cloned_emulator.LDPlayer(ldplayer_dir=LDPLAYER_DIR)
    return ld, cloned_keys


WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
MK_LBUTTON = 0x0001
VK_ESCAPE = 0x1B
ANDROID_TO_WINDOWS_KEY = {
    111: VK_ESCAPE,
}
PW_RENDERFULLCONTENT = 0x00000002
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
BI_RGB = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002


def _make_lparam(x: int, y: int) -> int:
    return ((y & 0xFFFF) << 16) | (x & 0xFFFF)


# NOTE: Helper này dùng để đánh dấu các thao tác click mù theo tọa độ.
# Các chỗ gọi hàm này nên được thay dần bằng template ảnh / wait_for_template().
def blind_tap(
    emulator,
    position: tuple[int, int],
    *,
    label: str,
    post_delay: float = 0.1,
) -> tuple[int, int]:
    emulator.tap(position)
    if post_delay > 0:
        time.sleep(post_delay)
    return position



def _collect_window_handles(*hwnds: int) -> list[int]:
    user32 = ctypes.windll.user32
    collected: list[int] = []
    seen: set[int] = set()

    def add_hwnd(candidate: int) -> None:
        if not candidate or candidate in seen:
            return
        if not user32.IsWindow(candidate):
            return
        seen.add(candidate)
        collected.append(candidate)

    for hwnd in hwnds:
        add_hwnd(hwnd)

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(child_hwnd, _lparam):
        add_hwnd(int(child_hwnd))
        return True

    callback_fn = enum_proc(callback)
    for hwnd in list(collected):
        user32.EnumChildWindows(hwnd, callback_fn, 0)

    return collected


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]



def focus_window_for_input(hwnd: int) -> dict:
    user32 = ctypes.windll.user32
    if not hwnd or not user32.IsWindow(hwnd):
        return {
            "ok": False,
            "reason": "window_not_found",
            "hwnd": hwnd,
        }

    placement_result = user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
    show_result = user32.ShowWindow(hwnd, 5)
    foreground_result = user32.SetForegroundWindow(hwnd)
    active_result = user32.SetActiveWindow(hwnd)
    focus_result = user32.SetFocus(hwnd)

    return {
        "ok": bool(foreground_result or active_result or focus_result),
        "reason": "focused" if (foreground_result or active_result or focus_result) else "focus_failed",
        "hwnd": hwnd,
        "placement_result": int(placement_result),
        "show_result": int(show_result),
        "foreground_result": int(foreground_result),
        "active_result": int(active_result),
        "focus_result": int(focus_result),
    }



def send_input_vk(vk_code: int, *, long_press: bool = False) -> dict:
    user32 = ctypes.windll.user32
    scan_code = user32.MapVirtualKeyW(vk_code, 0)
    extra = ctypes.c_ulong(0)

    key_down = INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(
            ki=KEYBDINPUT(
                wVk=vk_code,
                wScan=scan_code,
                dwFlags=0,
                time=0,
                dwExtraInfo=ctypes.pointer(extra),
            )
        ),
    )
    key_up = INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(
            ki=KEYBDINPUT(
                wVk=vk_code,
                wScan=scan_code,
                dwFlags=KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=ctypes.pointer(extra),
            )
        ),
    )

    sent_down = user32.SendInput(1, ctypes.byref(key_down), ctypes.sizeof(INPUT))
    if long_press:
        time.sleep(0.3)
    sent_up = user32.SendInput(1, ctypes.byref(key_up), ctypes.sizeof(INPUT))

    return {
        "ok": sent_down == 1 and sent_up == 1,
        "reason": "send_input_ok" if sent_down == 1 and sent_up == 1 else "send_input_failed",
        "vk_code": vk_code,
        "scan_code": int(scan_code),
        "sent_down": int(sent_down),
        "sent_up": int(sent_up),
    }



def inactive_click_window(hwnd: int, position: tuple[int, int], delay: float = 0.05) -> dict:
    if not hwnd:
        return {
            "ok": False,
            "reason": "invalid_hwnd",
            "hwnd": hwnd,
            "position": position,
        }

    user32 = ctypes.windll.user32
    if not user32.IsWindow(hwnd):
        return {
            "ok": False,
            "reason": "window_not_found",
            "hwnd": hwnd,
            "position": position,
        }

    x, y = position
    lparam = _make_lparam(x, y)

    down_result = user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
    time.sleep(delay)
    up_result = user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)

    if not down_result or not up_result:
        return {
            "ok": False,
            "reason": "post_message_failed",
            "hwnd": hwnd,
            "position": position,
            "down_result": int(down_result),
            "up_result": int(up_result),
        }

    return {
        "ok": True,
        "reason": "posted",
        "hwnd": hwnd,
        "position": position,
        "down_result": int(down_result),
        "up_result": int(up_result),
    }



def inactive_send_key_window(hwnd: int, vk_code: int, *, long_press: bool = False) -> dict:
    if not hwnd:
        return {
            "ok": False,
            "reason": "invalid_hwnd",
            "hwnd": hwnd,
            "vk_code": vk_code,
        }

    user32 = ctypes.windll.user32
    if not user32.IsWindow(hwnd):
        return {
            "ok": False,
            "reason": "window_not_found",
            "hwnd": hwnd,
            "vk_code": vk_code,
        }

    scan_code = user32.MapVirtualKeyW(vk_code, 0)
    is_system_key = vk_code == VK_ESCAPE
    keydown_msg = WM_SYSKEYDOWN if is_system_key else WM_KEYDOWN
    keyup_msg = WM_SYSKEYUP if is_system_key else WM_KEYUP
    keydown_lparam = 1 | (int(scan_code) << 16)
    keyup_lparam = keydown_lparam | (1 << 30) | (1 << 31)
    result_value = ctypes.c_size_t()
    send_flags = 0x0000
    send_timeout_ms = 200

    down_result = user32.SendMessageTimeoutW(
        hwnd,
        keydown_msg,
        vk_code,
        keydown_lparam,
        send_flags,
        send_timeout_ms,
        ctypes.byref(result_value),
    )
    if long_press:
        time.sleep(0.3)
    up_result = user32.SendMessageTimeoutW(
        hwnd,
        keyup_msg,
        vk_code,
        keyup_lparam,
        send_flags,
        send_timeout_ms,
        ctypes.byref(result_value),
    )

    fallback_down_result = 0
    fallback_up_result = 0
    if not down_result or not up_result:
        fallback_down_result = user32.PostMessageW(hwnd, keydown_msg, vk_code, keydown_lparam)
        if long_press:
            time.sleep(0.3)
        fallback_up_result = user32.PostMessageW(hwnd, keyup_msg, vk_code, keyup_lparam)

    ok = bool((down_result and up_result) or (fallback_down_result and fallback_up_result))
    reason = "sent" if ok else "send_message_failed"

    return {
        "ok": ok,
        "reason": reason,
        "hwnd": hwnd,
        "vk_code": vk_code,
        "scan_code": int(scan_code),
        "keydown_msg": int(keydown_msg),
        "keyup_msg": int(keyup_msg),
        "down_result": int(down_result),
        "up_result": int(up_result),
        "fallback_down_result": int(fallback_down_result),
        "fallback_up_result": int(fallback_up_result),
    }


def inactive_click_emulator(
    emulator,
    position: tuple[int, int],
    *,
    prefer_bind_hwnd: bool = True,
    delay: float = 0.05,
) -> dict:
    if prefer_bind_hwnd:
        hwnd_candidates = _collect_window_handles(getattr(emulator, "bind_hwnd", 0), getattr(emulator, "top_hwnd", 0))
    else:
        hwnd_candidates = _collect_window_handles(getattr(emulator, "top_hwnd", 0), getattr(emulator, "bind_hwnd", 0))

    tried: list[dict] = []
    for hwnd in hwnd_candidates:
        if not hwnd:
            continue
        result = inactive_click_window(hwnd, position, delay=delay)
        tried.append(result)
        if result["ok"]:
            return {
                "ok": True,
                "target_hwnd": hwnd,
                "position": position,
                "results": tried,
            }

    return {
        "ok": False,
        "reason": "inactive_click_failed",
        "position": position,
        "results": tried,
    }



def inactive_drag_window(
    hwnd: int,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    duration: float = 0.2,
    steps: int = 8,
) -> dict:
    if not hwnd:
        return {
            "ok": False,
            "reason": "invalid_hwnd",
            "hwnd": hwnd,
            "start": start,
            "end": end,
        }

    user32 = ctypes.windll.user32
    if not user32.IsWindow(hwnd):
        return {
            "ok": False,
            "reason": "window_not_found",
            "hwnd": hwnd,
            "start": start,
            "end": end,
        }

    sx, sy = start
    ex, ey = end
    step_count = max(1, steps)
    sleep_time = duration / step_count if step_count else duration

    user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, _make_lparam(sx, sy))
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, _make_lparam(sx, sy))
    for step_index in range(1, step_count + 1):
        x = int(sx + (ex - sx) * step_index / step_count)
        y = int(sy + (ey - sy) * step_index / step_count)
        user32.PostMessageW(hwnd, WM_MOUSEMOVE, MK_LBUTTON, _make_lparam(x, y))
        time.sleep(sleep_time)
    up_result = user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, _make_lparam(ex, ey))

    return {
        "ok": bool(up_result),
        "reason": "posted" if up_result else "post_message_failed",
        "hwnd": hwnd,
        "start": start,
        "end": end,
        "up_result": int(up_result),
    }



def inactive_drag_emulator(
    emulator,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    prefer_bind_hwnd: bool = True,
    duration: float = 0.2,
    steps: int = 8,
) -> dict:
    if prefer_bind_hwnd:
        hwnd_candidates = _collect_window_handles(getattr(emulator, "bind_hwnd", 0), getattr(emulator, "top_hwnd", 0))
    else:
        hwnd_candidates = _collect_window_handles(getattr(emulator, "top_hwnd", 0), getattr(emulator, "bind_hwnd", 0))

    tried: list[dict] = []
    for hwnd in hwnd_candidates:
        if not hwnd:
            continue
        result = inactive_drag_window(hwnd, start, end, duration=duration, steps=steps)
        tried.append(result)
        if result["ok"]:
            return {
                "ok": True,
                "target_hwnd": hwnd,
                "start": start,
                "end": end,
                "results": tried,
            }

    return {
        "ok": False,
        "reason": "inactive_drag_failed",
        "start": start,
        "end": end,
        "results": tried,
    }



def inactive_send_key_emulator(
    emulator,
    keycode: int,
    *,
    long_press: bool = False,
    prefer_top_hwnd: bool = True,
) -> dict:
    vk_code = ANDROID_TO_WINDOWS_KEY.get(keycode)
    if vk_code is None:
        return {
            "ok": False,
            "reason": "unsupported_keycode",
            "keycode": keycode,
        }

    if prefer_top_hwnd:
        hwnd_candidates = _collect_window_handles(getattr(emulator, "top_hwnd", 0), getattr(emulator, "bind_hwnd", 0))
    else:
        hwnd_candidates = _collect_window_handles(getattr(emulator, "bind_hwnd", 0), getattr(emulator, "top_hwnd", 0))

    tried: list[dict] = []
    for hwnd in hwnd_candidates:
        result = inactive_send_key_window(hwnd, vk_code, long_press=long_press)
        result = {
            **result,
            "keycode": keycode,
        }
        tried.append(result)
        if result["ok"]:
            return {
                "ok": True,
                "target_hwnd": hwnd,
                "keycode": keycode,
                "vk_code": vk_code,
                "results": tried,
            }

    return {
        "ok": False,
        "reason": "inactive_key_failed",
        "keycode": keycode,
        "vk_code": vk_code,
        "results": tried,
    }



def bind_window_input(emulator):
    emulator._update()

    def _window_tap(self, *positions):
        self._error = ""
        last_result: dict | None = None
        for position in positions:
            last_result = inactive_click_emulator(self, position)
            if not last_result["ok"]:
                self._error = str(last_result)
                return self
        if last_result is not None:
            self._error = ""
        return self

    def _window_drag_drop(self, _from, to):
        result = inactive_drag_emulator(self, _from, to)
        self._error = "" if result["ok"] else str(result)
        return self

    def _window_send_event(self, keycode: int, long_press: bool = False):
        result = inactive_send_key_emulator(self, keycode, long_press=long_press)
        self._error = "" if result["ok"] else str(result)
        return self

    emulator.tap = types.MethodType(_window_tap, emulator)
    emulator.drag_drop = types.MethodType(_window_drag_drop, emulator)
    emulator.send_event = types.MethodType(_window_send_event, emulator)
    return emulator


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]



def capture_window_image(hwnd: int) -> np.ndarray:
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    if not hwnd or not user32.IsWindow(hwnd):
        raise RuntimeError(f"HWND không hợp lệ: {hwnd}")

    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError(f"GetClientRect failed for hwnd={hwnd}")

    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        raise RuntimeError(f"Client rect không hợp lệ cho hwnd={hwnd}: {width}x{height}")

    hwnd_dc = user32.GetDC(hwnd)
    if not hwnd_dc:
        raise RuntimeError(f"GetDC failed for hwnd={hwnd}")

    mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
    if not mem_dc or not bitmap:
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if mem_dc:
            gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(hwnd, hwnd_dc)
        raise RuntimeError(f"CreateCompatibleBitmap/DC failed for hwnd={hwnd}")

    old_bitmap = gdi32.SelectObject(mem_dc, bitmap)
    try:
        print_result = user32.PrintWindow(hwnd, mem_dc, PW_RENDERFULLCONTENT)
        if not print_result:
            bitblt_result = gdi32.BitBlt(mem_dc, 0, 0, width, height, hwnd_dc, 0, 0, SRCCOPY)
            if not bitblt_result:
                raise RuntimeError(f"PrintWindow và BitBlt đều failed for hwnd={hwnd}")

        bitmap_info = BITMAPINFO()
        bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bitmap_info.bmiHeader.biWidth = width
        bitmap_info.bmiHeader.biHeight = -height
        bitmap_info.bmiHeader.biPlanes = 1
        bitmap_info.bmiHeader.biBitCount = 32
        bitmap_info.bmiHeader.biCompression = BI_RGB

        buffer_size = width * height * 4
        buffer = ctypes.create_string_buffer(buffer_size)
        rows_copied = gdi32.GetDIBits(
            mem_dc,
            bitmap,
            0,
            height,
            buffer,
            ctypes.byref(bitmap_info),
            DIB_RGB_COLORS,
        )
        if rows_copied != height:
            raise RuntimeError(f"GetDIBits failed for hwnd={hwnd}: rows={rows_copied}, expected={height}")

        image = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    finally:
        gdi32.SelectObject(mem_dc, old_bitmap)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(hwnd, hwnd_dc)



def capture_window_emulator(emulator) -> np.ndarray:
    def _candidate_hwnds() -> list[int]:
        candidates: list[int] = []
        for hwnd in (getattr(emulator, "bind_hwnd", 0), getattr(emulator, "top_hwnd", 0)):
            if hwnd and hwnd not in candidates:
                candidates.append(hwnd)
        return candidates

    last_error: str | None = None

    for refresh_index in range(2):
        if refresh_index == 0:
            try:
                emulator._update()
            except Exception as exc:
                last_error = repr(exc)
        else:
            try:
                emulator._update()
            except Exception as exc:
                last_error = repr(exc)
                continue

        for hwnd in _candidate_hwnds():
            try:
                return capture_window_image(hwnd)
            except Exception as exc:
                last_error = repr(exc)

    raise RuntimeError(last_error or f"Không capture được emulator index={getattr(emulator, 'index', '?')}")



def bind_window_capture(emulator):
    def _window_screencap(self):
        try:
            image = capture_window_emulator(self)
            success, encoded = cv2.imencode(".png", image)
            if not success:
                self._error = "window_capture_encode_failed"
                return None
            self._error = ""
            return encoded.tobytes()
        except Exception as exc:
            self._error = repr(exc)
            return None

    def _window_run_adb(self, cmd: str, decode: str | None = "latin-1"):
        raise RuntimeError("ADB disabled in window mode")

    def _window_run_app(self, package_name: str):
        self._error = f"run_app disabled in window mode: {package_name}"
        return self

    def _window_kill_app(self, package_name: str):
        self._error = f"kill_app disabled in window mode: {package_name}"
        return self

    emulator._get_screencap_b64decode = types.MethodType(_window_screencap, emulator)
    emulator._run_adb = types.MethodType(_window_run_adb, emulator)
    emulator.run_app = types.MethodType(_window_run_app, emulator)
    emulator.kill_app = types.MethodType(_window_kill_app, emulator)
    return emulator



def bind_window_mode(emulator):
    bind_window_input(emulator)
    bind_window_capture(emulator)
    return emulator


class QueueWriter:
    def __init__(self, log_queue: multiprocessing.Queue | None) -> None:
        self.log_queue = log_queue
        self.buffer = ""

    def write(self, text: str) -> int:
        if self.log_queue is None:
            return len(text)
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line:
                self.log_queue.put(line)
        return len(text)

    def flush(self) -> None:
        if self.log_queue is None:
            return
        if self.buffer:
            self.log_queue.put(self.buffer)
            self.buffer = ""


def warmup_adb(ld, emulator) -> str:
    cmd = f'{ld.controller} adb --index {emulator.index} --command "devices"'
    return ld._run_cmd(cmd)



def go_home_by_esc(emulator, keys_module, delay: float = 0.2) -> None:
    adb_cmd = f'{emulator.controller} adb {emulator.this} --command "shell input keyevent {keys_module.KEYCODE_ESCAPE}"'
    emulator._run_cmd(adb_cmd)
    time.sleep(delay)
    emulator._run_cmd(adb_cmd)
    time.sleep(delay)
def go_home_by_esc22(emulator, keys_module, delay: float = 0.5) -> None:
    try:
        screen = capture_window_emulator(emulator)
        back_templates = [
            load_template(BACK1_TEMPLATE),
            load_template(BACK2_TEMPLATE),
            load_template(CONFIRM_CHANNEL_TEMPLATE),
        ]

        best_target: tuple[int, int] | None = None
        best_score = -1.0
        for template in back_templates:
            positions = deduplicate_positions(
                find_template_positions(screen, template, threshold=0.8),
                template,
            )
            if positions:
                score = match_score(screen, template)
                if score > best_score:
                    best_score = score
                    best_target = positions[0]

        if best_target is None:
            return
        inactive_click_emulator(emulator, best_target)
        time.sleep(0.3)
        # inactive_click_emulator(emulator, best_target)
        # time.sleep(0.3)
    except Exception:
        return



def select_channel(emulator) -> dict:
    tab_channel_template = load_template(TAB_CHANNEL_TEMPLATE)
    attempts: list[dict] = []

    for attempt_index in range(5):
        # TODO: click mù tọa độ mở panel channel; hiện verify bằng ảnh tab_channel sau click.
        blind_tap(emulator, (1192, 269), label=f"open_channel_panel_attempt_{attempt_index + 1}", post_delay=0.1)
        verify_result = wait_for_template(
            emulator,
            tab_channel_template,
            threshold=0.7,
            timeout=1.0,
            interval=0.15,
            region=(520, 180, 980, 360),
        )
        attempts.append(verify_result)
        if verify_result["matched"]:
            return {
                "success": True,
                "attempts": attempts,
                "attempt": attempt_index + 1,
                "reason": "tab_channel_visible",
            }

    return {
        "success": False,
        "attempts": attempts,
        "attempt": len(attempts),
        "reason": "tab_channel_not_visible_after_retry",
    }


def go_home(emulator, delay: float = 0.5) -> None:
    home_template = load_template(HOME_TEMPLATE)
    confirm_home_template = load_template(CONFIRM_HOME_TEMPLATE)

    home_click = tap_when_template_appears(
        emulator,
        home_template,
        threshold=0.75,
        timeout=max(0.6, delay),
        interval=0.15,
        region=(1000, 80, 1235, 260),
    )
    if not home_click["clicked"]:
        # TODO: fallback click mù tọa độ icon home, giữ lại để dùng khi template chưa match được.
        blind_tap(emulator, (1106, 160), label="go_home_back_button_fallback", post_delay=max(0.1, delay))

    confirm_click = tap_when_template_appears(
        emulator,
        confirm_home_template,
        threshold=0.75,
        timeout=1.2,
        interval=0.15,
        region=(560, 460, 940, 640),
    )
    if not confirm_click["clicked"]:
        # TODO: fallback click mù tọa độ confirm về nhà, giữ lại để dùng khi template chưa match được.
        blind_tap(emulator, (751, 542), label="go_home_confirm_fallback", post_delay=0.1)


def go_map_5x(emulator, keys_module) -> dict:
    def wait_and_click_step(
        template: np.ndarray,
        *,
        step_name: str,
        threshold: float,
        timeout: float,
        region: tuple[int, int, int, int],
        initial_delay: float = 0.2,
        retry_count: int = 1,
    ) -> dict:
        attempts: list[dict] = []
        for attempt_index in range(retry_count):
            step_result = tap_when_template_appears(
                emulator,
                template,
                threshold=threshold,
                timeout=timeout,
                interval=0.15,
                initial_delay=initial_delay,
                region=region,
            )
            attempts.append(step_result)
            if step_result["clicked"]:
                return {
                    **step_result,
                    "step": step_name,
                    "attempt": attempt_index + 1,
                    "attempts": attempts,
                }
        raise RuntimeError(f"go_map_5x: không thấy {step_name}")

    go_home_by_esc(emulator, keys_module)
    time.sleep(0.3)

    map_template = load_template(MAP_TEMPLATE)
    map_6x_template = load_template(MAP_6X_TEMPLATE)
    map_list_template = load_template(MAP_LIST_TEMPLATE)
    map_creep_template = load_template(MAP_CREEP_TEMPLATE)
    instance_move_template = load_template(INSTANCE_MOVE_TEMPLATE)
    confirm_home_template = load_template(CONFIRM_HOME_TEMPLATE)

    # TODO: vẫn là click mù để mở map; sau click sẽ verify bằng ảnh `map.png`.
    blind_tap(emulator, (1191, 214), label="go_map_5x_open_map", post_delay=0.2)

    map_click = wait_and_click_step(
        map_template,
        step_name="map.png sau khi mở map",
        threshold=0.70,
        timeout=3.0,
        region=(480, 120, 980, 720),
        initial_delay=0.25,
    )

    map_6x_click = wait_and_click_step(
        map_6x_template,
        step_name="map6x.png sau khi chọn map",
        threshold=0.70,
        timeout=3.5,
        region=(480, 120, 980, 720),
        initial_delay=0.35,
        retry_count=2,
    )

    map_list_click = wait_and_click_step(
        map_list_template,
        step_name="map_list.png",
        threshold=0.70,
        timeout=3.0,
        region=(520, 120, 980, 720),
        initial_delay=0.3,
    )

    #creep 61
    map_creep_click = wait_and_click_step(
        map_creep_template,
        step_name="map_creep.png",
        threshold=0.70,
        timeout=3.0,
        region=(520, 120, 980, 720),
        initial_delay=0.3,
    )


    #creep 68
    # emulator.drag_drop((862, 574), (862, 190))
    # time.sleep(1)
    # emulator.drag_drop((862, 574), (862, 190))
    # time.sleep(1)
    # map_creep_click = wait_and_click_step(
    #     map_creep_template,
    #     step_name="map_creep_68.png",
    #     threshold=0.70,
    #     timeout=3.0,
    #     region=(520, 120, 980, 720),
    #     initial_delay=0.3,
    # )

    instance_move_click = wait_and_click_step(
        instance_move_template,
        step_name="intance_move.png",
        threshold=0.70,
        timeout=3.0,
        region=(760, 540, 1230, 720),
        initial_delay=0.3,
    )

    confirm_click = wait_and_click_step(
        confirm_home_template,
        step_name="confirm_home.png",
        threshold=0.72,
        timeout=3.0,
        region=(560, 460, 940, 640),
        initial_delay=0.3,
    )

    loading_result = wait_loading(emulator, timeout=20.0, interval=0.2, first_wait=0.5)
    auto_result = enable_auto(emulator, True)
    return {
        "loading": loading_result,
        "auto": auto_result,
        "status": "completed",
    }


def dismantle_items(emulator, keys_module) -> dict:
    def wait_and_click_step(
        template: np.ndarray,
        *,
        step_name: str,
        threshold: float = 0.72,
        timeout: float = 3.0,
        region: tuple[int, int, int, int] | None = None,
        initial_delay: float = 0.2,
        double_tap: bool = False,
        required: bool = True,
    ) -> dict:
        step_result = tap_when_template_appears(
            emulator,
            template,
            threshold=threshold,
            timeout=timeout,
            interval=0.15,
            initial_delay=initial_delay,
            region=region,
            double_tap=double_tap,
            tap_delay=0.1,
        )
        if not step_result["clicked"]:
            return {
                **step_result,
                "step": step_name,
                "success": False,
                "required": required,
                "error": f"dismantle_items: không thấy {step_name}",
            }
        return {
            **step_result,
            "step": step_name,
            "success": True,
            "required": required,
        }

    def require_step(step_result: dict) -> dict:
        if step_result.get("success", False):
            return step_result
        return {
            "status": "failed",
            "failed_step": step_result.get("step"),
            "reason": step_result.get("error", "dismantle_step_failed"),
            "steps": steps,
            "last_click": None,
        }

    go_home_by_esc(emulator, keys_module)
    time.sleep(0.2)

    menu_template = load_template(MENU_TEMPLATE)
    icon_disman_template = load_template(ICON_DISMAN_TEMPLATE)
    disman_tab_template = load_template(DISMAN_TAB_TEMPLATE)
    select_all_template = load_template(SELECT_ALL_TEMPLATE)
    confirm_home_template = load_template(CONFIRM_HOME_TEMPLATE)
    dismantle_button_template = load_template(DISMANTLE_BUTTON_TEMPLATE)
    dismantle_confirm_template = load_template(DISMANTLE_CONFIRM_TEMPLATE)
    back1_template = load_template(BACK1_TEMPLATE)
    steps: dict[str, dict] = {}

    steps["dismantle_open_inventory_menu"] = wait_and_click_step(
        menu_template,
        step_name="menu.png",
        region=(1080, 0, 1280, 140),
        initial_delay=0.2,
    )
    failed_result = require_step(steps["dismantle_open_inventory_menu"])
    if failed_result.get("status") == "failed":
        return failed_result

    steps["dismantle_open_tab"] = wait_and_click_step(
        icon_disman_template,
        step_name="icon_disman.png",
        region=(860, 300, 1260, 560),
        initial_delay=0.25,
    )
    failed_result = require_step(steps["dismantle_open_tab"])
    if failed_result.get("status") == "failed":
        return failed_result

    steps["dismantle_select_filter"] = wait_and_click_step(
        disman_tab_template,
        step_name="disman_tab.png",
        region=(320, 20, 640, 160),
        initial_delay=0.25,
    )
    failed_result = require_step(steps["dismantle_select_filter"])
    if failed_result.get("status") == "failed":
        return failed_result

    steps["dismantle_select_group"] = wait_and_click_step(
        select_all_template,
        step_name="select_all.png",
        region=(900, 560, 1240, 720),
        initial_delay=0.25,
    )
    failed_result = require_step(steps["dismantle_select_group"])
    if failed_result.get("status") == "failed":
        return failed_result

    steps["dismantle_confirm_group"] = wait_and_click_step(
        confirm_home_template,
        step_name="confirm_home.png cho chọn group",
        region=(560, 460, 940, 640),
        initial_delay=0.25,
    )
    failed_result = require_step(steps["dismantle_confirm_group"])
    if failed_result.get("status") == "failed":
        return failed_result

    steps["dismantle_select_all"] = wait_and_click_step(
        dismantle_button_template,
        step_name="dismant_bt.png",
        region=(240, 620, 900, 740),
        initial_delay=0.25,
    )
    failed_result = require_step(steps["dismantle_select_all"])
    if failed_result.get("status") == "failed":
        return failed_result

    steps["dismantle_execute"] = wait_and_click_step(
        confirm_home_template,
        step_name="confirm_home.png cho execute",
        region=(560, 460, 940, 640),
        initial_delay=0.25,
    )
    failed_result = require_step(steps["dismantle_execute"])
    if failed_result.get("status") == "failed":
        return failed_result

    steps["dismantle_confirm_1"] = wait_and_click_step(
        dismantle_confirm_template,
        step_name="disman_com.png",
        region=(760, 600, 1080, 740),
        initial_delay=0.8,
        timeout=6.0,
        required=False,
    )
    if not steps["dismantle_confirm_1"].get("success", False):
        # Fallback giữ flow sống nếu popup confirm ra chậm hoặc không ổn định.
        blind_tap(emulator, (910, 693), label="dismantle_confirm_1_fallback", post_delay=0.5)
        steps["dismantle_confirm_1_fallback"] = {
            "step": "dismantle_confirm_1_fallback",
            "success": True,
            "target": (910, 693),
        }

    steps["dismantle_confirm_2"] = wait_and_click_step(
        back1_template,
        step_name="back1.png",
        region=(1030, 80, 1230, 260),
        initial_delay=0.5,
        timeout=5.0,
        required=False,
    )
    if not steps["dismantle_confirm_2"].get("success", False):
        try:
            go_home_by_esc(emulator, keys_module)
            steps["dismantle_confirm_2_recover"] = {
                "step": "dismantle_confirm_2_recover",
                "success": True,
                "target": "go_home_by_esc",
            }
        except Exception as recover_exc:
            return {
                "status": "failed",
                "failed_step": "dismantle_confirm_2",
                "reason": f"dismantle_items: recover_failed {recover_exc!r}",
                "steps": steps,
                "last_click": None,
            }

    last_click = None
    if steps.get("dismantle_confirm_2", {}).get("target") is not None:
        last_click = steps["dismantle_confirm_2"]["target"]
    elif steps.get("dismantle_confirm_1", {}).get("target") is not None:
        last_click = steps["dismantle_confirm_1"]["target"]
    elif steps.get("dismantle_confirm_1_fallback", {}).get("target") is not None:
        last_click = steps["dismantle_confirm_1_fallback"]["target"]

    go_home_by_esc(emulator, keys_module)
    return {
        "status": "completed",
        "steps": steps,
        "last_click": last_click,
    }


def go_to_boss(emulator, keys_module, boss_number: int, retry_on_fail: bool = True) -> None:
    if boss_number not in BOSS_CHOICE_TEMPLATES:
        raise ValueError(f"boss_number không hợp lệ: {boss_number}")

    def wait_and_click_step(
        template: np.ndarray,
        *,
        step_name: str,
        threshold: float = 0.70,
        timeout: float = 3.0,
        region: tuple[int, int, int, int] | None = None,
        initial_delay: float = 0.2,
    ) -> dict:
        step_result = tap_when_template_appears(
            emulator,
            template,
            threshold=threshold,
            timeout=timeout,
            interval=0.15,
            initial_delay=initial_delay,
            region=region,
        )
        if step_result["clicked"]:
            return step_result

        started_at = time.perf_counter()
        last_detail: dict | None = None
        while time.perf_counter() - started_at < timeout:
            screen = capture_screen(emulator)
            target = crop_region(screen, region)
            score_detail = match_icon_score(target, template)
            last_detail = score_detail
            if score_detail["combined_score"] >= threshold or score_detail["edge_score"] >= max(0.72, threshold):
                positions = deduplicate_positions(
                    find_template_positions(target, template, threshold=max(0.55, threshold - 0.12)),
                    template,
                )
                if positions:
                    if region is not None:
                        offset_x, offset_y, _, _ = region
                        target_position = (positions[0][0] + offset_x, positions[0][1] + offset_y)
                    else:
                        target_position = positions[0]
                    emulator.tap(target_position)
                    return {
                        "clicked": True,
                        "target": target_position,
                        "score": score_detail["combined_score"],
                        "detail": score_detail,
                    }
            time.sleep(0.15)

        raise RuntimeError(f"go_to_boss: không thấy {step_name} | detail={last_detail!r}")

    try:
        go_home_by_esc(emulator, keys_module)
        menu_template = load_template(MENU_TEMPLATE)
        icon_field_boss_template = load_template(ICON_FIELD_BOSS_TEMPLATE)
        boss_choice_template = load_template(BOSS_CHOICE_TEMPLATES[boss_number])
        instance_move_template = load_template(INSTANCE_MOVE_BOSS_TEMPLATE)
        confirm_home_template = load_template(CONFIRM_HOME_TEMPLATE)

        go_to_boss_open_boss_menu = wait_and_click_step(
            menu_template,
            step_name="menu.png",
            threshold=0.68,
            timeout=3.0,
            region=(1080, 0, 1280, 140),
            initial_delay=0.2,
        )
        time.sleep(0.5)
        go_to_boss_open_boss_list = wait_and_click_step(
            icon_field_boss_template,
            step_name="icon_fielboss.png",
            threshold=0.66,
            timeout=3.0,
            region=(860, 520, 1260, 720),
            initial_delay=0.25,
        )
        time.sleep(0.5)
        go_to_boss_select_boss = wait_and_click_step(
            boss_choice_template,
            step_name=f"boss{boss_number}_choice.png",
            threshold=0.64,
            timeout=3.5,
            region=(40, 80, 360, 760),
            initial_delay=0.3,
        )
        time.sleep(1)
        go_to_boss_instance_move = wait_and_click_step(
            instance_move_template,
            step_name="intance_move_boss.png",
            threshold=0.70,
            timeout=3.0,
            region=(760, 540, 1230, 720),
            initial_delay=0.25,
        )
        go_to_boss_move = wait_and_click_step(
            confirm_home_template,
            step_name="confirm_home.png cho move boss",
            threshold=0.72,
            timeout=3.0,
            region=(560, 460, 940, 640),
            initial_delay=0.25,
        )

        _ = go_to_boss_open_boss_menu, go_to_boss_open_boss_list, go_to_boss_select_boss, go_to_boss_instance_move, go_to_boss_move
    except Exception:
        if retry_on_fail:
            try:
                go_home_by_esc(emulator, keys_module)
            except Exception:
                pass
            return go_to_boss(emulator, keys_module, boss_number, retry_on_fail=False)
        raise


# Quy trình chọn channel boss:
# 1. Mở danh sách channel boss và nạp template icon theo boss_number.
# 2. Thử tối đa 2 lượt danh sách:
#    - Lượt 1 kéo xuống.
#    - Lượt 2 kéo ngược lên.
# 3. Mỗi lượt sẽ tạo danh sách ứng viên click theo rule của từng boss.
# 4. Boss 1 và 2, 3, 4, 5, 6 ưu tiên icon thứ 2; nếu lượt 1 chỉ có 1 icon thì sang lượt 2 ưu tiên icon đầu tiên.
# 5. Boss 99 và 9999 ưu tiên icon đầu tiên, sau đó mới thử icon tiếp theo nếu còn.
# 6. Sau mỗi lần click icon boss, luôn đợi 1 giây rồi chụp lại màn hình:
#    - Nếu không còn icon boss nữa thì coi như vào channel thành công.
#    - Nếu vẫn còn icon boss thì thử ứng viên tiếp theo trong cùng lượt trước khi sang lượt sau.
# 7. Nếu sau cả 2 lượt vẫn không chọn được thì return skip.
def select_channel_boss(emulator, boss_number: int, threshold: float = 0.7) -> dict:
    debug_steps: list[dict] = []

    if boss_number not in BOSS_ICON_TEMPLATES:
        print("Ko có template")
        return {
            "success": False,
            "boss_number": boss_number,
            "clicked": False,
            "target": None,
            "template": None,
            "reason": "invalid_boss_number",
            "debug": debug_steps,
        }

    template_path = BOSS_ICON_TEMPLATES[boss_number]
    template = load_template(template_path)
    channel_template = load_template(CHANNEL_TEMPLATE)

    select_channel_result = select_channel(emulator)
    debug_steps.append(
        {
            "step": "open_channel_panel",
            "result": select_channel_result,
        }
    )

    if not select_channel_result.get("success", False):
        return {
            "success": False,
            "boss_number": boss_number,
            "clicked": False,
            "target": None,
            "template": str(template_path),
            "reason": "channel_panel_not_found_after_retry",
            "debug": debug_steps,
        }

    first_scroll_single_icon = False

    for scroll_index in range(2):
        scroll_name = f"scroll_{scroll_index + 1}"
        if scroll_index == 0:
            emulator.drag_drop((641, 286), (638, 414))
            time.sleep(0.5)
            debug_steps.append({"step": scroll_name, "action": "drag_down"})
        else:
            emulator.drag_drop((638, 414), (641, 286))
            time.sleep(0.5)
            debug_steps.append({"step": scroll_name, "action": "drag_up"})

        screen_bytes = emulator._get_screencap_b64decode()
        if not screen_bytes:
            return {
                "success": False,
                "boss_number": boss_number,
                "clicked": False,
                "target": None,
                "template": str(template_path),
                "reason": f"capture_failed_scroll_{scroll_index + 1}: {emulator.error!r}",
                "debug": debug_steps,
            }

        screen = decode_screen(screen_bytes)
        boss_score = match_score(screen, template)
        positions = deduplicate_positions(
            find_template_positions(screen, template, threshold=threshold),
            template,
        )
        debug_steps.append(
            {
                "step": scroll_name,
                "score": boss_score,
                "threshold": threshold,
                "positions": positions,
                "positions_count": len(positions),
                "first_scroll_single_icon": first_scroll_single_icon,
            }
        )

        if not positions:
            debug_steps.append({"step": scroll_name, "decision": "no_icon_found_continue"})
            continue

        candidate_indices: list[int] = []
        candidate_reasons: list[str] = []

        if boss_number in (99,9999):
            candidate_indices.append(0)
            candidate_reasons.append(f"clicked_first_match_scroll_{scroll_index + 1}")
            if len(positions) >= 2:
                candidate_indices.append(1)
                candidate_reasons.append(f"clicked_second_match_scroll_{scroll_index + 1}")
        else:
            if scroll_index == 0 and len(positions) == 1:
                first_scroll_single_icon = True
                debug_steps.append({"step": scroll_name, "decision": "single_icon_on_scroll_1_wait_for_scroll_2"})
                continue

            if scroll_index == 1 and first_scroll_single_icon:
                candidate_indices.append(0)
                candidate_reasons.append("clicked_first_match_scroll_2_after_single_match_on_scroll_1")
                if len(positions) >= 2:
                    candidate_indices.append(1)
                    candidate_reasons.append("clicked_second_match_scroll_2_after_single_match_on_scroll_1")
            else:
                if len(positions) >= 2:
                    candidate_indices.append(1)
                    candidate_reasons.append(f"clicked_second_match_scroll_{scroll_index + 1}")
                if scroll_index == 1 and len(positions) >= 1:
                    candidate_indices.append(0)
                    candidate_reasons.append("clicked_first_match_scroll_2_fallback")

        debug_steps.append(
            {
                "step": scroll_name,
                "candidate_indices": candidate_indices,
                "candidate_reasons": candidate_reasons,
            }
        )

        for candidate_index, reason in zip(candidate_indices, candidate_reasons):
            if candidate_index >= len(positions):
                debug_steps.append(
                    {
                        "step": scroll_name,
                        "candidate_index": candidate_index,
                        "decision": "candidate_index_out_of_range_skip",
                    }
                )
                continue

            target = positions[candidate_index]
            debug_steps.append(
                {
                    "step": scroll_name,
                    "candidate_index": candidate_index,
                    "target": target,
                    "reason": reason,
                    "decision": "tap_candidate",
                }
            )
            emulator.tap(target)
            time.sleep(1)

            screen_bytes = emulator._get_screencap_b64decode()
            if not screen_bytes:
                return {
                    "success": False,
                    "boss_number": boss_number,
                    "clicked": True,
                    "target": target,
                    "template": str(template_path),
                    "reason": f"capture_failed_after_click_scroll_{scroll_index + 1}: {emulator.error!r}",
                    "debug": debug_steps,
                }

            screen = decode_screen(screen_bytes)
            retry_positions = deduplicate_positions(
                find_template_positions(screen, template, threshold=threshold),
                template,
            )
            debug_steps.append(
                {
                    "step": scroll_name,
                    "candidate_index": candidate_index,
                    "retry_positions": retry_positions,
                    "retry_positions_count": len(retry_positions),
                }
            )
            if not retry_positions:
                return {
                    "success": True,
                    "boss_number": boss_number,
                    "clicked": True,
                    "target": target,
                    "template": str(template_path),
                    "reason": f"{reason}_success",
                    "debug": debug_steps,
                }

            debug_steps.append(
                {
                    "step": scroll_name,
                    "candidate_index": candidate_index,
                    "decision": "icon_still_visible_try_next_candidate",
                }
            )

    print("Không thấy boss")
    return {
        "success": True,
        "boss_number": boss_number,
        "clicked": False,
        "target": None,
        "template": str(template_path),
        "reason": "icon_not_found_skip_click",
        "debug": debug_steps,
    }
def load_template(template_path: Path, flags: int = cv2.IMREAD_COLOR) -> np.ndarray:
    cache_key = (str(template_path), int(flags))
    cached = TEMPLATE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    template = cv2.imread(str(template_path), flags)
    if template is None:
        raise FileNotFoundError(f"Không đọc được ảnh mẫu: {template_path}")
    TEMPLATE_CACHE[cache_key] = template
    return template



def decode_screen(screen_bytes: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(screen_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Không giải mã được ảnh chụp màn hình từ LDPlayer")
    return image



def capture_screen(emulator) -> np.ndarray:
    last_error = ""
    for attempt_index in range(3):
        screen_bytes = emulator._get_screencap_b64decode()
        if screen_bytes:
            return decode_screen(screen_bytes)

        last_error = getattr(emulator, "error", "") or "capture returned empty bytes"
        if attempt_index < 2:
            time.sleep(0.3)

    raise RuntimeError(f"Không chụp được màn hình LDPlayer: {last_error!r}")



def crop_region(image: np.ndarray, region: tuple[int, int, int, int] | None) -> np.ndarray:
    if region is None:
        return image

    x1, y1, x2, y2 = region
    height, width = image.shape[:2]
    x1 = max(0, min(x1, width))
    x2 = max(0, min(x2, width))
    y1 = max(0, min(y1, height))
    y2 = max(0, min(y2, height))
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"Region không hợp lệ: {region}")
    return image[y1:y2, x1:x2]


def match_score(image: np.ndarray, template: np.ndarray) -> float:
    img_h, img_w = image.shape[:2]
    tem_h, tem_w = template.shape[:2]
    if tem_h > img_h or tem_w > img_w:
        return -1.0

    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return float(max_val)


def find_template_positions(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8,
) -> list[tuple[int, int]]:
    img_h, img_w = image.shape[:2]
    tem_h, tem_w = template.shape[:2]
    if tem_h > img_h or tem_w > img_w:
        return []

    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    y_loc, x_loc = np.where(result >= threshold)
    positions: list[tuple[int, int]] = []
    for x, y in zip(x_loc, y_loc):
        positions.append((int(x + tem_w // 2), int(y + tem_h // 2)))
    return positions

def deduplicate_positions(
    positions: list[tuple[int, int]],
    template: np.ndarray,
) -> list[tuple[int, int]]:
    distinct_positions: list[tuple[int, int]] = []
    min_dx = max(1, template.shape[1] // 2)
    min_dy = max(1, template.shape[0] // 2)
    for position in positions:
        if all(abs(position[0] - existing[0]) > min_dx or abs(position[1] - existing[1]) > min_dy for existing in distinct_positions):
            distinct_positions.append(position)
    return distinct_positions



def match_icon_score(image: np.ndarray, template: np.ndarray) -> dict:
    color_score = match_score(image, template)

    if len(image.shape) == 3:
        image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        image_gray = image
    if len(template.shape) == 3:
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    else:
        template_gray = template

    gray_score = match_score(image_gray, template_gray)
    image_edges = cv2.Canny(image_gray, 80, 160)
    template_edges = cv2.Canny(template_gray, 80, 160)
    edge_score = match_score(image_edges, template_edges)
    combined_score = color_score * 0.15 + gray_score * 0.35 + edge_score * 0.50

    return {
        "color_score": color_score,
        "gray_score": gray_score,
        "edge_score": edge_score,
        "combined_score": combined_score,
    }



def wait_until(
    predicate,
    *,
    timeout: float,
    interval: float = 0.2,
    initial_delay: float = 0.0,
):
    if initial_delay > 0:
        time.sleep(initial_delay)

    started_at = time.perf_counter()
    last_value = None
    while time.perf_counter() - started_at < timeout:
        last_value = predicate()
        if last_value:
            return {
                "matched": True,
                "value": last_value,
                "elapsed": time.perf_counter() - started_at,
            }
        time.sleep(interval)

    return {
        "matched": False,
        "value": last_value,
        "elapsed": time.perf_counter() - started_at,
    }



def wait_for_template(
    emulator,
    template: np.ndarray,
    *,
    threshold: float = 0.8,
    timeout: float = 10.0,
    interval: float = 0.2,
    initial_delay: float = 0.0,
    region: tuple[int, int, int, int] | None = None,
    min_count: int = 1,
) -> dict:
    last_score = -1.0
    last_positions: list[tuple[int, int]] = []
    last_screen_size: tuple[int, int] | None = None

    def _probe():
        nonlocal last_score, last_positions, last_screen_size
        screen = capture_screen(emulator)
        target = crop_region(screen, region)
        last_screen_size = tuple(int(x) for x in screen.shape[:2])
        last_score = match_score(target, template)
        matched_positions = deduplicate_positions(
            find_template_positions(target, template, threshold=threshold),
            template,
        )
        if region is not None:
            offset_x, offset_y, _, _ = region
            last_positions = [
                (int(position[0] + offset_x), int(position[1] + offset_y))
                for position in matched_positions
            ]
        else:
            last_positions = matched_positions
        if len(last_positions) >= min_count:
            return {
                "score": last_score,
                "positions": last_positions,
                "screen_size": last_screen_size,
            }
        return None

    wait_result = wait_until(
        _probe,
        timeout=timeout,
        interval=interval,
        initial_delay=initial_delay,
    )
    return {
        "matched": wait_result["matched"],
        "elapsed": wait_result["elapsed"],
        "score": last_score,
        "positions": last_positions,
        "screen_size": last_screen_size,
        "threshold": threshold,
        "region": region,
        "min_count": min_count,
        "result": wait_result["value"],
    }



def tap_when_template_appears(
    emulator,
    template: np.ndarray,
    tap_position: tuple[int, int] | None = None,
    *,
    threshold: float = 0.8,
    timeout: float = 10.0,
    interval: float = 0.2,
    initial_delay: float = 0.0,
    region: tuple[int, int, int, int] | None = None,
    min_count: int = 1,
    tap_delay: float = 0.05,
    double_tap: bool = False,
) -> dict:
    wait_result = wait_for_template(
        emulator,
        template,
        threshold=threshold,
        timeout=timeout,
        interval=interval,
        initial_delay=initial_delay,
        region=region,
        min_count=min_count,
    )
    if not wait_result["matched"]:
        return {
            **wait_result,
            "clicked": False,
            "target": None,
        }

    target = tap_position if tap_position is not None else wait_result["positions"][0]
    emulator.tap(target)
    if double_tap:
        time.sleep(tap_delay)
        emulator.tap(target)

    return {
        **wait_result,
        "clicked": True,
        "target": target,
    }



def detect_auto_state(
    emulator,
    auto_template_path: Path = AUTO_TEMPLATE,
    not_auto_template_path: Path = NOT_AUTO_TEMPLATE,
    region: tuple[int, int, int, int] | None = None,
) -> dict:
    screen = capture_screen(emulator)
    target = crop_region(screen, region)
    auto_template = load_template(auto_template_path)
    not_auto_template = load_template(not_auto_template_path)

    auto_score = match_score(target, auto_template)
    not_auto_score = match_score(target, not_auto_template)

    target_gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
    auto_gray = cv2.cvtColor(auto_template, cv2.COLOR_BGR2GRAY)
    not_auto_gray = cv2.cvtColor(not_auto_template, cv2.COLOR_BGR2GRAY)

    target_edges = cv2.Canny(target_gray, 80, 160)
    auto_edges = cv2.Canny(auto_gray, 80, 160)
    not_auto_edges = cv2.Canny(not_auto_gray, 80, 160)

    auto_edge_score = match_score(target_edges, auto_edges)
    not_auto_edge_score = match_score(target_edges, not_auto_edges)

    auto_combined_score = auto_score * 0.35 + auto_edge_score * 0.65
    not_auto_combined_score = not_auto_score * 0.35 + not_auto_edge_score * 0.65

    if auto_combined_score < 0 and not_auto_combined_score < 0:
        state = "not_auto"
        confidence = -1.0
    else:
        state = "auto" if auto_combined_score >= not_auto_combined_score else "not_auto"
        confidence = max(auto_combined_score, not_auto_combined_score)

    return {
        "state": state,
        "confidence": confidence,
        "auto_score": auto_score,
        "not_auto_score": not_auto_score,
        "auto_edge_score": auto_edge_score,
        "not_auto_edge_score": not_auto_edge_score,
        "auto_combined_score": auto_combined_score,
        "not_auto_combined_score": not_auto_combined_score,
        "region": region,
        "screen_size": tuple(int(x) for x in screen.shape[:2]),
        "auto_template_size": tuple(int(x) for x in auto_template.shape[:2]),
        "not_auto_template_size": tuple(int(x) for x in not_auto_template.shape[:2]),
    }


def enable_auto(emulator, enabled: bool) -> dict:
    detection = detect_auto_state(emulator)
    current_state = detection["state"]
    target_state = "auto" if enabled else "not_auto"
    detection["previous_state"] = current_state
    detection["target_state"] = target_state
    detection["toggle_attempts"] = 0
    detection["verification_history"] = []

    if current_state == target_state:
        detection["action"] = "already_target_state"
        detection["verified"] = True
        return detection

    last_verification = detection
    for attempt_index in range(3):
        emulator.tap((1226, 514))
        detection["action"] = "toggled_auto_button" if attempt_index == 0 else "toggled_auto_button_retry"
        detection["toggle_attempts"] = attempt_index + 1

        def _detect_target_auto_state():
            auto_state = detect_auto_state(emulator)
            if auto_state["state"] == target_state:
                return auto_state
            return None

        verify_result = wait_until(
            _detect_target_auto_state,
            timeout=1.8,
            interval=0.2,
            initial_delay=0.15,
        )

        verification = verify_result["value"] or detect_auto_state(emulator)
        verification["verification_index"] = attempt_index
        verification["toggle_attempts_before"] = attempt_index + 1
        verification["retoggled"] = attempt_index > 0
        verification["toggle_attempts_after"] = attempt_index + 1
        detection["verification_history"].append(verification)
        last_verification = verification

        if verification["state"] == target_state:
            break

    detection["verification"] = last_verification
    detection["state"] = last_verification["state"]
    detection["confidence"] = last_verification["confidence"]
    detection["auto_score"] = last_verification["auto_score"]
    detection["not_auto_score"] = last_verification["not_auto_score"]
    detection["auto_edge_score"] = last_verification["auto_edge_score"]
    detection["not_auto_edge_score"] = last_verification["not_auto_edge_score"]
    detection["auto_combined_score"] = last_verification["auto_combined_score"]
    detection["not_auto_combined_score"] = last_verification["not_auto_combined_score"]
    detection["verified"] = last_verification["state"] == target_state
    return detection


def map_name_from_template_path(template_path: Path) -> str:
    name = template_path.stem
    if name.startswith("map_"):
        name = name[4:]
    return name.replace("_", " ").upper()


def detect_current_map(
    emulator,
    map_images_dir: Path = MAP_IMAGES_DIR,
    map_glob: str = MAP_IMAGE_GLOB,
    threshold: float = 0.8,
) -> dict:
    screen = capture_screen(emulator)
    template_paths = sorted(map_images_dir.glob(map_glob))
    if not template_paths:
        raise FileNotFoundError(f"Không tìm thấy ảnh map nào theo mẫu: {map_images_dir / map_glob}")

    best_path: Path | None = None
    best_score = -1.0
    all_scores: dict[str, float] = {}

    for template_path in template_paths:
        template = load_template(template_path)
        score = match_score(screen, template)
        all_scores[template_path.name] = score
        if score > best_score:
            best_score = score
            best_path = template_path

    current_map = "unknown"
    if best_path is not None and best_score >= threshold:
        current_map = map_name_from_template_path(best_path)

    print(current_map)
    return {
        "map": current_map,
        "best_score": best_score,
        "threshold": threshold,
        "matched_template": best_path.name if best_path is not None else None,
        "screen_size": tuple(int(x) for x in screen.shape[:2]),
        "all_scores": all_scores,
    }


def wait_loading(
    emulator,
    done_template_path: Path = DONE_LOADING_TEMPLATE,
    first_wait: float = 0.0,
    timeout: float = 30.0,
    interval: float = 0.2,
    threshold: float = 0.8,
) -> dict:
    loading_template = load_template(LOADING_TEMPLATE)
    done_template = load_template(done_template_path)
    loading_last_score = -1.0

    def _detect_loading_icon():
        nonlocal loading_last_score
        screen = capture_screen(emulator)
        score_detail = match_icon_score(screen, loading_template)
        loading_last_score = score_detail["combined_score"]
        if score_detail["combined_score"] >= 0.62 or score_detail["edge_score"] >= 0.72:
            return score_detail
        return None

    loading_seen_result = wait_until(
        _detect_loading_icon,
        timeout=7.0,
        interval=interval,
        initial_delay=first_wait,
    )

    done_wait_initial_delay = 0.0 if loading_seen_result["matched"] else 0.3
    wait_result = wait_for_template(
        emulator,
        done_template,
        threshold=threshold,
        timeout=timeout,
        interval=interval,
        initial_delay=done_wait_initial_delay,
    )
    return {
        "done": True,
        "loading_seen": loading_seen_result["matched"],
        "loading_elapsed": loading_seen_result["elapsed"],
        "loading_score": loading_last_score,
        "loading_detail": loading_seen_result["value"],
        "matched": wait_result["matched"],
        "score": wait_result["score"],
        "threshold": threshold,
        "elapsed": wait_result["elapsed"],
        "positions": wait_result["positions"],
    }


def wait_boss_done(
    emulator,
    done_template_path: Path = BOSS_DONE_TEMPLATE,
    first_wait: float = 0.0,
    timeout: float = 30.0,
    interval: float = 0.2,
    threshold: float = 0.8,
) -> dict:
    done_template = load_template(done_template_path)
    wait_result = wait_for_template(
        emulator,
        done_template,
        threshold=threshold,
        timeout=timeout,
        interval=interval,
        initial_delay=first_wait,
    )
    return {
        "done": True,
        "matched": wait_result["matched"],
        "score": wait_result["score"],
        "threshold": threshold,
        "elapsed": wait_result["elapsed"],
        "positions": wait_result["positions"],
    }


# Logic `active_boss_world()`:
# 1. Back về trạng thái an toàn trước khi bắt đầu flow boss world.
# 2. Chuẩn bị boss 2 trước giờ spawn:
#    - đi tới boss 2
#    - chờ loading
#    - tắt auto để đứng chờ
#    - đợi tới đúng mốc thời gian spawn
# 3. Với từng boss:
#    - nếu chưa đứng đúng boss hiện tại thì recover rồi đi tới boss đó
#    - chờ loading xong
#    - chọn channel bằng `select_channel_boss()`
# 4. Nếu chọn channel fail hoặc không click được:
#    - recover về neutral state
#    - ghi nhận `select_skipped`
#    - chuyển sang boss tiếp theo
# 5. Nếu chọn channel thành công:
#    - bật auto
#    - trong 30 giây liên tục kiểm tra `boss_rank.png`
#    - nếu không còn thấy `boss_rank.png` thì coi như boss không còn / đã chết, return sớm cho boss đó
#    - nếu vẫn còn thấy `boss_rank.png` thì tiếp tục chờ `wait_boss_done()` như bình thường
# 6. Kết thúc mỗi boss:
#    - recover về neutral state
#    - lưu toàn bộ kết quả loading/select/enter/auto/boss_done/recover
# 7. Sau khi xong boss 2 thì tiếp tục lần lượt boss 3, 4, 5 ,6
def active_boss_world(emulator, keys_module) -> list[dict]:
    boss_rank_template = load_template(BOSS_RANK_TEMPLATE)

    def append_boss_log(entry: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        window_label = f"index={emulator.index}, name={emulator.name}"
        with LOG_BOSS_FILE.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] [{window_label}] {entry}\n")

    def wait_boss_start_time() -> dict:
        started_at = time.perf_counter()
        while True:
            now = datetime.now()
            if now.hour in {10, 15, 19, 22, 1} and now.second >= 15:
            # if True:
                return {
                    "ready": True,
                    "trigger_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "elapsed": time.perf_counter() - started_at,
                }
            time.sleep(1)

    def recover_to_neutral_state() -> dict:
        go_home_by_esc(emulator, keys_module)
        time.sleep(0.5)
        return {
            "status": "recovered",
        }

    def verify_boss_rank_alive(
        timeout: float = 30.0,
        interval: float = 0.5,
        threshold: float = 0.6,
    ) -> dict:
        started_at = time.perf_counter()
        last_score = -1.0
        last_detail: dict | None = None

        while time.perf_counter() - started_at < timeout:
            try:
                screen = capture_screen(emulator)
                score_detail = match_icon_score(screen, boss_rank_template)
                last_detail = score_detail
                last_score = score_detail["combined_score"]
                if score_detail["combined_score"] >= threshold or score_detail["edge_score"] >= max(0.7, threshold):
                    return {
                        "alive": True,
                        "matched": True,
                        "score": score_detail["combined_score"],
                        "detail": score_detail,
                        "threshold": threshold,
                        "elapsed": time.perf_counter() - started_at,
                        "reason": "boss_rank_seen_within_timeout",
                    }
            except Exception as exc:
                last_detail = {
                    "error": repr(exc),
                }
            time.sleep(interval)

        return {
            "alive": False,
            "matched": False,
            "score": last_score,
            "detail": last_detail,
            "threshold": threshold,
            "elapsed": time.perf_counter() - started_at,
            "reason": "boss_rank_not_seen_within_timeout",
        }

    def run_single_boss_cycle(boss_number: int, loading_result: dict | None = None, retry_select: bool = True) -> dict:
        append_boss_log(f"boss={boss_number} | step=start_cycle | has_loading={loading_result is not None} | retry_select={retry_select}")

        def build_cycle_failure(
            step: str,
            exc: Exception,
            *,
            current_loading: dict | None,
            current_select: dict | None,
            current_enter: dict | None,
            current_auto: dict | None,
            current_boss_rank: dict | None,
            current_boss_done: dict | None,
        ) -> dict:
            try:
                recover_result = recover_to_neutral_state()
            except Exception as recover_exc:
                recover_result = {
                    "status": "recover_failed",
                    "error": repr(recover_exc),
                }
            result = {
                "boss": boss_number,
                "loading": current_loading,
                "select": current_select,
                "enter": current_enter,
                "auto": current_auto,
                "boss_rank": current_boss_rank,
                "boss_done": current_boss_done,
                "recover": recover_result,
                "status": "failed",
                "failed_step": step,
                "error": repr(exc),
            }
            append_boss_log(f"boss={boss_number} | step={step} | exception={exc!r}")
            append_boss_log(f"boss_cycle={result!r}")
            return result

        select_result: dict | None = None
        enter_result: dict | None = None
        auto_result: dict | None = None
        boss_rank_result: dict | None = None
        boss_done_result: dict | None = None

        try:
            if loading_result is None:
                # recover_before_go = recover_to_neutral_state()
                # append_boss_log(f"boss={boss_number} | step=recover_before_go | result={recover_before_go!r}")
                print("Go BOSS " + str(boss_number))
                go_to_boss(emulator, keys_module, boss_number)
                append_boss_log(f"boss={boss_number} | step=go_to_boss | result=sent")
                loading_result = wait_loading(emulator)
                append_boss_log(f"boss={boss_number} | step=wait_loading | result={loading_result!r}")
            else:
                append_boss_log(f"boss={boss_number} | step=use_preloaded_loading | result={loading_result!r}")
        except Exception as exc:
            return build_cycle_failure(
                "prepare_or_loading",
                exc,
                current_loading=loading_result,
                current_select=select_result,
                current_enter=enter_result,
                current_auto=auto_result,
                current_boss_rank=boss_rank_result,
                current_boss_done=boss_done_result,
            )

        try:
            select_result = select_channel_boss(emulator, boss_number)
            append_boss_log(f"boss={boss_number} | step=select_channel_boss | result={select_result!r}")
        except Exception as exc:
            return build_cycle_failure(
                "select_channel_boss",
                exc,
                current_loading=loading_result,
                current_select=select_result,
                current_enter=enter_result,
                current_auto=auto_result,
                current_boss_rank=boss_rank_result,
                current_boss_done=boss_done_result,
            )

        if (not select_result.get("success", False)) or (not select_result.get("clicked", False)):
            recover_result = recover_to_neutral_state()
            append_boss_log(f"boss={boss_number} | step=recover_after_select_skip | result={recover_result!r}")
            if retry_select:
                append_boss_log(f"boss={boss_number} | step=retry_same_boss_after_select_skip | action=restart_cycle_once")
                return run_single_boss_cycle(boss_number, loading_result=None, retry_select=False)
            result = {
                "boss": boss_number,
                "loading": loading_result,
                "select": select_result,
                "enter": {
                    "verified": False,
                    "reason": "select_not_clicked_or_failed",
                },
                "auto": None,
                "boss_rank": None,
                "boss_done": None,
                "recover": recover_result,
                "status": "select_skipped",
            }
            append_boss_log(f"boss_cycle={result!r}")
            return result

        enter_result = {
            "verified": True,
            "reason": "select_clicked",
        }
        append_boss_log(f"boss={boss_number} | step=enter_verified | result={enter_result!r}")

        try:
            auto_result = enable_auto(emulator, True)
            append_boss_log(f"boss={boss_number} | step=enable_auto | result={auto_result!r}")
            boss_rank_result = verify_boss_rank_alive()
            append_boss_log(f"boss={boss_number} | step=verify_boss_rank_alive | result={boss_rank_result!r}")
        except Exception as exc:
            return build_cycle_failure(
                "auto_or_boss_rank",
                exc,
                current_loading=loading_result,
                current_select=select_result,
                current_enter=enter_result,
                current_auto=auto_result,
                current_boss_rank=boss_rank_result,
                current_boss_done=boss_done_result,
            )

        if not boss_rank_result.get("alive", True):
            recover_result = recover_to_neutral_state()
            append_boss_log(f"boss={boss_number} | step=recover_after_boss_rank_missing | result={recover_result!r}")
            status = "boss_missing_after_auto" if auto_result.get("verified", False) else "boss_missing_after_auto_with_auto_unverified"
            result = {
                "boss": boss_number,
                "loading": loading_result,
                "select": select_result,
                "enter": enter_result,
                "auto": auto_result,
                "boss_rank": boss_rank_result,
                "boss_done": None,
                "recover": recover_result,
                "status": status,
            }
            append_boss_log(f"boss_cycle={result!r}")
            return result

        try:
            boss_done_result = wait_boss_done(emulator, timeout=boss_timeouts[boss_number])
            append_boss_log(f"boss={boss_number} | step=wait_boss_done | result={boss_done_result!r}")
            recover_result = recover_to_neutral_state()
            append_boss_log(f"boss={boss_number} | step=recover_after_boss_done | result={recover_result!r}")
        except Exception as exc:
            return build_cycle_failure(
                "wait_boss_done_or_recover",
                exc,
                current_loading=loading_result,
                current_select=select_result,
                current_enter=enter_result,
                current_auto=auto_result,
                current_boss_rank=boss_rank_result,
                current_boss_done=boss_done_result,
            )

        if boss_done_result.get("matched", False):
            status = "completed" if auto_result.get("verified", False) else "completed_with_auto_unverified"
        else:
            status = "boss_done_timeout" if auto_result.get("verified", False) else "boss_done_timeout_with_auto_unverified"

        result = {
            "boss": boss_number,
            "loading": loading_result,
            "select": select_result,
            "enter": enter_result,
            "auto": auto_result,
            "boss_rank": boss_rank_result,
            "boss_done": boss_done_result,
            "recover": recover_result,
            "status": status,
        }
        append_boss_log(f"boss_cycle={result!r}")
        return result

    # go_home_by_esc(emulator, keys_module)
    results: list[dict] = []
    boss_timeouts = {
        1: 20,
        2: 60,
        3: 2 * 60,
        4: 3 * 60,
        5: 10 * 60,
        6: 15 * 60,
    }

    print("Go BOSS 2")
    append_boss_log("step=prepare_boss_2 | action=go_to_boss_2")
    go_to_boss(emulator, keys_module, 2)

    first_loading_result = wait_loading(emulator)
   
    append_boss_log(f"step=prepare_boss_2 | wait_loading={first_loading_result!r}")
    first_auto_result = enable_auto(emulator, False)
    append_boss_log(f"step=prepare_boss_2 | disable_auto={first_auto_result!r}")
    wait_result = wait_boss_start_time()
    append_boss_log(f"step=prepare_boss_2 | wait_boss_start_time={wait_result!r}")

    prepare_result = {
        "step": "prepare_boss_2",
        "loading": first_loading_result,
        "auto": first_auto_result,
        "wait": wait_result,
        "status": "prepared",
    }
    results.append(prepare_result)
    append_boss_log(f"prepare={prepare_result!r}")

    results.append(run_single_boss_cycle(2, first_loading_result))
    for boss_number in (3, 4, 5, 6):
        results.append(run_single_boss_cycle(boss_number))

    append_boss_log(f"active_boss_world_completed={results!r}")
    return results


def should_run_boss_world(now: datetime) -> bool:
    return (now.hour, now.minute) in {(9, 58), (14, 58), (18, 58), (21, 58), (0, 58)}


def infinite_farm_loop(emulator, keys_module, loop_interval: float = 10.0) -> None:
    last_dismantle_at = 0.0
    last_boss_trigger: str | None = None

    while True:
        try:
            go_home_by_esc(emulator, keys_module)
            time.sleep(3)
            now = datetime.now()
            trigger_key = now.strftime("%Y-%m-%d %H:%M")

            if should_run_boss_world(now) and last_boss_trigger != trigger_key:
                print(f"Run boss world at {trigger_key}")
                active_boss_world(emulator, keys_module)
                last_boss_trigger = trigger_key
                go_map_5x(emulator, keys_module)
                last_dismantle_at = time.time()
                time.sleep(loop_interval)
                continue

            auto_state = detect_auto_state(emulator)
            print(f"Auto state: {auto_state['state']}")

            if auto_state["state"] != "auto":
                print("Auto is off, go to map 5x")
                go_map_5x(emulator, keys_module)

            now_ts = time.time()
            if now_ts - last_dismantle_at >= 20 * 60:
                print("Run dismantle items")
                dismantle_result = dismantle_items(emulator, keys_module)
                print(f"Dismantle result: {dismantle_result!r}")
                last_dismantle_at = now_ts

            time.sleep(loop_interval)
        except Exception as exc:
            print(f"Farm loop recovered from error: {exc!r}")
            print(traceback.format_exc())
            try:
                go_home_by_esc(emulator, keys_module)
            except Exception as recover_exc:
                print(f"Farm loop recovery failed: {recover_exc!r}")
            time.sleep(3)


def active_fever(emulator, check_interval: float = 10.0, threshold: float = 0.8) -> None:
    fever_template = load_template(FEVER_TEMPLATE)

    while True:
        screen_bytes = emulator._get_screencap_b64decode()
        if screen_bytes:
            screen = decode_screen(screen_bytes)
            fever_positions = deduplicate_positions(
                find_template_positions(screen, fever_template, threshold=threshold),
                fever_template,
            )
            if fever_positions:
                emulator.tap((808, 562))
        time.sleep(check_interval)


def run_emulator_adb_command(emulator, command: str) -> str:
    adb_cmd = f'{emulator.controller} adb {emulator.this} --command "{command}"'
    return emulator._run_cmd(adb_cmd)


def active_login(emulator, keys_module, threshold: float = 0.6) -> dict:
    login_template = load_template(LOGIN_TEMPLATE)
    startgame_template = load_template(STARTGAME_TEMPLATE)
    package_name = "com.playwith.sealm.g.googl"

    try:
        run_emulator_adb_command(emulator, f"shell am force-stop {package_name}")
    except Exception as exc:
        print(f"Login force-stop failed for {package_name}: {exc}")
    time.sleep(5)
    try:
        run_emulator_adb_command(emulator, f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
    except Exception as exc:
        print(f"Login launch failed for {package_name}: {exc}")

    while True:
        screen_bytes = emulator._get_screencap_b64decode()
        if screen_bytes:
            screen = decode_screen(screen_bytes)
            login_positions = deduplicate_positions(
                find_template_positions(screen, login_template, threshold=threshold),
                login_template,
            )
            if login_positions:
                break
        time.sleep(0.5)

    go_home_by_esc(emulator, keys_module)
    # emulator.tap((656, 592))
    # emulator.tap((656, 592))
    # emulator.tap((406, 575))
    emulator.tap((656, 200))
    emulator.tap((656, 200))
    time.sleep(2)
    emulator.tap((656, 200))
    # emulator.tap((653, 310))
    # time.sleep(10)
    # time.sleep(1)
    # emulator.tap((395, 355))
    # time.sleep(1)
    # emulator.tap((871, 214))

    while True:
        screen_bytes = emulator._get_screencap_b64decode()
        if screen_bytes:
            screen = decode_screen(screen_bytes)
            startgame_positions = deduplicate_positions(
                find_template_positions(screen, startgame_template, threshold=threshold),
                startgame_template,
            )
            if startgame_positions:
                emulator.tap((650, 670))
                break
        time.sleep(0.5)

    loading_result = wait_loading(emulator)
    return {
        "status": "completed",
        "loading": loading_result,
        "package": package_name,
    }


def active_detect_disconnect(emulator, keys_module, check_interval: float = 10 * 60, threshold: float = 0.9) -> None:
    disconnect_template = load_template(DISCONNECT_TEMPLATE)
    package_name = "com.playwith.sealm.g.googl"

    def is_target_app_active() -> bool:
        activity_output = ""
        window_output = ""

        try:
            activity_output = run_emulator_adb_command(emulator, "shell dumpsys activity activities")
        except Exception as exc:
            print(f"Cannot read activity state for {package_name}: {exc}")

        try:
            window_output = run_emulator_adb_command(emulator, "shell dumpsys window windows")
        except Exception as exc:
            print(f"Cannot read window state for {package_name}: {exc}")

        focus_markers = (
            "mresumedactivity",
            "resumedactivity",
            "topresumedactivity",
            "mfocusedapp",
            "mcurrentfocus",
        )

        for raw_output in (activity_output, window_output):
            if not raw_output:
                continue

            for line in raw_output.splitlines():
                normalized_line = line.strip().lower()
                if package_name in normalized_line and any(marker in normalized_line for marker in focus_markers):
                    return True

        return False

    while True:
        disconnect_detected = False

        screen_bytes = emulator._get_screencap_b64decode()
        if screen_bytes:
            screen = decode_screen(screen_bytes)
            disconnect_positions = deduplicate_positions(
                find_template_positions(screen, disconnect_template, threshold=threshold),
                disconnect_template,
            )
            if disconnect_positions:
                print("Disconnect detected from template, requesting UI to stop other processes")
                disconnect_detected = True

        if not disconnect_detected and not is_target_app_active():
            print(f"Disconnect detected because focused app is not {package_name}")
            disconnect_detected = True

        if disconnect_detected:
            raise RuntimeError("__DISCONNECT_DETECTED__")

        time.sleep(check_interval)


def active_quest(emulator, keys_module, check_interval: float = 15.0, threshold: float = 0.8) -> None:
    quest_done_template = load_template(QUEST_DONE_TEMPLATE)
    confirm_quest_template = load_template(CONFIRM_QUEST_TEMPLATE)

    go_home_by_esc(emulator, keys_module)
    emulator.tap((1247, 31))
    time.sleep(0.5)
    emulator.tap((1222, 411))
    time.sleep(4)
    
    emulator.tap((817, 676))
    time.sleep(2)
    emulator.tap((817, 676))
    time.sleep(1)

    emulator.tap((538, 680))
    time.sleep(0.5)
    emulator.tap((725, 569))

    time.sleep(2)

    while True:
        screen_bytes = emulator._get_screencap_b64decode()
        if screen_bytes:
            screen = decode_screen(screen_bytes)
            confirm_positions = deduplicate_positions(
                find_template_positions(screen, confirm_quest_template, threshold=threshold),
                confirm_quest_template,
            )
            if confirm_positions:
                emulator.tap((642, 541))
                time.sleep(1)
                emulator.tap((642, 541))
                break
        time.sleep(0.5)

    while True:
        screen_bytes = emulator._get_screencap_b64decode()
        if screen_bytes:
            screen = decode_screen(screen_bytes)
            quest_done_positions = deduplicate_positions(
                find_template_positions(screen, quest_done_template, threshold=threshold),
                quest_done_template,
            )
            if len(quest_done_positions) >= 3:
                emulator.tap((817, 676))
                time.sleep(2)
                emulator.tap((817, 676))
                time.sleep(1)

                emulator.tap((538, 680))
                time.sleep(0.5)
                emulator.tap((725, 569))

                time.sleep(2)
                
                while True:
                    screen_bytes = emulator._get_screencap_b64decode()
                    if screen_bytes:
                        screen = decode_screen(screen_bytes)
                        confirm_positions = deduplicate_positions(
                            find_template_positions(screen, confirm_quest_template, threshold=threshold),
                            confirm_quest_template,
                        )
                        if confirm_positions:
                            emulator.tap((642, 541))
                            time.sleep(1)
                            emulator.tap((642, 541))
                            break
                    time.sleep(0.5)

        time.sleep(check_interval)


def active_dungeon(emulator, keys_module, threshold: float = 0.93) -> dict:
    dungeon_enter_template = load_template(DUNGEON_ENTER_TEMPLATE)
    dungeon_instance_template = load_template(DUNGEON_INSTANCE_TEMPLATE)
    dungeon_leave_template = load_template(DUNGEON_LEAVE_TEMPLATE)
    dungeon_retry_template = load_template(DUNGEON_RETRY_TEMPLATE)

    def run_dungeon_boss(boss_number: int, boss_position: tuple[int, int]) -> dict:
        entered = False
        enter_result: dict | None = None
        for attempt_index in range(2):
            if attempt_index == 0:
                emulator.tap(boss_position)
            else:
                emulator.tap((1193, 160))
            time.sleep(1)

            screen_bytes = emulator._get_screencap_b64decode()
            if not screen_bytes:
                return {
                    "success": False,
                    "boss": boss_number,
                    "entered": False,
                    "attempt": attempt_index + 1,
                    "reason": f"capture_failed_before_enter_boss_{boss_number}_attempt_{attempt_index + 1}: {emulator.error!r}",
                }

            screen = decode_screen(screen_bytes)
            enter_score = match_score(screen, dungeon_enter_template)
            instance_score = match_score(screen, dungeon_instance_template)
            if enter_score >= threshold and instance_score >= threshold:
                emulator.tap((1114, 659))
                entered = True
                enter_result = {
                    "success": True,
                    "boss": boss_number,
                    "entered": True,
                    "attempt": attempt_index + 1,
                    "enter_score": enter_score,
                    "instance_score": instance_score,
                    "reason": f"entered_dungeon_boss_{boss_number}_attempt_{attempt_index + 1}",
                }
                break

        if not entered:
            return {
                "success": True,
                "boss": boss_number,
                "entered": False,
                "attempt": 2,
                "reason": f"dungeon_boss_{boss_number}_entry_not_found",
            }

        while True:
            screen_bytes = emulator._get_screencap_b64decode()
            if not screen_bytes:
                time.sleep(0.5)
                continue

            screen = decode_screen(screen_bytes)
            leave_score = match_score(screen, dungeon_leave_template)
            if leave_score < threshold:
                time.sleep(0.5)
                continue

            retry_score = match_score(screen, dungeon_retry_template)
            if retry_score >= threshold:
                emulator.tap((634, 640))
                time.sleep(1)
                continue

            time.sleep(60)
            return {
                **enter_result,
                "leave_score": leave_score,
                "retry_score": retry_score,
                "reason": f"dungeon_boss_{boss_number}_completed",
            }

    go_home_by_esc(emulator, keys_module)
    emulator.tap((1253, 33))
    time.sleep(1)
    emulator.tap((943, 505))
    time.sleep(2)

    results = [
        run_dungeon_boss(1, (105, 158)),
        run_dungeon_boss(2, (105, 300)),
        run_dungeon_boss(3, (105, 224)),
    ]

    go_home_by_esc(emulator, keys_module)
    return {
        "success": all(result.get("success", False) for result in results),
        "results": results,
        "reason": "dungeon_boss_1_2_3_completed",
    }


def get_running_emulators() -> list[dict]:
    ld, _ = create_ldplayer()
    running_names = set(ld.list_running())
    running_emulators: list[dict] = []

    for emulator in ld.emulators:
        is_running = emulator.name in running_names or emulator.is_running()
        if not is_running:
            continue
        emulator._update()
        running_emulators.append(
            {
                "index": emulator.index,
                "name": emulator.name,
                "top_hwnd": emulator.top_hwnd,
                "bind_hwnd": emulator.bind_hwnd,
                "pid": emulator.pid,
                "pid_vbox": emulator.pid_vbox,
            }
        )

    return running_emulators


def run_emulator_worker(emulator_index: int, log_queue: multiprocessing.Queue | None = None) -> None:
    writer = QueueWriter(log_queue)
    sys.stdout = writer
    sys.stderr = writer
    try:
        ld, cloned_keys = create_ldplayer()
        emulator = ld.emulators[emulator_index]
        emulator.start(wait=True)
        bind_window_mode(emulator)
        print(
            f"Selected emulator: index={emulator.index}, "
            f"name={emulator.name}, top_hwnd={emulator.top_hwnd}, bind_hwnd={emulator.bind_hwnd}"
        )
        adb_state = warmup_adb(ld, emulator)
        print(f"ADB warmup: {adb_state!r}")
        infinite_farm_loop(emulator, cloned_keys)
    except Exception as exc:
        print(f"Worker crashed: {exc}")
        raise
    finally:
        writer.flush()


def run_boss_worker(emulator_index: int, log_queue: multiprocessing.Queue | None = None) -> None:
    writer = QueueWriter(log_queue)
    sys.stdout = writer
    sys.stderr = writer
    try:
        ld, cloned_keys = create_ldplayer()
        emulator = ld.emulators[emulator_index]
        emulator.start(wait=True)
        bind_window_mode(emulator)
        print(
            f"Selected emulator for boss: index={emulator.index}, "
            f"name={emulator.name}, top_hwnd={emulator.top_hwnd}, bind_hwnd={emulator.bind_hwnd}"
        )
        adb_state = warmup_adb(ld, emulator)
        print(f"ADB warmup boss: {adb_state!r}")
        active_boss_world(emulator, cloned_keys)
    except Exception as exc:
        print(f"Boss worker crashed: {exc}")
        raise
    finally:
        writer.flush()


def run_quest_worker(emulator_index: int, log_queue: multiprocessing.Queue | None = None) -> None:
    writer = QueueWriter(log_queue)
    sys.stdout = writer
    sys.stderr = writer
    try:
        ld, cloned_keys = create_ldplayer()
        emulator = ld.emulators[emulator_index]
        emulator.start(wait=True)
        bind_window_mode(emulator)
        print(
            f"Selected emulator for quest: index={emulator.index}, "
            f"name={emulator.name}, top_hwnd={emulator.top_hwnd}, bind_hwnd={emulator.bind_hwnd}"
        )
        adb_state = warmup_adb(ld, emulator)
        print(f"ADB warmup quest: {adb_state!r}")
        active_quest(emulator, cloned_keys)
    except Exception as exc:
        print(f"Quest worker crashed: {exc}")
        raise
    finally:
        writer.flush()


def run_dismantle_worker(emulator_index: int, log_queue: multiprocessing.Queue | None = None, interval_seconds: float = 5 * 60) -> None:
    writer = QueueWriter(log_queue)
    sys.stdout = writer
    sys.stderr = writer
    try:
        ld, cloned_keys = create_ldplayer()
        emulator = ld.emulators[emulator_index]
        emulator.start(wait=True)
        bind_window_mode(emulator)
        print(
            f"Selected emulator for dismantle: index={emulator.index}, "
            f"name={emulator.name}, top_hwnd={emulator.top_hwnd}, bind_hwnd={emulator.bind_hwnd}"
        )
        adb_state = warmup_adb(ld, emulator)
        print(f"ADB warmup dismantle: {adb_state!r}")
        while True:
            try:
                go_home_by_esc(emulator, cloned_keys)
                result = dismantle_items(emulator, cloned_keys)
                go_home_by_esc(emulator, cloned_keys)
                print(f"Dismantle result: {result!r}")
            except Exception as loop_exc:
                print(f"Dismantle iteration failed: {loop_exc!r}")
                print(traceback.format_exc())
                try:
                    go_home_by_esc(emulator, cloned_keys)
                except Exception as recover_exc:
                    print(f"Dismantle worker recovery failed: {recover_exc!r}")
            time.sleep(interval_seconds)
    except Exception as exc:
        print(f"Dismantle worker crashed: {exc}")
        raise
    finally:
        writer.flush()


def run_dungeon_worker(emulator_index: int, log_queue: multiprocessing.Queue | None = None) -> None:
    writer = QueueWriter(log_queue)
    sys.stdout = writer
    sys.stderr = writer
    try:
        ld, cloned_keys = create_ldplayer()
        emulator = ld.emulators[emulator_index]
        emulator.start(wait=True)
        bind_window_mode(emulator)
        print(
            f"Selected emulator for dungeon: index={emulator.index}, "
            f"name={emulator.name}, top_hwnd={emulator.top_hwnd}, bind_hwnd={emulator.bind_hwnd}"
        )
        adb_state = warmup_adb(ld, emulator)
        print(f"ADB warmup dungeon: {adb_state!r}")
        dungeon_result = active_dungeon(emulator, cloned_keys)
        print(f"Dungeon result: {dungeon_result!r}")
        if log_queue is not None:
            log_queue.put("__START_RUN_AFTER_DUNGEON__")
        print("Dungeon finished, requesting UI to start Run")
    except Exception as exc:
        print(f"Dungeon worker crashed: {exc}")
        raise
    finally:
        writer.flush()


def run_fever_worker(emulator_index: int, log_queue: multiprocessing.Queue | None = None) -> None:
    writer = QueueWriter(log_queue)
    sys.stdout = writer
    sys.stderr = writer
    try:
        ld, _ = create_ldplayer()
        emulator = ld.emulators[emulator_index]
        emulator.start(wait=True)
        bind_window_mode(emulator)
        print(
            f"Selected emulator for fever: index={emulator.index}, "
            f"name={emulator.name}, top_hwnd={emulator.top_hwnd}, bind_hwnd={emulator.bind_hwnd}"
        )
        adb_state = warmup_adb(ld, emulator)
        print(f"ADB warmup fever: {adb_state!r}")
        active_fever(emulator)
    except Exception as exc:
        print(f"Fever worker crashed: {exc}")
        raise
    finally:
        writer.flush()


def run_detect_disconnect_worker(emulator_index: int, log_queue: multiprocessing.Queue | None = None) -> None:
    writer = QueueWriter(log_queue)
    sys.stdout = writer
    sys.stderr = writer
    try:
        ld, cloned_keys = create_ldplayer()
        emulator = ld.emulators[emulator_index]
        emulator.start(wait=True)
        bind_window_mode(emulator)
        print(
            f"Selected emulator for detect_disconnect: index={emulator.index}, "
            f"name={emulator.name}, top_hwnd={emulator.top_hwnd}, bind_hwnd={emulator.bind_hwnd}"
        )
        adb_state = warmup_adb(ld, emulator)
        print(f"ADB warmup detect_disconnect: {adb_state!r}")
        active_detect_disconnect(emulator, cloned_keys)
    except Exception as exc:
        if str(exc) == "__DISCONNECT_DETECTED__":
            if log_queue is not None:
                log_queue.put("__DISCONNECT_DETECTED__")
            login_result = active_login(emulator, cloned_keys)
            print(f"Detect disconnect -> login result: {login_result!r}")
            if login_result.get("status") == "completed" and log_queue is not None:
                log_queue.put("__START_RUN_AFTER_LOGIN__")
            return
        print(f"Detect disconnect worker crashed: {exc}")
        raise
    finally:
        writer.flush()


class LDPlayerManagerApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("SEALM LDPlayer Manager")
        self.root.geometry("1200x420")
        self.root.minsize(1000, 340)
        self.root.configure(bg="#f4f6fb")
        self.processes: dict[int, multiprocessing.Process] = {}
        self.boss_processes: dict[int, multiprocessing.Process] = {}
        self.quest_processes: dict[int, multiprocessing.Process] = {}
        self.dungeon_processes: dict[int, multiprocessing.Process] = {}
        self.dismantle_processes: dict[int, multiprocessing.Process] = {}
        self.fever_processes: dict[int, multiprocessing.Process] = {}
        self.detect_disconnect_processes: dict[int, multiprocessing.Process] = {}
        self.log_queues: dict[int, multiprocessing.Queue] = {}
        self.button_refs: dict[int, ttk.Button] = {}
        self.boss_button_refs: dict[int, ttk.Button] = {}
        self.quest_button_refs: dict[int, ttk.Button] = {}
        self.dungeon_button_refs: dict[int, ttk.Button] = {}
        self.dismantle_button_refs: dict[int, ttk.Button] = {}
        self.fever_button_refs: dict[int, ttk.Button] = {}
        self.detect_disconnect_button_refs: dict[int, ttk.Button] = {}
        self.test_click_button_refs: dict[int, ttk.Button] = {}
        self.log_button_refs: dict[int, ttk.Button] = {}
        self.rows: dict[int, dict[str, ttk.Label]] = {}
        self.log_windows: dict[int, tk.Toplevel] = {}
        self.log_texts: dict[int, tk.Text] = {}

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("App.TFrame", background="#f4f6fb")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("Header.TLabel", background="#f4f6fb", foreground="#172033", font=("Segoe UI", 16, "bold"))
        style.configure("SubHeader.TLabel", background="#f4f6fb", foreground="#5b6475", font=("Segoe UI", 10))
        style.configure("TableHeader.TLabel", background="#e9eef8", foreground="#1f2937", font=("Segoe UI", 10, "bold"), padding=(8, 8))
        style.configure("NameCell.TLabel", background="#ffffff", foreground="#111827", font=("Segoe UI", 10, "bold"), padding=(8, 8))
        style.configure("Cell.TLabel", background="#ffffff", foreground="#374151", font=("Segoe UI", 10), padding=(8, 8))
        style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"), padding=(10, 6))
        style.configure("Action.TButton", font=("Segoe UI", 9), padding=(8, 6))

        container = ttk.Frame(self.root, padding=16, style="App.TFrame")
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container, style="App.TFrame")
        header.pack(fill="x", pady=(0, 12))

        ttk.Label(header, text="LDPlayer đang chạy", style="Header.TLabel").pack(side="left")
        ttk.Button(header, text="Refresh", command=self.refresh_emulators, style="Primary.TButton").pack(side="right")

        status_card = ttk.Frame(container, padding=12, style="Card.TFrame")
        status_card.pack(fill="x", pady=(0, 12))
        self.message_var = tk.StringVar(value="Sẵn sàng")
        ttk.Label(status_card, textvariable=self.message_var, style="Cell.TLabel").pack(anchor="w")

        self.table = ttk.Frame(container, padding=10, style="Card.TFrame")
        self.table.pack(fill="both", expand=True)

        headers = ["Name", "Status", "Farm", "Boss", "Quest", "Dungeon", "Dismantle", "Faver", "Disconnect", "TestClick", "Log"]
        widths = [10, 14, 10, 10, 10, 11, 12, 10, 12, 12, 10]
        for col, (text, width) in enumerate(zip(headers, widths, strict=False)):
            label = ttk.Label(self.table, text=text, anchor="center", style="TableHeader.TLabel")
            label.grid(row=0, column=col, padx=4, pady=(0, 6), sticky="nsew")
            self.table.grid_columnconfigure(col, weight=1, minsize=width * 9)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_emulators()
        self.poll_processes()
        self.drain_log_queues()

    def is_process_running(self, emulator_index: int) -> bool:
        process = self.processes.get(emulator_index)
        return process is not None and process.is_alive()

    def is_boss_process_running(self, emulator_index: int) -> bool:
        process = self.boss_processes.get(emulator_index)
        return process is not None and process.is_alive()

    def is_quest_process_running(self, emulator_index: int) -> bool:
        process = self.quest_processes.get(emulator_index)
        return process is not None and process.is_alive()

    def is_dungeon_process_running(self, emulator_index: int) -> bool:
        process = self.dungeon_processes.get(emulator_index)
        return process is not None and process.is_alive()

    def is_dismantle_process_running(self, emulator_index: int) -> bool:
        process = self.dismantle_processes.get(emulator_index)
        return process is not None and process.is_alive()

    def is_fever_process_running(self, emulator_index: int) -> bool:
        process = self.fever_processes.get(emulator_index)
        return process is not None and process.is_alive()

    def is_detect_disconnect_process_running(self, emulator_index: int) -> bool:
        process = self.detect_disconnect_processes.get(emulator_index)
        return process is not None and process.is_alive()

    def has_active_process(self, emulator_index: int) -> bool:
        return (
            self.is_process_running(emulator_index)
            or self.is_boss_process_running(emulator_index)
            or self.is_quest_process_running(emulator_index)
            or self.is_dungeon_process_running(emulator_index)
            or self.is_dismantle_process_running(emulator_index)
            or self.is_fever_process_running(emulator_index)
            or self.is_detect_disconnect_process_running(emulator_index)
        )

    def update_button_state(self, emulator_index: int) -> None:
        button = self.button_refs.get(emulator_index)
        boss_button = self.boss_button_refs.get(emulator_index)
        quest_button = self.quest_button_refs.get(emulator_index)
        dungeon_button = self.dungeon_button_refs.get(emulator_index)
        dismantle_button = self.dismantle_button_refs.get(emulator_index)
        fever_button = self.fever_button_refs.get(emulator_index)
        detect_disconnect_button = self.detect_disconnect_button_refs.get(emulator_index)
        test_click_button = self.test_click_button_refs.get(emulator_index)
        log_button = self.log_button_refs.get(emulator_index)
        status_label = self.rows.get(emulator_index, {}).get("status")
        if button is None or boss_button is None or quest_button is None or dungeon_button is None or dismantle_button is None or fever_button is None or detect_disconnect_button is None or test_click_button is None or status_label is None or log_button is None:
            return

        if self.is_process_running(emulator_index):
            button.configure(text="Stop", command=lambda idx=emulator_index: self.stop_emulator(idx))
        else:
            button.configure(text="Run", command=lambda idx=emulator_index: self.start_emulator(idx))

        if self.is_boss_process_running(emulator_index):
            boss_button.configure(text="Stop", command=lambda idx=emulator_index: self.stop_boss(idx))
        else:
            boss_button.configure(text="Boss", command=lambda idx=emulator_index: self.start_boss(idx))

        if self.is_quest_process_running(emulator_index):
            quest_button.configure(text="Stop", command=lambda idx=emulator_index: self.stop_quest(idx))
        else:
            quest_button.configure(text="Quest", command=lambda idx=emulator_index: self.start_quest(idx))

        if self.is_dungeon_process_running(emulator_index):
            dungeon_button.configure(text="Stop", command=lambda idx=emulator_index: self.stop_dungeon(idx))
        else:
            dungeon_button.configure(text="Dungeon", command=lambda idx=emulator_index: self.start_dungeon(idx))

        if self.is_dismantle_process_running(emulator_index):
            dismantle_button.configure(text="Stop", command=lambda idx=emulator_index: self.stop_dismantle(idx))
        else:
            dismantle_button.configure(text="Dismantle", command=lambda idx=emulator_index: self.start_dismantle(idx))

        if self.is_fever_process_running(emulator_index):
            fever_button.configure(text="Stop", command=lambda idx=emulator_index: self.stop_fever(idx))
        else:
            fever_button.configure(text="Faver", command=lambda idx=emulator_index: self.start_fever(idx))

        if self.is_detect_disconnect_process_running(emulator_index):
            detect_disconnect_button.configure(text="Stop", command=lambda idx=emulator_index: self.stop_detect_disconnect(idx))
        else:
            detect_disconnect_button.configure(text="Disconnect", command=lambda idx=emulator_index: self.start_detect_disconnect(idx))

        fever_button.configure(state="normal")
        detect_disconnect_button.configure(state="normal")
        test_click_button.configure(state="normal")
        log_button.configure(state="normal")

        if self.is_process_running(emulator_index):
            status_label.configure(text="Running bot")
        elif self.is_boss_process_running(emulator_index):
            status_label.configure(text="Running boss")
        elif self.is_quest_process_running(emulator_index):
            status_label.configure(text="Running quest")
        elif self.is_dungeon_process_running(emulator_index):
            status_label.configure(text="Running dungeon")
        elif self.is_dismantle_process_running(emulator_index):
            status_label.configure(text="Running dismantle")
        elif self.is_fever_process_running(emulator_index):
            status_label.configure(text="Running faver")
        elif self.is_detect_disconnect_process_running(emulator_index):
            status_label.configure(text="Running disconnect")
        else:
            status_label.configure(text="Idle")

    def clear_table_rows(self) -> None:
        for widgets in self.rows.values():
            for widget in widgets.values():
                widget.destroy()
        for button in self.button_refs.values():
            button.destroy()
        for button in self.boss_button_refs.values():
            button.destroy()
        for button in self.quest_button_refs.values():
            button.destroy()
        for button in self.dungeon_button_refs.values():
            button.destroy()
        for button in self.dismantle_button_refs.values():
            button.destroy()
        for button in self.fever_button_refs.values():
            button.destroy()
        for button in self.detect_disconnect_button_refs.values():
            button.destroy()
        for button in self.test_click_button_refs.values():
            button.destroy()
        for button in self.log_button_refs.values():
            button.destroy()
        self.rows.clear()
        self.button_refs.clear()
        self.boss_button_refs.clear()
        self.quest_button_refs.clear()
        self.dungeon_button_refs.clear()
        self.dismantle_button_refs.clear()
        self.fever_button_refs.clear()
        self.detect_disconnect_button_refs.clear()
        self.test_click_button_refs.clear()
        self.log_button_refs.clear()

    def refresh_emulators(self) -> None:
        current_running = {index for index, process in self.processes.items() if process.is_alive()}
        current_boss_running = {index for index, process in self.boss_processes.items() if process.is_alive()}
        current_quest_running = {index for index, process in self.quest_processes.items() if process.is_alive()}
        current_dungeon_running = {index for index, process in self.dungeon_processes.items() if process.is_alive()}
        current_dismantle_running = {index for index, process in self.dismantle_processes.items() if process.is_alive()}
        current_fever_running = {index for index, process in self.fever_processes.items() if process.is_alive()}
        current_detect_disconnect_running = {index for index, process in self.detect_disconnect_processes.items() if process.is_alive()}
        self.clear_table_rows()

        try:
            emulators = get_running_emulators()
        except Exception as exc:
            self.message_var.set(f"Không tải được danh sách LDPlayer: {exc}")
            return

        if not emulators:
            self.message_var.set("Không có cửa sổ LDPlayer nào đang chạy")
            return

        self.message_var.set(
            f"Đã tìm thấy {len(emulators)} cửa sổ LDPlayer đang chạy | "
            f"Farm: {len(current_running)} | Boss: {len(current_boss_running)} | "
            f"Quest: {len(current_quest_running)} | Dungeon: {len(current_dungeon_running)} | "
            f"Dismantle: {len(current_dismantle_running)} | Faver: {len(current_fever_running)} | Disconnect: {len(current_detect_disconnect_running)}"
        )

        for row_index, emulator in enumerate(emulators, start=1):
            emulator_index = emulator["index"]
            labels = {
                "name": ttk.Label(self.table, text=emulator["name"], anchor="w", style="NameCell.TLabel"),
                "status": ttk.Label(
                    self.table,
                    text="Running bot" if emulator_index in current_running else "Running boss" if emulator_index in current_boss_running else "Running quest" if emulator_index in current_quest_running else "Running dungeon" if emulator_index in current_dungeon_running else "Running dismantle" if emulator_index in current_dismantle_running else "Running faver" if emulator_index in current_fever_running else "Running disconnect" if emulator_index in current_detect_disconnect_running else "Idle",
                    anchor="center",
                    style="Cell.TLabel",
                ),
            }
            for col, key in enumerate(("name", "status")):
                labels[key].grid(row=row_index, column=col, padx=4, pady=4, sticky="nsew")

            button = ttk.Button(
                self.table,
                text="Stop" if emulator_index in current_running else "Run",
                command=(lambda idx=emulator_index: self.stop_emulator(idx)) if emulator_index in current_running else (lambda idx=emulator_index: self.start_emulator(idx)),
                style="Action.TButton",
            )
            button.grid(row=row_index, column=2, padx=4, pady=4, sticky="nsew")

            boss_button = ttk.Button(
                self.table,
                text="Stop" if emulator_index in current_boss_running else "Boss",
                command=(lambda idx=emulator_index: self.stop_boss(idx)) if emulator_index in current_boss_running else (lambda idx=emulator_index: self.start_boss(idx)),
                style="Action.TButton",
            )
            boss_button.grid(row=row_index, column=3, padx=4, pady=4, sticky="nsew")

            quest_button = ttk.Button(
                self.table,
                text="Stop" if emulator_index in current_quest_running else "Quest",
                command=(lambda idx=emulator_index: self.stop_quest(idx)) if emulator_index in current_quest_running else (lambda idx=emulator_index: self.start_quest(idx)),
                style="Action.TButton",
            )
            quest_button.grid(row=row_index, column=4, padx=4, pady=4, sticky="nsew")

            dungeon_button = ttk.Button(
                self.table,
                text="Stop" if emulator_index in current_dungeon_running else "Dungeon",
                command=(lambda idx=emulator_index: self.stop_dungeon(idx)) if emulator_index in current_dungeon_running else (lambda idx=emulator_index: self.start_dungeon(idx)),
                style="Action.TButton",
            )
            dungeon_button.grid(row=row_index, column=5, padx=4, pady=4, sticky="nsew")

            dismantle_button = ttk.Button(
                self.table,
                text="Stop" if emulator_index in current_dismantle_running else "Dismantle",
                command=(lambda idx=emulator_index: self.stop_dismantle(idx)) if emulator_index in current_dismantle_running else (lambda idx=emulator_index: self.start_dismantle(idx)),
                style="Action.TButton",
            )
            dismantle_button.grid(row=row_index, column=6, padx=4, pady=4, sticky="nsew")

            fever_button = ttk.Button(
                self.table,
                text="Stop" if emulator_index in current_fever_running else "Faver",
                command=(lambda idx=emulator_index: self.stop_fever(idx)) if emulator_index in current_fever_running else (lambda idx=emulator_index: self.start_fever(idx)),
                style="Action.TButton",
            )
            fever_button.grid(row=row_index, column=7, padx=4, pady=4, sticky="nsew")

            detect_disconnect_button = ttk.Button(
                self.table,
                text="Stop" if emulator_index in current_detect_disconnect_running else "Disconnect",
                command=(lambda idx=emulator_index: self.stop_detect_disconnect(idx)) if emulator_index in current_detect_disconnect_running else (lambda idx=emulator_index: self.start_detect_disconnect(idx)),
                style="Action.TButton",
            )
            detect_disconnect_button.grid(row=row_index, column=8, padx=4, pady=4, sticky="nsew")

            test_click_button = ttk.Button(
                self.table,
                text="Click",
                command=lambda idx=emulator_index: self.test_inactive_click(idx),
                style="Action.TButton",
            )
            test_click_button.grid(row=row_index, column=9, padx=4, pady=4, sticky="nsew")

            log_button = ttk.Button(
                self.table,
                text="Log",
                command=lambda idx=emulator_index, name=emulator["name"]: self.open_log_window(idx, name),
                style="Action.TButton",
            )
            log_button.grid(row=row_index, column=10, padx=4, pady=4, sticky="nsew")

            self.rows[emulator_index] = labels
            self.button_refs[emulator_index] = button
            self.boss_button_refs[emulator_index] = boss_button
            self.quest_button_refs[emulator_index] = quest_button
            self.dungeon_button_refs[emulator_index] = dungeon_button
            self.dismantle_button_refs[emulator_index] = dismantle_button
            self.fever_button_refs[emulator_index] = fever_button
            self.detect_disconnect_button_refs[emulator_index] = detect_disconnect_button
            self.test_click_button_refs[emulator_index] = test_click_button
            self.log_button_refs[emulator_index] = log_button
            self.update_button_state(emulator_index)

    def open_log_window(self, emulator_index: int, emulator_name: str) -> None:
        existing_window = self.log_windows.get(emulator_index)
        if existing_window is not None and existing_window.winfo_exists():
            existing_window.lift()
            existing_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        window.title(f"Live Log - {emulator_name} [{emulator_index}]")
        window.geometry("760x420")

        text = tk.Text(window, wrap="word", state="disabled", font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(window, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.log_windows[emulator_index] = window
        self.log_texts[emulator_index] = text
        self.append_log(emulator_index, f"Đang hiển thị log của {emulator_name} [{emulator_index}]")
        window.protocol("WM_DELETE_WINDOW", lambda idx=emulator_index: self.close_log_window(idx))

    def close_log_window(self, emulator_index: int) -> None:
        window = self.log_windows.pop(emulator_index, None)
        self.log_texts.pop(emulator_index, None)
        if window is not None and window.winfo_exists():
            window.destroy()

    def append_log(self, emulator_index: int, message: str) -> None:
        text = self.log_texts.get(emulator_index)
        if text is None or not text.winfo_exists():
            return
        text.configure(state="normal")
        text.insert("end", message + "\n")
        text.see("end")
        text.configure(state="disabled")

    def test_inactive_click(self, emulator_index: int) -> None:
        try:
            ld, cloned_keys = create_ldplayer()
            emulator = ld.emulators[emulator_index]
            bind_window_mode(emulator)
            emulator._update()
            click_result = inactive_click_emulator(emulator, (1193, 213))
            time.sleep(2)
            go_home_by_esc(emulator, cloned_keys)
            combined_result = {
                "click": click_result,
                "esc": "go_home_by_esc_adb",
            }
            self.message_var.set(f"Test click {emulator.name}: {combined_result!r}")
            self.append_log(emulator_index, f"Test inactive click (1193, 213) + esc: {combined_result!r}")
        except Exception as exc:
            message = f"Test click failed for emulator {emulator_index}: {exc!r}"
            self.message_var.set(message)
            self.append_log(emulator_index, message)

    def start_emulator(self, emulator_index: int) -> None:
        if self.is_process_running(emulator_index):
            self.update_button_state(emulator_index)
            return

        self.close_log_window(emulator_index)
        log_queue = self.log_queues.get(emulator_index)
        if log_queue is None:
            log_queue = multiprocessing.Queue()
            self.log_queues[emulator_index] = log_queue
        process = multiprocessing.Process(target=run_emulator_worker, args=(emulator_index, log_queue), daemon=True)
        process.start()
        self.processes[emulator_index] = process
        self.message_var.set("Đang chạy bot")
        self.update_button_state(emulator_index)

    def start_boss(self, emulator_index: int) -> None:
        if self.is_boss_process_running(emulator_index):
            self.update_button_state(emulator_index)
            return

        self.close_log_window(emulator_index)
        log_queue = self.log_queues.get(emulator_index)
        if log_queue is None:
            log_queue = multiprocessing.Queue()
            self.log_queues[emulator_index] = log_queue
        process = multiprocessing.Process(target=run_boss_worker, args=(emulator_index, log_queue), daemon=True)
        process.start()
        self.boss_processes[emulator_index] = process
        self.message_var.set("Đang chạy boss")
        self.update_button_state(emulator_index)

    def start_quest(self, emulator_index: int) -> None:
        if self.is_quest_process_running(emulator_index):
            self.update_button_state(emulator_index)
            return

        self.close_log_window(emulator_index)
        log_queue = self.log_queues.get(emulator_index)
        if log_queue is None:
            log_queue = multiprocessing.Queue()
            self.log_queues[emulator_index] = log_queue
        process = multiprocessing.Process(target=run_quest_worker, args=(emulator_index, log_queue), daemon=True)
        process.start()
        self.quest_processes[emulator_index] = process
        self.message_var.set("Đang chạy quest")
        self.update_button_state(emulator_index)

    def start_dungeon(self, emulator_index: int) -> None:
        if self.is_dungeon_process_running(emulator_index):
            self.update_button_state(emulator_index)
            return

        self.close_log_window(emulator_index)
        log_queue = self.log_queues.get(emulator_index)
        if log_queue is None:
            log_queue = multiprocessing.Queue()
            self.log_queues[emulator_index] = log_queue
        process = multiprocessing.Process(target=run_dungeon_worker, args=(emulator_index, log_queue), daemon=True)
        process.start()
        self.dungeon_processes[emulator_index] = process
        self.message_var.set("Đang chạy dungeon")
        self.update_button_state(emulator_index)

    def start_dismantle(self, emulator_index: int) -> None:
        if self.is_dismantle_process_running(emulator_index):
            self.update_button_state(emulator_index)
            return

        self.close_log_window(emulator_index)
        log_queue = self.log_queues.get(emulator_index)
        if log_queue is None:
            log_queue = multiprocessing.Queue()
            self.log_queues[emulator_index] = log_queue
        process = multiprocessing.Process(target=run_dismantle_worker, args=(emulator_index, log_queue), daemon=True)
        process.start()
        self.dismantle_processes[emulator_index] = process
        self.message_var.set("Đang chạy dismantle")
        self.update_button_state(emulator_index)

    def start_fever(self, emulator_index: int) -> None:
        if self.is_fever_process_running(emulator_index):
            self.update_button_state(emulator_index)
            return

        self.close_log_window(emulator_index)
        log_queue = self.log_queues.get(emulator_index)
        if log_queue is None:
            log_queue = multiprocessing.Queue()
            self.log_queues[emulator_index] = log_queue
        process = multiprocessing.Process(target=run_fever_worker, args=(emulator_index, log_queue), daemon=True)
        process.start()
        self.fever_processes[emulator_index] = process
        self.message_var.set("Đang chạy faver")
        self.update_button_state(emulator_index)

    def start_detect_disconnect(self, emulator_index: int) -> None:
        if self.is_detect_disconnect_process_running(emulator_index):
            self.update_button_state(emulator_index)
            return

        self.close_log_window(emulator_index)
        log_queue = self.log_queues.get(emulator_index)
        if log_queue is None:
            log_queue = multiprocessing.Queue()
            self.log_queues[emulator_index] = log_queue
        process = multiprocessing.Process(target=run_detect_disconnect_worker, args=(emulator_index, log_queue), daemon=True)
        process.start()
        self.detect_disconnect_processes[emulator_index] = process
        self.message_var.set("Đang chạy detect_disconnect")
        self.update_button_state(emulator_index)

    def stop_emulator(self, emulator_index: int) -> None:
        process = self.processes.get(emulator_index)
        if process is None:
            self.update_button_state(emulator_index)
            return

        if process.is_alive():
            process.kill()
            process.join(timeout=1)

        self.processes.pop(emulator_index, None)
        if not self.has_active_process(emulator_index):
            log_queue = self.log_queues.pop(emulator_index, None)
            if log_queue is not None:
                try:
                    log_queue.close()
                except Exception:
                    pass
        self.message_var.set("Đã dừng bot")
        self.update_button_state(emulator_index)

    def stop_boss(self, emulator_index: int) -> None:
        process = self.boss_processes.get(emulator_index)
        if process is None:
            self.update_button_state(emulator_index)
            return

        if process.is_alive():
            process.kill()
            process.join(timeout=1)

        self.boss_processes.pop(emulator_index, None)
        if not self.has_active_process(emulator_index):
            log_queue = self.log_queues.pop(emulator_index, None)
            if log_queue is not None:
                try:
                    log_queue.close()
                except Exception:
                    pass
        self.message_var.set("Đã dừng boss")
        self.update_button_state(emulator_index)

    def stop_quest(self, emulator_index: int) -> None:
        process = self.quest_processes.get(emulator_index)
        if process is None:
            self.update_button_state(emulator_index)
            return

        if process.is_alive():
            process.kill()
            process.join(timeout=1)

        self.quest_processes.pop(emulator_index, None)
        if not self.has_active_process(emulator_index):
            log_queue = self.log_queues.pop(emulator_index, None)
            if log_queue is not None:
                try:
                    log_queue.close()
                except Exception:
                    pass
        self.message_var.set("Đã dừng quest")
        self.update_button_state(emulator_index)

    def stop_dungeon(self, emulator_index: int) -> None:
        process = self.dungeon_processes.get(emulator_index)
        if process is None:
            self.update_button_state(emulator_index)
            return

        if process.is_alive():
            process.kill()
            process.join(timeout=1)

        self.dungeon_processes.pop(emulator_index, None)
        if not self.has_active_process(emulator_index):
            log_queue = self.log_queues.pop(emulator_index, None)
            if log_queue is not None:
                try:
                    log_queue.close()
                except Exception:
                    pass
        self.message_var.set("Đã dừng dungeon")
        self.update_button_state(emulator_index)

    def stop_dismantle(self, emulator_index: int) -> None:
        process = self.dismantle_processes.get(emulator_index)
        if process is None:
            self.update_button_state(emulator_index)
            return

        if process.is_alive():
            process.kill()
            process.join(timeout=1)

        self.dismantle_processes.pop(emulator_index, None)
        if not self.has_active_process(emulator_index):
            log_queue = self.log_queues.pop(emulator_index, None)
            if log_queue is not None:
                try:
                    log_queue.close()
                except Exception:
                    pass
        self.message_var.set("Đã dừng dismantle")
        self.update_button_state(emulator_index)

    def stop_fever(self, emulator_index: int) -> None:
        process = self.fever_processes.get(emulator_index)
        if process is None:
            self.update_button_state(emulator_index)
            return

        if process.is_alive():
            process.kill()
            process.join(timeout=1)

        self.fever_processes.pop(emulator_index, None)
        if not self.has_active_process(emulator_index):
            log_queue = self.log_queues.pop(emulator_index, None)
            if log_queue is not None:
                try:
                    log_queue.close()
                except Exception:
                    pass
        self.message_var.set("Đã dừng faver")
        self.update_button_state(emulator_index)

    def stop_detect_disconnect(self, emulator_index: int) -> None:
        process = self.detect_disconnect_processes.get(emulator_index)
        if process is None:
            self.update_button_state(emulator_index)
            return

        if process.is_alive():
            process.kill()
            process.join(timeout=1)

        self.detect_disconnect_processes.pop(emulator_index, None)
        if not self.has_active_process(emulator_index):
            log_queue = self.log_queues.pop(emulator_index, None)
            if log_queue is not None:
                try:
                    log_queue.close()
                except Exception:
                    pass
        self.message_var.set("Đã dừng detect_disconnect")
        self.update_button_state(emulator_index)

    def drain_log_queues(self) -> None:
        for emulator_index, log_queue in list(self.log_queues.items()):
            while True:
                try:
                    message = log_queue.get_nowait()
                except queue.Empty:
                    break
                except (OSError, ValueError):
                    break

                if message == "__START_RUN_AFTER_DUNGEON__":
                    self.dungeon_processes.pop(emulator_index, None)
                    self.update_button_state(emulator_index)
                    self.start_emulator(emulator_index)
                    continue

                if message == "__DISCONNECT_DETECTED__":
                    self.stop_emulator(emulator_index)
                    self.stop_boss(emulator_index)
                    self.stop_quest(emulator_index)
                    self.stop_dungeon(emulator_index)
                    self.stop_dismantle(emulator_index)
                    self.stop_fever(emulator_index)
                    self.detect_disconnect_processes.pop(emulator_index, None)
                    self.message_var.set("Đã phát hiện disconnect, đang login lại")
                    self.update_button_state(emulator_index)
                    continue

                if message == "__START_RUN_AFTER_LOGIN__":
                    existing_detect_process = self.detect_disconnect_processes.get(emulator_index)
                    if existing_detect_process is not None and existing_detect_process.is_alive():
                        existing_detect_process.kill()
                        existing_detect_process.join(timeout=1)
                    self.detect_disconnect_processes.pop(emulator_index, None)
                    self.update_button_state(emulator_index)
                    self.start_emulator(emulator_index)
                    self.message_var.set("Login lại thành công, đang chạy lại infinity farm")
                    self.root.after(5000, lambda idx=emulator_index: self.start_detect_disconnect(idx))
                    continue

                if emulator_index in self.log_texts:
                    self.append_log(emulator_index, str(message))
        self.root.after(300, self.drain_log_queues)

    def poll_processes(self) -> None:
        stopped_indexes: set[int] = set()
        for emulator_index, process in list(self.processes.items()):
            if process.is_alive():
                continue
            process.join(timeout=0.1)
            stopped_indexes.add(emulator_index)
            self.processes.pop(emulator_index, None)
            if not self.has_active_process(emulator_index):
                log_queue = self.log_queues.pop(emulator_index, None)
                if log_queue is not None:
                    try:
                        log_queue.close()
                    except Exception:
                        pass

        for emulator_index, process in list(self.boss_processes.items()):
            if process.is_alive():
                continue
            process.join(timeout=0.1)
            stopped_indexes.add(emulator_index)
            self.boss_processes.pop(emulator_index, None)
            if not self.has_active_process(emulator_index):
                log_queue = self.log_queues.pop(emulator_index, None)
                if log_queue is not None:
                    try:
                        log_queue.close()
                    except Exception:
                        pass

        for emulator_index, process in list(self.quest_processes.items()):
            if process.is_alive():
                continue
            process.join(timeout=0.1)
            stopped_indexes.add(emulator_index)
            self.quest_processes.pop(emulator_index, None)
            if not self.has_active_process(emulator_index):
                log_queue = self.log_queues.pop(emulator_index, None)
                if log_queue is not None:
                    try:
                        log_queue.close()
                    except Exception:
                        pass

        for emulator_index, process in list(self.dungeon_processes.items()):
            if process.is_alive():
                continue
            process.join(timeout=0.1)
            stopped_indexes.add(emulator_index)
            self.dungeon_processes.pop(emulator_index, None)
            if not self.has_active_process(emulator_index):
                log_queue = self.log_queues.pop(emulator_index, None)
                if log_queue is not None:
                    try:
                        log_queue.close()
                    except Exception:
                        pass

        for emulator_index, process in list(self.dismantle_processes.items()):
            if process.is_alive():
                continue
            process.join(timeout=0.1)
            stopped_indexes.add(emulator_index)
            self.dismantle_processes.pop(emulator_index, None)
            if not self.has_active_process(emulator_index):
                log_queue = self.log_queues.pop(emulator_index, None)
                if log_queue is not None:
                    try:
                        log_queue.close()
                    except Exception:
                        pass

        for emulator_index, process in list(self.fever_processes.items()):
            if process.is_alive():
                continue
            process.join(timeout=0.1)
            stopped_indexes.add(emulator_index)
            self.fever_processes.pop(emulator_index, None)
            if not self.has_active_process(emulator_index):
                log_queue = self.log_queues.pop(emulator_index, None)
                if log_queue is not None:
                    try:
                        log_queue.close()
                    except Exception:
                        pass

        for emulator_index, process in list(self.detect_disconnect_processes.items()):
            if process.is_alive():
                continue
            process.join(timeout=0.1)
            stopped_indexes.add(emulator_index)
            self.detect_disconnect_processes.pop(emulator_index, None)
            if not self.has_active_process(emulator_index):
                log_queue = self.log_queues.pop(emulator_index, None)
                if log_queue is not None:
                    try:
                        log_queue.close()
                    except Exception:
                        pass

        for emulator_index in stopped_indexes:
            self.update_button_state(emulator_index)

        self.root.after(1000, self.poll_processes)

    def on_close(self) -> None:
        alive_indexes = [index for index, process in self.processes.items() if process.is_alive()]
        if alive_indexes:
            for emulator_index in alive_indexes:
                process = self.processes.get(emulator_index)
                if process is not None and process.is_alive():
                    process.kill()
                    process.join(timeout=1)
            self.processes.clear()

        alive_boss_indexes = [index for index, process in self.boss_processes.items() if process.is_alive()]
        if alive_boss_indexes:
            for emulator_index in alive_boss_indexes:
                process = self.boss_processes.get(emulator_index)
                if process is not None and process.is_alive():
                    process.kill()
                    process.join(timeout=1)
            self.boss_processes.clear()

        alive_quest_indexes = [index for index, process in self.quest_processes.items() if process.is_alive()]
        if alive_quest_indexes:
            for emulator_index in alive_quest_indexes:
                process = self.quest_processes.get(emulator_index)
                if process is not None and process.is_alive():
                    process.kill()
                    process.join(timeout=1)
            self.quest_processes.clear()

        alive_dungeon_indexes = [index for index, process in self.dungeon_processes.items() if process.is_alive()]
        if alive_dungeon_indexes:
            for emulator_index in alive_dungeon_indexes:
                process = self.dungeon_processes.get(emulator_index)
                if process is not None and process.is_alive():
                    process.kill()
                    process.join(timeout=1)
            self.dungeon_processes.clear()

        alive_dismantle_indexes = [index for index, process in self.dismantle_processes.items() if process.is_alive()]
        if alive_dismantle_indexes:
            for emulator_index in alive_dismantle_indexes:
                process = self.dismantle_processes.get(emulator_index)
                if process is not None and process.is_alive():
                    process.kill()
                    process.join(timeout=1)
            self.dismantle_processes.clear()

        alive_fever_indexes = [index for index, process in self.fever_processes.items() if process.is_alive()]
        if alive_fever_indexes:
            for emulator_index in alive_fever_indexes:
                process = self.fever_processes.get(emulator_index)
                if process is not None and process.is_alive():
                    process.kill()
                    process.join(timeout=1)
            self.fever_processes.clear()

        alive_detect_disconnect_indexes = [index for index, process in self.detect_disconnect_processes.items() if process.is_alive()]
        if alive_detect_disconnect_indexes:
            for emulator_index in alive_detect_disconnect_indexes:
                process = self.detect_disconnect_processes.get(emulator_index)
                if process is not None and process.is_alive():
                    process.kill()
                    process.join(timeout=1)
            self.detect_disconnect_processes.clear()

        for emulator_index, log_queue in list(self.log_queues.items()):
            try:
                log_queue.close()
            except Exception:
                pass
            self.log_queues.pop(emulator_index, None)

        for emulator_index in list(self.log_windows.keys()):
            self.close_log_window(emulator_index)

        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    multiprocessing.freeze_support()
    print(f"Loaded from: {EMULATOR_INIT}")
    print(f"Repo dir: {REPO_DIR}")
    print("Library version: cloned-local")
    app = LDPlayerManagerApp()
    app.run()


if __name__ == "__main__":
    main()

from __future__ import annotations

import importlib.util
import sys
import time
import types
from datetime import datetime
from pathlib import Path

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
LDPLAYER_DIR = r"C:/LDPlayer/LDPlayer9"
AUTO_TEMPLATE = Path("images/auto.png")
NOT_AUTO_TEMPLATE = Path("images/not_auto.png")
MAP_IMAGES_DIR = Path("images")
MAP_IMAGE_GLOB = "map_*.png"
DONE_LOADING_TEMPLATE = Path("images/done_loading.png")
BOSS_DONE_TEMPLATE = Path("images/boss_done.png")
BOSS_ICON_TEMPLATES = {
    1: Path("images/icon_boss1.png"),
    2: Path("images/icon_boss2.png"),
    3: Path("images/icon_boss3.png"),
    4: Path("images/icon_boss4.png"),
}


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


def warmup_adb(ld, emulator) -> str:
    cmd = f'{ld.controller} adb --index {emulator.index} --command "devices"'
    return ld._run_cmd(cmd)


def go_home_by_esc(emulator, keys_module, delay: float = 0.5) -> None:
    emulator.send_event(keys_module.KEYCODE_ESCAPE)
    time.sleep(delay)
    emulator.send_event(keys_module.KEYCODE_ESCAPE)
    time.sleep(1)


def select_channel(emulator) -> None:
    emulator.tap((1490, 336))


def go_home(emulator, delay: float = 0.5) -> None:
    emulator.tap((1382, 200))
    time.sleep(delay)
    emulator.tap((939, 677))


def go_map_5x(emulator, keys_module) -> dict:
    go_home_by_esc(emulator, keys_module)
    time.sleep(1)
    emulator.tap((1489, 267))
    time.sleep(1)
    emulator.tap((734, 792))
    time.sleep(1)
    emulator.tap((253, 478))
    time.sleep(1)
    emulator.tap((1105, 303))
    time.sleep(1)
    emulator.tap((1103, 383))
    time.sleep(1)
    emulator.tap((1217, 792))
    time.sleep(1)
    emulator.tap((947, 676))
    time.sleep(5)
    loading_result = wait_loading(emulator)
    auto_result = enable_auto(emulator)
    return {
        "loading": loading_result,
        "auto": auto_result,
        "status": "completed",
    }


def dismantle_items(emulator, keys_module) -> dict:
    go_home_by_esc(emulator, keys_module)
    time.sleep(1)
    emulator.tap((1563, 43))
    time.sleep(1)
    emulator.tap((1296, 534))
    time.sleep(5)
    emulator.tap((603, 110))
    time.sleep(1)
    emulator.tap((1415, 833))
    time.sleep(1)
    emulator.tap((944, 733))
    time.sleep(1)
    emulator.tap((473, 856))
    time.sleep(1)
    emulator.tap((941, 670))
    time.sleep(5)
    go_home_by_esc(emulator, keys_module)
    go_home_by_esc(emulator, keys_module)
    return {
        "status": "completed",
        "last_click": (937, 4),
    }


def go_to_boss(emulator, boss_number: int) -> None:
    boss_positions = {
        1: (204, 171),
        2: (202, 318),
        3: (206, 478),
        4: (222, 618),
    }
    if boss_number not in boss_positions:
        raise ValueError(f"boss_number không hợp lệ: {boss_number}")

    emulator.tap((1566, 44))
    time.sleep(0.4)
    emulator.tap((1418, 775))
    time.sleep(0.5)
    emulator.tap(boss_positions[boss_number])
    time.sleep(0.3)
    emulator.tap((1447, 833))
    time.sleep(1)
    emulator.tap((939, 677))


def select_channel_boss(emulator, boss_number: int, threshold: float = 0.8) -> dict:
    if boss_number not in BOSS_ICON_TEMPLATES:
        print("Ko có template")
        return {
            "success": False,
            "boss_number": boss_number,
            "clicked": False,
            "target": None,
            "template": None,
            "reason": "invalid_boss_number",
        }

    template_path = BOSS_ICON_TEMPLATES[boss_number]
    template = load_template(template_path)

    emulator.tap((1490, 336))
    time.sleep(1)
    emulator.drag_drop((801, 358), (798, 517))
    time.sleep(0.5)

    screen_bytes = emulator._get_screencap_b64decode()
    if not screen_bytes:
        return {
            "success": False,
            "boss_number": boss_number,
            "clicked": False,
            "target": None,
            "template": str(template_path),
            "reason": f"capture_failed: {emulator.error!r}",
        }

    screen = decode_screen(screen_bytes)
    positions = find_template_positions(screen, template, threshold=threshold)

    first_scroll_single_icon = boss_number in (1, 2) and len(positions) == 1
    if not positions or first_scroll_single_icon:
        emulator.drag_drop((798, 517), (801, 358))
        time.sleep(0.5)
        screen_bytes = emulator._get_screencap_b64decode()
        if not screen_bytes:
            return {
                "success": False,
                "boss_number": boss_number,
                "clicked": False,
                "target": None,
                "template": str(template_path),
                "reason": f"capture_failed_after_retry: {emulator.error!r}",
            }
        screen = decode_screen(screen_bytes)
        positions = find_template_positions(screen, template, threshold=threshold)

    if not positions:
        print("Không thấy boss")
        return {
            "success": True,
            "boss_number": boss_number,
            "clicked": False,
            "target": None,
            "template": str(template_path),
            "reason": "icon_not_found_skip_click",
        }

    if len(positions) >= 3:
        target = positions[1]
        reason = "clicked_middle_match_after_second_scroll"
    elif len(positions) == 2:
        target = positions[0]
        reason = "clicked_first_match_after_second_scroll"
    else:
        target = positions[0]
        reason = "clicked_single_match_after_second_scroll"

    emulator.tap(target)
    return {
        "success": True,
        "boss_number": boss_number,
        "clicked": True,
        "target": target,
        "template": str(template_path),
        "reason": reason,
    }


def load_template(template_path: Path) -> np.ndarray:
    template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
    if template is None:
        raise FileNotFoundError(f"Không đọc được ảnh mẫu: {template_path}")
    return template


def decode_screen(screen_bytes: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(screen_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Không giải mã được ảnh chụp màn hình từ LDPlayer")
    return image


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


def detect_auto_state(
    emulator,
    auto_template_path: Path = AUTO_TEMPLATE,
    not_auto_template_path: Path = NOT_AUTO_TEMPLATE,
    region: tuple[int, int, int, int] | None = None,
) -> dict:
    screen_bytes = emulator._get_screencap_b64decode()
    if not screen_bytes:
        raise RuntimeError(f"Không chụp được màn hình LDPlayer: {emulator.error!r}")

    screen = decode_screen(screen_bytes)
    target = crop_region(screen, region)
    auto_template = load_template(auto_template_path)
    not_auto_template = load_template(not_auto_template_path)

    auto_score = match_score(target, auto_template)
    not_auto_score = match_score(target, not_auto_template)

    state = "auto" if auto_score >= not_auto_score else "not_auto"
    confidence = max(auto_score, not_auto_score)

    return {
        "state": state,
        "confidence": confidence,
        "auto_score": auto_score,
        "not_auto_score": not_auto_score,
        "region": region,
        "screen_size": tuple(int(x) for x in screen.shape[:2]),
        "auto_template_size": tuple(int(x) for x in auto_template.shape[:2]),
        "not_auto_template_size": tuple(int(x) for x in not_auto_template.shape[:2]),
    }


def enable_auto(emulator) -> dict:
    detection = detect_auto_state(emulator)
    if detection["state"] == "not_auto":
        emulator.tap((1533, 643))
        detection["action"] = "tapped_auto_button"
    else:
        detection["action"] = "already_auto"
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
    screen_bytes = emulator._get_screencap_b64decode()
    if not screen_bytes:
        raise RuntimeError(f"Không chụp được màn hình LDPlayer: {emulator.error!r}")

    screen = decode_screen(screen_bytes)
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
    first_wait: float = 5.0,
    timeout: float = 30.0,
    interval: float = 0.5,
    threshold: float = 0.8,
) -> dict:
    time.sleep(first_wait)
    done_template = load_template(done_template_path)
    started_at = time.perf_counter()
    last_score = -1.0

    while time.perf_counter() - started_at < timeout:
        screen_bytes = emulator._get_screencap_b64decode()
        if screen_bytes:
            screen = decode_screen(screen_bytes)
            last_score = match_score(screen, done_template)
            if last_score >= threshold:
                return {
                    "done": True,
                    "matched": True,
                    "score": last_score,
                    "threshold": threshold,
                    "elapsed": time.perf_counter() - started_at,
                }
        time.sleep(interval)
    print("Đã loading xong")
    time.sleep(2)
    return {
        "done": True,
        "matched": False,
        "score": last_score,
        "threshold": threshold,
        "elapsed": time.perf_counter() - started_at,
    }


def wait_boss_done(
    emulator,
    done_template_path: Path = BOSS_DONE_TEMPLATE,
    first_wait: float = 5.0,
    timeout: float = 30.0,
    interval: float = 0.5,
    threshold: float = 0.8,
) -> dict:
    time.sleep(first_wait)
    done_template = load_template(done_template_path)
    started_at = time.perf_counter()
    last_score = -1.0

    while time.perf_counter() - started_at < timeout:
        screen_bytes = emulator._get_screencap_b64decode()
        if screen_bytes:
            screen = decode_screen(screen_bytes)
            last_score = match_score(screen, done_template)
            if last_score >= threshold:
                return {
                    "done": True,
                    "matched": True,
                    "score": last_score,
                    "threshold": threshold,
                    "elapsed": time.perf_counter() - started_at,
                }
        time.sleep(interval)
    return {
        "done": True,
        "matched": False,
        "score": last_score,
        "threshold": threshold,
        "elapsed": time.perf_counter() - started_at,
    }


def active_boss_world(emulator, keys_module) -> list[dict]:
    go_home_by_esc(emulator, keys_module)
    results: list[dict] = []
    boss_timeouts = {
        1: 2 * 60,
        2: 5 * 60,
        3: 7 * 60,
        4: 10 * 60,
    }

    go_home(emulator)
    loading_home = wait_loading(emulator)
    results.append({"step": "go_home", "result": loading_home})
    time.sleep(60)

    for boss_number in (1, 2, 3, 4):
        go_home_by_esc(emulator, keys_module)
        print('Go BOSS ' + str(boss_number))
        go_to_boss(emulator, boss_number)
        loading_result = wait_loading(emulator)

        select_result = select_channel_boss(emulator, boss_number)
        if (not select_result.get("success", False)) or (not select_result.get("clicked", False)):
            results.append(
                {
                    "boss": boss_number,
                    "loading": loading_result,
                    "select": select_result,
                    "auto": None,
                    "boss_done": None,
                    "status": "select_skipped",
                }
            )
            continue

        time.sleep(5)
        go_home_by_esc(emulator, keys_module)
        auto_result = enable_auto(emulator)
        boss_done_result = wait_boss_done(emulator, timeout=boss_timeouts[boss_number])
        time.sleep(1)
        go_home_by_esc(emulator, keys_module)

        results.append(
            {
                "boss": boss_number,
                "loading": loading_result,
                "select": select_result,
                "auto": auto_result,
                "boss_done": boss_done_result,
                "status": "completed",
            }
        )

    return results


def should_run_boss_world(now: datetime) -> bool:
    return (now.hour, now.minute) in {(9, 59), (14, 59), (18, 59), (21, 59)}


def infinite_farm_loop(emulator, keys_module, loop_interval: float = 10.0) -> None:
    last_dismantle_at = 0.0
    last_boss_trigger: str | None = None

    while True:
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
            dismantle_items(emulator, keys_module)
            last_dismantle_at = now_ts

        time.sleep(loop_interval)


def main() -> None:
    ensure_pkg_resources_stub()
    cloned_emulator = load_module("cloned_emulator", EMULATOR_INIT, is_package=True)
    cloned_keys = load_module("cloned_emulator.keys", EMULATOR_DIR / "keys.py")

    print(f"Loaded from: {EMULATOR_INIT}")
    print(f"Repo dir: {REPO_DIR}")
    print(f"Library version: {getattr(cloned_emulator, '__version__', 'unknown')}")

    ld = cloned_emulator.LDPlayer(ldplayer_dir=LDPLAYER_DIR)
    first_emulator = ld.emulators[0]
    first_emulator.start(wait=True)

    print(
        f"Selected emulator: index={first_emulator.index}, "
        f"name={first_emulator.name}, top_hwnd={first_emulator.top_hwnd}, bind_hwnd={first_emulator.bind_hwnd}"
    )

    adb_state = warmup_adb(ld, first_emulator)
    print(f"ADB warmup: {adb_state!r}")

    infinite_farm_loop(first_emulator, cloned_keys)

    # active_boss_world(first_emulator,cloned_keys)
    
if __name__ == "__main__":
    main()

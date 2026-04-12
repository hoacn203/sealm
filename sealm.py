from __future__ import annotations
 
import importlib.util
import multiprocessing
import queue
import sys
import time
import types
import tkinter as tk
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
DONE_LOADING_TEMPLATE = Path("images/done_loading.png")
BOSS_DONE_TEMPLATE = Path("images/boss_done.png")
QUEST_DONE_TEMPLATE = Path("images/quest_done.png")
CONFIRM_QUEST_TEMPLATE = Path("images/confirm_quest.png")
DUNGEON_ENTER_TEMPLATE = Path("images/dungeon_enter.png")
DUNGEON_INSTANCE_TEMPLATE = Path("images/dungeon_intance.png")
DUNGEON_LEAVE_TEMPLATE = Path("images/dungeon_leave.png")
DUNGEON_RETRY_TEMPLATE = Path("images/dungeon_retry.png")
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


def load_runtime_modules():
    ensure_pkg_resources_stub()
    cloned_emulator = load_module("cloned_emulator", EMULATOR_INIT, is_package=True)
    cloned_keys = load_module("cloned_emulator.keys", EMULATOR_DIR / "keys.py")
    return cloned_emulator, cloned_keys


def create_ldplayer():
    cloned_emulator, cloned_keys = load_runtime_modules()
    ld = cloned_emulator.LDPlayer(ldplayer_dir=LDPLAYER_DIR)
    return ld, cloned_keys


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


def go_home_by_esc(emulator, keys_module, delay: float = 0.5) -> None:
    emulator.send_event(keys_module.KEYCODE_ESCAPE)
    time.sleep(0.3)
    emulator.send_event(keys_module.KEYCODE_ESCAPE)
    time.sleep(0.3)



def select_channel(emulator) -> None:
    emulator.tap((1192, 269))


def go_home(emulator, delay: float = 0.5) -> None:
    emulator.tap((1106, 160))
    time.sleep(delay)
    emulator.tap((751, 542))


def go_map_5x(emulator, keys_module) -> dict:
    go_home_by_esc(emulator, keys_module)
    time.sleep(1)
    emulator.tap((1191, 214))
    time.sleep(1)
    emulator.tap((587, 634))
    time.sleep(1)
    emulator.tap((202, 382))
    time.sleep(1)
    emulator.tap((884, 242))
    time.sleep(1)
    emulator.tap((882, 306))
    time.sleep(1)
    emulator.tap((974, 634))
    time.sleep(1)
    emulator.tap((758, 541))
    time.sleep(5)
    loading_result = wait_loading(emulator)
    auto_result = enable_auto(emulator, True)
    return {
        "loading": loading_result,
        "auto": auto_result,
        "status": "completed",
    }


def dismantle_items(emulator, keys_module) -> dict:
    go_home_by_esc(emulator, keys_module)
    time.sleep(1)
    emulator.tap((1250, 34))
    time.sleep(1)
    emulator.tap((1037, 427))
    time.sleep(5)
    emulator.tap((482, 88))
    time.sleep(1)
    emulator.tap((1132, 666))
    time.sleep(1)
    emulator.tap((755, 586))
    time.sleep(1)
    emulator.tap((378, 685))
    time.sleep(1)
    emulator.tap((753, 536))
    time.sleep(5)
    go_home_by_esc(emulator, keys_module)
    go_home_by_esc(emulator, keys_module)
    go_home_by_esc(emulator, keys_module)
    time.sleep(1)

    return {
        "status": "completed",
        "last_click": (750, 3),
    }


def go_to_boss(emulator, boss_number: int) -> None:
    boss_positions = {
        1: (163, 137),
        2: (162, 254),
        3: (165, 382),
        4: (178, 494),
    }
    if boss_number not in boss_positions:
        raise ValueError(f"boss_number không hợp lệ: {boss_number}")

    emulator.tap((1253, 35))
    time.sleep(0.4)
    emulator.tap((1134, 620))
    time.sleep(0.5)
    emulator.tap(boss_positions[boss_number])
    time.sleep(0.3)
    emulator.tap((1158, 666))
    time.sleep(1)
    emulator.tap((751, 542))


# Quy trình chọn channel boss:
# 1. Mở danh sách channel boss và nạp template icon theo boss_number.
# 2. Thử tối đa 2 lượt danh sách:
#    - Lượt 1 kéo xuống.
#    - Lượt 2 kéo ngược lên.
# 3. Boss 1 và 2 giữ logic cũ: ưu tiên icon thứ 2, nhưng nếu lượt 1 chỉ có 1 icon thì sang lượt 2 sẽ ưu tiên icon đầu tiên.
# 4. Boss 3 và 4 ưu tiên click icon đầu tiên ngay khi thấy.
# 5. Sau mỗi lần click icon boss, luôn đợi 1 giây rồi chụp lại màn hình:
#    - Nếu không còn icon boss nữa thì coi như vào channel thành công.
#    - Nếu vẫn còn icon boss thì tiếp tục logic chọn tiếp trong cùng lượt hoặc sang lượt sau.
# 6. Nếu sau cả 2 lượt vẫn không chọn được thì return skip.
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

    emulator.tap((1192, 269))
    time.sleep(1)

    first_scroll_single_icon = False

    for scroll_index in range(2):
        if scroll_index == 0:
            emulator.drag_drop((641, 286), (638, 414))
            time.sleep(0.5)
        else:
            emulator.drag_drop((638, 414), (641, 286))
            time.sleep(0.5)

        screen_bytes = emulator._get_screencap_b64decode()
        if not screen_bytes:
            return {
                "success": False,
                "boss_number": boss_number,
                "clicked": False,
                "target": None,
                "template": str(template_path),
                "reason": f"capture_failed_scroll_{scroll_index + 1}: {emulator.error!r}",
            }

        screen = decode_screen(screen_bytes)
        positions = deduplicate_positions(
            find_template_positions(screen, template, threshold=threshold),
            template,
        )

        if not positions:
            continue

        target: tuple[int, int] | None = None
        reason: str | None = None

        if boss_number in (3, 4):
            target = positions[0]
            reason = f"clicked_first_match_scroll_{scroll_index + 1}"
        else:
            if scroll_index == 0 and len(positions) == 1:
                first_scroll_single_icon = True
                continue

            if scroll_index == 1 and first_scroll_single_icon:
                target = positions[0]
                reason = "clicked_first_match_scroll_2_after_single_match_on_scroll_1"
            elif len(positions) >= 2:
                target = positions[1]
                reason = f"clicked_second_match_scroll_{scroll_index + 1}"
            elif scroll_index == 1:
                target = positions[0]
                reason = "clicked_first_match_scroll_2_fallback"

        if target is None or reason is None:
            continue

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
            }

        screen = decode_screen(screen_bytes)
        retry_positions = deduplicate_positions(
            find_template_positions(screen, template, threshold=threshold),
            template,
        )
        if not retry_positions:
            return {
                "success": True,
                "boss_number": boss_number,
                "clicked": True,
                "target": target,
                "template": str(template_path),
                "reason": f"{reason}_success",
            }

    print("Không thấy boss")
    return {
        "success": True,
        "boss_number": boss_number,
        "clicked": False,
        "target": None,
        "template": str(template_path),
        "reason": "icon_not_found_skip_click",
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

    if current_state == target_state:
        detection["action"] = "already_target_state"
        return detection

    detection["action"] = "toggled_auto_button"
    detection["toggle_attempts"] = 0

    for attempt in range(5):
        emulator.tap((1226, 514))
        detection["toggle_attempts"] = attempt + 1
        time.sleep(1)

        verification = detect_auto_state(emulator)
        detection["verification"] = verification
        detection["state"] = verification["state"]
        detection["confidence"] = verification["confidence"]
        detection["auto_score"] = verification["auto_score"]
        detection["not_auto_score"] = verification["not_auto_score"]
        detection["auto_edge_score"] = verification["auto_edge_score"]
        detection["not_auto_edge_score"] = verification["not_auto_edge_score"]
        detection["auto_combined_score"] = verification["auto_combined_score"]
        detection["not_auto_combined_score"] = verification["not_auto_combined_score"]

        if verification["state"] == target_state:
            detection["verified"] = True
            return detection

    detection["verified"] = False
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
    time.sleep(1)
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

    print("Go BOSS 1")
    go_to_boss(emulator, 1)
    first_loading_result = wait_loading(emulator)
    first_auto_result = enable_auto(emulator, False)
    results.append(
        {
            "step": "prepare_boss_1",
            "loading": first_loading_result,
            "auto": first_auto_result,
            "status": "prepared",
        }
    )

    while True:
        now = datetime.now()
        if now.hour in {10, 15, 19, 22, 1} and now.second >= 10:
            break
        time.sleep(1)

    for boss_number in (1, 2, 3, 4):
        if boss_number != 1:
            go_home_by_esc(emulator, keys_module)
            print("Go BOSS " + str(boss_number))
            go_to_boss(emulator, boss_number)
            loading_result = wait_loading(emulator)
        else:
            loading_result = first_loading_result

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

        auto_result = enable_auto(emulator, True)
        boss_done_result = wait_boss_done(emulator, timeout=boss_timeouts[boss_number])
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
    return (now.hour, now.minute) in {(9, 59), (14, 59), (18, 59), (21, 59), (0, 59)}


def infinite_farm_loop(emulator, keys_module, loop_interval: float = 10.0) -> None:
    last_dismantle_at = 0.0
    last_boss_trigger: str | None = None

    while True:
        go_home_by_esc(emulator, keys_module)
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
                if boss_number == 3:
                    emulator.tap((881, 659))
                    time.sleep(1)
                    emulator.tap((738, 531))
                    time.sleep(1)
                    emulator.tap((653, 533))
                    time.sleep(0.5)
                    emulator.tap((752, 540))
                    time.sleep(5)
                    go_home_by_esc(emulator, keys_module)
                    go_home_by_esc(emulator, keys_module)

                    return {
                        "success": True,
                        "boss": boss_number,
                        "entered": True,
                        "attempt": attempt_index + 1,
                        "enter_score": enter_score,
                        "instance_score": instance_score,
                        "reason": f"dungeon_boss_{boss_number}_completed",
                    }

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

        if not entered and boss_number != 3:
            if enter_result is None:
                return {
                    "success": True,
                    "boss": boss_number,
                    "entered": False,
                    "attempt": 2,
                    "reason": f"dungeon_boss_{boss_number}_entry_not_found",
                }

        if boss_number == 3 and not entered:
            return {
                "success": True,
                "boss": boss_number,
                "entered": False,
                "attempt": 2,
                "reason": "dungeon_boss_3_entry_not_found",
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
        print(
            f"Selected emulator for dismantle: index={emulator.index}, "
            f"name={emulator.name}, top_hwnd={emulator.top_hwnd}, bind_hwnd={emulator.bind_hwnd}"
        )
        adb_state = warmup_adb(ld, emulator)
        print(f"ADB warmup dismantle: {adb_state!r}")
        while True:
            go_home_by_esc(emulator, cloned_keys)
            go_home_by_esc(emulator, cloned_keys)
            go_home_by_esc(emulator, cloned_keys)
            go_home_by_esc(emulator, cloned_keys)
            go_home_by_esc(emulator, cloned_keys)
            go_home_by_esc(emulator, cloned_keys)
            result = dismantle_items(emulator, cloned_keys)
            go_home_by_esc(emulator, cloned_keys)
            go_home_by_esc(emulator, cloned_keys)
            go_home_by_esc(emulator, cloned_keys)
            go_home_by_esc(emulator, cloned_keys)
            go_home_by_esc(emulator, cloned_keys)
            print(f"Dismantle result: {result!r}")
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


class LDPlayerManagerApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("SEALM LDPlayer Manager")
        self.root.geometry("860x420")
        self.root.minsize(780, 340)
        self.root.configure(bg="#f4f6fb")
        self.processes: dict[int, multiprocessing.Process] = {}
        self.boss_processes: dict[int, multiprocessing.Process] = {}
        self.quest_processes: dict[int, multiprocessing.Process] = {}
        self.dungeon_processes: dict[int, multiprocessing.Process] = {}
        self.dismantle_processes: dict[int, multiprocessing.Process] = {}
        self.log_queues: dict[int, multiprocessing.Queue] = {}
        self.button_refs: dict[int, ttk.Button] = {}
        self.boss_button_refs: dict[int, ttk.Button] = {}
        self.quest_button_refs: dict[int, ttk.Button] = {}
        self.dungeon_button_refs: dict[int, ttk.Button] = {}
        self.dismantle_button_refs: dict[int, ttk.Button] = {}
        self.auto_button_refs: dict[int, ttk.Button] = {}
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

        headers = ["Name", "Status", "Farm", "Boss", "Quest", "Dungeon", "Dismantle", "Auto", "Log"]
        widths = [10, 14, 10, 10, 10, 11, 12, 10, 10]
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

    def has_active_process(self, emulator_index: int) -> bool:
        return (
            self.is_process_running(emulator_index)
            or self.is_boss_process_running(emulator_index)
            or self.is_quest_process_running(emulator_index)
            or self.is_dungeon_process_running(emulator_index)
            or self.is_dismantle_process_running(emulator_index)
        )

    def update_button_state(self, emulator_index: int) -> None:
        button = self.button_refs.get(emulator_index)
        boss_button = self.boss_button_refs.get(emulator_index)
        quest_button = self.quest_button_refs.get(emulator_index)
        dungeon_button = self.dungeon_button_refs.get(emulator_index)
        dismantle_button = self.dismantle_button_refs.get(emulator_index)
        auto_button = self.auto_button_refs.get(emulator_index)
        log_button = self.log_button_refs.get(emulator_index)
        status_label = self.rows.get(emulator_index, {}).get("status")
        if button is None or boss_button is None or quest_button is None or dungeon_button is None or dismantle_button is None or auto_button is None or status_label is None or log_button is None:
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

        auto_button.configure(state="normal")
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
        for button in self.auto_button_refs.values():
            button.destroy()
        for button in self.log_button_refs.values():
            button.destroy()
        self.rows.clear()
        self.button_refs.clear()
        self.boss_button_refs.clear()
        self.quest_button_refs.clear()
        self.dungeon_button_refs.clear()
        self.dismantle_button_refs.clear()
        self.auto_button_refs.clear()
        self.log_button_refs.clear()

    def refresh_emulators(self) -> None:
        current_running = {index for index, process in self.processes.items() if process.is_alive()}
        current_boss_running = {index for index, process in self.boss_processes.items() if process.is_alive()}
        current_quest_running = {index for index, process in self.quest_processes.items() if process.is_alive()}
        current_dungeon_running = {index for index, process in self.dungeon_processes.items() if process.is_alive()}
        current_dismantle_running = {index for index, process in self.dismantle_processes.items() if process.is_alive()}
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
            f"Dismantle: {len(current_dismantle_running)}"
        )

        for row_index, emulator in enumerate(emulators, start=1):
            emulator_index = emulator["index"]
            labels = {
                "name": ttk.Label(self.table, text=emulator["name"], anchor="w", style="NameCell.TLabel"),
                "status": ttk.Label(
                    self.table,
                    text="Running bot" if emulator_index in current_running else "Running boss" if emulator_index in current_boss_running else "Running quest" if emulator_index in current_quest_running else "Running dungeon" if emulator_index in current_dungeon_running else "Running dismantle" if emulator_index in current_dismantle_running else "Idle",
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

            auto_button = ttk.Button(
                self.table,
                text="Auto Test",
                command=lambda idx=emulator_index, name=emulator["name"]: self.test_detect_auto(idx, name),
                style="Action.TButton",
            )
            auto_button.grid(row=row_index, column=7, padx=4, pady=4, sticky="nsew")

            log_button = ttk.Button(
                self.table,
                text="Log",
                command=lambda idx=emulator_index, name=emulator["name"]: self.open_log_window(idx, name),
                style="Action.TButton",
            )
            log_button.grid(row=row_index, column=8, padx=4, pady=4, sticky="nsew")

            self.rows[emulator_index] = labels
            self.button_refs[emulator_index] = button
            self.boss_button_refs[emulator_index] = boss_button
            self.quest_button_refs[emulator_index] = quest_button
            self.dungeon_button_refs[emulator_index] = dungeon_button
            self.dismantle_button_refs[emulator_index] = dismantle_button
            self.auto_button_refs[emulator_index] = auto_button
            self.log_button_refs[emulator_index] = log_button
            self.update_button_state(emulator_index)

    def test_detect_auto(self, emulator_index: int, emulator_name: str) -> None:
        try:
            ld, _ = create_ldplayer()
            emulator = ld.emulators[emulator_index]
            emulator.start(wait=True)
            detection = detect_auto_state(emulator)
            result = (
                f"{emulator_name} [{emulator_index}]\n"
                f"state={detection['state']}\n"
                f"confidence={detection['confidence']:.4f}\n"
                f"auto_score={detection['auto_score']:.4f}\n"
                f"not_auto_score={detection['not_auto_score']:.4f}\n"
                f"auto_edge_score={detection['auto_edge_score']:.4f}\n"
                f"not_auto_edge_score={detection['not_auto_edge_score']:.4f}\n"
                f"auto_combined_score={detection['auto_combined_score']:.4f}\n"
                f"not_auto_combined_score={detection['not_auto_combined_score']:.4f}"
            )
            self.message_var.set(f"Detect auto {emulator_name}: {detection['state']}")
            self.append_log(emulator_index, f"[AUTO TEST] {result}")
            messagebox.showinfo("Detect Auto", result)
        except Exception as exc:
            self.message_var.set(f"Detect auto lỗi cho {emulator_name}: {exc}")
            self.append_log(emulator_index, f"[AUTO TEST ERROR] {exc}")
            messagebox.showerror("Detect Auto", str(exc))

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

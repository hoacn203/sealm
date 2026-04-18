from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent / "ldplayer-auto"
EMULATOR_DIR = REPO_DIR / "emulator"
EMULATOR_INIT = EMULATOR_DIR / "__init__.py"
LDPLAYER_DIR = r"D:/LDPlayer/LDPlayer9"


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


def main() -> None:
    ensure_pkg_resources_stub()
    cloned_emulator = load_module("cloned_emulator", EMULATOR_INIT, is_package=True)

    ld = cloned_emulator.LDPlayer(ldplayer_dir=LDPLAYER_DIR)
    first_emulator = ld.emulators[0]
    first_emulator.start(wait=True)

    print(f"Selected emulator: index={first_emulator.index}, name={first_emulator.name}")
    print(f"top_hwnd={first_emulator.top_hwnd}, bind_hwnd={first_emulator.bind_hwnd}")

    packages = first_emulator.list_packages() or []
    print(f"Installed packages count: {len(packages)}")
    for package_name in packages:
        print(package_name)


if __name__ == "__main__":
    main()

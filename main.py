# main.py
from __future__ import annotations

import sys
from pathlib import Path

import cv2
from PySide6.QtWidgets import QApplication

from gui.baby_gui import GuiConfig


def _ensure_project_root_on_syspath() -> Path:
    """
    Make imports like `from components...` work no matter where the script is launched from
    (VSCode, double-click, terminal in a subfolder, etc.).

    Returns the project root (folder containing this main.py).
    """
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root


def _ensure_dirs(project_root: Path) -> None:
    # Ensure runtime folders exist
    (project_root / "logs").mkdir(parents=True, exist_ok=True)


def main() -> int:
    project_root = _ensure_project_root_on_syspath()
    _ensure_dirs(project_root)

    # Now safe to import your app code (after sys.path is fixed)
    from gui.baby_gui import BabyMonitorGui  # adjust if your file/class lives elsewhere


    app = QApplication(sys.argv)

    cfg = GuiConfig(
        source_name="pi_cam",
        log_path=project_root / "logs" / "monitor_log.csv",
        camera_backend=cv2.CAP_DSHOW,  # Windows: try CAP_MSMF if CAP_DSHOW is slow/buggy
    )

    w = BabyMonitorGui(cfg)
    w.resize(1500, 850)
    w.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
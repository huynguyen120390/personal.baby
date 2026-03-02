# main.py
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication


def _ensure_project_root_on_syspath() -> Path:
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root


def _ensure_dirs(project_root: Path) -> None:
    (project_root / "logs").mkdir(parents=True, exist_ok=True)


def main() -> int:
    project_root = _ensure_project_root_on_syspath()
    _ensure_dirs(project_root)

    # ✅ Import AFTER sys.path is fixed
    from src.babysitter.gui.baby_gui import BabyMonitorGui, GuiConfig

    #When the program receives Ctrl+C, use the default OS behavior to terminate the program immediately, 
    # instead of raising a KeyboardInterrupt exception that can be caught by the program. 
    # This allows for a more graceful shutdown when the user wants to exit the application using Ctrl+C.
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)

    cfg = GuiConfig(
        source_name="pi_cam",
        log_path=project_root / "logs" / "monitor_log.csv",
    )

    print("✅ before creating window")
    w = BabyMonitorGui(cfg)
    w.resize(1500, 850)
    print("✅ after creating window")
    w.show()
    print("✅ after show()")
   # w.raise_()
    w.activateWindow()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
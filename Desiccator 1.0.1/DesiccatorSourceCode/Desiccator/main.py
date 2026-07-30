# main.py
"""
Entry point for the Desiccator logger.

The excepthook below is the important addition. In PySide6, an unhandled
Python exception inside a slot (for example, connecting a signal to a
method that does not exist) does not always surface a readable traceback --
under a PyInstaller --windowed build it produces no visible output at all,
so the app simply appears to do nothing. Routing exceptions to both a
message box and a log file makes that class of failure obvious.
"""

import os
import sys
import traceback
from datetime import datetime

from PySide6.QtWidgets import QApplication, QMessageBox

from gui import ScaleLoggerGUI


LOG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0])),
    "desiccator_crash.log",
)


def excepthook(exc_type, exc_value, exc_tb):
    text = "".join(
        traceback.format_exception(exc_type, exc_value, exc_tb)
    )

    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.now().isoformat()} =====\n")
            f.write(text)
    except Exception:
        pass

    print(text, file=sys.stderr)

    try:
        QMessageBox.critical(None, "Unhandled error", text[-2000:])
    except Exception:
        pass


def main():
    sys.excepthook = excepthook

    app = QApplication(sys.argv)

    window = ScaleLoggerGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

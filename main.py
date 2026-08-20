import PySide6
import os
import sys
import platform
from pathlib import Path

# 1. वर्तमान ऑपरेटिंग सिस्टम का पता लगाएं
current_os = platform.system()

# 2. पायथन को बताएं कि कौन सा प्लेटफॉर्म प्लगइन इस्तेमाल करना है
if current_os == "Windows":
    os.environ["QT_QPA_PLATFORM"] = "windows"
elif current_os == "Darwin":  # Darwin का मतलब macOS है
    os.environ["QT_QPA_PLATFORM"] = "cocoa"
else:
    os.environ["QT_QPA_PLATFORM"] = "xcb"  # Linux के लिए

# 3. .venv के अंदर से डायनेमिकली Qt plugins का पाथ खोजें
base_dir = Path(__file__).resolve().parent

if current_os == "Windows":
    qt_plugins = (
        base_dir / ".venv" / "Lib" / "site-packages" / "PySide6" / "Qt" / "plugins"
    )
else:
    # macOS/Linux पर 'python3.x' फोल्डर को अपने आप खोजने के लिए
    lib_dir = base_dir / ".venv" / "lib"
    python_dirs = list(lib_dir.glob("python3.*"))
    if python_dirs:
        qt_plugins = python_dirs[0] / "site-packages" / "PySide6" / "Qt" / "plugins"
    else:
        qt_plugins = None

# 4. यदि पाथ सही सलामत मिल जाता है, तो उसे एनवायरनमेंट में सेट करें
if qt_plugins and qt_plugins.exists():
    os.environ["QT_PLUGIN_PATH"] = str(qt_plugins)
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(qt_plugins)

import sys
import traceback
from core.state import SimulationState
from PySide6.QtWidgets import QApplication

from core.simulation_runner import run_simulation_kernel
import core.state

print("STATE PATH =", core.state.__file__)
from PySide6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow

# =========================
# ERROR HANDLING
# =========================


def show_fatal_error(msg: str):
    app = QApplication.instance() or QApplication(sys.argv)
    QMessageBox.critical(None, "Fatal Error", msg)


def exception_hook(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    print(error_msg)
    show_fatal_error(error_msg)


# =========================
# GUI ENTRY
# =========================


def main():
    sys.excepthook = exception_hook

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    app.setStyleSheet("""

QWidget {

    background-color: white;

    color: black;

}

QLineEdit {

    background-color: white;

    color: black;

}

QTextEdit {

    background-color: white;

    color: black;

}

QComboBox {

    background-color: white;

    color: black;

}

QPushButton {

    background-color: #f0f0f0;

    color: black;

}

QGroupBox {

    background-color: white;

    color: black;

}

QLabel {

    color: black;

}

""")

    app.setApplicationName("FSO/QKD Simulator")
    app.setApplicationVersion("0.4.1")

    # 🔴 ADD THIS HERE (before window creation)
    state = SimulationState()
    state.atmospheric_model = "Kim"

    state.cn2_model = "Marine MOST"

    state.detector_model = "SNSPD"

    state.qkd_protocol = "BB84"
    window = MainWindow(state)
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

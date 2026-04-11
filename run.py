import sys
from PySide6.QtWidgets import QApplication

from app.bootstrap import build_application


def main() -> None:
    qt_app = QApplication.instance() or QApplication(sys.argv)
    application = build_application()
    application.run()


if __name__ == "__main__":
    main()
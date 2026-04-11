from PySide6.QtWidgets import QLabel


def section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("font-weight: bold; font-size: 14px;")
    return label

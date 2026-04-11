from datetime import datetime


def now_string() -> str:
    return datetime.now().isoformat(timespec="seconds")

from app.bootstrap import build_application


def main() -> None:
    app = build_application()
    app.run()

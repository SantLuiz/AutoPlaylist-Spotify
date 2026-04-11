from __future__ import annotations

import sys
import traceback

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.repositories.settings_repository import SettingsRepository
from app.services.scheduler_service import SchedulerService
from app.services.sync_service import SyncService
from app.ui.podcasts_tab import PodcastsTab
from app.ui.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    def __init__(
        self,
        sync_service: SyncService,
        settings_repository: SettingsRepository,
        scheduler_service: SchedulerService,
    ) -> None:
        super().__init__()
        self.sync_service = sync_service
        self.settings_repository = settings_repository
        self.scheduler_service = scheduler_service

        self.setWindowTitle("SunriseCast")
        self.resize(700, 500)

        central = QWidget()
        layout = QVBoxLayout()

        self.status_label = QLabel("Ready.")
        self.sync_button = QPushButton("Synchronize now")
        self.sync_button.clicked.connect(self.run_sync)

        tabs = QTabWidget()
        tabs.addTab(
            SettingsTab(
                settings_repository=self.settings_repository,
                on_settings_changed=self.scheduler_service.refresh,
            ),
            "Settings",
        )
        tabs.addTab(
            PodcastsTab(self.sync_service.podcasts_repository),
            "Podcasts",
        )

        layout.addWidget(self.status_label)
        layout.addWidget(self.sync_button)
        layout.addWidget(tabs)
        central.setLayout(layout)
        self.setCentralWidget(central)

    def run_sync(self) -> None:
        self.sync_button.setEnabled(False)
        self.status_label.setText("Synchronizing...")

        try:
            result = self.sync_service.run_sync()
            self.status_label.setText(
                "Done. "
                f"New: {result['new_found']} | "
                f"Removed finished: {result['removed_finished']} | "
                f"Final playlist: {result['final_total']}"
            )
        except Exception as exc:
            traceback.print_exc()
            self.status_label.setText("Synchronization failed.")
            QMessageBox.critical(self, "SunriseCast error", str(exc))
        finally:
            self.sync_button.setEnabled(True)

    def exec_app(self) -> None:
        QApplication.instance().exec()
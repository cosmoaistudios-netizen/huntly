from __future__ import annotations
"""Main Textual Application container and coordinator for Huntly."""

from textual.app import App
from textual.binding import Binding

from huntly.config.settings import Settings
from huntly.db.models import Database
from huntly.screens.dashboard import DashboardScreen
from huntly.screens.job_list import JobListScreen
from huntly.screens.scrape_panel import ScrapePanelScreen
from huntly.screens.settings_screen import SettingsScreen
from huntly.screens.tracker import TrackerScreen


class HuntlyApp(App):
    """Huntly - AI-Powered Job Hunting Terminal Assistant."""

    TITLE = "🎯 Huntly - AI Job Hunter"
    SUB_TITLE = "Built By Cosmo AI Studios"
    DARK = True

    BINDINGS = [
        Binding("d", "switch_dashboard", "Dashboard", show=True),
        Binding("f1", "switch_dashboard", "F1 Dashboard", show=False),
        Binding("j", "switch_jobs", "Job List", show=True),
        Binding("f2", "switch_jobs", "F2 Job List", show=False),
        Binding("s", "switch_scrape", "Scrape", show=True),
        Binding("f3", "switch_scrape", "F3 Scrape", show=False),
        Binding("t", "switch_tracker", "Tracker", show=True),
        Binding("f4", "switch_tracker", "F4 Tracker", show=False),
        Binding("c", "switch_settings", "Settings", show=True),
        Binding("f5", "switch_settings", "F5 Settings", show=False),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.settings = Settings()
        self.db = Database(self.settings.db_path)

    def on_mount(self) -> None:
        """Mount installed screens and present Dashboard on startup."""
        self.install_screen(DashboardScreen(self.db), name="dashboard")
        self.install_screen(JobListScreen(self.db), name="jobs")
        self.install_screen(ScrapePanelScreen(self.db), name="scrape")
        self.install_screen(TrackerScreen(self.db), name="tracker")
        self.install_screen(SettingsScreen(), name="settings")
        self.push_screen("dashboard")

    def action_switch_dashboard(self) -> None:
        self.switch_screen("dashboard")

    def action_switch_jobs(self) -> None:
        self.switch_screen("jobs")

    def action_switch_scrape(self) -> None:
        self.switch_screen("scrape")

    def action_switch_tracker(self) -> None:
        self.switch_screen("tracker")

    def action_switch_settings(self) -> None:
        self.switch_screen("settings")

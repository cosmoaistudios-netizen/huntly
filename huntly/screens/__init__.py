from __future__ import annotations
"""Screens module exports for Huntly."""

from huntly.screens.dashboard import DashboardScreen
from huntly.screens.job_detail import JobDetailScreen
from huntly.screens.job_list import JobListScreen
from huntly.screens.scrape_panel import ScrapePanelScreen
from huntly.screens.settings_screen import SettingsScreen
from huntly.screens.tracker import TrackerScreen

__all__ = [
    "DashboardScreen",
    "JobListScreen",
    "JobDetailScreen",
    "ScrapePanelScreen",
    "SettingsScreen",
    "TrackerScreen",
]

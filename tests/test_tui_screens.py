from __future__ import annotations
import pytest
from huntly.app import HuntlyApp


@pytest.mark.asyncio
async def test_tui_screen_navigation():
    """Test full TUI lifecycle and keyboard navigation across all screens headlessly."""
    app = HuntlyApp()
    async with app.run_test() as pilot:
        # 1. Start on Dashboard
        assert app.screen.__class__.__name__ == "DashboardScreen"

        # 2. Press 'j' -> Job List Screen
        await pilot.press("j")
        assert app.screen.__class__.__name__ == "JobListScreen"

        # 3. Press 's' -> Scrape Panel Screen
        await pilot.press("s")
        assert app.screen.__class__.__name__ == "ScrapePanelScreen"

        # 4. Press 't' -> Application Tracker Screen
        await pilot.press("t")
        assert app.screen.__class__.__name__ == "TrackerScreen"

        # 5. Press 'c' -> Settings Screen
        await pilot.press("c")
        assert app.screen.__class__.__name__ == "SettingsScreen"

        # 6. Press 'd' -> Return to Dashboard
        await pilot.press("d")
        assert app.screen.__class__.__name__ == "DashboardScreen"


@pytest.mark.asyncio
async def test_tui_job_list_interactions():
    """Test Job List screen filtering and interactions."""
    app = HuntlyApp()
    async with app.run_test() as pilot:
        await pilot.press("j")
        assert app.screen.__class__.__name__ == "JobListScreen"

        # Check filter widgets exist
        job_screen = app.screen
        assert job_screen.query_one("#select-date-filter") is not None
        assert job_screen.query_one("#select-source-filter") is not None
        assert job_screen.query_one("#select-sort-by") is not None
        assert job_screen.query_one("#jobs-table") is not None

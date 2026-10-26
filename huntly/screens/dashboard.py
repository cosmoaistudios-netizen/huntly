from __future__ import annotations
"""Dashboard screen displaying high-level metrics, API quotas, and top job matches."""

import json
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Static

from huntly.config.settings import Settings
from huntly.db.models import Database
from huntly.db.queries import AnalysisQueries, ApplicationQueries, JobQueries, QuotaQueries
from huntly.widgets import BannerWidget, QuotaBar


class DashboardScreen(Screen):
    """Primary overview dashboard for Huntly."""

    DEFAULT_CSS = """
    DashboardScreen {
        background: $surface;
    }
    #dashboard-header {
        height: auto;
        content-align: center middle;
        margin: 0 1;
    }
    .metric-box {
        border: solid $primary;
        padding: 1;
        margin: 1;
        height: auto;
    }
    .metric-value {
        text-style: bold;
        color: $accent;
    }
    #top-matches-table {
        height: 12;
        border: solid $secondary;
        margin: 1;
    }
    """

    def __init__(self, db: Database, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.settings = Settings()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield BannerWidget(id="dashboard-header")

        with Vertical():
            with Horizontal():
                with Vertical(classes="metric-box"):
                    yield Label("Total Jobs Indexed:")
                    yield Label("0", id="total-jobs-count", classes="metric-value")

                with Vertical(classes="metric-box"):
                    yield Label("Highest Fit Score:")
                    yield Label("0.0%", id="highest-fit-score", classes="metric-value")

                with Vertical(classes="metric-box"):
                    yield Label("Application Pipeline:")
                    yield Label("Saved: 0 | Applied: 0 | Int: 0", id="pipeline-summary", classes="metric-value")

            with Horizontal():
                yield QuotaBar(used=0, limit=self.settings.daily_job_limit, label="Today's Limit", id="quota-today")
                yield QuotaBar(used=0, limit=self.settings.monthly_requests_limit, label="Monthly Requests", id="quota-reqs")
                yield QuotaBar(used=0, limit=self.settings.monthly_jobs_limit, label="Monthly Jobs", id="quota-jobs")

            yield Label("[bold cyan]🔥 Top Matching Opportunities[/bold cyan]")
            yield DataTable(id="top-matches-table")

        yield Footer()

    def on_mount(self) -> None:
        try:
            table = self.query_one("#top-matches-table", DataTable)
            table.add_columns("ID", "Job Title", "Company", "Location", "Match %", "Category")
            table.cursor_type = "row"
            self.refresh_data()
        except Exception:
            pass

    def on_screen_resume(self) -> None:
        self.settings = Settings()
        self.refresh_data()

    def refresh_data(self) -> None:
        """Load up-to-date metrics and top job rankings from the database."""
        try:
            today_bar = self.query_one("#quota-today", QuotaBar)
            req_bar = self.query_one("#quota-reqs", QuotaBar)
            job_bar = self.query_one("#quota-jobs", QuotaBar)
            table = self.query_one("#top-matches-table", DataTable)
        except Exception:
            return

        self.settings = Settings()

        # 1. Quota
        usage = QuotaQueries.get_monthly_usage(
            self.db,
            requests_limit=self.settings.monthly_requests_limit,
            jobs_limit=self.settings.monthly_jobs_limit,
        )
        today_used = QuotaQueries.get_daily_jobs_scraped(self.db)
        today_bar.set_usage(today_used, self.settings.daily_job_limit)
        req_bar.set_usage(usage["requests_used"], usage["requests_limit"])
        job_bar.set_usage(usage["jobs_used"], usage["jobs_limit"])

        # 2. Total Jobs
        count = JobQueries.count_jobs(self.db)
        self.query_one("#total-jobs-count", Label).update(str(count))

        # 3. Pipeline
        pipe = ApplicationQueries.get_pipeline_counts(self.db)
        pipe_text = f"Saved: {pipe['saved']} | Applied: {pipe['applied']} | Int: {pipe['interviewing']} | Offers: {pipe['offered']}"
        self.query_one("#pipeline-summary", Label).update(pipe_text)

        # 4. Top Matches
        matches = AnalysisQueries.get_top_matches(self.db, limit=5)
        table.clear()

        highest = 0.0
        for job, analysis in matches:
            if analysis.match_score > highest:
                highest = analysis.match_score
            score_color = "green" if analysis.match_score >= 80 else ("yellow" if analysis.match_score >= 50 else "red")
            table.add_row(
                job.id,
                job.title[:35],
                (job.company or "N/A")[:20],
                (job.location or "Remote")[:20],
                f"[{score_color}]{analysis.match_score:.1f}%[/{score_color}]",
                analysis.category,
            )

        self.query_one("#highest-fit-score", Label).update(f"{highest:.1f}%")

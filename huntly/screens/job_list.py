from __future__ import annotations
"""Interactive Job List screen with filtering, sorting, and direct job selection."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Label, Select

from huntly.db.models import Database
from huntly.db.queries import AnalysisQueries, ApplicationQueries


class JobListScreen(Screen):
    """Full-featured sortable and searchable list of scraped job listings."""

    DEFAULT_CSS = """
    #filter-bar {
        margin: 1;
        height: auto;
    }
    #search-input {
        width: 2fr;
        margin-right: 1;
    }
    .filter-select {
        width: 1fr;
        margin-right: 1;
    }
    #jobs-table {
        height: 1fr;
        margin: 1;
        border: solid $primary;
    }
    """

    BINDINGS = [
        Binding("enter", "view_details", "View Full Description"),
        Binding("r", "refresh_list", "Refresh"),
        Binding("a", "mark_applied", "Mark Applied"),
        Binding("e", "enrich_selected", "Enrich HR Email"),
    ]

    def __init__(self, db: Database, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            with Horizontal(id="filter-bar"):
                yield Input(placeholder="Search title, skills, company...", id="search-input")
                yield Select(
                    [
                        ("All Time", "all"),
                        ("Past 24 Hours", "24h"),
                        ("Past 3 Days", "3d"),
                        ("Past 7 Days", "7d"),
                        ("Past 30 Days", "30d"),
                    ],
                    value="all",
                    id="select-date-filter",
                    classes="filter-select",
                )
                yield Select(
                    [
                        ("Sort: Fit Score", "match_score"),
                        ("Sort: Date Added", "date_added"),
                        ("Sort: Company", "company"),
                        ("Sort: Title", "title"),
                    ],
                    value="match_score",
                    id="select-sort-by",
                    classes="filter-select",
                )
                yield Select(
                    [
                        ("All Sources", "all"),
                        ("LinkedIn", "linkedin"),
                        ("Hacker News", "hackernews"),
                        ("RemoteOK", "remoteok"),
                        ("WeWorkRemotely", "weworkremotely"),
                    ],
                    value="all",
                    id="select-source-filter",
                    classes="filter-select",
                )
            yield DataTable(id="jobs-table")
        yield Footer()

    def on_mount(self) -> None:
        try:
            table = self.query_one("#jobs-table", DataTable)
            table.add_columns("ID", "Job Title", "Company", "Location", "Match %", "Source", "Date Added", "Contact Email")
            table.cursor_type = "row"
            self.load_jobs()
            table.focus()
        except Exception:
            pass

    def on_screen_resume(self) -> None:
        self.load_jobs()
        try:
            self.query_one("#jobs-table", DataTable).focus()
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        self.load_jobs(search_term=event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        try:
            self.query_one("#jobs-table", DataTable).focus()
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        search_val = ""
        try:
            search_val = self.query_one("#search-input", Input).value
        except Exception:
            pass
        self.load_jobs(search_term=search_val)

    def load_jobs(self, search_term: str = "") -> None:
        try:
            table = self.query_one("#jobs-table", DataTable)
        except Exception:
            return

        date_val = "all"
        sort_val = "match_score"
        source_val = "all"
        try:
            date_val = str(self.query_one("#select-date-filter", Select).value)
            sort_val = str(self.query_one("#select-sort-by", Select).value)
            source_val = str(self.query_one("#select-source-filter", Select).value)
        except Exception:
            pass

        table.clear()
        jobs_with_eval = AnalysisQueries.get_jobs_with_analysis(
            self.db,
            limit=150,
            sort_by=sort_val,
            date_filter=date_val,
            source_filter=source_val,
        )
        filter_lower = search_term.strip().lower()

        for job, analysis in jobs_with_eval:
            if filter_lower:
                combined = f"{job.title} {job.company or ''} {job.location or ''} {job.description_text or ''}".lower()
                if filter_lower not in combined:
                    continue

            score = analysis.match_score if analysis else 0.0
            color = "green" if score >= 80 else ("yellow" if score >= 50 else "red")
            email_display = f"[cyan]{job.contact_email}[/cyan]" if job.contact_email else "[dim]None[/dim]"

            # Format source badge
            src = (job.source or "linkedin").lower()
            if src == "hackernews":
                src_badge = "[bold yellow]HN[/bold yellow]"
            elif src == "remoteok":
                src_badge = "[bold cyan]RemoteOK[/bold cyan]"
            elif src == "weworkremotely":
                src_badge = "[bold magenta]WWR[/bold magenta]"
            else:
                src_badge = "[blue]LinkedIn[/blue]"

            # Format date added
            date_str = str(job.scraped_at or job.posted_date or "N/A")[:10]

            table.add_row(
                job.id,
                job.title[:30],
                (job.company or "N/A")[:18],
                (job.location or "Remote")[:16],
                f"[{color}]{score:.1f}%[/{color}]",
                src_badge,
                date_str,
                email_display,
                key=job.id,
            )

    def _open_detail(self, job_id: str) -> None:
        if job_id:
            from huntly.screens.job_detail import JobDetailScreen
            self.app.push_screen(JobDetailScreen(db=self.db, job_id=job_id))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key.value if event.row_key else None
        if row_key:
            self._open_detail(str(row_key))

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        row_key = event.cell_key.row_key.value if event.cell_key and event.cell_key.row_key else None
        if row_key:
            self._open_detail(str(row_key))

    def action_view_details(self) -> None:
        try:
            table = self.query_one("#jobs-table", DataTable)
        except Exception:
            return
        if table.cursor_row is not None:
            try:
                cell_key = table.coordinate_to_cell_key((table.cursor_row, 0))
                row_key = cell_key.row_key.value
                self._open_detail(str(row_key))
            except Exception:
                try:
                    job_id = str(table.get_cell_at((table.cursor_row, 0)))
                    self._open_detail(job_id)
                except Exception:
                    pass

    def action_refresh_list(self) -> None:
        self.load_jobs()

    def action_mark_applied(self) -> None:
        try:
            table = self.query_one("#jobs-table", DataTable)
        except Exception:
            return
        if table.cursor_row is not None:
            cell_value = str(table.get_cell_at((table.cursor_row, 0)))
            ApplicationQueries.create_application(self.db, job_id=cell_value, status="applied")
            self.notify(f"Marked job {cell_value} as Applied!")

    def action_enrich_selected(self) -> None:
        try:
            table = self.query_one("#jobs-table", DataTable)
        except Exception:
            return
        if table.cursor_row is not None:
            job_id = str(table.get_cell_at((table.cursor_row, 0)))
            self.run_worker(self._async_enrich_job(job_id), exclusive=True)

    async def _async_enrich_job(self, job_id: str) -> None:
        from huntly.core.enricher import CompanyEmailEnricher, enrich_single_job
        from huntly.db.queries import JobQueries

        job = JobQueries.get_job(self.db, job_id)
        if not job:
            return
        self.notify(f"Searching HR contact for {job.company}...")
        enricher = CompanyEmailEnricher()
        email = await enrich_single_job(self.db, job, enricher)
        if email:
            self.load_jobs()
            self.notify(f"Found HR contact for {job.company}: {email}")
        else:
            self.notify(f"No direct email found for {job.company}.", severity="warning")

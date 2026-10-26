from __future__ import annotations
"""Application pipeline tracking screen across candidate stages."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label

from huntly.db.models import Database
from huntly.db.queries import ApplicationQueries, JobQueries


class TrackerScreen(Screen):
    """Kanban-style application pipeline manager."""

    DEFAULT_CSS = """
    #pipeline-stats-row {
        height: auto;
        padding: 1;
        margin: 1;
        border: solid $secondary;
    }
    .status-stat {
        width: 1fr;
        text-align: center;
        text-style: bold;
    }
    #applications-table {
        height: 1fr;
        margin: 1;
        border: solid $primary;
    }
    """

    BINDINGS = [
        Binding("r", "refresh_data", "Refresh"),
        Binding("s", "move_to_saved", "Mark Saved"),
        Binding("a", "move_to_applied", "Mark Applied"),
        Binding("i", "move_to_interview", "Mark Interviewing"),
        Binding("o", "move_to_offered", "Mark Offered"),
    ]

    def __init__(self, db: Database, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            with Horizontal(id="pipeline-stats-row"):
                yield Label("Saved: 0", id="stat-saved", classes="status-stat")
                yield Label("Applied: 0", id="stat-applied", classes="status-stat")
                yield Label("Interviewing: 0", id="stat-interviewing", classes="status-stat")
                yield Label("Offered: 0", id="stat-offered", classes="status-stat")
                yield Label("Rejected: 0", id="stat-rejected", classes="status-stat")

            yield Label("[bold cyan]Application Tracker (Keys: [a] Applied, [i] Interview, [o] Offer, [s] Save)[/bold cyan]")
            yield DataTable(id="applications-table")

        yield Footer()

    def on_mount(self) -> None:
        try:
            table = self.query_one("#applications-table", DataTable)
            table.add_columns("Job ID", "Role", "Company", "Status", "Last Updated")
            table.cursor_type = "row"
            self.refresh_data()
        except Exception:
            pass

    def on_screen_resume(self) -> None:
        self.refresh_data()

    def refresh_data(self) -> None:
        try:
            table = self.query_one("#applications-table", DataTable)
        except Exception:
            return

        counts = ApplicationQueries.get_pipeline_counts(self.db)
        self.query_one("#stat-saved", Label).update(f"[cyan]Saved:[/cyan] {counts['saved']}")
        self.query_one("#stat-applied", Label).update(f"[blue]Applied:[/blue] {counts['applied']}")
        self.query_one("#stat-interviewing", Label).update(f"[yellow]Interviewing:[/yellow] {counts['interviewing']}")
        self.query_one("#stat-offered", Label).update(f"[green]Offered:[/green] {counts['offered']}")
        self.query_one("#stat-rejected", Label).update(f"[red]Rejected:[/red] {counts['rejected']}")

        table.clear()
        apps = ApplicationQueries.get_applications(self.db)
        for app in apps:
            job = JobQueries.get_job(self.db, app.job_id)
            title = job.title if job else "N/A"
            company = job.company if job else "N/A"
            status_color = {
                "saved": "cyan",
                "applied": "blue",
                "interviewing": "yellow",
                "offered": "green",
                "rejected": "red",
            }.get(app.status, "white")

            table.add_row(
                app.job_id,
                title[:30],
                company[:20],
                f"[{status_color}]{app.status.upper()}[/{status_color}]",
                str(app.updated_at or "")[:19],
                key=app.job_id,
            )

    def _update_cursor_status(self, new_status: str) -> None:
        try:
            table = self.query_one("#applications-table", DataTable)
        except Exception:
            return
        if table.cursor_row is not None:
            job_id = str(table.get_cell_at((table.cursor_row, 0)))
            ApplicationQueries.update_status(self.db, job_id=job_id, status=new_status)
            self.notify(f"Job {job_id} updated to {new_status.upper()}")
            self.refresh_data()

    def action_move_to_saved(self) -> None:
        self._update_cursor_status("saved")

    def action_move_to_applied(self) -> None:
        self._update_cursor_status("applied")

    def action_move_to_interview(self) -> None:
        self._update_cursor_status("interviewing")

    def action_move_to_offered(self) -> None:
        self._update_cursor_status("offered")

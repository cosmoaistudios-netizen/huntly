from __future__ import annotations
"""Custom visual widgets for Huntly TUI."""

from textual.widgets import Static


class QuotaBar(Static):
    """Renders a progress meter indicating API quota consumption."""

    def __init__(self, used: int = 0, limit: int = 25, label: str = "Requests", **kwargs) -> None:
        super().__init__(**kwargs)
        self.used = used
        self.limit = limit
        self.label = label
        self.update_meter()

    def set_usage(self, used: int, limit: int) -> None:
        self.used = used
        self.limit = limit
        self.update_meter()

    def update_meter(self) -> None:
        percent = (self.used / max(self.limit, 1)) * 100
        bars = int((percent / 100) * 20)
        remaining = 20 - bars

        color = "green"
        if percent >= 80:
            color = "red"
        elif percent >= 50:
            color = "yellow"

        bar_repr = f"[{color}]{'█' * bars}{'░' * remaining}[/{color}]"
        self.update(f"{self.label}: {bar_repr} {self.used}/{self.limit} ({percent:.0f}%)")


class MatchBadge(Static):
    """Visual badge displaying the match score."""

    def __init__(self, score: float = 0.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.score = score
        self.update_badge()

    def set_score(self, score: float) -> None:
        self.score = score
        self.update_badge()

    def update_badge(self) -> None:
        if self.score >= 80:
            color = "bold green"
            tag = "HIGH FIT"
        elif self.score >= 50:
            color = "bold yellow"
            tag = "MODERATE"
        else:
            color = "bold red"
            tag = "LOW FIT"

        self.update(f"[{color}] {self.score:.1f}% [{tag}] [/{color}]")


class SkillChips(Static):
    """Visual chips displaying matched and missing skills."""

    def __init__(self, matched: list[str] | None = None, missing: list[str] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.matched = matched or []
        self.missing = missing or []
        self.render_chips()

    def update_skills(self, matched: list[str], missing: list[str]) -> None:
        self.matched = matched
        self.missing = missing
        self.render_chips()

    def render_chips(self) -> None:
        matched_str = " ".join([f"[black on green] {s} [/black on green]" for s in self.matched[:8]])
        missing_str = " ".join([f"[white on red] {s} [/white on red]" for s in self.missing[:6]])

        output = ""
        if matched_str:
            output += f"[bold]Matched Skills:[/bold] {matched_str}\n"
        if missing_str:
            output += f"[bold]Missing Skills:[/bold] {missing_str}"

        self.update(output.strip() or "[dim]No skills specified[/dim]")


class JobCard(Static):
    """Compact summary card representing a job posting."""

    def __init__(self, title: str, company: str, location: str, match_score: float = 0.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.company = company
        self.location = location
        self.match_score = match_score
        self.render_card()

    def render_card(self) -> None:
        score_color = "green" if self.match_score >= 80 else ("yellow" if self.match_score >= 50 else "red")
        text = (
            f"[bold cyan]{self.title}[/bold cyan] @ [white]{self.company}[/white]\n"
            f"[dim]{self.location}[/dim] | Match: [{score_color}]{self.match_score:.1f}%[/{score_color}]"
        )
        self.update(text)

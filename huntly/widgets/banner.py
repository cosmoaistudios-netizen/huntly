from __future__ import annotations
"""ASCII Art launch banner structure for Huntly."""

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from textual.widgets import Static

BANNER_ART = """[bold #38bdf8]██╗  ██╗██╗   ██╗███╗   ██╗████████╗██╗  ██╗   ██╗[/bold #38bdf8]
[bold #38bdf8]██║  ██║██║   ██║████╗  ██║╚══██╔══╝██║  ╚██╗ ██╔╝[/bold #38bdf8]
[bold #818cf8]███████║██║   ██║██╔██╗ ██║   ██║   ██║   ╚████╔╝ [/bold #818cf8]
[bold #818cf8]██╔══██║██║   ██║██║╚██╗██║   ██║   ██║    ╚██╔╝  [/bold #818cf8]
[bold #a855f7]██║  ██║╚██████╔╝██║ ╚████║   ██║   ███████╗██║   [/bold #a855f7]
[bold #a855f7]╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝   [/bold #a855f7]
[dim #64748b]═══════════════════════════════════════════════════[/dim #64748b]
[bold #f8fafc]Autonomous AI Job Hunter[/bold #f8fafc] [dim]•[/dim] [green]Zero-Quota Scraper[/green] [dim]•[/dim] [magenta]Nemotron 3.5 120B / Ollama[/magenta]
[dim italic]made by cosmo AI Studios[/dim italic]"""


def get_banner_panel(border_style: str = "bold #6366f1") -> Panel:
    """Returns a Rich Panel formatted with the Huntly signature banner."""
    return Panel(
        Align.center(BANNER_ART),
        border_style=border_style,
        subtitle="[bold #6366f1]v0.2.0[/bold #6366f1]",
        subtitle_align="right",
        padding=(0, 2),
    )


def print_launch_banner(console: Console | None = None) -> None:
    """Outputs the styled launch banner to the terminal."""
    c = console or Console()
    c.print(get_banner_panel())


class BannerWidget(Static):
    """Textual widget displaying the launch banner drawing structure."""

    DEFAULT_CSS = """
    BannerWidget {
        height: auto;
        margin: 0 1 1 1;
        content-align: center middle;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(get_banner_panel(), **kwargs)

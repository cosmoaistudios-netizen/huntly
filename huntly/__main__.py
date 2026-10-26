from __future__ import annotations
"""Entry point for running Huntly as a module: python -m huntly."""

from huntly.app import HuntlyApp


def main():
    """Launch the Huntly TUI application."""
    app = HuntlyApp()
    app.run()


if __name__ == "__main__":
    main()

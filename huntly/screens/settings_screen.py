from __future__ import annotations
"""Settings screen for managing credentials, quota limits, resume parsing, and operational parameters."""

import os
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from huntly.config.settings import Settings
from huntly.core.resume import extract_skills, parse_resume


class SettingsScreen(Screen):
    """Configuration interface for credentials, operational quota limits, and candidate parameters."""

    DEFAULT_CSS = """
    #settings-scroll {
        height: 1fr;
        padding: 1;
    }
    .settings-section {
        border: solid $accent;
        padding: 1;
        margin-bottom: 1;
        height: auto;
    }
    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    .field-row {
        height: auto;
        margin-bottom: 1;
    }
    .field-label {
        width: 24;
        padding-top: 1;
    }
    #resume-preview {
        height: 8;
        border: solid $secondary;
        margin-top: 1;
        padding: 1;
    }
    .btn-row {
        margin-top: 1;
        margin-bottom: 1;
        height: auto;
    }
    .btn-item {
        margin-right: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.settings = Settings()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with ScrollableContainer(id="settings-scroll"):
            yield Label("[bold cyan]⚙️ Huntly System Settings & Limit Configuration[/bold cyan]\n")

            # Section 1: AI Provider & Credentials
            with Vertical(classes="settings-section"):
                yield Label("🤖 AI Engine & Provider Architecture", classes="section-title")

                with Horizontal(classes="field-row"):
                    yield Label("AI Provider:", classes="field-label")
                    yield Select(
                        [
                            ("NVIDIA Nemotron (Cloud NIM)", "nvidia"),
                            ("Ollama (Local / Free)", "ollama"),
                            ("OpenRouter (Multi-Model)", "openrouter"),
                        ],
                        value=self.settings.ai_provider if self.settings.ai_provider in ("nvidia", "ollama", "openrouter") else "nvidia",
                        id="select-ai-provider",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("Model ID / Name:", classes="field-label")
                    yield Input(
                        value=self.settings.ai_model,
                        placeholder="e.g. nvidia/nemotron-3.5-super-vl-120b-a12b, llama3.2, etc.",
                        id="input-ai-model",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("AI Base URL:", classes="field-label")
                    yield Input(
                        value=self.settings.ai_base_url,
                        placeholder="e.g. https://integrate.api.nvidia.com/v1 or http://localhost:11434/v1",
                        id="input-ai-base-url",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("NVIDIA API Key:", classes="field-label")
                    yield Input(
                        value=self.settings.nvidia_api_key,
                        password=True,
                        placeholder="nvapi-...",
                        id="input-nvidia-key",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("OpenRouter API Key:", classes="field-label")
                    yield Input(
                        value=self.settings.openrouter_api_key,
                        password=True,
                        placeholder="sk-or-v1-...",
                        id="input-openrouter-key",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("RapidAPI Key:", classes="field-label")
                    yield Input(
                        value=self.settings.rapidapi_key,
                        password=True,
                        placeholder="Required only for LinkedIn searches...",
                        id="input-rapid-key",
                    )

            # Section 2: Quota & Scraping Rate Limits
            with Vertical(classes="settings-section"):
                yield Label("⚡ Scraping & API Quota Limits", classes="section-title")

                with Horizontal(classes="field-row"):
                    yield Label("Daily Job Scraping Cap:", classes="field-label")
                    yield Input(
                        value=str(self.settings.daily_job_limit),
                        placeholder="e.g. 50 (Jobs/day limit)",
                        id="input-daily-limit",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("Monthly RapidAPI Requests:", classes="field-label")
                    yield Input(
                        value=str(self.settings.monthly_requests_limit),
                        placeholder="e.g. 25 (Monthly API calls)",
                        id="input-req-limit",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("Monthly Job Credits Cap:", classes="field-label")
                    yield Input(
                        value=str(self.settings.monthly_jobs_limit),
                        placeholder="e.g. 250 (Monthly job credits)",
                        id="input-job-limit",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("Default Batch Size:", classes="field-label")
                    yield Input(
                        value=str(self.settings.jobs_per_request),
                        placeholder="e.g. 10 (Jobs per search request)",
                        id="input-batch-size",
                    )

            # Section 3: Resume & Match Fit Thresholds
            with Vertical(classes="settings-section"):
                yield Label("🎯 Candidate Profile & Match Score Thresholds", classes="section-title")

                with Horizontal(classes="field-row"):
                    yield Label("Resume PDF Path:", classes="field-label")
                    yield Input(value=str(self.settings.resume_path), id="input-resume-path")

                with Horizontal(classes="field-row"):
                    yield Label("High Fit Threshold (%):", classes="field-label")
                    yield Input(
                        value=str(self.settings.match_threshold_green),
                        placeholder="Score for Green badge (default: 80)",
                        id="input-thresh-green",
                    )

                with Horizontal(classes="field-row"):
                    yield Label("Medium Fit Threshold (%):", classes="field-label")
                    yield Input(
                        value=str(self.settings.match_threshold_yellow),
                        placeholder="Score for Yellow badge (default: 50)",
                        id="input-thresh-yellow",
                    )

            # Buttons & Previews
            with Horizontal(classes="btn-row"):
                yield Button("💾 Save All Settings", variant="success", id="btn-save-settings", classes="btn-item")
                yield Button("📄 Parse & Test Resume", variant="primary", id="btn-test-resume", classes="btn-item")
                yield Button("🔄 Reset Limits to Defaults", variant="default", id="btn-reset-limits", classes="btn-item")

            yield Label("[bold]Resume Content & Skill Preview:[/bold]")
            yield Static("Click 'Parse & Test Resume' to preview extracted profile data.", id="resume-preview")

        yield Footer()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-ai-provider":
            prov = str(event.value)
            model_input = self.query_one("#input-ai-model", Input)
            url_input = self.query_one("#input-ai-base-url", Input)
            if prov == "ollama":
                url_input.value = "http://localhost:11434/v1"
                if "nemotron" in model_input.value or not model_input.value:
                    model_input.value = "llama3.2"
            elif prov == "openrouter":
                url_input.value = "https://openrouter.ai/api/v1"
                if "nemotron" in model_input.value or not model_input.value:
                    model_input.value = "meta-llama/llama-3.3-70b-instruct"
            elif prov == "nvidia":
                url_input.value = "https://integrate.api.nvidia.com/v1"
                model_input.value = "nvidia/nemotron-3.5-super-vl-120b-a12b"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-settings":
            provider = str(self.query_one("#select-ai-provider", Select).value)
            ai_model = self.query_one("#input-ai-model", Input).value.strip() or "nvidia/nemotron-3.5-super-vl-120b-a12b"
            ai_base_url = self.query_one("#input-ai-base-url", Input).value.strip()
            rapid_key = self.query_one("#input-rapid-key", Input).value.strip()
            nvidia_key = self.query_one("#input-nvidia-key", Input).value.strip()
            openrouter_key = self.query_one("#input-openrouter-key", Input).value.strip()
            resume_path = self.query_one("#input-resume-path", Input).value.strip()

            # Parse numeric limits safely
            try:
                daily_limit = int(self.query_one("#input-daily-limit", Input).value.strip())
            except ValueError:
                daily_limit = 50

            try:
                req_limit = int(self.query_one("#input-req-limit", Input).value.strip())
            except ValueError:
                req_limit = 25

            try:
                job_limit = int(self.query_one("#input-job-limit", Input).value.strip())
            except ValueError:
                job_limit = 250

            try:
                batch_size = int(self.query_one("#input-batch-size", Input).value.strip())
            except ValueError:
                batch_size = 10

            try:
                thresh_green = int(self.query_one("#input-thresh-green", Input).value.strip())
            except ValueError:
                thresh_green = 80

            try:
                thresh_yellow = int(self.query_one("#input-thresh-yellow", Input).value.strip())
            except ValueError:
                thresh_yellow = 50

            # Save in user's ~/.huntly/.env
            env_file = Path.home() / ".huntly" / ".env"
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(
                    f"RAPIDAPI_KEY={rapid_key}\n"
                    f"NVIDIA_API_KEY={nvidia_key}\n"
                    f"OPENROUTER_API_KEY={openrouter_key}\n"
                )

            os.environ["RAPIDAPI_KEY"] = rapid_key
            os.environ["NVIDIA_API_KEY"] = nvidia_key
            os.environ["OPENROUTER_API_KEY"] = openrouter_key

            # Save in user's ~/.huntly/config.yaml
            self.settings.save_user_config({
                "resume": {"path": resume_path},
                "ai": {
                    "provider": provider,
                    "model": ai_model,
                    "base_url": ai_base_url,
                },
                "limits": {
                    "daily_job_limit": daily_limit,
                    "monthly_requests_limit": req_limit,
                    "monthly_jobs_limit": job_limit,
                    "jobs_per_request": batch_size,
                },
                "display": {
                    "match_threshold_green": thresh_green,
                    "match_threshold_yellow": thresh_yellow,
                },
            })

            self.notify(f"Settings saved! Provider: {provider.upper()} | Model: {ai_model}")

        elif event.button.id == "btn-reset-limits":
            self.query_one("#input-daily-limit", Input).value = "50"
            self.query_one("#input-req-limit", Input).value = "25"
            self.query_one("#input-job-limit", Input).value = "250"
            self.query_one("#input-batch-size", Input).value = "10"
            self.query_one("#input-thresh-green", Input).value = "80"
            self.query_one("#input-thresh-yellow", Input).value = "50"
            self.notify("Limits reset to default values. Click 'Save All Settings' to apply.")

        elif event.button.id == "btn-test-resume":
            resume_path = self.query_one("#input-resume-path", Input).value.strip()
            text = parse_resume(resume_path)
            if not text:
                self.query_one("#resume-preview", Static).update(
                    f"[bold red]Failed to read resume at {resume_path}. Please verify the file path.[/bold red]"
                )
            else:
                skills = extract_skills(text)
                preview = (
                    f"[bold green]Successfully read {len(text)} characters![/bold green]\n"
                    f"[bold]Detected Skills ({len(skills)}):[/bold] {', '.join(skills)}\n\n"
                    f"[dim]Preview: {text[:250].replace(chr(10), ' ')}...[/dim]"
                )
                self.query_one("#resume-preview", Static).update(preview)

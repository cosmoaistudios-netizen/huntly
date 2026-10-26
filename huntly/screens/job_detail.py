from __future__ import annotations
"""Detailed job perspective screen with AI evaluations and drafting actions."""

import json
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Markdown, Static

from huntly.config.settings import Settings
from huntly.core.analyzer import JobAnalyzer
from huntly.core.enricher import CompanyEmailEnricher
from huntly.core.resume import parse_resume
from huntly.db.models import Database
from huntly.db.queries import AnalysisQueries, ApplicationQueries, JobQueries
from huntly.widgets import MatchBadge, SkillChips


class JobDetailScreen(Screen):
    """Inspects a single job listing alongside AI insights and action generators."""

    DEFAULT_CSS = """
    #detail-container {
        height: 1fr;
    }
    #desc-col {
        width: 60%;
        border-right: solid $primary;
        padding: 1;
    }
    #ai-col {
        width: 40%;
        padding: 1;
        background: $surface;
    }
    .action-bar {
        height: auto;
        dock: bottom;
        padding: 1;
        background: $panel;
    }
    .action-btn {
        margin-right: 2;
    }
    .section-title {
        text-style: bold;
        color: $accent;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
        Binding("s", "synthesize", "AI Synthesis"),
        Binding("c", "generate_cover_letter", "Cover Letter"),
        Binding("o", "generate_outreach", "Outreach Email"),
        Binding("e", "enrich_email", "Enrich HR Email"),
    ]

    def __init__(self, db: Database, job_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.job_id = job_id
        self.settings = Settings()
        self.job = JobQueries.get_job(self.db, self.job_id)
        self.analysis = AnalysisQueries.get_analysis(self.db, self.job_id)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        if not self.job:
            yield Static("[bold red]Job not found.[/bold red]")
            yield Footer()
            return

        with Horizontal(id="detail-container"):
            # Left: Job overview and description
            with ScrollableContainer(id="desc-col"):
                yield Label(f"[bold cyan]{self.job.title}[/bold cyan] @ [white]{self.job.company or 'N/A'}[/white]")
                yield Label(f"[dim]📍 {self.job.location} | Remote: {self.job.remote_type} | Posted: {self.job.posted_date}[/dim]")
                if self.job.apply_url:
                    yield Label(f"[underline blue]Apply Link: {self.job.apply_url}[/underline blue]")
                yield Label("\n[bold]Description:[/bold]")
                yield Markdown(self.job.description_text or "No detailed description provided.")

            # Right: AI insights
            with ScrollableContainer(id="ai-col"):
                yield Label("[bold]AI Fit Evaluation[/bold]", classes="section-title")
                score = self.analysis.match_score if self.analysis else 0.0
                yield MatchBadge(score=score)

                yield Label("[bold]Category:[/bold] " + (self.analysis.category if self.analysis else "General"), id="label-category")
                yield Label("[bold]Salary Estimate:[/bold] " + (self.analysis.salary_estimate if self.analysis else "N/A"), id="label-salary")

                yield Label("[bold]AI Synthesis:[/bold]", classes="section-title")
                summary_text = self.analysis.summary if self.analysis else "No analysis performed yet."
                yield Static(summary_text, id="ai-summary-text")

                # Skills
                key_skills = json.loads(self.analysis.key_skills) if self.analysis and self.analysis.key_skills else []
                missing_skills = json.loads(self.analysis.missing_skills) if self.analysis and self.analysis.missing_skills else []
                yield SkillChips(matched=key_skills, missing=missing_skills)

                # Contact Email & Red Flags
                yield Label("[bold]Contact Email:[/bold]", classes="section-title")
                yield Static(self.job.contact_email or "[dim]No email found[/dim]", id="contact-email-val")

                red_flags = json.loads(self.analysis.red_flags) if self.analysis and self.analysis.red_flags else []
                if red_flags:
                    yield Label("[bold red]⚠️ Red Flags / Warnings:[/bold red]", classes="section-title")
                    yield Static("\n".join([f"• {flag}" for flag in red_flags]))

        with Horizontal(classes="action-bar"):
            yield Button("AI Synthesis", variant="warning", id="btn-synthesize", classes="action-btn")
            yield Button("Mark Applied", variant="success", id="btn-apply", classes="action-btn")
            yield Button("Draft Cover Letter", variant="primary", id="btn-cover", classes="action-btn")
            yield Button("Draft Outreach Email", variant="default", id="btn-outreach", classes="action-btn")
            yield Button("Enrich HR Email", variant="primary", id="btn-enrich", classes="action-btn")
            yield Button("Back", variant="default", id="btn-back", classes="action-btn")

        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_synthesize(self) -> None:
        self.run_worker(self._async_synthesize_analysis(), exclusive=True)

    def action_enrich_email(self) -> None:
        self.run_worker(self._async_enrich_email(), exclusive=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.action_go_back()
        elif event.button.id == "btn-synthesize":
            self.action_synthesize()
        elif event.button.id == "btn-apply":
            ApplicationQueries.create_application(self.db, job_id=self.job_id, status="applied")
            self.notify("Application marked as Applied!")
        elif event.button.id == "btn-cover":
            self.run_worker(self._async_cover_letter(), exclusive=True)
        elif event.button.id == "btn-outreach":
            self.run_worker(self._async_outreach_email(), exclusive=True)
        elif event.button.id == "btn-enrich":
            self.action_enrich_email()

    async def _async_synthesize_analysis(self) -> None:
        self.notify(f"Synthesizing fit using {self.settings.ai_provider} ({self.settings.ai_model})...")
        resume_text = parse_resume(self.settings.resume_path)
        analyzer = JobAnalyzer(
            api_key=self.settings.ai_api_key,
            resume_text=resume_text,
            model=self.settings.ai_model,
            base_url=self.settings.ai_base_url,
        )
        job_dict = {
            "id": self.job.id,
            "title": self.job.title,
            "company": self.job.company,
            "location": self.job.location,
            "description_text": self.job.description_text,
            "contact_email": self.job.contact_email,
        }
        from huntly.db.models import AIAnalysis
        data = await analyzer.analyze_job(job_dict)
        ai_obj = AIAnalysis(
            job_id=self.job.id,
            match_score=data.get("match_score", 0.0),
            category=data.get("category", "General"),
            summary=data.get("summary", ""),
            key_skills=json.dumps(data.get("key_skills", [])),
            missing_skills=json.dumps(data.get("missing_skills", [])),
            salary_estimate=data.get("salary_estimate", ""),
            red_flags=json.dumps(data.get("red_flags", [])),
            learning_suggestions=json.dumps(data.get("learning_suggestions", [])),
        )
        AnalysisQueries.save_analysis(self.db, ai_obj)
        self.analysis = ai_obj

        try:
            self.query_one("#ai-summary-text", Static).update(ai_obj.summary)
            badge = self.query_one(MatchBadge)
            badge.score = ai_obj.match_score
            badge.refresh()
            self.query_one("#label-category", Label).update(f"[bold]Category:[/bold] {ai_obj.category}")
            self.query_one("#label-salary", Label).update(f"[bold]Salary Estimate:[/bold] {ai_obj.salary_estimate}")
        except Exception:
            pass

        self.notify(f"AI Synthesis complete: {ai_obj.match_score:.1f}% fit ({ai_obj.category})")

    async def _async_enrich_email(self) -> None:
        self.notify("Searching company website & Nemotron for HR contact...")
        enricher = CompanyEmailEnricher(self.settings)
        job_dict = {
            "id": self.job.id,
            "title": self.job.title,
            "company": self.job.company,
            "apply_url": self.job.apply_url,
            "description_text": self.job.description_text,
            "raw_json": self.job.raw_json,
        }
        res = await enricher.enrich_job_contact(job_dict)
        email = res.get("email")
        if email:
            self.job.contact_email = email
            JobQueries.update_contact_email(self.db, self.job.id, email)
            try:
                email_widget = self.query_one("#contact-email-val", Static)
                email_widget.update(f"[bold cyan]{email}[/bold cyan] [dim]({res.get('method', 'Tool')})[/dim]")
            except Exception:
                pass
            self.notify(f"HR Email Found: {email}")
        else:
            self.notify("No direct contact email discovered on site.", severity="warning")

    async def _async_cover_letter(self) -> None:
        self.notify("Synthesizing cover letter via Nemotron AI...")
        resume_text = parse_resume(self.settings.resume_path)
        analyzer = JobAnalyzer(
            api_key=self.settings.ai_api_key,
            resume_text=resume_text,
            model=self.settings.ai_model,
            base_url=self.settings.ai_base_url,
        )
        job_dict = {
            "title": self.job.title,
            "company": self.job.company,
            "description_text": self.job.description_text,
        }
        letter = await analyzer.generate_cover_letter(job_dict)
        if self.analysis:
            self.analysis.cover_letter = letter
            AnalysisQueries.save_analysis(self.db, self.analysis)
        self.app.push_screen(TextDisplayModal("Cover Letter Draft", letter))

    async def _async_outreach_email(self) -> None:
        email = self.job.contact_email or "founder@startup.com"
        self.notify("Drafting cold outreach email...")
        resume_text = parse_resume(self.settings.resume_path)
        analyzer = JobAnalyzer(
            api_key=self.settings.ai_api_key,
            resume_text=resume_text,
            model=self.settings.ai_model,
            base_url=self.settings.ai_base_url,
        )
        job_dict = {
            "title": self.job.title,
            "company": self.job.company,
            "description_text": self.job.description_text,
        }
        email_draft = await analyzer.generate_outreach_email(job_dict, email)
        if self.analysis:
            self.analysis.outreach_email = email_draft
            AnalysisQueries.save_analysis(self.db, self.analysis)
        self.app.push_screen(TextDisplayModal(f"Outreach Draft (To: {email})", email_draft))


class TextDisplayModal(Screen):
    """Modal dialog displaying generated documents."""

    DEFAULT_CSS = """
    TextDisplayModal {
        align: center middle;
    }
    #modal-box {
        width: 80%;
        height: 80%;
        background: $panel;
        border: thick $primary;
        padding: 2;
    }
    #modal-content {
        height: 1fr;
    }
    """

    def __init__(self, title: str, text: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.dialog_title = title
        self.text = text

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label(f"[bold cyan]{self.dialog_title}[/bold cyan]")
            with ScrollableContainer(id="modal-content"):
                yield Markdown(self.text)
            yield Button("Close", variant="primary", id="btn-close-modal")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-modal":
            self.app.pop_screen()

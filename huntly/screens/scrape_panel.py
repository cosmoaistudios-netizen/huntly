from __future__ import annotations
"""Scrape control screen allowing on-demand job extraction and automated AI analysis."""

import json
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Select,
    Static,
)

from huntly.config.settings import Settings
from huntly.core.analyzer import JobAnalyzer
from huntly.core.dedup import get_new_jobs
from huntly.core.enricher import CompanyEmailEnricher
from huntly.core.hn_scraper import HackerNewsScraper
from huntly.core.resume import parse_resume
from huntly.core.rss_scraper import FreeJobAggregator, RemoteOKScraper, WeWorkRemotelyScraper
from huntly.core.scraper import JobScraper
from huntly.db.models import AIAnalysis, Database, Job
from huntly.db.queries import AnalysisQueries, JobQueries, QuotaQueries


class ScrapePanelScreen(Screen):
    """Controls on-demand scraping operations and pipeline evaluation."""

    DEFAULT_CSS = """
    #form-container {
        padding: 1;
        margin: 1;
        border: solid $secondary;
        height: auto;
    }
    .form-row {
        height: auto;
        margin-bottom: 1;
    }
    .form-label {
        width: 18;
        padding-top: 1;
    }
    #scrape-log {
        height: 1fr;
        margin: 1;
        border: solid $primary;
        background: $surface;
    }
    #btn-start-scrape {
        margin-top: 1;
        width: 100%;
    }
    """

    def __init__(self, db: Database, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.settings = Settings()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            with Vertical(id="form-container"):
                yield Label("[bold cyan]🔍 Configure On-Demand Job Search[/bold cyan]")

                with Horizontal(classes="form-row"):
                    yield Label("Job Source:", classes="form-label")
                    yield Select(
                        [
                            ("LinkedIn (RapidAPI)", "linkedin"),
                            ("Hacker News Who is Hiring? (Free)", "hackernews"),
                            ("RemoteOK (Free)", "remoteok"),
                            ("WeWorkRemotely (Free)", "weworkremotely"),
                            ("All Free Sources (HN + RemoteOK + WWR)", "all_free"),
                        ],
                        value="all_free",
                        id="select-job-source",
                    )

                with Horizontal(classes="form-row"):
                    yield Label("Job Title / Role:", classes="form-label")
                    yield Input(value="Full Stack Developer", id="input-title")

                with Horizontal(classes="form-row"):
                    yield Label("Target Location:", classes="form-label")
                    yield Input(value="United States", placeholder="e.g. United States or leave blank for Global Remote", id="input-location")

                with Horizontal(classes="form-row"):
                    yield Label("Options:", classes="form-label")
                    yield Checkbox("Remote / Freelance Priority", value=True, id="check-remote")

                with Horizontal(classes="form-row"):
                    yield Label("Time Frame:", classes="form-label")
                    yield Select(
                        [("Past 24 Hours", "24h"), ("Past 7 Days", "7d")],
                        value="24h",
                        id="select-timeframe",
                    )

                with Horizontal(classes="form-row"):
                    yield Label("Jobs Count:", classes="form-label")
                    yield Input(value=str(self.settings.jobs_per_request), id="input-limit")

                yield Label(
                    f"[dim italic]Quota Cost: Free sources consume 0 API credits. LinkedIn Daily Cap: {self.settings.daily_job_limit} jobs/day.[/dim italic]"
                )
                yield Button("🚀 Start Scraping & AI Analysis", variant="success", id="btn-start-scrape")

            yield Label("[bold]Activity & Analysis Log:[/bold]")
            yield RichLog(id="scrape-log", highlight=True, markup=True)

        yield Footer()

    def on_screen_resume(self) -> None:
        self.settings = Settings()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start-scrape":
            self.run_worker(self._perform_scrape_and_analysis(), exclusive=True)

    async def _perform_scrape_and_analysis(self) -> None:
        self.settings = Settings()
        log = self.query_one("#scrape-log", RichLog)
        source = str(self.query_one("#select-job-source", Select).value)
        title = self.query_one("#input-title", Input).value.strip()
        location = self.query_one("#input-location", Input).value.strip()
        remote = self.query_one("#check-remote", Checkbox).value
        time_frame = str(self.query_one("#select-timeframe", Select).value)
        try:
            limit = int(self.query_one("#input-limit", Input).value.strip())
        except ValueError:
            limit = self.settings.jobs_per_request

        is_free_source = source in ("hackernews", "remoteok", "weworkremotely", "all_free")

        # Quota checks only apply to LinkedIn / RapidAPI
        if not is_free_source:
            daily_limit = self.settings.daily_job_limit
            scraped_today = QuotaQueries.get_daily_jobs_scraped(self.db)

            if scraped_today >= daily_limit:
                log.write(
                    f"[bold red]⛔ Daily Limit Reached: You have already scraped {scraped_today}/{daily_limit} jobs today.\n"
                    f"Switch to a Free Source (Hacker News, RemoteOK, or WeWorkRemotely) or adjust your limit in Settings (c).[/bold red]"
                )
                self.notify(f"Daily limit reached: {scraped_today}/{daily_limit} jobs used today!", severity="warning")
                return

            remaining_today = daily_limit - scraped_today
            if limit > remaining_today:
                log.write(
                    f"[yellow]⚡ Daily Cap: Adjusting batch from {limit} to {remaining_today} jobs "
                    f"(Limit: {daily_limit}/day | Used today: {scraped_today}).[/yellow]"
                )
                limit = remaining_today

        log.write(f"[bold cyan]Initiating search:[/bold cyan] source='{source.upper()}', title='{title}', limit={limit}")

        raw_jobs = []
        if source == "linkedin":
            api_key = self.settings.rapidapi_key
            if not api_key:
                log.write("[bold red]Error: RAPIDAPI_KEY is not set. Go to Settings (c) to configure it or select a Free Source.[/bold red]")
                self.notify("RAPIDAPI_KEY missing", severity="error")
                return
            scraper = JobScraper(api_key=api_key)
            raw_jobs = await scraper.search_jobs(
                title=title,
                location=location,
                remote=remote,
                limit=limit,
                time_frame=time_frame,
            )
            QuotaQueries.log_request(
                self.db,
                endpoint="/active-jb",
                jobs_returned=len(raw_jobs),
                credits_used=len(raw_jobs),
            )
        elif source == "hackernews":
            log.write("[yellow]Fetching monthly 'Ask HN: Who is hiring?' postings (Free public Algolia API)...[/yellow]")
            hn_scraper = HackerNewsScraper()
            raw_jobs = await hn_scraper.search_jobs(query=title, limit=limit, remote_only=remote)
        elif source == "remoteok":
            log.write("[cyan]Fetching RemoteOK public jobs API (Free)...[/cyan]")
            ro_scraper = RemoteOKScraper()
            raw_jobs = await ro_scraper.search_jobs(query=title, limit=limit, remote_only=remote)
        elif source == "weworkremotely":
            log.write("[magenta]Fetching WeWorkRemotely programming RSS feeds (Free)...[/magenta]")
            wwr_scraper = WeWorkRemotelyScraper()
            raw_jobs = await wwr_scraper.search_jobs(query=title, limit=limit, remote_only=remote)
        elif source == "all_free":
            log.write("[green]Concurrently aggregating from Hacker News, RemoteOK, and WeWorkRemotely (Free)...[/green]")
            aggregator = FreeJobAggregator()
            per_src = max(2, limit // 3)
            raw_jobs = await aggregator.search_all_free_sources(query=title, limit_per_source=per_src, remote_only=remote)

        log.write(f"Scraper returned [bold green]{len(raw_jobs)}[/bold green] raw listings.")

        if not raw_jobs:
            log.write("[yellow]No listings found matching criteria.[/yellow]")
            return

        # 2. Dedup
        new_jobs = get_new_jobs(raw_jobs, self.db)
        log.write(f"[bold]{len(new_jobs)}[/bold] novel listings after deduplication.")

        # 3. AI Analyzer Setup
        resume_text = parse_resume(self.settings.resume_path)
        analyzer = JobAnalyzer(
            api_key=self.settings.ai_api_key,
            resume_text=resume_text,
            model=self.settings.ai_model,
            base_url=self.settings.ai_base_url,
        )

        # 3b. Company Email Enricher Setup
        enricher = CompanyEmailEnricher(settings=self.settings)

        # 4. Save, Enrich and Analyze
        for idx, job_data in enumerate(new_jobs, 1):
            job_obj = Job(**job_data)
            JobQueries.insert_job(self.db, job_obj)
            log.write(f"[{idx}/{len(new_jobs)}] Stored: [cyan]{job_obj.title}[/cyan] at {job_obj.company}")

            # Contact email enrichment via web browsing & Nemotron tool
            if not job_obj.contact_email:
                log.write(f"   🔍 Web browsing company site & Nemotron tool for HR contact...")
                try:
                    enrich_info = await enricher.enrich_job_contact(job_data)
                    found_email = enrich_info.get("email")
                    if found_email:
                        JobQueries.update_contact_email(self.db, job_obj.id, found_email)
                        job_obj.contact_email = found_email
                        job_data["contact_email"] = found_email
                        method_label = enrich_info.get("method", "Web Tool")
                        log.write(f"   📬 HR Contact Found: [bold cyan]{found_email}[/bold cyan] ({method_label})")
                    else:
                        log.write("   ℹ️ No direct email published on site.")
                except Exception as enrich_err:
                    log.write(f"   [dim]Enrichment note: {enrich_err}[/dim]")
            else:
                log.write(f"   📬 Contact Email: [bold cyan]{job_obj.contact_email}[/bold cyan]")

            # AI reasoning
            log.write(f"   Analyzing with Nemotron AI ({self.settings.ai_model})...")
            analysis_data = await analyzer.analyze_job(job_data)

            ai_obj = AIAnalysis(
                job_id=job_obj.id,
                match_score=analysis_data.get("match_score", 0.0),
                category=analysis_data.get("category", "General"),
                summary=analysis_data.get("summary", ""),
                key_skills=json.dumps(analysis_data.get("key_skills", [])),
                missing_skills=json.dumps(analysis_data.get("missing_skills", [])),
                salary_estimate=analysis_data.get("salary_estimate", ""),
                red_flags=json.dumps(analysis_data.get("red_flags", [])),
                learning_suggestions=json.dumps(analysis_data.get("learning_suggestions", [])),
            )
            AnalysisQueries.save_analysis(self.db, ai_obj)

            score = ai_obj.match_score
            color = "green" if score >= 80 else ("yellow" if score >= 50 else "red")
            log.write(f"   Match Score: [{color}]{score:.1f}%[/{color}] | Category: {ai_obj.category}")

        log.write("[bold green]✅ Scraping & AI evaluation completed successfully![/bold green]")
        self.notify("Scrape & analysis complete!")

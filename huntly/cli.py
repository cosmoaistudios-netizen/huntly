from __future__ import annotations
"""Command-line interface for Huntly."""

import click
from rich.console import Console
from rich.table import Table

from huntly.config.settings import Settings
from huntly.core.resume import extract_skills, parse_resume
from huntly.db.models import Database
from huntly.db.queries import AnalysisQueries, ApplicationQueries, JobQueries, QuotaQueries

console = Console()


@click.group()
def cli() -> None:
    """🎯 Huntly - AI-Powered Job Hunting Terminal Assistant."""
    pass


@cli.command()
@click.option("--demo", is_flag=True, help="Launch in offline demo sandbox mode with pre-loaded postings")
def ui(demo: bool) -> None:
    """Launch the interactive terminal user interface."""
    from huntly.app import HuntlyApp
    from huntly.widgets.banner import print_launch_banner
    print_launch_banner(console)
    if demo:
        from huntly.core.demo_data import load_demo_fixtures
        settings = Settings()
        db = Database(settings.db_path)
        load_demo_fixtures(db)
    app = HuntlyApp()
    app.run()


@cli.command()
def demo() -> None:
    """Zero-key offline demo mode: explore full UI with pre-evaluated startup roles."""
    from huntly.app import HuntlyApp
    from huntly.core.demo_data import load_demo_fixtures
    from huntly.widgets.banner import print_launch_banner
    print_launch_banner(console)
    settings = Settings()
    db = Database(settings.db_path)
    load_demo_fixtures(db)
    app = HuntlyApp()
    app.run()


@cli.command()
def status() -> None:
    """Display system status, API quota remaining, and job statistics."""
    from huntly.widgets.banner import print_launch_banner
    print_launch_banner(console)
    settings = Settings()
    db = Database(settings.db_path)

    usage = QuotaQueries.get_monthly_usage(
        db,
        requests_limit=settings.monthly_requests_limit,
        jobs_limit=settings.monthly_jobs_limit,
    )
    job_count = JobQueries.count_jobs(db)
    pipe = ApplicationQueries.get_pipeline_counts(db)

    table = Table(title="Huntly System & Quota Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")

    today_used = QuotaQueries.get_daily_jobs_scraped(db)
    table.add_row("Total Jobs Indexed", str(job_count))
    table.add_row("Today's Jobs Scraped", f"{today_used} / {settings.daily_job_limit} (Daily Cap)")
    table.add_row("Monthly Requests Used", f"{usage['requests_used']} / {usage['requests_limit']}")
    table.add_row("Monthly Job Credits Used", f"{usage['jobs_used']} / {usage['jobs_limit']}")
    table.add_row(
        "Application Pipeline",
        f"Saved: {pipe['saved']} | Applied: {pipe['applied']} | Int: {pipe['interviewing']} | Offers: {pipe['offered']}",
    )
    table.add_row("Database Path", str(settings.db_path))
    table.add_row("Resume Path", str(settings.resume_path))
    table.add_row("Nemotron Model", settings.ai_model)

    console.print(table)


@cli.command()
@click.option("--limit", "-l", default=10, help="Number of top matches to display")
def top(limit: int) -> None:
    """List the highest scoring job opportunities."""
    settings = Settings()
    db = Database(settings.db_path)
    matches = AnalysisQueries.get_top_matches(db, limit=limit)

    if not matches:
        console.print("[yellow]No evaluated jobs found in database. Run 'huntly ui' to scrape jobs.[/yellow]")
        return

    table = Table(title=f"Top {limit} Matching Opportunities")
    table.add_column("ID", style="dim")
    table.add_column("Job Title", style="cyan")
    table.add_column("Company", style="white")
    table.add_column("Location", style="dim")
    table.add_column("Fit Score", justify="right")
    table.add_column("Category", style="magenta")

    for job, analysis in matches:
        score = analysis.match_score
        color = "green" if score >= 80 else ("yellow" if score >= 50 else "red")
        table.add_row(
            job.id,
            job.title,
            job.company or "N/A",
            job.location or "Remote",
            f"[{color}]{score:.1f}%[/{color}]",
            analysis.category,
        )

    console.print(table)


@cli.command()
def resume() -> None:
    """Parse configured resume and inspect extracted technical competencies."""
    settings = Settings()
    path = settings.resume_path
    console.print(f"Reading resume from: [cyan]{path}[/cyan]")
    text = parse_resume(path)

    if not text:
        console.print(f"[bold red]Could not parse resume at {path}. Please verify the file exists.[/bold red]")
        return

    skills = extract_skills(text)
    console.print(f"[green]Successfully parsed {len(text)} characters.[/green]")
    console.print(f"[bold]Detected Skills ({len(skills)}):[/bold] {', '.join(skills)}")


@cli.command()
@click.option("--limit", "-l", default=5, help="Number of jobs to enrich")
def enrich(limit: int) -> None:
    """Find and enrich HR / contact emails for indexed jobs using web browsing and Nemotron."""
    import asyncio
    from huntly.core.enricher import CompanyEmailEnricher, enrich_single_job

    settings = Settings()
    db = Database(settings.db_path)
    jobs = JobQueries.list_jobs(db, limit=limit)

    console.print(f"[bold cyan]🔍 Enriching contact emails for up to {limit} jobs...[/bold cyan]")
    enricher = CompanyEmailEnricher(settings)

    async def _run():
        enriched_count = 0
        for j in jobs:
            if j.contact_email:
                console.print(f"• [dim]{j.company}: Already has email ({j.contact_email})[/dim]")
                continue
            console.print(f"• Searching HR contact for [bold]{j.company}[/bold]...")
            email = await enrich_single_job(db, j, enricher)
            if email:
                console.print(f"  [green]✓ Found:[/green] [bold cyan]{email}[/bold cyan]")
                enriched_count += 1
            else:
                console.print(f"  [yellow]✗ No direct email published on site.[/yellow]")
        console.print(f"\n[bold green]Enrichment complete. {enriched_count} new emails discovered and saved.[/bold green]")

    asyncio.run(_run())


@cli.command()
@click.option("--source", "-s", default="all_free", type=click.Choice(["all_free", "hn", "remoteok", "wwr", "linkedin"]), help="Job source to query")
@click.option("--query", "-q", default="developer", help="Search keyword or role")
@click.option("--limit", "-l", default=10, help="Number of listings to scrape")
def scrape(source: str, query: str, limit: int) -> None:
    """Scrape listings directly from CLI using free sources or LinkedIn."""
    import asyncio
    from huntly.core.hn_scraper import HackerNewsScraper
    from huntly.core.rss_scraper import FreeJobAggregator, RemoteOKScraper, WeWorkRemotelyScraper
    from huntly.core.scraper import JobScraper
    from huntly.core.dedup import get_new_jobs
    from huntly.db.models import Job

    settings = Settings()
    db = Database(settings.db_path)

    console.print(f"[bold cyan]🔍 Scraping up to {limit} jobs from {source.upper()} for '{query}'...[/bold cyan]")

    async def _run():
        raw_jobs = []
        if source == "hn":
            raw_jobs = await HackerNewsScraper().search_jobs(query=query, limit=limit)
        elif source == "remoteok":
            raw_jobs = await RemoteOKScraper().search_jobs(query=query, limit=limit)
        elif source == "wwr":
            raw_jobs = await WeWorkRemotelyScraper().search_jobs(query=query, limit=limit)
        elif source == "all_free":
            raw_jobs = await FreeJobAggregator().search_all_free_sources(query=query, limit_per_source=max(2, limit // 3))
        elif source == "linkedin":
            if not settings.rapidapi_key:
                console.print("[bold red]RAPIDAPI_KEY is not set in environment or Settings.[/bold red]")
                return
            raw_jobs = await JobScraper(api_key=settings.rapidapi_key).search_jobs(title=query, limit=limit)

        console.print(f"Retrieved [bold green]{len(raw_jobs)}[/bold green] raw postings.")
        new_jobs = get_new_jobs(raw_jobs, db)
        console.print(f"Discovered [bold]{len(new_jobs)}[/bold] novel listings after deduplication.")

        for j_data in new_jobs:
            j_obj = Job(**j_data)
            JobQueries.insert_job(db, j_obj)
            console.print(f"  ✓ Saved: [cyan]{j_obj.title}[/cyan] @ [white]{j_obj.company}[/white] ({j_obj.source})")

        console.print(f"\n[bold green]Scrape complete! Stored {len(new_jobs)} new listings in database.[/bold green]")

    asyncio.run(_run())


@cli.command()
@click.option("--limit", "-l", default=5, help="Number of un-evaluated jobs to analyze")
def analyze(limit: int) -> None:
    """Run AI synthesis and fit evaluation on un-analyzed jobs in database."""
    import asyncio
    import json
    from huntly.core.analyzer import JobAnalyzer
    from huntly.core.resume import parse_resume
    from huntly.db.models import AIAnalysis

    settings = Settings()
    db = Database(settings.db_path)
    jobs_with_analysis = AnalysisQueries.get_jobs_with_analysis(db, limit=100, date_filter="all")

    # Find jobs that haven't been analyzed or had fallback errors
    pending_jobs = [
        j for j, a in jobs_with_analysis 
        if a is None or (a.summary and "analysis completed with fallback note" in a.summary)
    ][:limit]

    if not pending_jobs:
        console.print("[green]All jobs currently have valid AI synthesis! No pending jobs to analyze.[/green]")
        return

    console.print(f"[bold cyan]🤖 Running AI synthesis on {len(pending_jobs)} jobs using {settings.ai_provider.upper()} ({settings.ai_model})...[/bold cyan]")
    resume_text = parse_resume(settings.resume_path)
    analyzer = JobAnalyzer(
        api_key=settings.ai_api_key,
        resume_text=resume_text,
        model=settings.ai_model,
        base_url=settings.ai_base_url,
    )

    async def _run():
        for idx, j in enumerate(pending_jobs, 1):
            console.print(f"[{idx}/{len(pending_jobs)}] Analyzing: [bold]{j.title}[/bold] @ [white]{j.company}[/white]...")
            job_dict = {
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "description_text": j.description_text,
                "contact_email": j.contact_email,
            }
            data = await analyzer.analyze_job(job_dict)
            ai_obj = AIAnalysis(
                job_id=j.id,
                match_score=data.get("match_score", 0.0),
                category=data.get("category", "General"),
                summary=data.get("summary", ""),
                key_skills=json.dumps(data.get("key_skills", [])),
                missing_skills=json.dumps(data.get("missing_skills", [])),
                salary_estimate=data.get("salary_estimate", ""),
                red_flags=json.dumps(data.get("red_flags", [])),
                learning_suggestions=json.dumps(data.get("learning_suggestions", [])),
            )
            AnalysisQueries.save_analysis(db, ai_obj)
            score = ai_obj.match_score
            color = "green" if score >= 80 else ("yellow" if score >= 50 else "red")
            console.print(f"  → Fit Score: [{color}]{score:.1f}%[/{color}] | Category: {ai_obj.category}")
            console.print(f"  → Synthesis: [dim]{ai_obj.summary[:120]}...[/dim]")

        console.print(f"\n[bold green]AI synthesis complete! Evaluated {len(pending_jobs)} jobs.[/bold green]")

    asyncio.run(_run())


if __name__ == "__main__":
    cli()

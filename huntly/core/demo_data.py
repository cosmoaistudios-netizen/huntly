from __future__ import annotations
"""Demo fixture generator for zero-key evaluation of Huntly."""

import json
from huntly.db.models import AIAnalysis, Database, Job
from huntly.db.queries import AnalysisQueries, ApplicationQueries, JobQueries

DEMO_JOBS = [
    {
        "id": "demo-001",
        "title": "Senior Full-Stack AI Engineer (Remote)",
        "company": "NexusAI Labs (Berlin)",
        "location": "Remote (US / EU / India friendly)",
        "remote_type": "remote",
        "salary_min": 65.0,
        "salary_max": 95.0,
        "salary_currency": "EUR/hr",
        "posted_date": "2 hours ago",
        "contact_email": "careers@nexusailabs.eu",
        "apply_url": "https://nexusailabs.eu/careers/full-stack-ai",
        "description_text": """
# Senior Full-Stack AI Engineer (Remote Freelance / Contract)

**About NexusAI Labs:**
NexusAI Labs is a fast-growing European AI startup building autonomous agentic workflows and developer toolkits. We operate 100% remotely across Europe and global timezones.

### Role Overview:
We are seeking an experienced Full-Stack Engineer with deep experience in Python, FastAPI, React/Next.js, and LLM integrations (Nemotron, OpenAI API, LangChain). You will design high-throughput agent systems, real-time streaming dashboards, and clean REST APIs.

### Responsibilities:
- Build reactive frontends with React 19, TypeScript, and Tailwind CSS.
- Architect asynchronous microservices using Python 3.11+, FastAPI, and PostgreSQL.
- Integrate frontier language models with streaming completions and tool calling.
- Collaborate asynchronously with founders and product engineers.

### Requirements:
- 4+ years of professional software engineering experience.
- Strong proficiency in modern Python (asyncio, Pydantic, HTTPX).
- Solid frontend fundamentals (React, TypeScript, state management).
- Experience shipping real-world LLM or autonomous agent applications.
- Excellent written English and asynchronous communication skills.

### Perks & Compensation:
- Competitive hourly freelance rate (€65 - €95/hour).
- Flexible hours and 100% remote work.
- Annual learning & hardware stipend.
        """,
        "analysis": {
            "match_score": 94.5,
            "category": "Fullstack / AI",
            "summary": "Exceptional fit. The role emphasizes modern asynchronous Python, FastAPI, and React/Next.js alongside agentic LLM integration—aligning directly with candidate strengths.",
            "key_skills": ["Python", "FastAPI", "React", "TypeScript", "LLM APIs", "AsyncIO"],
            "missing_skills": ["LangChain"],
            "salary_estimate": "€65 - €95 / hr (~$130k - $190k annualized)",
            "red_flags": [],
            "learning_suggestions": ["Review LangChain expression language (LCEL) patterns"],
        },
    },
    {
        "id": "demo-002",
        "title": "Lead Python Backend & Agent Architect",
        "company": "Synthetix Dynamics (San Francisco)",
        "location": "Remote (Global)",
        "remote_type": "remote",
        "salary_min": 140000.0,
        "salary_max": 180000.0,
        "salary_currency": "USD",
        "posted_date": "5 hours ago",
        "contact_email": "talent@synthetixdynamics.ai",
        "apply_url": "https://synthetixdynamics.ai/jobs/lead-python",
        "description_text": """
# Lead Python Backend & Agent Architect (Contract-to-Hire)

Synthetix Dynamics is building next-generation agent orchestration runtimes for enterprise clients in North America.

### Responsibilities:
- Lead the backend core architecture using Python, Redis, and SQLite/PostgreSQL.
- Implement robust rate-limiting, token consumption meters, and background task queues.
- Optimize LLM prompt reasoning and multi-modal tool calling.

### Requirements:
- 5+ years backend Python development.
- Proven experience with distributed systems and async architectures.
- Experience with frontier open weights models (Nemotron, Llama 3, Mistral).
        """,
        "analysis": {
            "match_score": 88.0,
            "category": "Backend / Systems",
            "summary": "High alignment for backend systems engineering and Python async pipelines. Role requires distributed systems maturity.",
            "key_skills": ["Python", "AsyncIO", "Redis", "PostgreSQL", "Prompt Engineering"],
            "missing_skills": ["Distributed consensus / Raft"],
            "salary_estimate": "$140,000 - $180,000 / year",
            "red_flags": ["Contract-to-hire arrangement may require initial 3-month trial"],
            "learning_suggestions": ["Brush up on distributed task scheduling and Celery / temporal.io"],
        },
    },
    {
        "id": "demo-003",
        "title": "React & Terminal UI Design Engineer",
        "company": "HyperConsole (London)",
        "location": "Remote (EU/US/India)",
        "remote_type": "remote",
        "salary_min": 50.0,
        "salary_max": 75.0,
        "salary_currency": "GBP/hr",
        "posted_date": "1 day ago",
        "contact_email": "hiring@hyperconsole.dev",
        "apply_url": "https://hyperconsole.dev/careers",
        "description_text": """
# React & Terminal UI Design Engineer (Freelance)

HyperConsole builds developer tooling and terminal workspaces. We are looking for a UI specialist who loves craft, keyboards, and beautiful terminal experiences.
        """,
        "analysis": {
            "match_score": 82.0,
            "category": "Frontend / TUI",
            "summary": "Strong match for frontend and developer tooling UI. Strong alignment with Textual, Rich, and React design patterns.",
            "key_skills": ["React", "CSS", "UI Craft", "Keyboard Navigation", "Rich/Textual"],
            "missing_skills": ["Rust TUI frameworks (Ratatui)"],
            "salary_estimate": "£50 - £75 / hr",
            "red_flags": [],
            "learning_suggestions": ["Explore Rust-based terminal primitives for cross-language insight"],
        },
    },
]


def load_demo_fixtures(db: Database) -> int:
    """Populates database with rich demo postings and analysis for instant evaluation."""
    count = 0
    for item in DEMO_JOBS:
        if JobQueries.job_exists(db, item["id"]):
            continue

        job = Job(
            id=item["id"],
            title=item["title"],
            company=item["company"],
            location=item["location"],
            remote_type=item["remote_type"],
            salary_min=item["salary_min"],
            salary_max=item["salary_max"],
            salary_currency=item["salary_currency"],
            posted_date=item["posted_date"],
            contact_email=item["contact_email"],
            apply_url=item["apply_url"],
            description_text=item["description_text"],
        )
        JobQueries.insert_job(db, job)

        ana = item["analysis"]
        analysis = AIAnalysis(
            job_id=job.id,
            match_score=ana["match_score"],
            category=ana["category"],
            summary=ana["summary"],
            key_skills=json.dumps(ana["key_skills"]),
            missing_skills=json.dumps(ana["missing_skills"]),
            salary_estimate=ana["salary_estimate"],
            red_flags=json.dumps(ana["red_flags"]),
            learning_suggestions=json.dumps(ana["learning_suggestions"]),
        )
        AnalysisQueries.save_analysis(db, analysis)
        count += 1

    # Add a sample application tracker state
    if count > 0:
        ApplicationQueries.create_application(db, job_id="demo-001", status="applied")
        ApplicationQueries.create_application(db, job_id="demo-002", status="saved")

    return count

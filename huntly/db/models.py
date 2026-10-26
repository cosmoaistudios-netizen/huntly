from __future__ import annotations
"""Database models, dataclasses, and SQLite connection manager for Huntly."""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator, Optional


@dataclass
class Job:
    """Represents a scraped job listing."""
    id: str
    title: str
    company: Optional[str] = None
    company_industry: Optional[str] = None
    company_size: Optional[str] = None
    company_description: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None
    description_text: Optional[str] = None
    description_html: Optional[str] = None
    posted_date: Optional[str] = None
    apply_url: Optional[str] = None
    contact_email: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    scraped_at: Optional[str] = None
    search_query: Optional[str] = None
    raw_json: Optional[str] = None
    source: str = "linkedin"


@dataclass
class AIAnalysis:
    """Represents Nemotron AI analysis of a job."""
    job_id: str
    match_score: float = 0.0
    category: str = "General"
    summary: str = ""
    key_skills: str = "[]"  # JSON string
    missing_skills: str = "[]"  # JSON string
    salary_estimate: str = ""
    red_flags: str = "[]"  # JSON string
    learning_suggestions: str = "[]"  # JSON string
    cover_letter: Optional[str] = None
    outreach_email: Optional[str] = None
    analyzed_at: Optional[str] = None


@dataclass
class Application:
    """Tracks application status for a job."""
    id: Optional[int] = None
    job_id: str = ""
    status: str = "saved"  # saved | applied | interviewing | rejected | offered
    applied_date: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class SearchPreset:
    """Saved search preset for fast querying."""
    name: str
    id: Optional[int] = None
    title_query: Optional[str] = None
    location: Optional[str] = None
    remote_filter: Optional[str] = None
    time_frame: str = "24h"
    created_at: Optional[str] = None


@dataclass
class QuotaEntry:
    """Tracks RapidAPI usage to stay within monthly limits."""
    id: Optional[int] = None
    request_date: Optional[str] = None
    endpoint: str = ""
    jobs_returned: int = 0
    credits_used: int = 0


class Database:
    """SQLite database manager for Huntly."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def session(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Create database tables and required indexes."""
        with self.session() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT,
                    company_industry TEXT,
                    company_size TEXT,
                    company_description TEXT,
                    location TEXT,
                    remote_type TEXT,
                    description_text TEXT,
                    description_html TEXT,
                    posted_date TEXT,
                    apply_url TEXT,
                    contact_email TEXT,
                    salary_min REAL,
                    salary_max REAL,
                    salary_currency TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    search_query TEXT,
                    raw_json TEXT,
                    source TEXT DEFAULT 'linkedin'
                );

                CREATE TABLE IF NOT EXISTS ai_analysis (
                    job_id TEXT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
                    match_score REAL DEFAULT 0.0,
                    category TEXT DEFAULT 'General',
                    summary TEXT DEFAULT '',
                    key_skills TEXT DEFAULT '[]',
                    missing_skills TEXT DEFAULT '[]',
                    salary_estimate TEXT DEFAULT '',
                    red_flags TEXT DEFAULT '[]',
                    learning_suggestions TEXT DEFAULT '[]',
                    cover_letter TEXT,
                    outreach_email TEXT,
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
                    status TEXT DEFAULT 'saved',
                    applied_date TEXT,
                    notes TEXT,
                    follow_up_date TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS search_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    title_query TEXT,
                    location TEXT,
                    remote_filter TEXT,
                    time_frame TEXT DEFAULT '24h',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS quota_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    endpoint TEXT NOT NULL,
                    jobs_returned INTEGER DEFAULT 0,
                    credits_used INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS digests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    week_start TEXT NOT NULL,
                    week_end TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    top_job_ids TEXT DEFAULT '[]',
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at ON jobs(scraped_at DESC);
                CREATE INDEX IF NOT EXISTS idx_jobs_contact_email ON jobs(contact_email);
                CREATE INDEX IF NOT EXISTS idx_analysis_match_score ON ai_analysis(match_score DESC);
                CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status);
                """
            )
            # Schema migration check for existing databases
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(jobs)")
            cols = [row[1] for row in cursor.fetchall()]
            if "source" not in cols and cols:
                cursor.execute("ALTER TABLE jobs ADD COLUMN source TEXT DEFAULT 'linkedin'")

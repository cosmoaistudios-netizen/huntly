from __future__ import annotations
"""Deduplication utilities to prevent redundant processing and quota consumption."""

import re
from typing import Any, Dict, List
from huntly.db.models import Database
from huntly.db.queries import JobQueries


def is_duplicate(db: Database, job_id: str) -> bool:
    """Verifies whether a job ID is already persisted in the database."""
    return JobQueries.job_exists(db, job_id)


def find_similar(db: Database, title: str, company: str) -> List[str]:
    """Finds existing jobs with similar title and company."""
    clean_title = re.sub(r"[^\w\s]", "", title).strip().lower()
    clean_company = re.sub(r"[^\w\s]", "", company or "").strip().lower()

    matches: List[str] = []
    with db.session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, company FROM jobs")
        for row in cur.fetchall():
            db_title = re.sub(r"[^\w\s]", "", row["title"]).strip().lower()
            db_company = re.sub(r"[^\w\s]", "", row["company"] or "").strip().lower()
            if clean_title == db_title and clean_company == db_company:
                matches.append(row["id"])
    return matches


def get_new_jobs(jobs: List[Dict[str, Any]], db: Database) -> List[Dict[str, Any]]:
    """Filters incoming job dictionaries to retain only novel listings."""
    new_jobs: List[Dict[str, Any]] = []
    for j in jobs:
        jid = str(j.get("id") or j.get("job_id") or "")
        if jid and not is_duplicate(db, jid):
            new_jobs.append(j)
    return new_jobs

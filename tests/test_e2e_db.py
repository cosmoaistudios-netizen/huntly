from __future__ import annotations
import tempfile
from pathlib import Path
import pytest

from huntly.db.models import Database, Job, AIAnalysis, Application
from huntly.db.queries import JobQueries, AnalysisQueries, ApplicationQueries, QuotaQueries


def test_clean_db_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_huntly.db")
        db = Database(db_path)
        db.initialize()

        # 1. Insert jobs from different sources
        job_hn = Job(
            id="hn-test-01",
            title="Senior Python Backend Engineer",
            company="Tech Corp",
            location="Remote",
            remote_type="remote",
            description_text="FastAPI, PostgreSQL, Redis",
            posted_date="2026-10-21",
            source="hackernews",
        )
        job_rok = Job(
            id="rok-test-02",
            title="Staff React Engineer",
            company="Modern Web",
            location="Remote",
            remote_type="remote",
            description_text="React, TypeScript, Next.js",
            posted_date="2026-10-20",
            source="remoteok",
        )

        assert JobQueries.insert_job(db, job_hn) is True
        assert JobQueries.insert_job(db, job_rok) is True

        # Test duplicate detection
        from huntly.core.dedup import is_duplicate, get_new_jobs
        assert is_duplicate(db, "hn-test-01") is True
        assert is_duplicate(db, "novel-id") is False
        assert JobQueries.count_jobs(db) == 2

        batch = [
            {"id": "hn-test-01", "title": "Senior Python Backend Engineer"},
            {"id": "brand-new-id", "title": "DevOps Engineer"},
        ]
        new_jobs = get_new_jobs(batch, db)
        assert len(new_jobs) == 1
        assert new_jobs[0]["id"] == "brand-new-id"

        # 2. Test AI analysis storage & retrieval
        analysis = AIAnalysis(
            job_id="hn-test-01",
            match_score=85.0,
            category="Backend",
            summary="Strong candidate match for FastAPI.",
            key_skills='["FastAPI", "PostgreSQL"]',
            missing_skills='["Redis"]',
            salary_estimate="$120,000",
        )
        assert AnalysisQueries.save_analysis(db, analysis) is True

        retrieved_analysis = AnalysisQueries.get_analysis(db, "hn-test-01")
        assert retrieved_analysis is not None
        assert retrieved_analysis.match_score == 85.0
        assert retrieved_analysis.category == "Backend"

        # 3. Test filtering by source & date
        all_jobs = AnalysisQueries.get_jobs_with_analysis(db, source_filter="hackernews")
        assert len(all_jobs) == 1
        assert all_jobs[0][0].id == "hn-test-01"

        rok_jobs = AnalysisQueries.get_jobs_with_analysis(db, source_filter="remoteok")
        assert len(rok_jobs) == 1
        assert rok_jobs[0][0].id == "rok-test-02"

        # 4. Test pipeline application tracking
        app_id = ApplicationQueries.create_application(db, "hn-test-01", status="saved")
        assert app_id > 0
        assert ApplicationQueries.update_status(db, app_id, "applied") is True

        counts = ApplicationQueries.get_pipeline_counts(db)
        assert counts["applied"] == 1
        assert counts["saved"] == 0

        # 5. Test quota tracking
        QuotaQueries.log_request(db, endpoint="search", jobs_returned=10, credits_used=10)
        usage = QuotaQueries.get_monthly_usage(db)
        assert usage["requests_used"] == 1
        assert usage["jobs_used"] == 10

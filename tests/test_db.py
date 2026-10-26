from __future__ import annotations
import tempfile
from pathlib import Path
from huntly.db.models import AIAnalysis, Database, Job
from huntly.db.queries import AnalysisQueries, ApplicationQueries, JobQueries, QuotaQueries


def test_database_initialization():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        assert db_path.exists()
        assert JobQueries.count_jobs(db) == 0


def test_job_insert_and_retrieve():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(str(Path(tmpdir) / "test.db"))
        job = Job(
            id="job-101",
            title="Senior AI Engineer",
            company="TestOrg",
            location="Remote",
            contact_email="careers@testorg.com",
        )
        assert JobQueries.insert_job(db, job) is True
        assert JobQueries.job_exists(db, "job-101") is True

        retrieved = JobQueries.get_job(db, "job-101")
        assert retrieved is not None
        assert retrieved.title == "Senior AI Engineer"
        assert retrieved.contact_email == "careers@testorg.com"


def test_update_contact_email():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(str(Path(tmpdir) / "test.db"))
        job = Job(id="job-102", title="Full Stack Dev", company="StartupX")
        JobQueries.insert_job(db, job)

        assert JobQueries.update_contact_email(db, "job-102", "talent@startupx.com") is True
        updated = JobQueries.get_job(db, "job-102")
        assert updated is not None
        assert updated.contact_email == "talent@startupx.com"


def test_quota_logging_and_monthly_usage():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(str(Path(tmpdir) / "test.db"))
        QuotaQueries.log_request(db, endpoint="/active-jb", jobs_returned=10, credits_used=10)
        QuotaQueries.log_request(db, endpoint="/active-jb", jobs_returned=5, credits_used=5)

        usage = QuotaQueries.get_monthly_usage(db, requests_limit=50, jobs_limit=500)
        assert usage["requests_used"] == 2
        assert usage["jobs_used"] == 15
        assert usage["requests_limit"] == 50
        assert usage["jobs_limit"] == 500
        assert QuotaQueries.get_daily_jobs_scraped(db) == 15

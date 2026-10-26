from __future__ import annotations
import tempfile
from pathlib import Path
from huntly.db.models import Database, Job
from huntly.db.queries import JobQueries
from huntly.core.dedup import get_new_jobs, is_duplicate


def test_deduplication():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(str(Path(tmpdir) / "test.db"))
        job = Job(id="job-existing", title="Dev", company="CompA")
        JobQueries.insert_job(db, job)

        assert is_duplicate(db, "job-existing") is True
        assert is_duplicate(db, "job-novel") is False

        batch = [
            {"id": "job-existing", "title": "Dev", "company": "CompA"},
            {"id": "job-novel", "title": "Dev 2", "company": "CompB"},
        ]
        new_jobs = get_new_jobs(batch, db)
        assert len(new_jobs) == 1
        assert new_jobs[0]["id"] == "job-novel"

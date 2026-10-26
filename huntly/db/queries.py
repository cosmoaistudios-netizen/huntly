from __future__ import annotations
"""Query abstractions for Jobs, AI Analysis, Applications, and Quota logging."""

import json
from typing import Any, Dict, List, Optional, Tuple, Union
from huntly.db.models import AIAnalysis, Application, Database, Job, QuotaEntry, SearchPreset


class JobQueries:
    """Operations for persisting and retrieving job records."""

    @staticmethod
    def row_to_job(row: Any) -> Job:
        def _get(key: str, default: Any = None) -> Any:
            try:
                v = row[key]
                return v if v is not None else default
            except Exception:
                return default

        return Job(
            id=str(_get("id", "")),
            title=str(_get("title", "Untitled Position")),
            company=_get("company"),
            company_industry=_get("company_industry"),
            company_size=_get("company_size"),
            company_description=_get("company_description"),
            location=_get("location"),
            remote_type=_get("remote_type"),
            description_text=_get("description_text"),
            description_html=_get("description_html"),
            posted_date=_get("posted_date"),
            apply_url=_get("apply_url"),
            contact_email=_get("contact_email"),
            salary_min=_get("salary_min"),
            salary_max=_get("salary_max"),
            salary_currency=_get("salary_currency"),
            scraped_at=_get("scraped_at"),
            search_query=_get("search_query"),
            raw_json=_get("raw_json"),
            source=str(_get("source", "linkedin")),
        )

    @staticmethod
    def insert_job(db: Database, job: Job) -> bool:
        query = """
        INSERT INTO jobs (
            id, title, company, company_industry, company_size, company_description,
            location, remote_type, description_text, description_html, posted_date,
            apply_url, contact_email, salary_min, salary_max, salary_currency,
            search_query, raw_json, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            apply_url = excluded.apply_url,
            contact_email = COALESCE(excluded.contact_email, jobs.contact_email),
            raw_json = excluded.raw_json,
            source = COALESCE(excluded.source, jobs.source);
        """
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(
                query,
                (
                    job.id,
                    job.title,
                    job.company,
                    job.company_industry,
                    job.company_size,
                    job.company_description,
                    job.location,
                    job.remote_type,
                    job.description_text,
                    job.description_html,
                    job.posted_date,
                    job.apply_url,
                    job.contact_email,
                    job.salary_min,
                    job.salary_max,
                    job.salary_currency,
                    job.search_query,
                    job.raw_json,
                    job.source,
                ),
            )
            return cur.rowcount > 0

    @staticmethod
    def get_job(db: Database, job_id: str) -> Optional[Job]:
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cur.fetchone()
            return JobQueries.row_to_job(row) if row else None

    @staticmethod
    def job_exists(db: Database, job_id: str) -> bool:
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,))
            return cur.fetchone() is not None

    @staticmethod
    def update_contact_email(db: Database, job_id: str, email: str) -> bool:
        """Updates the contact email for an existing job posting."""
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE jobs SET contact_email = ? WHERE id = ?", (email, job_id))
            return cur.rowcount > 0

    @staticmethod
    def count_jobs(db: Database) -> int:
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM jobs")
            return int(cur.fetchone()[0])

    @staticmethod
    def list_jobs(
        db: Database,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "scraped_at",
        order: str = "DESC",
        category: Optional[str] = None,
        min_match: Optional[float] = None,
        has_email: bool = False,
    ) -> List[Job]:
        conditions = ["1=1"]
        params: List[Any] = []

        if has_email:
            conditions.append("jobs.contact_email IS NOT NULL AND jobs.contact_email != ''")

        if category:
            conditions.append("ai_analysis.category = ?")
            params.append(category)

        if min_match is not None:
            conditions.append("ai_analysis.match_score >= ?")
            params.append(min_match)

        allowed_sorts = {
            "scraped_at": "jobs.scraped_at",
            "title": "jobs.title",
            "company": "jobs.company",
            "match_score": "ai_analysis.match_score",
        }
        sort_col = allowed_sorts.get(sort_by, "jobs.scraped_at")
        sort_dir = "ASC" if order.upper() == "ASC" else "DESC"

        sql = f"""
        SELECT jobs.* FROM jobs
        LEFT JOIN ai_analysis ON jobs.id = ai_analysis.job_id
        WHERE {' AND '.join(conditions)}
        ORDER BY {sort_col} {sort_dir} NULLS LAST
        LIMIT ? OFFSET ?;
        """
        params.extend([limit, offset])

        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            return [JobQueries.row_to_job(row) for row in cur.fetchall()]

    @staticmethod
    def delete_job(db: Database, job_id: str) -> bool:
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            return cur.rowcount > 0


class AnalysisQueries:
    """Operations for persisting and retrieving AI insights."""

    @staticmethod
    def row_to_analysis(row: Any) -> AIAnalysis:
        jid = ""
        for k in ("job_id", "a_job_id", "id"):
            try:
                if row[k]:
                    jid = str(row[k])
                    break
            except Exception:
                pass

        def _val(key: str, default: Any = None) -> Any:
            try:
                v = row[key]
                return v if v is not None else default
            except Exception:
                return default

        return AIAnalysis(
            job_id=jid,
            match_score=float(_val("match_score", 0.0) or 0.0),
            category=str(_val("category", "General") or "General"),
            summary=str(_val("summary", "") or ""),
            key_skills=str(_val("key_skills", "[]") or "[]"),
            missing_skills=str(_val("missing_skills", "[]") or "[]"),
            salary_estimate=str(_val("salary_estimate", "") or ""),
            red_flags=str(_val("red_flags", "[]") or "[]"),
            learning_suggestions=str(_val("learning_suggestions", "[]") or "[]"),
            cover_letter=_val("cover_letter"),
            outreach_email=_val("outreach_email"),
            analyzed_at=_val("analyzed_at"),
        )

    @staticmethod
    def save_analysis(db: Database, analysis: AIAnalysis) -> bool:
        sql = """
        INSERT INTO ai_analysis (
            job_id, match_score, category, summary, key_skills, missing_skills,
            salary_estimate, red_flags, learning_suggestions, cover_letter, outreach_email
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            match_score = excluded.match_score,
            category = excluded.category,
            summary = excluded.summary,
            key_skills = excluded.key_skills,
            missing_skills = excluded.missing_skills,
            salary_estimate = excluded.salary_estimate,
            red_flags = excluded.red_flags,
            learning_suggestions = excluded.learning_suggestions,
            cover_letter = COALESCE(excluded.cover_letter, ai_analysis.cover_letter),
            outreach_email = COALESCE(excluded.outreach_email, ai_analysis.outreach_email),
            analyzed_at = CURRENT_TIMESTAMP;
        """
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(
                sql,
                (
                    analysis.job_id,
                    analysis.match_score,
                    analysis.category,
                    analysis.summary,
                    analysis.key_skills,
                    analysis.missing_skills,
                    analysis.salary_estimate,
                    analysis.red_flags,
                    analysis.learning_suggestions,
                    analysis.cover_letter,
                    analysis.outreach_email,
                ),
            )
            return cur.rowcount > 0

    @staticmethod
    def get_analysis(db: Database, job_id: str) -> Optional[AIAnalysis]:
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM ai_analysis WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            return AnalysisQueries.row_to_analysis(row) if row else None

    @staticmethod
    def get_top_matches(db: Database, limit: int = 10) -> List[Tuple[Job, AIAnalysis]]:
        sql = """
        SELECT jobs.*, ai_analysis.*
        FROM jobs
        JOIN ai_analysis ON jobs.id = ai_analysis.job_id
        ORDER BY ai_analysis.match_score DESC, jobs.scraped_at DESC
        LIMIT ?;
        """
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(sql, (limit,))
            results = []
            for row in cur.fetchall():
                job = JobQueries.row_to_job(row)
                analysis = AnalysisQueries.row_to_analysis(row)
                results.append((job, analysis))
            return results

    @staticmethod
    def get_jobs_with_analysis(
        db: Database,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "match_score",
        date_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
    ) -> List[Tuple[Job, Optional[AIAnalysis]]]:
        conditions = ["1=1"]
        params: List[Any] = []

        if source_filter and source_filter.lower() != "all":
            conditions.append("LOWER(jobs.source) = ?")
            params.append(source_filter.lower())

        if date_filter and date_filter.lower() != "all":
            df = date_filter.lower()
            if df in ("24h", "1d", "today"):
                conditions.append("jobs.scraped_at >= datetime('now', '-1 day')")
            elif df in ("3d", "3 days"):
                conditions.append("jobs.scraped_at >= datetime('now', '-3 days')")
            elif df in ("7d", "week", "past week"):
                conditions.append("jobs.scraped_at >= datetime('now', '-7 days')")
            elif df in ("30d", "month", "past month"):
                conditions.append("jobs.scraped_at >= datetime('now', '-30 days')")

        if sort_by in ("date_added", "scraped_at", "date"):
            order_clause = "jobs.scraped_at DESC, COALESCE(ai_analysis.match_score, 0) DESC"
        elif sort_by == "company":
            order_clause = "jobs.company ASC, COALESCE(ai_analysis.match_score, 0) DESC"
        elif sort_by == "title":
            order_clause = "jobs.title ASC, COALESCE(ai_analysis.match_score, 0) DESC"
        else:
            order_clause = "COALESCE(ai_analysis.match_score, 0) DESC, jobs.scraped_at DESC"

        sql = f"""
        SELECT jobs.*, ai_analysis.job_id AS a_job_id, ai_analysis.match_score,
               ai_analysis.category, ai_analysis.summary, ai_analysis.key_skills,
               ai_analysis.missing_skills, ai_analysis.salary_estimate,
               ai_analysis.red_flags, ai_analysis.learning_suggestions,
               ai_analysis.cover_letter, ai_analysis.outreach_email,
               ai_analysis.analyzed_at
        FROM jobs
        LEFT JOIN ai_analysis ON jobs.id = ai_analysis.job_id
        WHERE {' AND '.join(conditions)}
        ORDER BY {order_clause}
        LIMIT ? OFFSET ?;
        """
        params.extend([limit, offset])
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            results = []
            for row in cur.fetchall():
                job = JobQueries.row_to_job(row)
                analysis = None
                if row["a_job_id"]:
                    analysis = AnalysisQueries.row_to_analysis(row)
                results.append((job, analysis))
            return results


class ApplicationQueries:
    """Operations for the job application tracking funnel."""

    @staticmethod
    def create_application(db: Database, job_id: str, status: str = "saved") -> int:
        sql = """
        INSERT INTO applications (job_id, status)
        VALUES (?, ?)
        ON CONFLICT(job_id) DO UPDATE SET status = excluded.status, updated_at = CURRENT_TIMESTAMP;
        """
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(sql, (job_id, status))
            return int(cur.lastrowid or 0)

    @staticmethod
    def update_status(db: Database, job_id: Union[str, int], status: str) -> bool:
        if isinstance(job_id, int):
            sql = "UPDATE applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        else:
            sql = "UPDATE applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE job_id = ?"
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(sql, (status, job_id))
            return cur.rowcount > 0

    @staticmethod
    def get_applications(db: Database, status: Optional[str] = None) -> List[Application]:
        sql = "SELECT * FROM applications"
        params: List[Any] = []
        if status:
            sql += " WHERE status = ?"
            params.append(status)
        sql += " ORDER BY updated_at DESC"

        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            return [
                Application(
                    id=row["id"],
                    job_id=row["job_id"],
                    status=row["status"],
                    applied_date=row["applied_date"],
                    notes=row["notes"],
                    follow_up_date=row["follow_up_date"],
                    updated_at=row["updated_at"],
                )
                for row in cur.fetchall()
            ]

    @staticmethod
    def get_pipeline_counts(db: Database) -> Dict[str, int]:
        counts = {"saved": 0, "applied": 0, "interviewing": 0, "rejected": 0, "offered": 0}
        sql = "SELECT status, COUNT(*) as count FROM applications GROUP BY status"
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            for row in cur.fetchall():
                if row["status"] in counts:
                    counts[row["status"]] = int(row["count"])
        return counts


class QuotaQueries:
    """Monitors monthly API requests and credits consumed."""

    @staticmethod
    def log_request(db: Database, endpoint: str, jobs_returned: int, credits_used: int) -> None:
        sql = "INSERT INTO quota_log (endpoint, jobs_returned, credits_used) VALUES (?, ?, ?)"
        with db.session() as conn:
            conn.cursor().execute(sql, (endpoint, jobs_returned, credits_used))

    @staticmethod
    def get_daily_jobs_scraped(db: Database) -> int:
        sql = """
        SELECT COALESCE(SUM(jobs_returned), 0) as today_jobs
        FROM quota_log
        WHERE date(request_date) = date('now');
        """
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            row = cur.fetchone()
            return int(row["today_jobs"] or 0)

    @staticmethod
    def get_monthly_usage(
        db: Database,
        requests_limit: Optional[int] = None,
        jobs_limit: Optional[int] = None,
    ) -> Dict[str, int]:
        sql = """
        SELECT COUNT(*) as req_count, COALESCE(SUM(credits_used), 0) as cred_count
        FROM quota_log
        WHERE strftime('%Y-%m', request_date) = strftime('%Y-%m', 'now');
        """
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            row = cur.fetchone()
            reqs = int(row["req_count"] or 0)
            creds = int(row["cred_count"] or 0)

            r_lim = requests_limit if requests_limit is not None else 25
            j_lim = jobs_limit if jobs_limit is not None else 250

            return {
                "requests_used": reqs,
                "requests_limit": r_lim,
                "jobs_used": creds,
                "jobs_limit": j_lim,
            }


class PresetQueries:
    """Manages preset search preferences."""

    @staticmethod
    def save_preset(db: Database, preset: SearchPreset) -> int:
        sql = """
        INSERT INTO search_presets (name, title_query, location, remote_filter, time_frame)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            title_query = excluded.title_query,
            location = excluded.location,
            remote_filter = excluded.remote_filter,
            time_frame = excluded.time_frame;
        """
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(
                sql,
                (
                    preset.name,
                    preset.title_query,
                    preset.location,
                    preset.remote_filter,
                    preset.time_frame,
                ),
            )
            return int(cur.lastrowid or 0)

    @staticmethod
    def list_presets(db: Database) -> List[SearchPreset]:
        sql = "SELECT * FROM search_presets ORDER BY name ASC"
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            return [
                SearchPreset(
                    id=row["id"],
                    name=row["name"],
                    title_query=row["title_query"],
                    location=row["location"],
                    remote_filter=row["remote_filter"],
                    time_frame=row["time_frame"],
                    created_at=row["created_at"],
                )
                for row in cur.fetchall()
            ]

    @staticmethod
    def delete_preset(db: Database, preset_id: int) -> bool:
        sql = "DELETE FROM search_presets WHERE id = ?"
        with db.session() as conn:
            cur = conn.cursor()
            cur.execute(sql, (preset_id,))
            return cur.rowcount > 0

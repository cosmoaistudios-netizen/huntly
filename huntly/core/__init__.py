from __future__ import annotations
"""Core engine abstractions and utilities for Huntly."""

from huntly.core.analyzer import JobAnalyzer
from huntly.core.dedup import find_similar, get_new_jobs, is_duplicate
from huntly.core.demo_data import DEMO_JOBS, load_demo_fixtures
from huntly.core.enricher import CompanyEmailEnricher, WebContactCrawler, enrich_single_job
from huntly.core.hn_scraper import HackerNewsScraper
from huntly.core.matcher import calculate_match_score, get_skill_gaps
from huntly.core.resume import extract_skills, get_resume_summary, parse_resume
from huntly.core.rss_scraper import FreeJobAggregator, RemoteOKScraper, WeWorkRemotelyScraper
from huntly.core.scraper import JobScraper, parse_job_response

__all__ = [
    "JobScraper",
    "parse_job_response",
    "HackerNewsScraper",
    "RemoteOKScraper",
    "WeWorkRemotelyScraper",
    "FreeJobAggregator",
    "JobAnalyzer",
    "WebContactCrawler",
    "CompanyEmailEnricher",
    "enrich_single_job",
    "DEMO_JOBS",
    "load_demo_fixtures",
    "parse_resume",
    "extract_skills",
    "get_resume_summary",
    "calculate_match_score",
    "get_skill_gaps",
    "is_duplicate",
    "find_similar",
    "get_new_jobs",
]

from __future__ import annotations
import pytest

from huntly.core.hn_scraper import HackerNewsScraper, strip_html_tags
from huntly.core.rss_scraper import RemoteOKScraper, WeWorkRemotelyScraper, FreeJobAggregator
from huntly.core.analyzer import JobAnalyzer


def test_strip_html_edge_cases():
    assert strip_html_tags("") == ""
    assert strip_html_tags("   ") == ""
    assert strip_html_tags("&amp; &lt; &gt; &#39;") == "& < > '"
    raw = "<div>Hello <a href='https://example.com'>World</a></div>"
    assert strip_html_tags(raw) == "Hello World"


def test_analyzer_json_recovery():
    analyzer = JobAnalyzer(
        api_key="test-key",
        resume_text="Senior Python Engineer",
        model="nvidia/nemotron-3.5-super-vl-120b-a12b",
    )
    # Check fallback returns expected schema when no API key
    empty_analyzer = JobAnalyzer(api_key="", resume_text="Test")
    import asyncio
    res = asyncio.run(empty_analyzer.analyze_job({"title": "Dev"}))
    assert "match_score" in res
    assert "category" in res
    assert "summary" in res
    assert "key_skills" in res
    assert "salary_estimate" in res


@pytest.mark.asyncio
async def test_live_hn_scraper_structure():
    """Live network smoke test for Hacker News Algolia API."""
    scraper = HackerNewsScraper(timeout=8.0)
    jobs = await scraper.search_jobs(query="python", limit=2)
    # Network might be empty if query is ultra specific, but list should be returned
    assert isinstance(jobs, list)
    if jobs:
        j = jobs[0]
        assert j["source"] == "hackernews"
        assert "id" in j
        assert "title" in j
        assert "company" in j
        assert "description_text" in j


@pytest.mark.asyncio
async def test_live_remoteok_scraper_structure():
    """Live network smoke test for RemoteOK public API."""
    scraper = RemoteOKScraper(timeout=8.0)
    jobs = await scraper.search_jobs(query="", limit=2)
    assert isinstance(jobs, list)
    if jobs:
        j = jobs[0]
        assert j["source"] == "remoteok"
        assert "id" in j
        assert "title" in j
        assert "company" in j
        assert "apply_url" in j


@pytest.mark.asyncio
async def test_live_wwr_scraper_structure():
    """Live network smoke test for WeWorkRemotely RSS feed."""
    scraper = WeWorkRemotelyScraper(timeout=8.0)
    jobs = await scraper.search_jobs(query="", limit=2)
    assert isinstance(jobs, list)
    if jobs:
        j = jobs[0]
        assert j["source"] == "weworkremotely"
        assert "id" in j
        assert "title" in j
        assert "apply_url" in j

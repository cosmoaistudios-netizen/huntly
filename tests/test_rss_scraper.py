from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from huntly.core.rss_scraper import RemoteOKScraper, WeWorkRemotelyScraper


@pytest.mark.asyncio
async def test_remoteok_scraper_parsing():
    mock_payload = [
        {"legal": "disclaimer"},
        {
            "id": "123456",
            "position": "Senior Python Developer",
            "company": "FastTech",
            "tags": ["python", "django", "backend"],
            "description": "<p>Looking for a Senior Python Developer. Apply with resume.</p>",
            "location": "Remote",
            "url": "https://remoteok.com/l/123456",
            "salary_min": 120000,
            "salary_max": 150000,
            "date": "2026-10-20T10:00:00Z",
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        scraper = RemoteOKScraper()
        jobs = await scraper.search_jobs(query="python", limit=5)

        assert len(jobs) == 1
        job = jobs[0]
        assert job["title"] == "Senior Python Developer"
        assert job["company"] == "FastTech"
        assert job["source"] == "remoteok"
        assert job["salary_min"] == 120000.0
        assert job["salary_max"] == 150000.0
        assert "123456" in job["id"]


@pytest.mark.asyncio
async def test_weworkremotely_scraper_parsing():
    mock_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>We Work Remotely</title>
        <item>
          <title>GitLab: Senior Infrastructure Engineer</title>
          <link>https://weworkremotely.com/jobs/111</link>
          <guid>https://weworkremotely.com/jobs/111</guid>
          <pubDate>Tue, 20 Oct 2026 12:00:00 +0000</pubDate>
          <description><![CDATA[<p>Join GitLab as an Infrastructure Engineer. Reach out to careers@gitlab.com</p>]]></description>
        </item>
      </channel>
    </rss>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = mock_xml

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        scraper = WeWorkRemotelyScraper()
        jobs = await scraper.search_jobs(query="infrastructure", limit=5)

        assert len(jobs) == 1
        job = jobs[0]
        assert job["title"] == "Senior Infrastructure Engineer"
        assert job["company"] == "GitLab"
        assert job["source"] == "weworkremotely"
        assert job["contact_email"] == "careers@gitlab.com"

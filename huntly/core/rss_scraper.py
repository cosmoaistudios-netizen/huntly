from __future__ import annotations
"""RemoteOK and WeWorkRemotely free RSS / API job scrapers."""

import hashlib
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
import httpx

from huntly.core.hn_scraper import strip_html_tags
from huntly.core.scraper import extract_email_from_text


class RemoteOKScraper:
    """Fetches remote software engineering jobs from RemoteOK's public JSON API."""

    API_URL = "https://remoteok.com/api"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Huntly-JobHunter/0.2.0 (Terminal AI Assistant; https://github.com/cosmoaistudios-netizen/huntly)"
        }

    async def search_jobs(
        self,
        query: str = "",
        limit: int = 15,
        remote_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Queries public remote listings from RemoteOK."""
        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=self.timeout) as client:
            try:
                resp = await client.get(self.API_URL, timeout=self.timeout)
                if resp.status_code != 200:
                    return []
                data = resp.json()
            except Exception:
                return []

        # First element is legal/disclaimer notice
        raw_items = data[1:] if len(data) > 1 and isinstance(data, list) else []
        results: List[Dict[str, Any]] = []

        q_lower = query.lower().strip()

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            title = item.get("position") or ""
            company = item.get("company") or "Remote Company"
            tags = item.get("tags") or []
            tags_str = " ".join(tags) if isinstance(tags, list) else str(tags)
            desc_html = item.get("description") or ""
            desc_text = strip_html_tags(desc_html)

            # Filter by query if supplied
            if q_lower:
                searchable = f"{title} {company} {tags_str} {desc_text[:500]}".lower()
                if q_lower not in searchable:
                    continue

            job_id = f"remoteok-{item.get('id') or hashlib.md5((company + title).encode()).hexdigest()[:10]}"
            location = item.get("location") or "Remote (Worldwide)"
            apply_url = item.get("url") or item.get("apply_url") or f"https://remoteok.com/l/{item.get('id')}"

            # Salary parsing
            sal_min = None
            sal_max = None
            if item.get("salary_min"):
                try:
                    sal_min = float(item["salary_min"])
                except Exception:
                    pass
            if item.get("salary_max"):
                try:
                    sal_max = float(item["salary_max"])
                except Exception:
                    pass

            email = extract_email_from_text(desc_text)

            results.append({
                "id": job_id,
                "title": title[:100],
                "company": company[:60],
                "company_industry": tags_str[:60] if tags_str else "Software Development",
                "company_size": "Remote Startup / Tech",
                "company_description": f"Tags: {tags_str}",
                "location": location[:60],
                "remote_type": "remote",
                "description_text": desc_text,
                "description_html": desc_html,
                "posted_date": str(item.get("date") or ""),
                "apply_url": apply_url,
                "contact_email": email,
                "salary_min": sal_min,
                "salary_max": sal_max,
                "salary_currency": "USD",
                "search_query": f"remoteok|query={query}",
                "raw_json": str(item),
                "source": "remoteok",
            })

            if len(results) >= limit:
                break

        return results


class WeWorkRemotelyScraper:
    """Parses WeWorkRemotely programming RSS feeds."""

    RSS_FEEDS = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    ]

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Huntly-JobHunter/0.2.0 (Terminal AI Assistant; https://github.com/cosmoaistudios-netizen/huntly)"
        }

    async def search_jobs(
        self,
        query: str = "",
        limit: int = 15,
        remote_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Queries listings from WeWorkRemotely RSS feed."""
        results: List[Dict[str, Any]] = []
        seen_ids = set()
        q_lower = query.lower().strip()

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=self.timeout) as client:
            for feed_url in self.RSS_FEEDS:
                try:
                    resp = await client.get(feed_url, timeout=self.timeout)
                    if resp.status_code != 200:
                        continue
                    root = ET.fromstring(resp.content)
                except Exception:
                    continue

                for item in root.findall(".//item"):
                    raw_title = item.findtext("title") or ""
                    link = item.findtext("link") or ""
                    pub_date = item.findtext("pubDate") or ""
                    desc_html = item.findtext("description") or ""
                    desc_text = strip_html_tags(desc_html)

                    # Split "Company: Title" convention
                    if ":" in raw_title:
                        company_part, title_part = raw_title.split(":", 1)
                        company = company_part.strip()
                        title = title_part.strip()
                    else:
                        company = "Remote Tech"
                        title = raw_title.strip()

                    # Query filter
                    if q_lower:
                        searchable = f"{title} {company} {desc_text[:500]}".lower()
                        if q_lower not in searchable:
                            continue

                    guid = item.findtext("guid") or link
                    raw_hash = hashlib.md5(guid.encode()).hexdigest()[:12]
                    job_id = f"wwr-{raw_hash}"

                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    email = extract_email_from_text(desc_text)

                    results.append({
                        "id": job_id,
                        "title": title[:100],
                        "company": company[:60],
                        "company_industry": "Software Engineering",
                        "company_size": "Remote Company",
                        "company_description": "WeWorkRemotely remote position",
                        "location": "Remote (Worldwide)",
                        "remote_type": "remote",
                        "description_text": desc_text,
                        "description_html": desc_html,
                        "posted_date": pub_date,
                        "apply_url": link,
                        "contact_email": email,
                        "salary_min": None,
                        "salary_max": None,
                        "salary_currency": "USD",
                        "search_query": f"wwr|query={query}",
                        "raw_json": str({"title": raw_title, "link": link, "pubDate": pub_date}),
                        "source": "weworkremotely",
                    })

                    if len(results) >= limit:
                        break

                if len(results) >= limit:
                    break

        return results


class FreeJobAggregator:
    """Aggregates listings concurrently from all free sources (HN + RemoteOK + WeWorkRemotely)."""

    def __init__(self) -> None:
        from huntly.core.hn_scraper import HackerNewsScraper
        self.hn = HackerNewsScraper()
        self.remoteok = RemoteOKScraper()
        self.wwr = WeWorkRemotelyScraper()

    async def search_all_free_sources(
        self,
        query: str = "",
        limit_per_source: int = 5,
        remote_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Concurrently fetches from all 3 free channels."""
        import asyncio
        tasks = [
            self.hn.search_jobs(query=query, limit=limit_per_source, remote_only=remote_only),
            self.remoteok.search_jobs(query=query, limit=limit_per_source, remote_only=remote_only),
            self.wwr.search_jobs(query=query, limit=limit_per_source, remote_only=remote_only),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        aggregated: List[Dict[str, Any]] = []
        for res in results:
            if isinstance(res, list):
                aggregated.extend(res)
        return aggregated

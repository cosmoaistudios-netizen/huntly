from __future__ import annotations
"""Hacker News 'Who is Hiring?' scraper using public Algolia API."""

import html
import re
from typing import Any, Dict, List, Optional
import httpx

from huntly.core.scraper import EMAIL_REGEX, extract_email_from_text


def strip_html_tags(text: str) -> str:
    """Converts HTML markup into clean readable terminal text."""
    if not text:
        return ""
    # Replace paragraph and break tags with newlines
    text = re.sub(r"<(?:p|br|div)\s*/?>", "\n", text, flags=re.IGNORECASE)
    # Extract link text and URL
    text = re.sub(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', r"\2 (\1)", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Clean up excess whitespace
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


class HackerNewsScraper:
    """Fetches and parses job listings from monthly 'Ask HN: Who is hiring?' threads."""

    ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
    ALGOLIA_COMMENTS_URL = "https://hn.algolia.com/api/v1/search"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Huntly-JobHunter/0.2.0 (Terminal AI Assistant; https://github.com/cosmoaistudios-netizen/huntly)"
        }

    async def get_latest_hiring_thread_id(self, client: httpx.AsyncClient) -> Optional[str]:
        """Finds the most recent 'Ask HN: Who is hiring?' thread objectID."""
        params = {
            "tags": "story,author_whoishiring",
            "query": "hiring",
            "hitsPerPage": 5,
        }
        try:
            resp = await client.get(self.ALGOLIA_SEARCH_URL, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                hits = resp.json().get("hits", [])
                for hit in hits:
                    title = hit.get("title", "")
                    if "who is hiring?" in title.lower():
                        return str(hit.get("objectID"))
        except Exception:
            pass
        return None

    async def search_jobs(
        self,
        query: str = "",
        limit: int = 15,
        remote_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Queries recent top-level job comments from the latest HN hiring thread."""
        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=self.timeout) as client:
            story_id = await self.get_latest_hiring_thread_id(client)
            if not story_id:
                return []

            params: Dict[str, Any] = {
                "tags": f"comment,story_{story_id}",
                "hitsPerPage": min(limit * 3, 100),
            }
            if query:
                params["query"] = query

            try:
                resp = await client.get(self.ALGOLIA_COMMENTS_URL, params=params, timeout=self.timeout)
                if resp.status_code != 200:
                    return []
                hits = resp.json().get("hits", [])
            except Exception:
                return []

            results: List[Dict[str, Any]] = []
            for hit in hits:
                # Top-level comments on the story are job postings
                parent_id = str(hit.get("parent_id") or "")
                if parent_id != story_id:
                    continue

                raw_html = hit.get("comment_text") or ""
                if not raw_html:
                    continue

                clean_text = strip_html_tags(raw_html)
                first_line = clean_text.split("\n")[0] if clean_text else "Software Engineer"

                # Parse pipe or dash separated header: Company | Role | Location | Remote | ...
                parts = [p.strip() for p in re.split(r"\s*[|•;]\s*", first_line) if p.strip()]

                company = parts[0] if parts else "Hacker News Startup"
                # Strip out trailing URLs or parenthetical links in company name
                company = re.sub(r"\(http.*?\)", "", company).strip() or "Hacker News Startup"

                title = parts[1] if len(parts) > 1 else "Software Engineer"
                location = parts[2] if len(parts) > 2 else "Remote / Flexible"

                # Detect remote eligibility
                full_lower = clean_text.lower()
                is_remote = "remote" in full_lower or "anywhere" in full_lower or "distributed" in full_lower
                if remote_only and not is_remote:
                    continue

                remote_type = "remote" if is_remote else "onsite"

                # Extract contact email
                email = extract_email_from_text(clean_text)

                # Extract first external link for apply_url, else fallback to HN comment permalink
                urls = re.findall(r"https?://[^\s<>\"'()]+", clean_text)
                permalink = f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                apply_url = permalink
                for u in urls:
                    if "ycombinator.com" not in u and not any(u.endswith(ext) for ext in [".png", ".jpg", ".gif"]):
                        apply_url = u
                        break

                job_id = f"hn-{hit.get('objectID')}"

                results.append({
                    "id": job_id,
                    "title": title[:100],
                    "company": company[:60],
                    "company_industry": "Technology / Startup",
                    "company_size": "Startup / Scaleup",
                    "company_description": f"Posted on Hacker News 'Who is Hiring?' thread #{story_id}",
                    "location": location[:60],
                    "remote_type": remote_type,
                    "description_text": clean_text,
                    "description_html": raw_html,
                    "posted_date": str(hit.get("created_at") or ""),
                    "apply_url": apply_url,
                    "contact_email": email,
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": "USD",
                    "search_query": f"hn|query={query}",
                    "raw_json": str(hit),
                    "source": "hackernews",
                })

                if len(results) >= limit:
                    break

            return results

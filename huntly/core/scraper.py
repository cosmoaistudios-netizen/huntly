from __future__ import annotations
"""LinkedIn Job Search API client using RapidAPI."""

import re
from typing import Any, Dict, List, Optional
import httpx


EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def extract_email_from_text(text: str) -> Optional[str]:
    """Finds contact emails embedded within job description text."""
    if not text:
        return None
    matches = EMAIL_REGEX.findall(text)
    for m in matches:
        lower = m.lower()
        if not lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".pdf", "example.com", "domain.com")):
            return m
    return None


def parse_job_response(raw: Dict[str, Any], search_query: str = "") -> Dict[str, Any]:
    """Normalizes raw RapidAPI response objects into standard Job dictionary fields."""
    job_id = str(raw.get("id") or raw.get("job_id") or raw.get("urn") or "")
    title = raw.get("title") or "Untitled Position"

    # Extract company name (can be string or dict)
    org_val = raw.get("organization") or raw.get("company")
    if isinstance(org_val, dict):
        company = org_val.get("name") or "Unknown Company"
    elif isinstance(org_val, str):
        company = org_val
    else:
        company = "Unknown Company"

    # Extract location representation
    location = "Remote"
    loc_list = raw.get("locations")
    if isinstance(loc_list, list) and loc_list:
        first_loc = loc_list[0]
        if isinstance(first_loc, dict):
            addr = first_loc.get("address", {})
            city = addr.get("addressLocality") or ""
            country = addr.get("addressCountry") or ""
            parts = [p for p in [city, country] if p]
            if parts:
                location = ", ".join(parts)
    elif raw.get("locations_raw"):
        location = str(raw.get("locations_raw"))
    elif raw.get("location"):
        location = str(raw.get("location"))

    desc = raw.get("description") or raw.get("job_description") or raw.get("text") or ""
    desc_html = raw.get("description_html") or raw.get("html") or ""

    # Extract email if present
    contact_email = raw.get("contact_email") or extract_email_from_text(desc)

    # Determine remote status
    remote_flag = raw.get("remote") or raw.get("location_type") == "TELECOMMUTE" or False
    combined_text = f"{title} {location} {desc[:400]}".lower()
    remote_type = "remote" if remote_flag or "remote" in combined_text or "freelance" in combined_text else "onsite"

    # Salary extraction if available
    salary_min = None
    salary_max = None
    salary_curr = None
    sal_info = raw.get("salary") or raw.get("compensation") or {}
    if isinstance(sal_info, dict):
        salary_min = sal_info.get("min") or sal_info.get("minValue")
        salary_max = sal_info.get("max") or sal_info.get("maxValue")
        salary_curr = sal_info.get("currency", "USD")

    apply_url = raw.get("url") or raw.get("job_url") or raw.get("apply_url") or raw.get("organization_url") or ""

    return {
        "id": job_id,
        "title": title,
        "company": company,
        "company_industry": raw.get("industry") or raw.get("company_industry"),
        "company_size": raw.get("company_size") or raw.get("company_employees"),
        "company_description": raw.get("company_description"),
        "location": location,
        "remote_type": remote_type,
        "description_text": desc,
        "description_html": desc_html,
        "posted_date": str(raw.get("date_posted") or raw.get("posted_date") or ""),
        "apply_url": apply_url,
        "contact_email": contact_email,
        "salary_min": float(salary_min) if salary_min is not None else None,
        "salary_max": float(salary_max) if salary_max is not None else None,
        "salary_currency": salary_curr,
        "search_query": search_query,
        "raw_json": str(raw),
    }


class JobScraper:
    """Handles communication with the RapidAPI LinkedIn Job Search endpoint."""

    BASE_URL = "https://linkedin-job-search-api.p.rapidapi.com"
    API_HOST = "linkedin-job-search-api.p.rapidapi.com"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def search_jobs(
        self,
        title: str = "",
        location: str = "",
        remote: bool = True,
        limit: int = 10,
        offset: int = 0,
        time_frame: str = "24h",
    ) -> List[Dict[str, Any]]:
        """Queries the LinkedIn API for matching job postings via /active-jb."""
        if not self.api_key:
            return []

        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.API_HOST,
        }

        endpoint = f"{self.BASE_URL}/active-jb"

        params: Dict[str, Any] = {
            "time_frame": time_frame if time_frame in ["1h", "24h", "7d", "6m"] else "24h",
            "limit": limit,
            "offset": offset,
            "description_format": "text",
        }
        if title:
            params["title"] = title
        if location and "," not in location and location.lower() != "remote":
            params["location"] = location.strip()
        if remote:
            params["description"] = "remote"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(endpoint, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    raw_list = data if isinstance(data, list) else data.get("data", [])
                    query_label = f"title={title}|loc={location}|tf={time_frame}"
                    return [parse_job_response(item, search_query=query_label) for item in raw_list]
                else:
                    print(f"RapidAPI request returned HTTP {response.status_code}: {response.text}")
                    return []
            except Exception as err:
                print(f"Exception during LinkedIn API search: {err}")
                return []

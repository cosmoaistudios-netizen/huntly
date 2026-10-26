from __future__ import annotations
"""Web browsing search and Nemotron-driven contact email enrichment tool."""

import ast
import asyncio
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import httpx
from openai import AsyncOpenAI

from huntly.config.settings import Settings
from huntly.db.models import Database, Job
from huntly.db.queries import JobQueries

# Regex for finding valid email addresses
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}")

# Unwanted email patterns, extensions, and dummy domains
BLACKLIST_EXT = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf",
    ".css", ".js", ".woff", ".woff2", ".ttf", ".eot"
)
BLACKLIST_DOMAINS = (
    "example.com", "domain.com", "sentry.io", "wixpress.com",
    "w3.org", "google.com", "schema.org", "github.com",
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
    "gravatar.com", "cloudflare.com", "wp.com", "wordpress.org"
)

# Common web paths where HR, recruiting, or contact emails are published
PROBE_PATHS = [
    "",
    "/contact",
    "/contact-us",
    "/contactus",
    "/careers",
    "/jobs",
    "/join-us",
    "/about",
    "/about-us",
    "/team",
    "/people",
]

# Priority categories for HR/hiring addresses
HR_PREFIXES = (
    "career", "careers", "recruiting", "recruit", "recruitment",
    "talent", "jobs", "job", "hr", "people", "hiring", "join",
    "work", "apply"
)
FOUNDER_PREFIXES = ("founder", "founders", "ceo", "cto", "co-founder")
GENERAL_PREFIXES = ("contact", "hello", "hi", "info", "team", "support", "office")


class WebContactCrawler:
    """Asynchronous website crawler for discovering contact and recruiter emails."""

    def __init__(self, timeout: float = 4.5) -> None:
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    @staticmethod
    def extract_domain_from_url(url: str) -> str:
        """Extracts the clean host domain from a URL."""
        if not url:
            return ""
        clean = url.strip()
        if not clean.startswith(("http://", "https://")):
            clean = "https://" + clean
        try:
            parsed = urlparse(clean)
            return parsed.netloc.lower().replace("www.", "")
        except Exception:
            return ""

    @staticmethod
    def clean_emails(raw_emails: List[str]) -> List[str]:
        """Cleans and filters out dummy, script, or invalid emails."""
        cleaned: Set[str] = set()
        for e in raw_emails:
            lower = e.strip().lower().rstrip(".,;:'\"")
            if not lower or "@" not in lower:
                continue
            if any(lower.endswith(ext) for ext in BLACKLIST_EXT):
                continue
            parts = lower.split("@")
            if len(parts) != 2:
                continue
            domain = parts[1]
            # Ensure domain has at least one dot and a pure alpha TLD
            if "." not in domain:
                continue
            tld = domain.split(".")[-1]
            if not tld.isalpha() or len(tld) < 2:
                continue
            if any(bd in domain for bd in BLACKLIST_DOMAINS):
                continue
            cleaned.add(lower)
        return sorted(list(cleaned))

    async def _fetch_page(self, client: httpx.AsyncClient, url: str) -> str:
        try:
            resp = await client.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        return ""

    async def crawl_site(self, target_url: str) -> Dict[str, Any]:
        """Crawls candidate contact/career pages on target domain to extract emails."""
        if not target_url:
            return {"domain": "", "emails": [], "hr_emails": [], "general_emails": []}

        clean = target_url.strip()
        if not clean.startswith(("http://", "https://")):
            clean = "https://" + clean

        parsed = urlparse(clean)
        domain = parsed.netloc.lower().replace("www.", "")
        scheme = parsed.scheme or "https"
        base_url = f"{scheme}://{parsed.netloc}"

        endpoints = [f"{base_url}{path}" for path in PROBE_PATHS]

        async with httpx.AsyncClient(
            headers=self.headers,
            follow_redirects=True,
            verify=False,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        ) as client:
            tasks = [self._fetch_page(client, u) for u in endpoints]
            pages = await asyncio.gather(*tasks)

        all_raw_matches: List[str] = []
        for text in pages:
            if not text:
                continue
            # 1. Look for mailto: links
            mailto_matches = re.findall(r'mailto:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,})', text, re.IGNORECASE)
            all_raw_matches.extend(mailto_matches)
            # 2. General regex matches
            all_raw_matches.extend(EMAIL_REGEX.findall(text))

        valid_emails = self.clean_emails(all_raw_matches)

        # Categorize
        hr_emails: List[str] = []
        founder_emails: List[str] = []
        general_emails: List[str] = []
        other_emails: List[str] = []

        for email in valid_emails:
            local = email.split("@")[0].lower()
            if any(local.startswith(p) or local == p for p in HR_PREFIXES):
                hr_emails.append(email)
            elif any(local.startswith(p) or local == p for p in FOUNDER_PREFIXES):
                founder_emails.append(email)
            elif any(local.startswith(p) or local == p for p in GENERAL_PREFIXES):
                general_emails.append(email)
            else:
                other_emails.append(email)

        best_email = None
        if hr_emails:
            best_email = hr_emails[0]
        elif founder_emails:
            best_email = founder_emails[0]
        elif general_emails:
            best_email = general_emails[0]
        elif other_emails:
            best_email = other_emails[0]

        return {
            "domain": domain,
            "base_url": base_url,
            "best_email": best_email,
            "hr_emails": hr_emails,
            "founder_emails": founder_emails,
            "general_emails": general_emails,
            "other_emails": other_emails,
            "all_emails": valid_emails,
        }


class CompanyEmailEnricher:
    """Coordinates web crawler and Nemotron 3 Super 120B reasoning to locate HR emails."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or Settings()
        self.crawler = WebContactCrawler()
        effective_key = self.settings.ai_api_key or (
            "ollama" if "localhost" in self.settings.ai_base_url or "127.0.0.1" in self.settings.ai_base_url else "placeholder"
        )
        self.ai_client = AsyncOpenAI(
            api_key=effective_key,
            base_url=self.settings.ai_base_url,
        )

    def extract_website_from_job(self, job_dict: Dict[str, Any]) -> str:
        """Determines the company's official website from raw RapidAPI data or apply link."""
        raw_json_str = job_dict.get("raw_json") or ""
        if raw_json_str:
            try:
                # Handle python dict string or json string
                try:
                    data = json.loads(raw_json_str)
                except Exception:
                    data = ast.literal_eval(raw_json_str)

                if isinstance(data, dict):
                    website = (
                        data.get("org_linkedin_website")
                        or data.get("website")
                        or data.get("company_website")
                        or data.get("company_url")
                    )
                    if website and isinstance(website, str) and "linkedin.com" not in website.lower():
                        return website.strip()
            except Exception:
                pass

        # Inspect apply URL if direct company domain
        apply_url = job_dict.get("apply_url") or ""
        if apply_url and not any(board in apply_url.lower() for board in ["linkedin.com", "lever.co", "greenhouse.io", "workday.com", "ashbyhq.com"]):
            return apply_url

        # Fallback: synthesize likely company domain
        company = job_dict.get("company") or ""
        clean_name = re.sub(r"[^a-zA-Z0-9]", "", company).lower()
        if clean_name and len(clean_name) > 2:
            return f"https://www.{clean_name}.com"

        return ""

    async def infer_hr_email_with_nemotron(
        self,
        company: str,
        domain: str,
        job_title: str,
        description: str,
        crawled_emails: List[str],
    ) -> Tuple[Optional[str], str, str]:
        """Prompts the configured AI model to analyze crawled emails or predict HR inbox."""
        is_local = "localhost" in self.settings.ai_base_url or "127.0.0.1" in self.settings.ai_base_url
        if not is_local and (not self.settings.ai_api_key or self.settings.ai_api_key == "placeholder"):
            if crawled_emails:
                return crawled_emails[0], "crawled", "Directly extracted from website pages."
            return None, "none", "No email found (AI provider key not configured)."

        prompt = f"""
You are an expert HR intelligence & talent research agent.
Company: {company}
Domain: {domain}
Job Title: {job_title}
Job Description Excerpt:
{description[:800]}
Crawled Emails Found on Company Website: {crawled_emails}

Your objective:
Identify or recommend the most direct and effective HR / Talent Acquisition / Founder email address for submitting a remote engineering application.
1. If the crawled list has an HR, talent, or careers address, select the highest-priority one.
2. If only general addresses exist (e.g. info@, contact@), evaluate if they work or if standard recruiting convention (e.g. careers@{domain} or talent@{domain}) is better.
3. If no emails were crawled, predict the most standard talent acquisition email for this domain.

Return a valid JSON object strictly matching this schema:
{{
  "email": "<the email address>",
  "source_type": "<crawled|inferred>",
  "reason": "<1 sentence explanation>"
}}
"""
        try:
            response = await self.ai_client.chat.completions.create(
                model=self.settings.ai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional HR intelligence agent. Always output valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=600,
            )
            msg = response.choices[0].message
            content = msg.content or getattr(msg, "reasoning_content", "") or "{}"
            match = re.search(r"\{.*\}", content, re.DOTALL)
            clean_json = match.group(0) if match else content
            data = json.loads(clean_json)

            email = data.get("email")
            source_type = data.get("source_type", "inferred")
            reason = data.get("reason", "Nemotron AI analysis")
            return email, source_type, reason
        except Exception as exc:
            if crawled_emails:
                return crawled_emails[0], "crawled", "Extracted from website pages (fallback)."
            return None, "error", f"Nemotron inference error: {exc}"

    async def enrich_job_contact(self, job_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the complete web browsing & Nemotron tool workflow for a single job."""
        company = job_dict.get("company") or "Unknown"
        title = job_dict.get("title") or "Position"
        description = job_dict.get("description_text") or ""

        # Step 1: Detect website
        website = self.extract_website_from_job(job_dict)
        domain = WebContactCrawler.extract_domain_from_url(website)

        # Step 2: Crawl website
        crawl_result = {"all_emails": [], "best_email": None, "hr_emails": []}
        if website:
            crawl_result = await self.crawler.crawl_site(website)

        crawled_emails = crawl_result.get("all_emails", [])
        hr_emails = crawl_result.get("hr_emails", [])

        # Step 3: Nemotron reasoning & verification
        # If we already have a direct HR email from the website, we can use it or verify with Nemotron
        if hr_emails and len(hr_emails) == 1:
            best_email = hr_emails[0]
            return {
                "email": best_email,
                "domain": domain,
                "source": "Website HR Page",
                "method": "Direct Crawl",
                "crawled_emails": crawled_emails,
            }

        # Otherwise let Nemotron evaluate crawled list or predict inbox
        nemotron_email, source_type, reason = await self.infer_hr_email_with_nemotron(
            company=company,
            domain=domain or f"{company.lower().replace(' ', '')}.com",
            job_title=title,
            description=description,
            crawled_emails=crawled_emails,
        )

        final_email = nemotron_email or crawl_result.get("best_email")
        method_desc = f"Nemotron AI ({source_type})" if nemotron_email else "Direct Crawl"

        return {
            "email": final_email,
            "domain": domain,
            "source": reason,
            "method": method_desc,
            "crawled_emails": crawled_emails,
        }


async def enrich_single_job(db: Database, job: Job, enricher: Optional[CompanyEmailEnricher] = None) -> Optional[str]:
    """Enriches a Job model instance with contact email and persists it to SQLite."""
    if not enricher:
        enricher = CompanyEmailEnricher()

    job_dict = {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "apply_url": job.apply_url,
        "description_text": job.description_text,
        "raw_json": job.raw_json,
    }

    result = await enricher.enrich_job_contact(job_dict)
    email = result.get("email")

    if email:
        JobQueries.update_contact_email(db, job.id, email)
        job.contact_email = email

    return email

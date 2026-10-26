from __future__ import annotations
from huntly.core.enricher import WebContactCrawler


def test_extract_domain_from_url():
    assert WebContactCrawler.extract_domain_from_url("https://ultahost.com/careers") == "ultahost.com"
    assert WebContactCrawler.extract_domain_from_url("http://www.nexusai.io/") == "nexusai.io"
    assert WebContactCrawler.extract_domain_from_url("kompella.io") == "kompella.io"


def test_clean_emails():
    raw = [
        "careers@nexusai.io",
        "logo.png",
        "info@example.com",
        "sentry@sentry.io",
        "jobs@startup.co.uk",
        "invalid@@email",
        "user@domain.com",
        "hello@company.com",
    ]
    cleaned = WebContactCrawler.clean_emails(raw)
    assert "careers@nexusai.io" in cleaned
    assert "jobs@startup.co.uk" in cleaned
    assert "hello@company.com" in cleaned
    assert "logo.png" not in cleaned
    assert "info@example.com" not in cleaned
    assert "sentry@sentry.io" not in cleaned
    assert "user@domain.com" not in cleaned

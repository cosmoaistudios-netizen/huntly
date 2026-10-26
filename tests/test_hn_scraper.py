from __future__ import annotations
from huntly.core.hn_scraper import strip_html_tags


def test_strip_html_tags():
    raw_html = "<p>Acme Corp | <b>Full Stack Engineer</b> | Remote</p><p>Apply at <a href=\"https://acme.io/apply\">https://acme.io/apply</a> or email jobs@acme.io</p>"
    clean = strip_html_tags(raw_html)
    assert "Acme Corp" in clean
    assert "Full Stack Engineer" in clean
    assert "jobs@acme.io" in clean
    assert "<p>" not in clean
    assert "<b>" not in clean

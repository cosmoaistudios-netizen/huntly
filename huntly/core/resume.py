from __future__ import annotations
"""Resume ingestion, PDF parsing, skill extraction, and in-memory caching."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pypdf import PdfReader

# In-memory resume text cache
_RESUME_CACHE: Dict[str, str] = {}

COMMON_TECH_SKILLS = [
    # AI & ML
    "ai", "artificial intelligence", "machine learning", "data annotation", "model support",
    "content moderation", "prompt engineering", "nlp", "computer vision", "llm", "pytorch",
    "tensorflow", "hugging face",
    # Data & Analytics
    "data analyst", "data analysis", "data collection", "data cleaning", "analytics",
    "sql", "postgresql", "mysql", "sqlite", "mongodb", "redis", "excel",
    # Web & Development
    "python", "flask", "fastapi", "django", "javascript", "typescript", "react", "next.js",
    "node.js", "express", "vue", "html", "css", "tailwind", "api", "rest", "graphql",
    # Systems & Security
    "cybersecurity", "robotics", "docker", "kubernetes", "aws", "gcp", "azure", "git",
    "linux", "bash", "scraping", "playwright", "automation", "freelancing", "project management"
]


def parse_resume(pdf_path: str | Path) -> str:
    """Extract raw text from a PDF resume file with caching."""
    resolved_path = Path(os.path.expanduser(str(pdf_path))).resolve()
    key = str(resolved_path)

    if key in _RESUME_CACHE:
        return _RESUME_CACHE[key]

    if not resolved_path.exists():
        return ""

    try:
        reader = PdfReader(str(resolved_path))
        extracted_pages: List[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_pages.append(text)
        full_text = "\n".join(extracted_pages).strip()
        # Normalize excessive whitespace between individual words
        normalized_text = re.sub(r"[ \t]+", " ", full_text)
        _RESUME_CACHE[key] = normalized_text
        return normalized_text
    except Exception as exc:
        print(f"Error parsing resume at {resolved_path}: {exc}")
        return ""


def extract_skills(resume_text: str) -> List[str]:
    """Identify technological and operational competencies from resume text."""
    lower_text = resume_text.lower()
    detected_skills: List[str] = []

    for skill in COMMON_TECH_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, lower_text):
            detected_skills.append(skill.title())

    return sorted(list(set(detected_skills)))


def get_resume_summary(resume_text: str) -> Dict[str, Any]:
    """Generates an initial profile summary from parsed resume content."""
    skills = extract_skills(resume_text)
    preview = resume_text[:300].strip().replace("\n", " ") if resume_text else "No resume content found."
    return {
        "skills_count": len(skills),
        "skills": skills,
        "preview": preview,
        "char_count": len(resume_text),
    }

from __future__ import annotations
"""Profile matching and deterministic skill overlap calculations."""

from typing import List, Set


def calculate_match_score(resume_skills: List[str], job_skills: List[str]) -> float:
    """Calculates a deterministic 0-100 skill compatibility score."""
    if not job_skills:
        return 70.0  # Baseline neutral score if no specific skills listed

    user_set: Set[str] = {s.strip().lower() for s in resume_skills if s.strip()}
    job_set: Set[str] = {s.strip().lower() for s in job_skills if s.strip()}

    if not job_set:
        return 70.0

    matched = user_set.intersection(job_set)
    ratio = len(matched) / len(job_set)
    return round(ratio * 100.0, 1)


def get_skill_gaps(resume_skills: List[str], job_skills: List[str]) -> List[str]:
    """Identifies skills requested by the job that are absent in the user's resume."""
    user_set: Set[str] = {s.strip().lower() for s in resume_skills if s.strip()}
    missing: List[str] = []

    for skill in job_skills:
        clean = skill.strip()
        if clean and clean.lower() not in user_set:
            missing.append(clean)

    return missing

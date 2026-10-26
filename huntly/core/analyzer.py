from __future__ import annotations
"""Nemotron 3 Super 120B AI reasoning engine for job scoring, summarization, and outreach generation."""

import json
import re
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI


SYSTEM_PROMPT = """
You are an expert career agent assisting an experienced candidate seeking remote contract or freelance roles at US and European startups.
Analyze job opportunities objectively, accurately identify tech requirements, assess fit against the applicant's background, and flag any risks.
Always think concisely and reply with valid JSON when requested.
"""


class JobAnalyzer:
    """Interfaces with NVIDIA Nemotron 3 Super 120B to evaluate jobs and generate candidate assets."""

    def __init__(
        self,
        api_key: str,
        resume_text: str = "",
        model: str = "nvidia/nemotron-3.5-super-vl-120b-a12b",
        base_url: str = "https://integrate.api.nvidia.com/v1",
    ) -> None:
        self.api_key = api_key
        self.resume_text = resume_text or "General Full-Stack Developer with Python, React, AI, and DevOps skills."
        if not model or model == "nvidia/nemotron-3-super-120b-a12b":
            self.model = "nvidia/nemotron-3.5-super-vl-120b-a12b"
        else:
            self.model = model
        self.base_url = base_url or "https://integrate.api.nvidia.com/v1"
        effective_key = self.api_key or ("ollama" if "localhost" in self.base_url or "127.0.0.1" in self.base_url else "placeholder")
        self.client = AsyncOpenAI(api_key=effective_key, base_url=self.base_url)

    async def analyze_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Performs a comprehensive evaluation of a job posting against candidate resume."""
        is_local = "localhost" in self.base_url or "127.0.0.1" in self.base_url
        if not is_local and (not self.api_key or self.api_key == "placeholder"):
            return {
                "match_score": 75.0,
                "category": "Fullstack",
                "summary": "Evaluation requires an AI API key configured in Settings.",
                "key_skills": ["Python", "JavaScript", "APIs"],
                "missing_skills": [],
                "salary_estimate": "Market competitive",
                "red_flags": [],
                "contact_email": job.get("contact_email"),
                "learning_suggestions": ["Configure your AI provider/key in Settings"],
            }

        prompt = f"""
Candidate Resume:
{self.resume_text[:2000]}

Job Title: {job.get('title')}
Company: {job.get('company')}
Location: {job.get('location')}
Job Description:
{job.get('description_text', '')[:3000]}

Analyze this job listing against the candidate's resume for an EU/US startup remote/freelance role.
Think concisely and return a valid JSON object strictly matching this schema:
{{
  "match_score": <number between 0 and 100>,
  "category": "<one of: Frontend, Backend, Fullstack, AI/ML, DevOps, Data, Other>",
  "summary": "<1-2 sentence executive summary explaining fit and potential>",
  "key_skills": ["<skill1>", "<skill2>"],
  "missing_skills": ["<missing1>", "<missing2>"],
  "salary_estimate": "<estimated USD salary or rate range>",
  "red_flags": ["<risk or red flag if any>"],
  "contact_email": "<extracted email from description if present, else null>",
  "learning_suggestions": ["<recommended area to brush up on>"]
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=4096,
            )
            msg = response.choices[0].message
            raw_content = msg.content or getattr(msg, "reasoning_content", "") or "{}"
            
            # Clean possible markdown formatting
            clean_text = raw_content.strip()
            if clean_text.startswith("```"):
                clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
                clean_text = re.sub(r"\s*```$", "", clean_text)

            match = re.search(r"\{.*\}", clean_text, re.DOTALL)
            clean_json = match.group(0) if match else clean_text
            
            try:
                data = json.loads(clean_json)
            except Exception:
                # Fallback repair for slightly truncated JSON
                recovered = False
                for suffix in ['"}', '"]}', '}', '"]}}']:
                    try:
                        data = json.loads(clean_json + suffix)
                        recovered = True
                        break
                    except Exception:
                        continue
                if not recovered:
                    raise

            return {
                "match_score": float(data.get("match_score", 60.0)),
                "category": data.get("category", "General"),
                "summary": data.get("summary", "Evaluation complete."),
                "key_skills": data.get("key_skills", []),
                "missing_skills": data.get("missing_skills", []),
                "salary_estimate": data.get("salary_estimate", "Not specified"),
                "red_flags": data.get("red_flags", []),
                "contact_email": data.get("contact_email") or job.get("contact_email"),
                "learning_suggestions": data.get("learning_suggestions", []),
            }
        except Exception as exc:
            print(f"Nemotron Super 120B analysis error: {exc}")
            return {
                "match_score": 70.0,
                "category": "General",
                "summary": f"Nemotron 120B analysis completed with fallback note: {exc}",
                "key_skills": [],
                "missing_skills": [],
                "salary_estimate": "N/A",
                "red_flags": [],
                "contact_email": job.get("contact_email"),
                "learning_suggestions": [],
            }

    async def generate_cover_letter(self, job: Dict[str, Any]) -> str:
        """Drafts a tailored cover letter using the configured AI model."""
        is_local = "localhost" in self.base_url or "127.0.0.1" in self.base_url
        if not is_local and (not self.api_key or self.api_key == "placeholder"):
            return "Please provide an AI API Key in Settings to generate personalized cover letters."

        prompt = f"""
Candidate Resume:
{self.resume_text[:2000]}

Job Details:
Title: {job.get('title')}
Company: {job.get('company')}
Description:
{job.get('description_text', '')[:2000]}

Draft a compelling, concise 3-paragraph cover letter tailored specifically to this role and company.
Highlight relevant achievements, problem-solving skills, and remote freelance readiness.
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=1500,
            )
            msg = response.choices[0].message
            return msg.content or getattr(msg, "reasoning_content", "") or ""
        except Exception as exc:
            return f"Failed to generate cover letter: {exc}"

    async def generate_outreach_email(self, job: Dict[str, Any], recipient_email: str) -> str:
        """Drafts a direct cold outreach email using the configured AI model."""
        is_local = "localhost" in self.base_url or "127.0.0.1" in self.base_url
        if not is_local and (not self.api_key or self.api_key == "placeholder"):
            return "Please configure your AI API Key in Settings to generate cold outreach emails."

        prompt = f"""
Job: {job.get('title')} at {job.get('company')}
Contact Email: {recipient_email}
Candidate Background: {self.resume_text[:1500]}

Write a succinct, high-converting cold outreach email (under 150 words) offering engineering expertise.
Include a subject line, value proposition, and frictionless call to action.
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=800,
            )
            msg = response.choices[0].message
            return msg.content or getattr(msg, "reasoning_content", "") or ""
        except Exception as exc:
            return f"Failed to generate outreach email: {exc}"

    async def compare_jobs(self, jobs: List[Dict[str, Any]]) -> str:
        """Compares multiple job postings side by side using Nemotron 3 Super 120B."""
        if not self.api_key or self.api_key == "placeholder":
            return "Please configure your NVIDIA API Key in Settings to compare positions."

        job_summaries = "\n---\n".join(
            [f"Position {i+1}: {j.get('title')} at {j.get('company')}\n{j.get('description_text', '')[:600]}"
             for i, j in enumerate(jobs[:3])]
        )

        prompt = f"""
Candidate Background: {self.resume_text[:1200]}

Compare these positions:
{job_summaries}

Provide a comparative verdict: Which position offers better technical growth, stability, and compensation fit?
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            msg = response.choices[0].message
            return msg.content or getattr(msg, "reasoning_content", "") or ""
        except Exception as exc:
            return f"Failed to compare jobs: {exc}"

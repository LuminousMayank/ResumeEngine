"""
Matching & Scoring Engine
Handles eligibility filtering, semantic matching via FAISS, skill overlap scoring,
recruiter signal scoring, and final composite ranking.
"""

import json
import os
import numpy as np
import faiss
from sqlalchemy.orm import Session

from ..models import Job, CandidateProfile
from ..config import get_settings

settings = get_settings()


# ──────────────────────── Eligibility Filter ────────────────────────

def check_eligibility(profile: CandidateProfile, job: Job) -> str:
    """
    Returns: "Eligible", "Partially Eligible", or "Not Eligible"
    """
    issues = []

    # Graduation year check
    eligible_years = job.eligible_years or []
    if eligible_years and profile.graduation_year not in eligible_years:
        issues.append("graduation_year")

    # Degree check
    eligible_degrees = job.eligible_degrees or []
    if eligible_degrees:
        profile_degree = (profile.degree or "").lower()
        if not any(d.lower() in profile_degree or profile_degree in d.lower() for d in eligible_degrees):
            issues.append("degree")

    # Mandatory skills check
    required = set(s.lower() for s in (job.required_skills or []))
    candidate = set(s.lower() for s in (profile.skills or []))
    missing_required = required - candidate
    if len(missing_required) == len(required) and required:
        issues.append("all_required_skills_missing")
    elif missing_required:
        issues.append("some_required_skills_missing")

    # Role type vs internship count
    if job.role_type == "fulltime" and (profile.internships or 0) == 0:
        issues.append("no_internships_for_fulltime")

    if not issues:
        return "Eligible"
    elif len(issues) <= 2 and "all_required_skills_missing" not in issues:
        return "Partially Eligible"
    else:
        return "Not Eligible"


# ──────────────────────── Skill Overlap Score ────────────────────────

def compute_skill_score(profile: CandidateProfile, job: Job) -> float:
    """
    Compute a 0-100 skill overlap score.
    Weights required skills more than preferred skills.
    """
    candidate_skills = set(s.lower() for s in (profile.skills or []))
    required = set(s.lower() for s in (job.required_skills or []))
    preferred = set(s.lower() for s in (job.preferred_skills or []))

    if not required and not preferred:
        return 50.0  # neutral if no skills specified

    required_match = len(required & candidate_skills) / len(required) if required else 1.0
    preferred_match = len(preferred & candidate_skills) / len(preferred) if preferred else 0.5

    # Required skills are worth 70%, preferred 30%
    score = (required_match * 70) + (preferred_match * 30)
    return round(min(score, 100.0), 2)


# ──────────────────────── Recruiter Signals Score ────────────────────────

def compute_signals_score(profile: CandidateProfile, job: Job) -> float:
    """
    Score based on recruiter-relevant signals (0-100):
    - Has relevant project work
    - Has internship experience
    - Technical stack depth
    - Initiative signals (project count)
    """
    score = 0.0

    # Internship experience (up to 30 points)
    internships = profile.internships or 0
    score += min(internships * 15, 30)

    # Project depth (up to 30 points)
    projects = profile.projects or []
    score += min(len(projects) * 10, 30)

    # Technical stack relevance (up to 25 points)
    candidate_skills = set(s.lower() for s in (profile.skills or []))
    all_job_skills = set(s.lower() for s in ((job.required_skills or []) + (job.preferred_skills or [])))
    if all_job_skills:
        overlap = len(candidate_skills & all_job_skills) / len(all_job_skills)
        score += overlap * 25

    # Base initiative signal (up to 15 points)
    if len(projects) >= 2:
        score += 10
    if internships >= 1:
        score += 5

    return round(min(score, 100.0), 2)


# ──────────────────────── Semantic Match (FAISS) ────────────────────────

def semantic_search(query_embedding: np.ndarray, top_k: int = 20) -> list[tuple[str, float]]:
    """
    Search the FAISS index for the top-k most similar jobs.
    Returns list of (job_id, similarity_score) tuples.
    """
    index_path = os.path.join(settings.faiss_index_path, "jobs.index")
    map_path = os.path.join(settings.faiss_index_path, "id_map.json")

    if not os.path.exists(index_path):
        return []

    index = faiss.read_index(index_path)

    with open(map_path, "r") as f:
        id_map = json.load(f)

    # Normalize query
    faiss.normalize_L2(query_embedding)
    distances, indices = index.search(query_embedding, min(top_k, index.ntotal))

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        job_id = id_map.get(str(idx))
        if job_id:
            # Convert cosine similarity to 0-100 score
            similarity = max(0.0, float(dist)) * 100
            results.append((job_id, round(similarity, 2)))

    return results


# ──────────────────────── Final Ranking ────────────────────────

def categorize_fit(score: float) -> str:
    if score >= 85:
        return "Strong Match"
    elif score >= 70:
        return "Good Match"
    elif score >= 50:
        return "Stretch Match"
    else:
        return "Weak Match"


def compute_final_score(semantic: float, skill: float, signals: float) -> float:
    """Weighted combination of the three scores."""
    return round(
        (settings.semantic_weight * semantic)
        + (settings.skill_weight * skill)
        + (settings.signals_weight * signals),
        2,
    )

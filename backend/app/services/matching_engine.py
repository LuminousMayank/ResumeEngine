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

    # Semantic Mandatory Skills Check
    # Instead of strict string intersection, we use the LLM score.
    # We call evaluate_skills_with_llm which evaluates the whole profile against requirements.
    # If score is very low (<30), likely missing core requirements.
    skill_score = evaluate_skills_with_llm(
        profile.skills or [],
        job.required_skills or [],
        job.preferred_skills or [],
        job.role_type or ""
    )
    
    if (job.required_skills or job.preferred_skills) and skill_score < 30.0:
         issues.append("low_skill_match")

    # Role type vs internship count
    if job.role_type == "fulltime" and (profile.internships or 0) == 0:
        issues.append("no_internships_for_fulltime")

    if not issues:
        return "Eligible"
    elif len(issues) <= 2 and "low_skill_match" not in issues:
        return "Partially Eligible"
    else:
        return "Not Eligible"


# ──────────────────────── Skill Overlap Score ────────────────────────

def evaluate_skills_with_llm(candidate_skills: list[str], required_skills: list[str], preferred_skills: list[str], role_type: str = "") -> float:
    """
    Uses an LLM to evaluate the semantic overlap between candidate skills and job requirements.
    Returns a score from 0-100.
    """
    if not required_skills and not preferred_skills:
        return 50.0

    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)

    prompt = f"""You are an expert technical and executive recruiter. 
Evaluate how well the candidate's skills match the job's required and preferred skills.
Consider semantic similarities and implicit hierarchical relationships.
For example: 
- If the job requires 'Machine Learning', and the candidate has 'TensorFlow', 'PyTorch', or 'Pandas', consider it a HIGH match because those imply ML knowledge.
- If the job requires 'JavaScript', and the candidate has 'React', 'Node.js', or 'MongoDB', consider it a HIGH match.
- If the job requires 'SQL', and the candidate has 'PostgreSQL' or 'MySQL', consider it a HIGH match.

Also, consider management, leadership, and domain-specific skills for appropriate roles. 

Candidate Skills: {', '.join(candidate_skills)}
Job Required Skills (weight: 70%): {', '.join(required_skills)}
Job Preferred Skills (weight: 30%): {', '.join(preferred_skills)}
Role Type contextual info: {role_type}

Return ONLY a valid JSON object with a single key 'score' containing an integer from 0 to 100 representing the match percentage.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        result = json.loads(response.choices[0].message.content)
        return float(result.get("score", 0))
    except Exception as e:
        print(f"Error evaluating skills with LLM: {e}")
        # Fallback to simple matching if API fails
        return compute_skill_score_exact_match(candidate_skills, required_skills, preferred_skills)


def compute_skill_score_exact_match(candidate_skills: list[str], required_skills: list[str], preferred_skills: list[str]) -> float:
    c_set = set(s.lower() for s in candidate_skills)
    r_set = set(s.lower() for s in required_skills)
    p_set = set(s.lower() for s in preferred_skills)
    
    required_match = len(r_set & c_set) / len(r_set) if r_set else 1.0
    preferred_match = len(p_set & c_set) / len(p_set) if p_set else 0.5

    score = (required_match * 70) + (preferred_match * 30)
    return round(min(score, 100.0), 2)


def compute_skill_score(profile: CandidateProfile, job: Job) -> float:
    """
    Compute a 0-100 skill overlap score using semantic evaluation.
    """
    return evaluate_skills_with_llm(
        profile.skills or [],
        job.required_skills or [],
        job.preferred_skills or [],
        job.role_type or ""
    )


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
    # Reusing the LLM evaluation for a unified understanding of stack relevance
    stack_relevance_score = evaluate_skills_with_llm(
        profile.skills or [],
        job.required_skills or [],
        job.preferred_skills or [],
        job.role_type or ""
    )
    score += (stack_relevance_score / 100.0) * 25

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

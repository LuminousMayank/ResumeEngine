"""
FastAPI API Routes
Endpoints for job management, resume upload, and analysis results.
"""

import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Job, CandidateProfile, MatchResult
from ..schemas import JobOut, CandidateProfileOut, MatchResultOut, AnalysisResponse, HRExplanation
from ..config import get_settings
from ..services.job_ingestion import ingest_jobs_to_db, build_faiss_index, build_job_text
from ..services.resume_parser import extract_text, parse_resume_with_llm
from ..services.matching_engine import (
    check_eligibility,
    compute_skill_score,
    compute_signals_score,
    semantic_search,
    compute_final_score,
    categorize_fit,
)
from ..services.explanation import generate_hr_explanation
from ..services.embeddings import get_embeddings

settings = get_settings()
router = APIRouter()


# ──────────────────────── Job Endpoints ────────────────────────

@router.post("/jobs/ingest", tags=["Jobs"])
def ingest_jobs(db: Session = Depends(get_db)):
    """Read JSON/YAML files from the data directory and load them into the DB."""
    count = ingest_jobs_to_db(db)
    return {"message": f"Ingested {count} jobs into the database."}


@router.post("/jobs/build-index", tags=["Jobs"])
def build_index(db: Session = Depends(get_db)):
    """Build the FAISS vector index from all jobs in the database. Requires OpenAI API key."""
    id_map = build_faiss_index(db, get_embeddings)
    return {"message": f"Built FAISS index with {len(id_map)} job vectors."}


@router.get("/jobs", tags=["Jobs"], response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    """List all jobs currently in the database."""
    jobs = db.query(Job).all()
    return [
        JobOut(
            job_id=j.id,
            title=j.title,
            company=j.company,
            required_skills=j.required_skills or [],
            preferred_skills=j.preferred_skills or [],
            eligible_degrees=j.eligible_degrees or [],
            eligible_years=j.eligible_years or [],
            role_type=j.role_type or "",
            location=j.location or "",
            role_description=j.role_description or "",
        )
        for j in jobs
    ]


# ──────────────────────── Resume Upload & Analysis ────────────────────────

def _run_analysis(profile_id: int, db_url: str):
    """
    Background task: runs the full matching pipeline for a saved profile.
    This is designed to run in a background thread / worker.
    """
    from ..database import SessionLocal
    db = SessionLocal()

    try:
        profile = db.query(CandidateProfile).filter(CandidateProfile.id == profile_id).first()
        if not profile:
            return

        # 1. Generate candidate embedding from resume text
        candidate_text = profile.raw_text or ""
        candidate_embedding = get_embeddings([candidate_text])

        # 2. Semantic search against FAISS index
        semantic_results = semantic_search(candidate_embedding)
        semantic_map = {job_id: score for job_id, score in semantic_results}

        # 3. Score every job in the database
        all_jobs = db.query(Job).all()

        for job in all_jobs:
            # Eligibility
            eligibility = check_eligibility(profile, job)

            # Skip jobs that definitely don't match
            if eligibility == "Not Eligible":
                # Still save with zero scores for transparency
                match = MatchResult(
                    profile_id=profile.id,
                    job_id=job.id,
                    semantic_score=0,
                    skill_score=0,
                    signals_score=0,
                    final_fit_score=0,
                    eligibility_status=eligibility,
                    fit_category="Weak Match",
                    hr_explanation={
                        "why_fits": [],
                        "why_may_not_be_shortlisted": ["Did not meet basic eligibility requirements."],
                        "missing_skills": list(set(s.lower() for s in (job.required_skills or [])) - set(s.lower() for s in (profile.skills or []))),
                        "improvement_suggestions": [],
                    },
                )
                db.add(match)
                continue

            # Scores
            semantic_score = semantic_map.get(job.id, 30.0)
            skill_score = compute_skill_score(profile, job)
            signals_score = compute_signals_score(profile, job)
            final_score = compute_final_score(semantic_score, skill_score, signals_score)
            category = categorize_fit(final_score)

            # AI Explanation
            candidate_data = {
                "skills": profile.skills,
                "projects": profile.projects,
                "internships": profile.internships,
                "degree": profile.degree,
                "graduation_year": profile.graduation_year,
            }
            job_data = {
                "title": job.title,
                "company": job.company,
                "required_skills": job.required_skills,
                "preferred_skills": job.preferred_skills,
                "role_type": job.role_type,
                "role_description": job.role_description,
            }

            try:
                hr_explanation = generate_hr_explanation(candidate_data, job_data)
            except Exception:
                hr_explanation = {
                    "why_fits": [],
                    "why_may_not_be_shortlisted": [],
                    "missing_skills": [],
                    "improvement_suggestions": [],
                }

            match = MatchResult(
                profile_id=profile.id,
                job_id=job.id,
                semantic_score=semantic_score,
                skill_score=skill_score,
                signals_score=signals_score,
                final_fit_score=final_score,
                eligibility_status=eligibility,
                fit_category=category,
                hr_explanation=hr_explanation,
            )
            db.add(match)

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Analysis error: {e}")
    finally:
        db.close()


@router.post("/analyze", tags=["Analysis"])
async def analyze_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a resume (PDF/DOCX), parse it, and trigger the full matching pipeline.
    Returns the parsed profile immediately; match results are computed in the background.
    """
    # Validate file type
    filename = file.filename or "resume"
    if not (filename.lower().endswith(".pdf") or filename.lower().endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

    # Save uploaded file
    uploads_dir = settings.uploads_dir
    os.makedirs(uploads_dir, exist_ok=True)
    filepath = os.path.join(uploads_dir, filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract text
    try:
        raw_text = extract_text(filepath)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text from file: {str(e)}")

    # Parse with LLM
    try:
        parsed = parse_resume_with_llm(raw_text)
    except Exception as e:
        if "429" in str(e) or "Quota" in str(e) or "quota" in str(e):
            raise HTTPException(status_code=429, detail="Gemini API rate limit exceeded. Please try again later.")
        raise HTTPException(status_code=500, detail=f"Failed to parse resume with AI: {str(e)}")

    # Save profile to DB
    profile = CandidateProfile(
        filename=filename,
        raw_text=raw_text,
        skills=parsed.get("skills", []),
        projects=parsed.get("projects", []),
        internships=parsed.get("internships", 0),
        degree=parsed.get("degree", ""),
        graduation_year=parsed.get("graduation_year"),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # Trigger background analysis
    background_tasks.add_task(_run_analysis, profile.id, settings.database_url)

    return {
        "message": "Resume uploaded and parsed. Analysis is running in the background.",
        "profile_id": profile.id,
        "profile": {
            "skills": profile.skills,
            "projects": profile.projects,
            "internships": profile.internships,
            "degree": profile.degree,
            "graduation_year": profile.graduation_year,
        },
    }


@router.get("/results/{profile_id}", tags=["Analysis"], response_model=AnalysisResponse)
def get_results(profile_id: int, db: Session = Depends(get_db)):
    """
    Retrieve the analysis results for a given profile.
    Poll this endpoint until matches are populated.
    """
    profile = db.query(CandidateProfile).filter(CandidateProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    matches = (
        db.query(MatchResult)
        .filter(MatchResult.profile_id == profile_id)
        .order_by(MatchResult.final_fit_score.desc())
        .all()
    )

    profile_out = CandidateProfileOut(
        id=profile.id,
        filename=profile.filename or "",
        skills=profile.skills or [],
        projects=profile.projects or [],
        internships=profile.internships or 0,
        degree=profile.degree or "",
        graduation_year=profile.graduation_year,
    )

    match_results = []
    for m in matches:
        job = m.job
        job_out = JobOut(
            job_id=job.id,
            title=job.title,
            company=job.company,
            required_skills=job.required_skills or [],
            preferred_skills=job.preferred_skills or [],
            eligible_degrees=job.eligible_degrees or [],
            eligible_years=job.eligible_years or [],
            role_type=job.role_type or "",
            location=job.location or "",
            role_description=job.role_description or "",
        )

        explanation = m.hr_explanation or {}
        hr = HRExplanation(
            why_fits=explanation.get("why_fits", []),
            why_may_not_be_shortlisted=explanation.get("why_may_not_be_shortlisted", []),
            missing_skills=explanation.get("missing_skills", []),
            improvement_suggestions=explanation.get("improvement_suggestions", []),
        )

        match_results.append(MatchResultOut(
            job=job_out,
            semantic_score=m.semantic_score or 0,
            skill_score=m.skill_score or 0,
            signals_score=m.signals_score or 0,
            final_fit_score=m.final_fit_score or 0,
            eligibility_status=m.eligibility_status or "",
            fit_category=m.fit_category or "",
            hr_explanation=hr,
        ))

    return AnalysisResponse(profile=profile_out, matches=match_results)

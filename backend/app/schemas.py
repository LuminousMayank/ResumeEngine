from pydantic import BaseModel
from typing import List, Optional


# ---------- Job Schemas ----------

class JobBase(BaseModel):
    job_id: str
    title: str
    company: str
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    eligible_degrees: List[str] = []
    eligible_years: List[int] = []
    role_type: str = "internship"
    location: str = ""
    role_description: str = ""


class JobOut(JobBase):
    """Returned to the frontend."""
    class Config:
        from_attributes = True


# ---------- Candidate Schemas ----------

class CandidateProfileParsed(BaseModel):
    """Structured data extracted from a resume by the LLM."""
    skills: List[str] = []
    projects: List[str] = []
    internships: int = 0
    degree: str = ""
    graduation_year: Optional[int] = None


class CandidateProfileOut(CandidateProfileParsed):
    id: int
    filename: str

    class Config:
        from_attributes = True


# ---------- Match / Result Schemas ----------

class HRExplanation(BaseModel):
    why_fits: List[str] = []
    why_may_not_be_shortlisted: List[str] = []
    missing_skills: List[str] = []
    improvement_suggestions: List[str] = []


class MatchResultOut(BaseModel):
    job: JobOut
    semantic_score: float
    skill_score: float
    signals_score: float
    final_fit_score: float
    eligibility_status: str
    fit_category: str
    hr_explanation: HRExplanation

    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    """Top-level response returned to the student dashboard."""
    profile: CandidateProfileOut
    matches: List[MatchResultOut]

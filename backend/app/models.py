from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)  # job_id from JSON/YAML
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    required_skills = Column(JSON)       # stored as JSON list
    preferred_skills = Column(JSON)      # stored as JSON list
    eligible_degrees = Column(JSON)      # stored as JSON list
    eligible_years = Column(JSON)        # stored as JSON list of ints
    role_type = Column(String)           # "internship" | "fulltime"
    location = Column(String)
    role_description = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String)
    raw_text = Column(Text)              # full extracted resume text
    skills = Column(JSON)                # parsed skill list
    projects = Column(JSON)              # parsed project list
    internships = Column(Integer, default=0)
    degree = Column(String)
    graduation_year = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    matches = relationship("MatchResult", back_populates="profile")


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"))
    job_id = Column(String, ForeignKey("jobs.id"))

    semantic_score = Column(Float)
    skill_score = Column(Float)
    signals_score = Column(Float)
    final_fit_score = Column(Float)

    eligibility_status = Column(String)  # "Eligible" | "Partially Eligible" | "Not Eligible"
    fit_category = Column(String)        # "Strong Match" | "Good Match" | "Stretch Match" | "Weak Match"

    hr_explanation = Column(JSON)        # {why_fits, why_may_not_be_shortlisted, missing_skills, improvement_suggestions}

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    profile = relationship("CandidateProfile", back_populates="matches")
    job = relationship("Job")

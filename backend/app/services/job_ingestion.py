"""
Job Data Ingestion Service
Loads jobs from local JSON and YAML files into the database and builds the FAISS index.
"""

import json
import os
import yaml
import numpy as np
import faiss
from sqlalchemy.orm import Session

from ..models import Job
from ..config import get_settings

settings = get_settings()


def _read_jobs_from_file(filepath: str) -> list[dict]:
    """Read a single JSON or YAML file and return a list of job dicts."""
    ext = os.path.splitext(filepath)[1].lower()
    with open(filepath, "r") as f:
        if ext == ".json":
            data = json.load(f)
        elif ext in (".yaml", ".yml"):
            data = yaml.safe_load(f)
        else:
            return []

    # Support both top-level list and {"jobs": [...]} wrapper
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "jobs" in data:
        return data["jobs"]
    return []


def load_all_jobs_from_files() -> list[dict]:
    """Scan the jobs data directory and merge all job entries."""
    jobs_dir = settings.jobs_data_dir
    all_jobs: list[dict] = []

    if not os.path.isdir(jobs_dir):
        os.makedirs(jobs_dir, exist_ok=True)
        return all_jobs

    for filename in os.listdir(jobs_dir):
        filepath = os.path.join(jobs_dir, filename)
        if os.path.isfile(filepath):
            all_jobs.extend(_read_jobs_from_file(filepath))

    return all_jobs


def ingest_jobs_to_db(db: Session) -> int:
    """
    Read job files, upsert into the database.
    Returns count of jobs ingested.
    """
    raw_jobs = load_all_jobs_from_files()
    count = 0

    for job_data in raw_jobs:
        job_id = job_data.get("job_id")
        if not job_id:
            continue

        existing = db.query(Job).filter(Job.id == job_id).first()
        if existing:
            # Update existing record
            existing.title = job_data.get("title", existing.title)
            existing.company = job_data.get("company", existing.company)
            existing.domain = job_data.get("domain", existing.domain)
            existing.required_skills = job_data.get("required_skills", [])
            existing.preferred_skills = job_data.get("preferred_skills", [])
            existing.eligible_degrees = job_data.get("eligible_degrees", [])
            existing.eligible_years = job_data.get("eligible_years", [])
            existing.role_type = job_data.get("role_type", "internship")
            existing.location = job_data.get("location", "")
            existing.role_description = job_data.get("role_description", "")
        else:
            new_job = Job(
                id=job_id,
                title=job_data.get("title", ""),
                company=job_data.get("company", ""),
                domain=job_data.get("domain", ""),
                required_skills=job_data.get("required_skills", []),
                preferred_skills=job_data.get("preferred_skills", []),
                eligible_degrees=job_data.get("eligible_degrees", []),
                eligible_years=job_data.get("eligible_years", []),
                role_type=job_data.get("role_type", "internship"),
                location=job_data.get("location", ""),
                role_description=job_data.get("role_description", ""),
            )
            db.add(new_job)

        count += 1

    db.commit()
    return count


def build_job_text(job: Job) -> str:
    """Concatenate job fields into a single text string for embedding."""
    parts = [
        f"Title: {job.title}",
        f"Company: {job.company}",
        f"Role Type: {job.role_type}",
        f"Location: {job.location}",
        f"Required Skills: {', '.join(job.required_skills or [])}",
        f"Preferred Skills: {', '.join(job.preferred_skills or [])}",
        f"Description: {job.role_description}",
    ]
    return "\n".join(parts)


def build_faiss_index(db: Session, get_embeddings_fn) -> dict:
    """
    Build a FAISS index from all jobs in the database.
    get_embeddings_fn: callable that takes list[str] and returns np.ndarray of shape (n, dim)
    Returns a mapping from faiss row index -> job_id.
    """
    jobs = db.query(Job).all()
    if not jobs:
        return {}

    texts = [build_job_text(j) for j in jobs]
    embeddings = get_embeddings_fn(texts)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner Product (cosine sim if vectors are normalized)

    # L2 normalize for cosine similarity
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    # Save index to disk
    index_dir = settings.faiss_index_path
    os.makedirs(index_dir, exist_ok=True)
    faiss.write_index(index, os.path.join(index_dir, "jobs.index"))

    # Save mapping
    id_map = {i: jobs[i].id for i in range(len(jobs))}
    with open(os.path.join(index_dir, "id_map.json"), "w") as f:
        json.dump(id_map, f)

    return id_map

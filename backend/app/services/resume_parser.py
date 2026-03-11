"""
Resume Parsing Service
Extracts text from PDF/DOCX and uses the LLM to produce structured candidate data.
"""

import json
import fitz  # PyMuPDF
from docx import Document
from openai import OpenAI

from ..config import get_settings

settings = get_settings()

RESUME_PARSE_SYSTEM_PROMPT = """You are an expert technical and executive recruiter matching service.
Your sole task is to extract specific information from a candidate's resume text and format it into a strict JSON structure.
Do not hallucinate skills. Do not include any surrounding conversational text, return ONLY valid JSON.

CRITICAL INSTRUCTION: IMPLICIT SKILL EXPANSION
If a candidate lists a specific framework, tool, or library (e.g., Pandas, Scikit-learn, React, MongoDB, Firebase), you MUST explicitly infer and append the foundational "parent" skills that it implies (e.g., Machine Learning, Frontend, JavaScript, Databases, NoSQL) into their skills list.

Format Required:
{
  "candidate_name": "<the full name of the candidate, e.g., 'John Doe'>",
  "domain": "<the primary domain of the candidate's profile, e.g., 'Tech', 'Management', 'Law', 'Marketing', 'Finance', 'Design'>",
  "skills": ["<list of all technical, management, and leadership skills identified, including inferred parent skills>"],
  "projects": ["<list of project names or short descriptions>"],
  "internships": <integer, count of distinct internships found>,
  "degree": "<the primary degree, e.g., 'B.Tech CSE'>",
  "graduation_year": <integer, e.g., 2027. Infer from dates if not explicit>
}"""


def extract_text_from_pdf(filepath: str) -> str:
    """Extract all text from a PDF file using PyMuPDF."""
    doc = fitz.open(filepath)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def extract_text_from_docx(filepath: str) -> str:
    """Extract all text from a DOCX file."""
    doc = Document(filepath)
    return "\n".join([para.text for para in doc.paragraphs])


def extract_text(filepath: str) -> str:
    """Route to the correct extractor based on file extension."""
    lower = filepath.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(filepath)
    elif lower.endswith(".docx"):
        return extract_text_from_docx(filepath)
    else:
        raise ValueError(f"Unsupported file type: {filepath}")


from app.services.skill_graph import get_expanded_skills

def parse_resume_with_llm(raw_text: str) -> dict:
    """
    Send resume text to the LLM and get back structured candidate JSON.
    Returns a dict with keys: skills, projects, internships, degree, graduation_year
    """
    client = OpenAI(api_key=settings.openai_api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": RESUME_PARSE_SYSTEM_PROMPT},
            {"role": "user", "content": raw_text}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    parsed_data = json.loads(response.choices[0].message.content)
    
    # Deterministic Skill Graph Expansion
    extracted_skills = parsed_data.get("skills", [])
    if isinstance(extracted_skills, list):
        expanded_skills = get_expanded_skills(extracted_skills)
        # Combine and deduplicate
        parsed_data["skills"] = list(set(extracted_skills + expanded_skills))
        
    return parsed_data

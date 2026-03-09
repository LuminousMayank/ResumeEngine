"""
Resume Parsing Service
Extracts text from PDF/DOCX and uses the LLM to produce structured candidate data.
"""

import json
import fitz  # PyMuPDF
from docx import Document
import google.generativeai as genai

from ..config import get_settings

settings = get_settings()

RESUME_PARSE_SYSTEM_PROMPT = """You are an expert technical recruiter matching service.
Your sole task is to extract specific information from a candidate's resume text and format it into a strict JSON structure.
Do not hallucinate skills. Do not include any surrounding conversational text, return ONLY valid JSON.

Format Required:
{
  "skills": ["<list of all technical and soft skills identified>"],
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


def parse_resume_with_llm(raw_text: str) -> dict:
    """
    Send resume text to the LLM and get back structured candidate JSON.
    Returns a dict with keys: skills, projects, internships, degree, graduation_year
    """
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("models/gemini-2.5-flash", system_instruction=RESUME_PARSE_SYSTEM_PROMPT)

    response = model.generate_content(
        raw_text,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1
        )
    )

    return json.loads(response.text)

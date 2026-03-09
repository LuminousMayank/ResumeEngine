"""
AI Explanation Layer
Uses a FAANG HR Manager persona to generate structured feedback for each job match.
"""

import json
import google.generativeai as genai
from ..config import get_settings

settings = get_settings()


HR_EXPLANATION_SYSTEM_PROMPT = """Act as an experienced FAANG HR Manager evaluating a candidate for a specific role.
I will provide you with a 'Candidate Profile' and a 'Job Listing'.
Analyze the gap between the candidate and the job requirements and provide actionable, direct, and constructive feedback.
Format your output as a JSON object with four exact keys: 'why_fits', 'why_may_not_be_shortlisted', 'missing_skills', and 'improvement_suggestions'.
Keep each point brief (one sentence max) and return them as arrays of strings.

Format Required:
{
  "why_fits": ["..."],
  "why_may_not_be_shortlisted": ["..."],
  "missing_skills": ["..."],
  "improvement_suggestions": ["..."]
}"""


def generate_hr_explanation(candidate_profile: dict, job_data: dict) -> dict:
    """
    Call the LLM with the HR persona prompt.
    Returns a dict with keys: why_fits, why_may_not_be_shortlisted, missing_skills, improvement_suggestions
    """
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("models/gemini-2.5-flash", system_instruction=HR_EXPLANATION_SYSTEM_PROMPT)

    user_message = (
        f"Candidate Profile:\n{json.dumps(candidate_profile, indent=2)}\n\n"
        f"Job Listing:\n{json.dumps(job_data, indent=2)}"
    )

    response = model.generate_content(
        user_message,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.3
        )
    )

    return json.loads(response.text)

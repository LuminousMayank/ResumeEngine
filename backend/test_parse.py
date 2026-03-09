import json
import google.generativeai as genai
from app.config import get_settings

settings = get_settings()
genai.configure(api_key=settings.gemini_api_key)

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

model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=RESUME_PARSE_SYSTEM_PROMPT)

raw_text = "John Doe. B.Tech CSE 2025. Skills: Python, React. Internships: Google, Meta. Projects: Chatbot."

print("Testing Gemini...")
response = model.generate_content(
    raw_text,
    generation_config=genai.GenerationConfig(
        response_mime_type="application/json",
        temperature=0.1
    )
)
print("Response:", response.text)
try:
    print("Parsed JSON:", json.loads(response.text))
except Exception as e:
    print("Error:", e)

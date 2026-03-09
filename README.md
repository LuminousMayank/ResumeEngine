# Caarya Job Fit Engine (Resume Analyzer) 🚀

An AI-powered application designed to seamlessly match candidates’ resumes against job openings. The system extracts structured candidate profiles from uploaded PDFs or DOCX files and leverages standard machine learning along with Advanced LLM explanations to score candidates accurately.

---

## 🏗️ Architecture & Features

The platform evaluates resumes utilizing three core "scores" which generate a final fit percentage.

1. **Semantic Match (40%)**: Embeds job descriptions and candidate resumes into vector space using FAISS to measure pure topical and conceptual similarities.
2. **Skill Match (35%)**: Direct matching and extraction of the candidate's skills leveraging the Gemini 2.5 Flash LLM, checking against Required and Preferred job skills.
3. **Signal & Heuristics Match (25%)**: Evaluates recruiter rules, counting projects, internships, and calculating degree/graduation year eligibility.

### Full Walkthrough Pipeline
1. **Upload Phase**: A candidate drops their resume on the Next.js frontend GUI.
2. **Extraction Engine**: Text is extracted locally strictly using PyMuPDF (for PDFs) and `python-docx` (for Word documents). 
3. **LLM Parsing**: A call to Google's Gemini Flash AI translates the raw text into structured JSON `CandidateProfiles` stored into the SQLite DB.
4. **Vector Search / FAISS**: Candidate structures are compared against pre-computed Job Vectors. 
5. **Generative Explanation**: AI synthesizes the scores into an HR-friendly explanation of "Why you fit", "Concerns", and "Missing skills". 

---

## 🛠️ Technology Stack

**Frontend**
- **Framework**: Next.js 16 (App Router)
- **UI & Styling**: React 19, custom CSS modules (Retro Dawn Aesthetic & Glassmorphism)
- **State**: React Hooks with aggressive polling for background DB results

**Backend**
- **Framework**: FastAPI (Python)
- **Database**: SQLite / SQLAlchemy ORM
- **LLM/AI Model**: Google Gemini API (`models/gemini-2.5-flash`)
- **Vector Search**: Meta FAISS (Facebook AI Similarity Search)
- **Async Tasks**: FastAPI BackgroundTasks built-in worker (easily upgradeable to Redis/Celery)
- **PDF Parsing**: PyMuPDF (`fitz`) & `python-docx`

---

## 🚀 Getting Started

### 1. Requirements
Ensure you have Python 3.9+ and Node.js v18+ installed on your computer.

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///./caarya_job_fit.db
```

Launch the FastAPI engine on port 8080:
```bash
uvicorn app.main:app --port 8080 --reload
```

### 3. Frontend Setup
In a new terminal, launch the Next.js app:
```bash
cd frontend
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to upload your resume!

---

*Built with ❤️ for LuminousMayank and the Caarya AI Job Fit Pipeline.*

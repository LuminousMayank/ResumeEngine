"use client";

import { useState, useRef, useCallback, useEffect } from "react";

// ─── Types ───
interface Profile {
  id: number;
  filename: string;
  skills: string[];
  projects: string[];
  internships: number;
  degree: string;
  graduation_year: number | null;
}

interface HRExplanation {
  why_fits: string[];
  why_may_not_be_shortlisted: string[];
  missing_skills: string[];
  improvement_suggestions: string[];
}

interface JobInfo {
  job_id: string;
  title: string;
  company: string;
  required_skills: string[];
  preferred_skills: string[];
  eligible_degrees: string[];
  eligible_years: number[];
  role_type: string;
  location: string;
  role_description: string;
}

interface MatchResult {
  job: JobInfo;
  semantic_score: number;
  skill_score: number;
  signals_score: number;
  final_fit_score: number;
  eligibility_status: string;
  fit_category: string;
  hr_explanation: HRExplanation;
}

const API_BASE = "http://localhost:8080/api";

// ─── Score colors ───
const BAR_COLORS: Record<string, string> = {
  semantic: "#2B4BFF",
  skill: "#FF2D78",
  signals: "#00D4C8",
};

function getScoreBg(score: number): string {
  if (score >= 85) return "#B8FF47";
  if (score >= 70) return "#FFE600";
  if (score >= 50) return "#00D4C8";
  return "#FF2D78";
}

function getFitClass(cat: string): string {
  if (cat === "Strong Match") return "fit-strong";
  if (cat === "Good Match") return "fit-good";
  if (cat === "Stretch Match") return "fit-stretch";
  return "fit-weak";
}

function getEligClass(status: string): string {
  if (status === "Eligible") return "elig-eligible";
  if (status === "Partially Eligible") return "elig-partial";
  return "elig-inelig";
}

// ─── Score Retro Bar ───
function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="score-bar-item">
      <div className="score-bar-label">
        <span>{label}</span>
        <span style={{ fontStyle: "italic" }}>{value.toFixed(0)}%</span>
      </div>
      <div className="score-bar-track">
        <div
          className="score-bar-fill"
          style={{ width: `${Math.min(value, 100)}%`, background: color }}
        />
      </div>
    </div>
  );
}

// ─── Job Card ───
function JobCard({ match, index }: { match: MatchResult; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const { job, hr_explanation: hr } = match;

  return (
    <div className="job-card">
      <div className="job-card-header" onClick={() => setExpanded(!expanded)}>
        <div className="job-card-info">
          <h3>{job.title}</h3>
          <div className="job-card-meta">
            <span className="meta-chip">🏢 {job.company}</span>
            <span className="meta-chip">📍 {job.location}</span>
            <span className="meta-chip">💼 {job.role_type}</span>
            <span className={`elig-chip ${getEligClass(match.eligibility_status)}`}>
              {match.eligibility_status}
            </span>
          </div>
        </div>

        <div className="score-sticker">
          <div
            className="score-circle"
            style={{ background: getScoreBg(match.final_fit_score) }}
          >
            {Math.round(match.final_fit_score)}%
          </div>
          <span className={`fit-label ${getFitClass(match.fit_category)}`}>
            {match.fit_category}
          </span>
        </div>
      </div>

      {expanded && (
        <div className="job-card-details">
          {/* Score Bars */}
          <div className="score-bars">
            <ScoreBar label="Semantic Match" value={match.semantic_score} color={BAR_COLORS.semantic} />
            <ScoreBar label="Skill Match" value={match.skill_score} color={BAR_COLORS.skill} />
            <ScoreBar label="Recruiter Signals" value={match.signals_score} color={BAR_COLORS.signals} />
          </div>

          {/* Explanation */}
          <div className="explanation-grid">
            {hr.why_fits.length > 0 && (
              <div className="explanation-block pros">
                <h4>✅ Why You Fit</h4>
                <ul className="explanation-list">
                  {hr.why_fits.map((t, i) => <li key={i}>{t}</li>)}
                </ul>
              </div>
            )}
            {hr.why_may_not_be_shortlisted.length > 0 && (
              <div className="explanation-block cons">
                <h4>⚠️ Concerns</h4>
                <ul className="explanation-list">
                  {hr.why_may_not_be_shortlisted.map((t, i) => <li key={i}>{t}</li>)}
                </ul>
              </div>
            )}
            {hr.missing_skills.length > 0 && (
              <div className="explanation-block missing">
                <h4>📋 Missing Skills</h4>
                <ul className="explanation-list">
                  {hr.missing_skills.map((t, i) => <li key={i}>{t}</li>)}
                </ul>
              </div>
            )}
            {hr.improvement_suggestions.length > 0 && (
              <div className="explanation-block tips">
                <h4>💡 Level Up</h4>
                <ul className="explanation-list">
                  {hr.improvement_suggestions.map((t, i) => <li key={i}>{t}</li>)}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ───
export default function Home() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [matches, setMatches] = useState<MatchResult[]>([]);

  const handleUpload = useCallback(async (file: File) => {
    setError(null); setUploading(true); setProfile(null); setMatches([]);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_BASE}/analyze`, { method: "POST", body: formData });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Upload failed"); }
      const data = await res.json();
      setProfile({ id: data.profile_id, filename: file.name, ...data.profile });
      setUploading(false); setPolling(true);
    } catch (err: unknown) {
      setUploading(false);
      setError(err instanceof Error ? err.message : "Something went wrong");
    }
  }, []);

  useEffect(() => {
    if (!polling || !profile) return;
    const iv = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/results/${profile.id}`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.matches?.length > 0) { setMatches(data.matches); setPolling(false); }
      } catch { /* keep polling */ }
    }, 2000);
    return () => clearInterval(iv);
  }, [polling, profile]);

  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragging(true); };
  const onDragLeave = () => setDragging(false);
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer.files?.[0]; if (file) handleUpload(file);
  };
  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (file) handleUpload(file);
  };

  return (
    <>
      {/* Decorative fixed elements */}
      <div className="deco deco-triangle-1" />
      <div className="deco deco-circle-1" />
      <div className="deco deco-zigzag">≋≋≋</div>

      {/* ─── Header ─── */}
      <header className="header">
        <div className="header-inner">
          <h1>Caarya <span>Job Fit</span> Engine</h1>
          <div className="header-sub">⚡ AI-Powered Resume Matching</div>
        </div>
      </header>

      <div className="app-container" style={{ position: "relative", zIndex: 1 }}>

        {/* Error */}
        {error && (
          <div className="error-banner">
            ⛔ ERROR: {error}
          </div>
        )}

        {/* ─── Upload ─── */}
        <section className="upload-section">
          <h2 className="section-title">Upload Resume</h2>
          <div
            className={`upload-zone${dragging ? " dragging" : ""}${uploading ? " uploading" : ""}`}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <span className="upload-icon">{uploading ? "⚙️" : "📁"}</span>
            <h3>{uploading ? "Crunching your resume..." : "Drop it like it's hot"}</h3>
            <p>{uploading ? "This might take a second — AI is thinking..." : "PDF or DOCX — click or drag & drop"}</p>
            {uploading && (
              <div className="loading-container" style={{ padding: "20px 0 0", gap: 12 }}>
                <div className="spinner-retro" />
              </div>
            )}
            <input ref={fileInputRef} type="file" accept=".pdf,.docx" onChange={onFileChange} />
          </div>
        </section>

        {/* ─── Profile ─── */}
        {profile && (
          <section className="profile-section">
            <h2 className="section-title">Your Profile</h2>
            <div className="profile-card">
              <div className="profile-grid">
                <div className="profile-field">
                  <div className="profile-label">Degree</div>
                  <div className="profile-value">{profile.degree || "—"}</div>
                </div>
                <div className="profile-field">
                  <div className="profile-label">Grad Year</div>
                  <div className="profile-value">{profile.graduation_year ?? "—"}</div>
                </div>
                <div className="profile-field">
                  <div className="profile-label">Internships</div>
                  <div className="profile-value">{profile.internships}</div>
                </div>
                <div className="profile-field">
                  <div className="profile-label">Projects</div>
                  <div className="profile-value">{profile.projects.length}</div>
                </div>
              </div>

              <div style={{ marginTop: 20 }}>
                <div className="profile-label" style={{ marginBottom: 8 }}>Skills</div>
                <div className="skill-tags">
                  {profile.skills.map((s, i) => (
                    <span className="skill-tag" key={i}>{s}</span>
                  ))}
                </div>
              </div>

              {profile.projects.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <div className="profile-label" style={{ marginBottom: 8 }}>Projects</div>
                  <div className="skill-tags">
                    {profile.projects.map((p, i) => (
                      <span className="skill-tag purple" key={i}>{p}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* ─── Polling ─── */}
        {polling && (
          <div className="loading-container">
            <div className="spinner-retro" />
            <div className="loading-text">AI Matching Engine is Running...</div>
          </div>
        )}

        {/* ─── Results ─── */}
        {matches.length > 0 && (
          <section className="results-section">
            <div className="results-header">
              <h2 className="section-title" style={{ marginBottom: 0 }}>Your Matches</h2>
              <div className="results-count">{matches.length} roles analyzed</div>
            </div>
            <div className="job-cards">
              {matches.map((m, i) => (
                <JobCard key={m.job.job_id} match={m} index={i} />
              ))}
            </div>
          </section>
        )}

      </div>
    </>
  );
}

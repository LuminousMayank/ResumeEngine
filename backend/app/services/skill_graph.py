"""
Explicit mapping of specific tools, libraries, and frameworks to their broader
foundational "parent" skills. This is used to deterministically expand a candidate's
skill set during resume parsing so that the matching engine can fairly evaluate them
against high-level job requirements (e.g., matching a candidate with "Pandas" to a 
job requiring "Machine Learning").
"""

IMPLICIT_SKILL_GRAPH = {
    # Data Science & Machine Learning
    "pandas": ["Data Analysis", "Python", "Machine Learning", "Data Science"],
    "numpy": ["Data Analysis", "Python", "Data Science"],
    "scikit-learn": ["Machine Learning", "Python", "Data Science"],
    "matplotlib": ["Data Visualization", "Python"],
    "seaborn": ["Data Visualization", "Python"],
    "jupyter": ["Data Science", "Python"],
    
    # Deep Learning & AI
    "tensorflow": ["Deep Learning", "Machine Learning", "Python", "Artificial Intelligence", "Neural Networks"],
    "pytorch": ["Deep Learning", "Machine Learning", "Python", "Artificial Intelligence", "Neural Networks"],
    "keras": ["Deep Learning", "Machine Learning", "Python", "Neural Networks"],
    "huggingface": ["NLP", "Machine Learning", "Deep Learning", "Transformers"],
    "transformers": ["NLP", "Deep Learning", "Machine Learning"],
    
    # Generative AI & LLM Engineering (Based on requested jobs)
    "langchain": ["Generative AI", "LLMs", "AI Agents", "Python", "RAG"],
    "langgraph": ["Generative AI", "LLMs", "AI Agents", "Python", "Multi-Agent Systems"],
    "langsmith": ["LLMOps", "Generative AI", "Observability"],
    "crewai": ["Generative AI", "AI Agents", "Multi-Agent Systems", "Python"],
    "openai api": ["Generative AI", "LLMs", "API Integration", "Prompt Engineering"],
    "gemini api": ["Generative AI", "LLMs", "API Integration", "Prompt Engineering"],
    "claude api": ["Generative AI", "LLMs", "API Integration", "Prompt Engineering"],
    "pinecone": ["Vector Databases", "Generative AI", "RAG", "Semantic Search"],
    "pgvector": ["Vector Databases", "PostgreSQL", "Generative AI", "RAG"],
    "qdrant": ["Vector Databases", "Generative AI", "RAG"],
    "weaviate": ["Vector Databases", "Generative AI", "RAG"],

    # Frontend
    "react": ["Frontend", "JavaScript", "UI/UX", "Web Development"],
    "react.js": ["Frontend", "JavaScript", "UI/UX", "Web Development"],
    "reactjs": ["Frontend", "JavaScript", "UI/UX", "Web Development"],
    "angular": ["Frontend", "JavaScript", "TypeScript", "Web Development"],
    "vue": ["Frontend", "JavaScript", "Web Development"],
    "next.js": ["Frontend", "JavaScript", "React", "Web Development", "Full Stack"],
    "html": ["Frontend", "Web Development"],
    "css": ["Frontend", "Web UI", "Web Development"],
    "tailwind": ["Frontend", "CSS", "UI Design"],
    "bootstrap": ["Frontend", "CSS"],
    
    # Backend & Frameworks
    "node.js": ["Backend", "JavaScript", "API Development"],
    "nodejs": ["Backend", "JavaScript", "API Development"],
    "express": ["Backend", "JavaScript", "Node.js", "API Development"],
    "django": ["Backend", "Python", "Web Development", "API Development"],
    "flask": ["Backend", "Python", "API Development"],
    "fastapi": ["Backend", "Python", "API Development", "REST"],
    "spring boot": ["Backend", "Java", "Enterprise Architecture"],
    "ruby on rails": ["Backend", "Ruby", "Web Development"],
    
    # Databases
    "mongodb": ["Database", "NoSQL", "JavaScript", "Backend"],
    "firebase": ["Database", "NoSQL", "Backend", "Cloud Services"],
    "postgresql": ["Database", "SQL", "Relational Databases", "Backend"],
    "mysql": ["Database", "SQL", "Relational Databases", "Backend"],
    "sqlite": ["Database", "SQL"],
    "redis": ["Caching", "Database", "NoSQL", "Backend"],
    "cassandra": ["Database", "NoSQL", "Big Data"],
    
    # Cloud & DevOps
    "aws": ["Cloud Computing", "DevOps", "Infrastructure"],
    "azure": ["Cloud Computing", "DevOps", "Infrastructure"],
    "gcp": ["Cloud Computing", "DevOps", "Infrastructure"],
    "docker": ["DevOps", "Containerization", "Cloud Computing"],
    "kubernetes": ["DevOps", "Container Orchestration", "Cloud Computing"],
    "jenkins": ["DevOps", "CI/CD"],
    "github actions": ["DevOps", "CI/CD"],
    "terraform": ["DevOps", "Infrastructure as Code", "Cloud Computing"],
    
    # Mobile
    "flutter": ["Mobile Development", "Dart", "Cross-Platform", "Frontend"],
    "react native": ["Mobile Development", "JavaScript", "React", "Cross-Platform", "Frontend"],
    "swift": ["Mobile Development", "iOS Development"],
    "kotlin": ["Mobile Development", "Android Development"],
    
    # Core Languages (when implying stacks)
    "javascript": ["Web Development", "Frontend"],
    "typescript": ["Web Development", "Frontend", "JavaScript"],
    "python": ["Backend", "Scripting", "Data Science"],
}

def get_expanded_skills(candidate_skills: list[str]) -> list[str]:
    """
    Takes a list of specific skills and returns a comprehensively expanded list
    that includes inferred parent/category skills based on IMPLICIT_SKILL_GRAPH.
    """
    if not candidate_skills:
        return []

    expanded = set(candidate_skills)
    
    # Normalize input skills to lowercase to match against the graph keys
    normalized_skills = [s.lower().strip() for s in candidate_skills]
    
    for skill in normalized_skills:
        if skill in IMPLICIT_SKILL_GRAPH:
            # If a mapping exists, add all parent skills to the set
            for parent_skill in IMPLICIT_SKILL_GRAPH[skill]:
                expanded.add(parent_skill)
                
    return list(expanded)

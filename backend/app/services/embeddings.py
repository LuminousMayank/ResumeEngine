"""
Embedding utility — wraps OpenAI embeddings API.
"""

import numpy as np
import google.generativeai as genai
from ..config import get_settings

settings = get_settings()


def get_embeddings(texts: list[str]) -> np.ndarray:
    """
    Generate embeddings for a list of texts using Gemini's embedding model.
    Returns numpy array of shape (len(texts), embedding_dim).
    """
    genai.configure(api_key=settings.gemini_api_key)

    embeddings = []
    # Gemini's embed_content can take a list of strings natively
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=texts,
        task_type="retrieval_document",
    )
    
    # If the response contains a list of embeddings
    embeddings = result['embedding']
    
    return np.array(embeddings, dtype=np.float32)

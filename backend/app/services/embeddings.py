"""
Embedding utility — wraps OpenAI embeddings API.
"""

import numpy as np
from openai import OpenAI
from ..config import get_settings

settings = get_settings()


def get_embeddings(texts: list[str]) -> np.ndarray:
    """
    Generate embeddings for a list of texts using OpenAI's embedding model.
    Returns numpy array of shape (len(texts), embedding_dim).
    """
    client = OpenAI(api_key=settings.openai_api_key)

    # OpenAI's embeddings.create can take a list of strings natively
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    
    # Extract embeddings from the response
    embeddings = [item.embedding for item in response.data]
    
    return np.array(embeddings, dtype=np.float32)

import numpy as np

def get_image_embedding(image_path_or_bytes):
    """
    MOCKED due to Render 512MB RAM limits. 
    Loading the 600MB PyTorch CLIP model will crash the free tier server.
    Returns a dummy 32-byte embedding to satisfy the database schema.
    """
    return np.zeros(32, dtype=np.float32).tobytes()

def calculate_similarity(embedding_bytes1, embedding_bytes2):
    """
    MOCKED due to Render 512MB RAM limits.
    Image similarity detection is disabled on the free tier to prevent crashes.
    """
    return 0.0

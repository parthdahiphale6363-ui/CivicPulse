import io
import torch
import numpy as np
from PIL import Image
from sentence_transformers import SentenceTransformer, util

# Load the model only once at startup
# 'clip-ViT-B-32' is fast and relatively lightweight (~600MB)
cv_model = SentenceTransformer('clip-ViT-B-32')

def get_image_embedding(image_path_or_bytes):
    """Generates a semantic embedding vector for a given image."""
    try:
        if isinstance(image_path_or_bytes, bytes):
            img = Image.open(io.BytesIO(image_path_or_bytes))
        else:
            img = Image.open(image_path_or_bytes)
        
        # Ensure image is in RGB format
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        embedding = cv_model.encode(img, convert_to_tensor=True)
        return embedding.cpu().numpy().tobytes() # Return bytes for SQLite BLOB
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def calculate_similarity(embedding_bytes1, embedding_bytes2):
    """Calculates cosine similarity between two stored embeddings."""
    if not embedding_bytes1 or not embedding_bytes2:
        return 0.0
        
    emb1 = torch.tensor(np.frombuffer(embedding_bytes1, dtype=np.float32))
    emb2 = torch.tensor(np.frombuffer(embedding_bytes2, dtype=np.float32))
    
    # Ensure they are 2D tensors for cos_sim
    if len(emb1.shape) == 1:
        emb1 = emb1.unsqueeze(0)
    if len(emb2.shape) == 1:
        emb2 = emb2.unsqueeze(0)
        
    similarity = util.cos_sim(emb1, emb2).item()
    return similarity

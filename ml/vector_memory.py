try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
except Exception:
    faiss = None
    np = None
    SentenceTransformer = None

class VectorMemory:
    """Simple local FAISS-backed memory with graceful fallback.

    If `faiss` or `sentence-transformers` are not available this class
    falls back to an in-memory text store and returns recent items.
    """
    def __init__(self):
        self._ready = False
        self.text_store = []

        if SentenceTransformer is None or faiss is None:
            # Lightweight fallback
            self.model = None
            self.index = None
            self.dimension = 0
            return

        # Initialize embedding model and FAISS index
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        # dimension for the chosen model
        self.dimension = 384
        self.index = faiss.IndexFlatL2(self.dimension)
        self._ready = True

    def add(self, text: str):
        """Add a text item to memory."""
        if self._ready:
            emb = self.model.encode([text])
            vec = np.array(emb).astype("float32")
            self.index.add(vec)
            self.text_store.append(text)
        else:
            # fallback: append only
            self.text_store.append(text)

    def search(self, query: str, k: int = 3):
        """Search for similar texts. Returns up to `k` entries."""
        if self._ready:
            emb = self.model.encode([query])
            D, I = self.index.search(np.array(emb).astype("float32"), k)
            results = []
            for i in I[0]:
                if i < len(self.text_store):
                    results.append(self.text_store[i])
            return results

        # fallback: return last k items containing a token or recent history
        if not self.text_store:
            return []
        # naive substring matching, then pad with most recent
        matches = [t for t in self.text_store if query.split()[0] in t]
        if len(matches) >= k:
            return matches[:k]
        # pad with most recent
        tail = list(reversed(self.text_store))[:k]
        # ensure no duplicates
        out = []
        for m in matches + tail:
            if m not in out:
                out.append(m)
        return out[:k]

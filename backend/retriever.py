from typing import List, Dict, AsyncGenerator
from ollama import AsyncClient
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import json
from pathlib import Path
from config import BackendSettings, get_backend_settings


class DocumentRetriever:
    def __init__(
        self,
        persist_directory: str | None = None,
        settings: BackendSettings | None = None,
    ):
        self.settings = settings or get_backend_settings()

        if persist_directory is None:
            persist_directory = self.settings.faiss_persist_dir

        self.persist_directory = Path(persist_directory)
        self.index_file = self.persist_directory / "index.faiss"
        self.metadata_file = self.persist_directory / "metadata.pkl"
        self.texts_file = self.persist_directory / "texts.pkl"

        # Initialize index state
        self.index = None
        self.metadata = []
        self.texts = []

        # Try to load existing index
        self._load_index()

        # Load embedding model
        print("Loading embedding model...")
        self.model = SentenceTransformer(self.settings.sentence_transformer_model)

        # Initialize Ollama client
        self.ollama_client = AsyncClient(
            host=self.settings.ollama_host
        )

    def _load_index(self):
        """Load the FAISS index and associated data from disk."""
        if self.index_file.exists():
            print("Loading FAISS index...")
            self.index = faiss.read_index(str(self.index_file))

            with open(self.metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)

            with open(self.texts_file, 'rb') as f:
                self.texts = pickle.load(f)

            print(f"✓ Loaded {len(self.texts)} document chunks")
        else:
            print("No index found - please index documents first")
            self.index = None
            self.metadata = []
            self.texts = []

    def reload(self):
        """Reload the index from disk. Call after indexing completes."""
        print("Reloading index...")
        self._load_index()

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant documents"""
        if self.index is None:
            return []

        # Generate query embedding
        query_embedding = self.model.encode([query])
        query_vector = np.array(query_embedding).astype('float32')

        # Search FAISS index - get more results to account for deleted chunks
        search_k = top_k * 3  # Get extra results to filter
        distances, indices = self.index.search(query_vector, min(search_k, self.index.ntotal))

        # Build results, filtering out deleted chunks
        sources = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata):  # Valid index
                metadata = self.metadata[idx]
                # Skip deleted chunks
                if metadata.get('deleted', False):
                    continue

                sources.append({
                    "text": self.texts[idx],
                    "metadata": metadata,
                    "score": float(distances[0][i])
                })

                # Stop once we have enough non-deleted results
                if len(sources) >= top_k:
                    break

        return sources

    async def ask_streaming(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """Ask question with streaming response"""

        # Retrieve relevant context
        sources = self.search(query, top_k=5)

        # Build context from sources
        context = "\n\n".join([
            f"Source: {s['metadata']['file_name']}\n{s['text']}"
            for s in sources
        ])

        # Build messages
        messages = conversation_history or []
        messages.append({
            "role": "user",
            "content": f"""Based on the following documentation context, please answer the question.

            Context:
            {context}

            Question: {query}

            Please cite which files you're referencing in your answer."""
        })

        # First yield the sources
        yield json.dumps({
            "type": "sources",
            "data": [
                {
                    "file": s['metadata']['file_name'],
                    "path": s['metadata']['file_path'],
                    "chunk": s['metadata']['chunk_index']
                }
                for s in sources
            ]
        }) + "\n"

        # Stream the response
        num_predict = self.settings.max_tokens
        stream = await self.ollama_client.chat(
            model=self.settings.ollama_model,
            messages=messages,
            stream=True,
            options={"num_predict": num_predict}
        )
        async for chunk in stream:
            text = chunk.message.content
            if text:
                yield json.dumps({"type": "content", "data": text}) + "\n"
            if chunk.done and chunk.done_reason == "length":
                yield json.dumps({
                    "type": "truncated",
                    "data": {"reason": "max_tokens", "output_tokens": num_predict}
                }) + "\n"

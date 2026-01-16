from typing import List, Dict, AsyncGenerator
import anthropic
from chromadb import PersistentClient
import os
import json

class DocumentRetriever:
    def __init__(self, persist_directory: str = "./data/chroma_db"):
        self.client = PersistentClient(path=persist_directory)
        self.collection = self.client.get_collection(name="docs")
        self.anthropic_client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant documents"""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        sources = []
        for i in range(len(results['ids'][0])):
            sources.append({
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "score": results['distances'][0][i] if 'distances' in results else None
            })
        
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
        async with self.anthropic_client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=messages
        ) as stream:
            async for text in stream.text_stream:
                yield json.dumps({
                    "type": "content",
                    "data": text
                }) + "\n"
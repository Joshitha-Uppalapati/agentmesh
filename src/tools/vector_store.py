import logging
from typing import List

import chromadb

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, persist_directory: str = "data/chroma"):
        # Chroma 0.5 deprecated the old Client(Settings(...)) path.
        # This is the supported path going forward.
        self.client = chromadb.PersistentClient(path=persist_directory)

        # TODO(joshitha): collection schema is implicit right now.
        # If we ever mix embeddings from different models, this will silently degrade retrieval quality.
        self.collection = self.client.get_or_create_collection(name="agentmesh")

    def add_documents(self, docs: List[str]) -> None:
        if not docs:
            # Seen this happen when upstream filtering removes everything.
            # Not worth blowing up the pipeline for.
            logger.warning("vector_store.add_documents called with empty docs list")
            return

        try:
            ids = [f"doc_{i}" for i in range(len(docs))]
            self.collection.add(documents=docs, ids=ids)

        except Exception as e:
            # This used to be `except: pass` which made debugging impossible.
            # Chroma failures are usually path/permissions or embedding mismatch.
            logger.warning("vector_store.add_documents failed: %s", e)

    def query(self, query: str, k: int = 3) -> List[str]:
        try:
            result = self.collection.query(query_texts=[query], n_results=k)
            return result.get("documents", [[]])[0]

        except Exception as e:
            # Don't kill the whole graph because retrieval failed.
            # Investigator can still run without context.
            logger.warning("vector_store.query failed: %s", e)
            return []
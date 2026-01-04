# app/rag/retrieve.py

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.db.models import Return
from app.schemas import RetrievalQuery, RetrievalResult


class RAGRetriever:
    """
    Builds a vector index over return records and supports semantic search.
    READ-ONLY component.
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = None
        self.records = []

    def build_index(self):
        returns = self.db.query(Return).all()

        texts = []
        self.records = []

        for r in returns:
            text = (
                f"Product: {r.product_name}. "
                f"Store: {r.store_name}. "
                f"Reason: {r.reason_raw}. "
                f"Price: {r.price} {r.currency}."
            )
            texts.append(text)
            self.records.append(r)

        if not texts:
            return

        embeddings = self.model.encode(texts, convert_to_numpy=True)
        dim = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings)

    def retrieve(self, query: RetrievalQuery):
        if self.index is None:
            raise RuntimeError("RAG index not built. Call build_index() first.")

        query_vec = self.model.encode([query.query], convert_to_numpy=True)
        distances, indices = self.index.search(query_vec, query.top_k)

        results = []

        for idx in indices[0]:
            record = self.records[idx]
            results.append(
                RetrievalResult(
                    content=record.reason_raw,
                    metadata={
                        "product": record.product_name,
                        "store": record.store_name,
                        "price": record.price,
                        "currency": record.currency,
                        "return_date": str(record.return_date),
                    },
                )
            )

        return results

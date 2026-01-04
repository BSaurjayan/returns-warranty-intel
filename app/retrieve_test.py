# app/retrieve_test.py

from app.db.database import SessionLocal
from app.rag.retrieve import RAGRetriever
from app.schemas import RetrievalQuery


def main():
    db = SessionLocal()
    retriever = RAGRetriever(db)

    retriever.build_index()

    query = RetrievalQuery(
        query="USB port not working",
        top_k=3
    )

    results = retriever.retrieve(query)

    for r in results:
        print(r)


if __name__ == "__main__":
    main()

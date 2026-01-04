# app/ingest_test.py

from app.db.database import SessionLocal
from app.rag.ingest import CSVIngestor


def main():
    db = SessionLocal()
    ingestor = CSVIngestor(db)

    csv_path = "data/sample.csv"
    inserted_count = ingestor.ingest(csv_path)

    print(f"CSV ingestion completed. Inserted {inserted_count} new rows.")


if __name__ == "__main__":
    main()

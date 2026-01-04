# app/rag/ingest.py

import csv
from datetime import datetime
from sqlalchemy.orm import Session

from app.agents.retrieval_agent import RetrievalAgent
from app.schemas import InsertReturnRequest


class CSVIngestor:
    """
    Ingests historical return data from CSV files and inserts
    them into the database via RetrievalAgent.
    """

    def __init__(self, db_session: Session):
        self.agent = RetrievalAgent(db_session)

    def ingest(self, csv_path: str) -> int:
        inserted = 0

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    request = InsertReturnRequest(
                        product_name=row["product_name"],
                        product_category=row.get("product_category"),

                        store_name=row["store_name"],
                        city=row.get("city"),
                        country=row.get("country"),

                        purchase_date=self._parse_date(row["purchase_date"]),
                        return_date=self._parse_date(row["return_date"]),

                        reason_raw=row["reason"],

                        price=float(row["price"]),
                        currency=row["currency"],
                        discount_pct=float(row["discount_pct"]) if row.get("discount_pct") else None,
                    )

                    self.agent.insert_return(request)
                    inserted += 1

                except Exception:
                    # duplicates or malformed rows are skipped safely
                    continue

        return inserted

    @staticmethod
    def _parse_date(value: str):
        return datetime.strptime(value, "%Y-%m-%d").date()

# app/agents/retrieval_agent.py

import hashlib
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Return
from app.schemas import InsertReturnRequest, InsertReturnResponse


class RetrievalAgent:
    """
    Handles WRITE operations for returns.
    Responsible for validation, deduplication, and DB insertion.
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def _generate_dedupe_key(self, data: InsertReturnRequest) -> str:
        """
        Deterministic hash to prevent duplicate return insertions.
        """
        raw_key = f"{data.product_name}|{data.store_name}|{data.purchase_date}|{data.price}|{data.currency}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def insert_return(self, request: InsertReturnRequest) -> InsertReturnResponse:
        dedupe_key = self._generate_dedupe_key(request)

        new_return = Return(
            product_name=request.product_name,
            product_category=request.product_category,
            store_name=request.store_name,
            city=request.city,
            country=request.country,
            purchase_date=request.purchase_date,
            return_date=request.return_date,
            reason_raw=request.reason_raw,
            price=request.price,
            currency=request.currency,
            discount_pct=request.discount_pct,
            dedupe_key=dedupe_key,
        )

        try:
            self.db.add(new_return)
            self.db.commit()
            self.db.refresh(new_return)

        except IntegrityError:
            self.db.rollback()
            raise ValueError(
                "Duplicate return detected. This item appears to have already been returned."
            )

        return InsertReturnResponse(
            return_id=new_return.id,
            product_name=new_return.product_name,
            store_name=new_return.store_name,
            price=new_return.price,
            currency=new_return.currency,
            message="Return successfully recorded."
        )

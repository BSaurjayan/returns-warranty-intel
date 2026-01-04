# app/db/models.py

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.db.database import Base


class Return(Base):
    __tablename__ = "returns"

    id = Column(Integer, primary_key=True, index=True)

    product_name = Column(String, index=True)
    product_category = Column(String, index=True)

    store_name = Column(String, index=True)
    city = Column(String)
    country = Column(String)

    purchase_date = Column(Date)
    return_date = Column(Date)

    reason_raw = Column(String)

    price = Column(Float)
    currency = Column(String)
    discount_pct = Column(Float)

    # 🔒 CRITICAL: duplicate prevention
    dedupe_key = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_dedupe_key"),
    )

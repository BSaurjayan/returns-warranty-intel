# app/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


# -----------------------------
# Coordinator-level schemas
# -----------------------------

class UserMessage(BaseModel):
    text: str


class IntentClassification(BaseModel):
    intent: str = Field(
        description="One of: insert_return, analytics, forecast"
    )
    confidence: float


# -----------------------------
# Retrieval Agent — WRITE
# -----------------------------

class InsertReturnRequest(BaseModel):
    product_name: str
    product_category: Optional[str]

    store_name: str
    city: Optional[str]
    country: Optional[str]

    purchase_date: date
    return_date: date

    reason_raw: str

    price: float
    currency: str
    discount_pct: Optional[float]


class InsertReturnResponse(BaseModel):
    return_id: int
    product_name: str
    store_name: str
    price: float
    currency: str
    message: str


# -----------------------------
# Retrieval Agent — READ (RAG)
# -----------------------------

class RetrievalQuery(BaseModel):
    query: str
    top_k: int = 5


class RetrievalResult(BaseModel):
    content: str
    metadata: dict


# -----------------------------
# Report / Analytics Agent
# -----------------------------

class ReportRequest(BaseModel):
    product_name: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    generate_excel: bool = False


class ReportSummary(BaseModel):
    total_returns: int
    total_loss: float
    trend: str
    insight: str
    excel_path: Optional[str]


# -----------------------------
# Forecasting Agent
# -----------------------------

class ForecastRequest(BaseModel):
    target: str = Field(
        description="Example: daily_return_volume"
    )
    horizon_days: int = Field(default=30)


class ForecastPoint(BaseModel):
    date: date
    predicted_value: float


class ForecastResponse(BaseModel):
    target: str
    horizon_days: int
    predictions: List[ForecastPoint]
    model_used: str
    metric: str
    metric_value: float

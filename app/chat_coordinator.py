# app/chat_coordinator.py

import re
from dataclasses import dataclass, field
from datetime import date, timedelta, datetime
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.agents.retrieval_agent import RetrievalAgent
from app.agents.report_agent import ReportAgent
from app.agents.forecasting_agent import ForecastingAgent
from app.rag.retrieve import RAGRetriever
from app.schemas import (
    InsertReturnRequest,
    ReportRequest,
    ForecastRequest,
    RetrievalQuery,
)


@dataclass
class ConversationState:
    pending_return: Dict[str, Optional[object]] = field(default_factory=lambda: {
        "product_name": None,
        "product_category": None,
        "store_name": None,
        "city": None,
        "country": None,
        "purchase_date": None,
        "return_date": None,
        "reason_raw": None,
        "price": None,
        "currency": None,
        "discount_pct": None,
    })
    mode: Optional[str] = None  # insert_return | analytics | forecast | rag


class Coordinator:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.retrieval_agent = RetrievalAgent(db_session)
        self.report_agent = ReportAgent(db_session)
        self.forecast_agent = ForecastingAgent(db_session)
        self.rag = RAGRetriever(db_session)

    def handle_message(
        self, user_text: str, state: ConversationState
    ) -> Tuple[str, ConversationState]:
        text = user_text.strip()

        if state.mode == "insert_return":
            return self._handle_insert_flow(text, state)

        intent = self._classify_intent(text)
        state.mode = intent

        if intent == "forecast":
            return self._handle_forecast(text, state)
        if intent == "analytics":
            return self._handle_analytics(text, state)
        if intent == "insert_return":
            return self._handle_insert_flow(text, state)

        return self._handle_rag(text, state)

    # ---------- intent ----------
    def _classify_intent(self, text: str) -> str:
        t = text.lower()
        if any(k in t for k in ["forecast", "predict", "next"]):
            return "forecast"
        if any(k in t for k in ["report", "analysis", "how many", "trend", "excel"]):
            return "analytics"
        if any(k in t for k in ["return", "refund"]):
            return "insert_return"
        return "rag"

    # ---------- insert ----------
    def _handle_insert_flow(
        self, text: str, state: ConversationState
    ) -> Tuple[str, ConversationState]:
        self._extract_fields(text, state)
        missing = self._missing_fields(state)

        if missing:
            return self._ask_next(missing), state

        try:
            req = InsertReturnRequest(**state.pending_return)  # type: ignore
            resp = self.retrieval_agent.insert_return(req)

            state.pending_return = {k: None for k in state.pending_return}
            state.mode = None

            return (
                f"✅ Return recorded: {resp.product_name} from {resp.store_name} "
                f"({resp.price} {resp.currency}). Return ID: {resp.return_id}",
                state,
            )
        except ValueError as e:
            state.pending_return = {k: None for k in state.pending_return}
            state.mode = None
            return str(e), state

    def _missing_fields(self, state: ConversationState):
        required = [
            "product_name",
            "store_name",
            "purchase_date",
            "reason_raw",
            "price",
            "currency",
        ]
        return [k for k in required if not state.pending_return.get(k)]


    def _ask_next(self, missing):
        if "product_name" in missing:
            return "What product are you returning?"
        if "store_name" in missing:
            return "Which store did you buy it from?"
        if "purchase_date" in missing:
            return "When did you purchase it? (YYYY-MM-DD or 'last week')"
        if "return_date" in missing:
            return "When is the return date?"
        if "reason_raw" in missing:
            return "What is the reason for return?"
        if "price" in missing or "currency" in missing:
            return "What was the price and currency?"
        return "Please provide the missing details."

    def _extract_fields(self, text: str, state: ConversationState):
        t = text.lower()

        # ---------- PRODUCT ----------
        # Product extraction
        if not state.pending_return["product_name"]:
            # Case 1: sentence-style input
            m = re.search(r"return (?:my|an|a)?\s*(.+)", text, re.I)
            if m:
                state.pending_return["product_name"] = m.group(1).strip()
            # Case 2: short answer (e.g. "iphone", "apple tv")
            elif len(text.split()) <= 4:
                state.pending_return["product_name"] = text.strip()


        # ---------- STORE ----------
        if not state.pending_return["store_name"]:
            m = re.search(r"(?:from|at)\s+(.+)", text, re.I)
            if m:
                state.pending_return["store_name"] = m.group(1).strip()
            elif (
                state.pending_return["product_name"]  # only after product known
                and len(text.split()) <= 5
                and not any(k in t for k in ["working", "broken", "week", "today"])
            ):
                state.pending_return["store_name"] = text.strip()

        # ---------- REASON ----------
        if not state.pending_return["reason_raw"]:
            if any(k in t for k in ["not working", "broken", "defective"]):
                state.pending_return["reason_raw"] = text.strip()

        # ---------- PRICE + CURRENCY ----------
        if not state.pending_return["price"] or not state.pending_return["currency"]:
            m = re.search(r"(\d+(?:\.\d+)?)\s*([A-Za-z]{2,5})", text)
            if m:
                state.pending_return["price"] = float(m.group(1))
                state.pending_return["currency"] = m.group(2).upper()

        # ---------- PURCHASE DATE ----------
        if not state.pending_return["purchase_date"]:
            if "last week" in t:
                state.pending_return["purchase_date"] = date.today() - timedelta(days=7)
            else:
                m = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
                if m:
                    state.pending_return["purchase_date"] = datetime.strptime(
                        m.group(1), "%Y-%m-%d"
                    ).date()

        # ---------- RETURN DATE (only if explicitly mentioned) ----------
        if not state.pending_return["return_date"]:
            if "today" in t:
                state.pending_return["return_date"] = date.today()

    # ---------- analytics ----------
    def _handle_analytics(self, text: str, state: ConversationState):
        req = ReportRequest(product_name=None, start_date=None, end_date=None, generate_excel=True)
        resp = self.report_agent.generate_report(req)
        state.mode = None
        return (
            f"📊 Returns: {resp.total_returns}\n"
            f"Loss: {resp.total_loss}\n"
            f"Trend: {resp.trend}\n{resp.insight}",
            state,
        )

    # ---------- forecast ----------
    def _handle_forecast(self, text: str, state: ConversationState):
        req = ForecastRequest(target="daily_return_volume", horizon_days=14)
        resp = self.forecast_agent.forecast(req)
        state.mode = None
        return (
            f"📈 Forecast ({resp.model_used})\nMAE: {resp.metric_value}",
            state,
        )

    # ---------- rag ----------
    def _handle_rag(self, text: str, state: ConversationState):
        self.rag.build_index()
        res = self.rag.retrieve(RetrievalQuery(query=text, top_k=3))
        state.mode = None
        if not res:
            return "No relevant returns found.", state
        return "\n".join(f"- {r.content}" for r in res), state

# app/agents/report_agent.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import Return
from app.schemas import ReportRequest, ReportSummary


class ReportAgent:
    """
    READ-ONLY analytics + optional Excel report generation.

    - Computes total returns, total loss (sum of price), and trend vs previous window.
    - Generates Excel report with two tabs: Summary + Findings.
    """

    def __init__(self, db_session: Session, reports_dir: str = "reports"):
        self.db = db_session
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, request: ReportRequest) -> ReportSummary:
        start_date, end_date = self._resolve_date_range(request.start_date, request.end_date)

        total_returns, total_loss = self._aggregate_window(
            start_date=start_date,
            end_date=end_date,
            product_name=request.product_name,
        )

        # Trend window: compare against immediately preceding window of same length
        window_days = (end_date - start_date).days + 1
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=window_days - 1)

        prev_returns, prev_loss = self._aggregate_window(
            start_date=prev_start,
            end_date=prev_end,
            product_name=request.product_name,
        )

        trend = self._compute_trend(current=total_returns, previous=prev_returns)

        insight = self._build_insight(
            product_name=request.product_name,
            start_date=start_date,
            end_date=end_date,
            total_returns=total_returns,
            total_loss=total_loss,
            prev_returns=prev_returns,
            prev_loss=prev_loss,
            trend=trend,
        )

        excel_path: Optional[str] = None
        if request.generate_excel:
            excel_path = self._write_excel(
                product_name=request.product_name,
                start_date=start_date,
                end_date=end_date,
                total_returns=total_returns,
                total_loss=total_loss,
                prev_returns=prev_returns,
                prev_loss=prev_loss,
                trend=trend,
                insight=insight,
            )

        return ReportSummary(
            total_returns=total_returns,
            total_loss=float(total_loss),
            trend=trend,
            insight=insight,
            excel_path=excel_path,
        )

    # -------------------------
    # Helpers
    # -------------------------

    def _resolve_date_range(self, start: Optional[date], end: Optional[date]) -> Tuple[date, date]:
        """
        Default to last 14 days (inclusive) if not provided.
        """
        if end is None:
            end = date.today()
        if start is None:
            start = end - timedelta(days=13)
        return start, end

    def _aggregate_window(self, start_date: date, end_date: date, product_name: Optional[str]) -> Tuple[int, float]:
        q = self.db.query(
            func.count(Return.id),
            func.coalesce(func.sum(Return.price), 0.0)
        ).filter(
            Return.return_date >= start_date,
            Return.return_date <= end_date
        )

        if product_name:
            q = q.filter(Return.product_name.ilike(f"%{product_name}%"))

        count_val, sum_val = q.one()
        return int(count_val), float(sum_val)

    def _compute_trend(self, current: int, previous: int) -> str:
        if previous == 0 and current == 0:
            return "flat"
        if previous == 0 and current > 0:
            return "increasing"
        if current > previous:
            return "increasing"
        if current < previous:
            return "decreasing"
        return "flat"

    def _build_insight(
        self,
        product_name: Optional[str],
        start_date: date,
        end_date: date,
        total_returns: int,
        total_loss: float,
        prev_returns: int,
        prev_loss: float,
        trend: str,
    ) -> str:
        scope = f"for '{product_name}' " if product_name else ""
        period = f"{start_date.isoformat()} to {end_date.isoformat()}"

        if trend == "increasing":
            return (
                f"Returns {scope}are increasing in {period} "
                f"({total_returns} vs {prev_returns} in the previous period). "
                f"Estimated loss is {total_loss:.2f} vs {prev_loss:.2f} previously. "
                f"Consider checking store handling, product batch quality, and common defect reasons."
            )
        if trend == "decreasing":
            return (
                f"Returns {scope}are decreasing in {period} "
                f"({total_returns} vs {prev_returns} previously). "
                f"Estimated loss is {total_loss:.2f} vs {prev_loss:.2f}. "
                f"This suggests recent mitigations may be working."
            )
        return (
            f"Returns {scope}are stable in {period} "
            f"({total_returns} vs {prev_returns} previously). "
            f"Estimated loss is {total_loss:.2f} vs {prev_loss:.2f}. "
            f"Monitor for emerging spikes in specific stores/products."
        )

    def _write_excel(
        self,
        product_name: Optional[str],
        start_date: date,
        end_date: date,
        total_returns: int,
        total_loss: float,
        prev_returns: int,
        prev_loss: float,
        trend: str,
        insight: str,
    ) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        product_tag = (product_name or "all").replace(" ", "_")
        out_path = self.reports_dir / f"returns_report_{product_tag}_{ts}.xlsx"

        summary_df = pd.DataFrame(
            [
                {"metric": "product_filter", "value": product_name or "ALL"},
                {"metric": "start_date", "value": start_date.isoformat()},
                {"metric": "end_date", "value": end_date.isoformat()},
                {"metric": "total_returns", "value": total_returns},
                {"metric": "total_loss", "value": total_loss},
                {"metric": "previous_period_returns", "value": prev_returns},
                {"metric": "previous_period_loss", "value": prev_loss},
                {"metric": "trend", "value": trend},
            ]
        )

        findings_df = pd.DataFrame(
            [
                {"finding": "Key Insight", "details": insight},
            ]
        )

        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            findings_df.to_excel(writer, sheet_name="Findings", index=False)

        return str(out_path)

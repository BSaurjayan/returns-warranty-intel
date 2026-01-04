# app/agents/forecasting_agent.py

from datetime import date, timedelta
from typing import List

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.db.models import Return
from app.schemas import ForecastRequest, ForecastResponse, ForecastPoint


class ForecastingAgent:
    """
    Forecasts daily return volume using a simple moving average model.
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def forecast(self, request: ForecastRequest) -> ForecastResponse:
        df = self._load_daily_series()

        if df.empty:
            raise ValueError("Not enough data to generate forecast.")

        window = min(7, len(df))  # 7-day moving average
        avg_value = df["count"].tail(window).mean()

        future_dates = [
            df["date"].max() + timedelta(days=i)
            for i in range(1, request.horizon_days + 1)
        ]

        predictions = [
            ForecastPoint(date=d, predicted_value=float(avg_value))
            for d in future_dates
        ]

        # Simple backtest (last window)
        actual = df["count"].tail(window).values
        predicted = np.full_like(actual, avg_value, dtype=float)
        mae = float(np.mean(np.abs(actual - predicted)))

        return ForecastResponse(
            target=request.target,
            horizon_days=request.horizon_days,
            predictions=predictions,
            model_used="7-day moving average",
            metric="MAE",
            metric_value=mae,
        )

    def _load_daily_series(self) -> pd.DataFrame:
        rows = (
            self.db.query(Return.return_date)
            .all()
        )

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=["date"])
        df["date"] = pd.to_datetime(df["date"])
        daily = df.groupby("date").size().reset_index(name="count")
        daily = daily.sort_values("date")

        return daily

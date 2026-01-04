# app/forecast_test.py

from app.db.database import SessionLocal
from app.agents.forecasting_agent import ForecastingAgent
from app.schemas import ForecastRequest


def main():
    db = SessionLocal()
    agent = ForecastingAgent(db)

    request = ForecastRequest(
        target="daily_return_volume",
        horizon_days=14
    )

    response = agent.forecast(request)

    print(f"\nForecast target: {response.target}")
    print(f"Model used: {response.model_used}")
    print(f"Evaluation metric: {response.metric} = {response.metric_value:.2f}")

    print("\nPredictions:")
    for p in response.predictions:
        print(p.date, "→", p.predicted_value)


if __name__ == "__main__":
    main()

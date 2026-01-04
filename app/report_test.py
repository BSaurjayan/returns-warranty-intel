# app/report_test.py

from datetime import date, timedelta

from app.db.database import SessionLocal
from app.agents.report_agent import ReportAgent
from app.schemas import ReportRequest


def main():
    db = SessionLocal()
    agent = ReportAgent(db)

    # Example 1: overall last 14 days, generate Excel
    req1 = ReportRequest(
        product_name=None,
        start_date=None,
        end_date=None,
        generate_excel=True
    )
    resp1 = agent.generate_report(req1)
    print("\n--- Overall Report ---")
    print(resp1)

    # Example 2: product-specific last 14 days, no Excel
    req2 = ReportRequest(
        product_name="Apple TV",
        start_date=date.today() - timedelta(days=13),
        end_date=date.today(),
        generate_excel=False
    )
    resp2 = agent.generate_report(req2)
    print("\n--- Product Report (Apple TV) ---")
    print(resp2)


if __name__ == "__main__":
    main()

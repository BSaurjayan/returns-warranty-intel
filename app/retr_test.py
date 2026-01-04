from datetime import date
from app.db.database import SessionLocal
from app.agents.retrieval_agent import RetrievalAgent
from app.schemas import InsertReturnRequest

db = SessionLocal()
agent = RetrievalAgent(db)

req = InsertReturnRequest(
    product_name="Apple TV",
    product_category="Streaming Device",
    store_name="Taipei 101 Apple Store",
    city="Taipei",
    country="Taiwan",
    purchase_date=date(2025, 1, 5),
    return_date=date(2025, 1, 10),
    reason_raw="USB port not working",
    price=3300,
    currency="NTD",
    discount_pct=10.0
)

resp = agent.insert_return(req)
print(resp)

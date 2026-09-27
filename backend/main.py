"""
VoiceSupport AI — backend
Run with: uvicorn main:app --reload --port 8083

This is the service your ElevenLabs agent will call as "tools" during a
conversation (e.g. lookup_order). It uses SQLite for now (zero setup,
built into Python) — swap the DATABASE section for PostgreSQL later
without changing the route logic.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "voicesupport.db")

app = FastAPI(title="VoiceSupport AI Backend")

# Allow the frontend (or ElevenLabs' server-side tool caller) to reach this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            item TEXT NOT NULL,
            status TEXT NOT NULL,
            amount REAL NOT NULL,
            placed_on TEXT NOT NULL,
            return_eligible INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        );
        CREATE TABLE IF NOT EXISTS kb_articles (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL
        );
        """
    )
    # seed sample data only if empty
    if conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
        conn.executescript(
            """
            INSERT INTO customers (id, name, email) VALUES
                (1, 'Sana Khan', 'sana@example.com'),
                (2, 'Ali Raza', 'ali@example.com');

            INSERT INTO orders (id, customer_id, item, status, amount, placed_on, return_eligible) VALUES
                (4521, 1, 'Wireless Keyboard', 'Shipped - arriving Tuesday', 49.99, '2026-09-20', 1),
                (4522, 2, 'Laptop Stand', 'Delivered', 29.99, '2026-09-10', 0);

            INSERT INTO kb_articles (id, title, body) VALUES
                (1, 'Resetting your password', 'Go to Settings > Account > Reset Password. A reset link is emailed within 2 minutes.'),
                (2, 'Return window policy', 'Items are returnable within 30 days of delivery, unmarked as final sale.');
            """
        )
    conn.commit()
    conn.close()


init_db()


class EligibilityResponse(BaseModel):
    order_id: int
    eligible: bool
    reason: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/orders/{order_id}")
def lookup_order(order_id: int):
    """Tool: lookup_order — used by the Billing agent."""
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return dict(row)


@app.get("/order-status")
def lookup_order_by_query(order_id: int):
    """
    Same as /orders/{order_id}, but takes order_id as a query parameter
    instead of a path parameter — e.g. /order-status?order_id=4521.
    Some webhook-tool UIs (like ElevenLabs') validate the URL field
    strictly and reject curly-brace path placeholders, so this version
    is the one to point the ElevenLabs tool at.
    """
    return lookup_order(order_id)


@app.get("/customers/{customer_id}/orders")
def customer_orders(customer_id: int):
    """Used for the 'proactive' feature — pull recent orders before the agent asks."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM orders WHERE customer_id = ? ORDER BY placed_on DESC", (customer_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/returns/{order_id}/eligibility", response_model=EligibilityResponse)
def check_return_eligibility(order_id: int):
    """Tool: check_return_eligibility — used by the Returns agent."""
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    eligible = bool(row["return_eligible"])
    reason = "Within return window" if eligible else "Outside return window or final sale"
    return EligibilityResponse(order_id=order_id, eligible=eligible, reason=reason)


@app.get("/kb/search")
def search_knowledge_base(q: str):
    """
    Tool: search_knowledge_base — used by the Technical agent.
    Placeholder keyword match for now; swap for pgvector similarity search
    once you move off SQLite (see README).
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM kb_articles WHERE title LIKE ? OR body LIKE ?",
        (f"%{q}%", f"%{q}%"),
    ).fetchall()
    conn.close()
    if not rows:
        return {"found": False, "results": []}
    return {"found": True, "results": [dict(r) for r in rows]}
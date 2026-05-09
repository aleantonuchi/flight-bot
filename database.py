"""
Banco de dados — usa PostgreSQL (Supabase) via asyncpg.
A variável DATABASE_URL deve estar configurada no .env.
"""
from __future__ import annotations

from datetime import datetime
from contextlib import asynccontextmanager

import asyncpg

from config import DATABASE_URL


@asynccontextmanager
async def _conn():
    conn = await asyncpg.connect(DATABASE_URL, ssl="require")
    try:
        yield conn
    finally:
        await conn.close()


async def init_db():
    async with _conn() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id            SERIAL PRIMARY KEY,
                chat_id       BIGINT NOT NULL,
                username      TEXT,
                origin_code   TEXT NOT NULL,
                origin_name   TEXT NOT NULL,
                dest_code     TEXT NOT NULL,
                dest_name     TEXT NOT NULL,
                depart_date   TEXT,
                flexible      INTEGER DEFAULT 0,
                adults        INTEGER DEFAULT 1,
                best_price    REAL,
                best_date     TEXT,
                currency      TEXT DEFAULT 'BRL',
                created_at    TEXT NOT NULL,
                expires_at    TEXT NOT NULL,
                active        INTEGER DEFAULT 1
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id          SERIAL PRIMARY KEY,
                alert_id    INTEGER NOT NULL REFERENCES alerts(id),
                price       REAL NOT NULL,
                airline     TEXT,
                depart_date TEXT,
                checked_at  TEXT NOT NULL
            )
        """)


async def create_alert(chat_id, username, origin_code, origin_name,
                       dest_code, dest_name, expires_at,
                       depart_date=None, flexible=False):
    now = datetime.utcnow().isoformat()
    async with _conn() as conn:
        row = await conn.fetchrow("""
            INSERT INTO alerts
                (chat_id, username, origin_code, origin_name,
                 dest_code, dest_name, depart_date, flexible,
                 created_at, expires_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            RETURNING id
        """, chat_id, username, origin_code, origin_name,
            dest_code, dest_name, depart_date, int(flexible),
            now, expires_at)
        return row["id"]


async def get_active_alerts():
    now = datetime.utcnow().isoformat()
    async with _conn() as conn:
        rows = await conn.fetch("""
            SELECT * FROM alerts
            WHERE active = 1 AND expires_at > $1
        """, now)
        return [dict(r) for r in rows]


async def get_user_alerts(chat_id):
    now = datetime.utcnow().isoformat()
    async with _conn() as conn:
        rows = await conn.fetch("""
            SELECT * FROM alerts
            WHERE chat_id = $1 AND active = 1 AND expires_at > $2
            ORDER BY created_at DESC
        """, chat_id, now)
        return [dict(r) for r in rows]


async def update_best_price(alert_id, price, airline, depart_date=None):
    now = datetime.utcnow().isoformat()
    async with _conn() as conn:
        await conn.execute("""
            UPDATE alerts SET best_price = $1, best_date = $2 WHERE id = $3
        """, price, depart_date, alert_id)
        await conn.execute("""
            INSERT INTO price_history (alert_id, price, airline, depart_date, checked_at)
            VALUES ($1,$2,$3,$4,$5)
        """, alert_id, price, airline, depart_date, now)


async def save_price_check(alert_id, price, airline, depart_date=None):
    now = datetime.utcnow().isoformat()
    async with _conn() as conn:
        await conn.execute("""
            INSERT INTO price_history (alert_id, price, airline, depart_date, checked_at)
            VALUES ($1,$2,$3,$4,$5)
        """, alert_id, price, airline, depart_date, now)


async def deactivate_alert(alert_id, chat_id):
    async with _conn() as conn:
        await conn.execute("""
            UPDATE alerts SET active = 0
            WHERE id = $1 AND chat_id = $2
        """, alert_id, chat_id)


async def deactivate_expired():
    now = datetime.utcnow().isoformat()
    async with _conn() as conn:
        await conn.execute("""
            UPDATE alerts SET active = 0
            WHERE active = 1 AND expires_at <= $1
        """, now)

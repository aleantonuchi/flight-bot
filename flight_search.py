"""
Busca preços de voos via Travelpayouts/Aviasales API (gratuita, sem aprovação).
Registro em: travelpayouts.com
"""
from __future__ import annotations

import asyncio
import logging
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from config import TRAVELPAYOUTS_TOKEN

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)

BASE_URL = "https://api.travelpayouts.com/v1/prices/cheap"

AIRLINE_NAMES = {
    "LA": "LATAM", "G3": "Gol", "AD": "Azul", "TP": "TAP",
    "IB": "Iberia", "AF": "Air France", "LH": "Lufthansa",
    "AA": "American", "UA": "United", "DL": "Delta",
    "CM": "Copa", "AV": "Avianca", "KL": "KLM", "BA": "British Airways",
}


def _airline_name(code: str) -> str:
    return AIRLINE_NAMES.get(code, code)


def _search_month(origin: str, destination: str, year_month: str) -> list[dict]:
    """Busca os voos mais baratos para um mês (formato YYYY-MM)."""
    try:
        resp = requests.get(BASE_URL, params={
            "origin":       origin,
            "destination":  destination,
            "depart_date":  year_month,
            "currency":     "BRL",
            "token":        TRAVELPAYOUTS_TOKEN,
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success") or not data.get("data"):
            return []

        results = []
        # Estrutura: data[destination][index] = {airline, price, departure_at, ...}
        for dest_key, offers in data["data"].items():
            for idx, info in offers.items():
                departure = info.get("departure_at", "")
                date_iso = departure[:10] if departure else None
                results.append({
                    "price":       float(info["price"]),
                    "currency":    data.get("currency", "BRL"),
                    "airline":     _airline_name(info.get("airline", "N/D")),
                    "depart_date": date_iso,
                })
        return results
    except Exception as e:
        logger.error("Travelpayouts erro %s→%s %s: %s", origin, destination, year_month, e)
        return []


def _search_date(origin: str, destination: str, depart_date: str) -> Optional[dict]:
    """Busca para uma data específica (busca o mês inteiro e filtra o dia)."""
    year_month = depart_date[:7]   # YYYY-MM
    results = _search_month(origin, destination, year_month)

    # Filtra pelo dia exato (ou pega o mais barato do mês como aproximação)
    exact = [r for r in results if r.get("depart_date") == depart_date]
    pool = exact if exact else results
    if not pool:
        return None

    best = min(pool, key=lambda r: r["price"])
    logger.info("Travelpayouts %s→%s %s: BRL %.2f (%s)",
                origin, destination, depart_date, best["price"], best["airline"])
    return {**best, "flexible": False, "depart_date": depart_date}


def _search_flexible(origin: str, destination: str) -> Optional[dict]:
    """Busca sem data — verifica os próximos 3 meses e retorna o mais barato."""
    today = datetime.utcnow().date()
    months = [
        (today + timedelta(days=30 * i)).strftime("%Y-%m")
        for i in range(3)
    ]

    all_results = []
    for ym in months:
        all_results.extend(_search_month(origin, destination, ym))

    if not all_results:
        return None

    best = min(all_results, key=lambda r: r["price"])
    logger.info("Travelpayouts flex %s→%s: BRL %.2f em %s (%s)",
                origin, destination, best["price"], best["depart_date"], best["airline"])
    return {**best, "flexible": True}


async def search_cheapest_flight(
    origin: str,
    destination: str,
    depart_date: Optional[str] = None,
    flexible: bool = False,
) -> Optional[dict]:
    """Wrapper assíncrono."""
    loop = asyncio.get_event_loop()
    if flexible or not depart_date:
        return await loop.run_in_executor(_executor, _search_flexible, origin, destination)
    else:
        return await loop.run_in_executor(_executor, _search_date, origin, destination, depart_date)

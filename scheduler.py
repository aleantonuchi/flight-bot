import logging
from urllib.parse import quote
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database import get_active_alerts, update_best_price, save_price_check, deactivate_expired
from flight_search import search_cheapest_flight

logger = logging.getLogger(__name__)


def _fmt_price(price: float, currency: str) -> str:
    if currency == "BRL":
        return f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{currency} {price:,.2f}"


def _fmt_date(iso_date: str) -> str:
    try:
        p = iso_date.split("-")
        return f"{p[2]}/{p[1]}/{p[0]}"
    except Exception:
        return iso_date or "—"


def _booking_buttons(origin: str, destination: str, date: str = None) -> InlineKeyboardMarkup:
    """Gera botões de compra para Google Flights, Decolar e Kayak."""

    # Google Flights
    if date:
        q = f"voos de {origin} para {destination} {_fmt_date(date)}"
        decolar_url = (
            f"https://www.decolar.com/shop/flights/results/oneway"
            f"/{origin}/{destination}/{date}/1/0/0"
        )
        kayak_url = f"https://www.kayak.com.br/flights/{origin}-{destination}/{date}"
    else:
        q = f"voos de {origin} para {destination}"
        decolar_url = (
            f"https://www.decolar.com/shop/flights/results/oneway"
            f"/{origin}/{destination}/flexible/1/0/0"
        )
        kayak_url = f"https://www.kayak.com.br/flights/{origin}-{destination}"

    google_url = (
        f"https://www.google.com/travel/flights?q={quote(q)}&hl=pt-BR&curr=BRL"
    )

    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✈️ Google Flights", url=google_url),
        InlineKeyboardButton("🛒 Decolar",        url=decolar_url),
        InlineKeyboardButton("🔍 Kayak",          url=kayak_url),
    ]])


async def check_all_prices(context: CallbackContext):
    """Job executado a cada hora: verifica preços e envia alertas."""
    logger.info("Iniciando verificação de preços...")
    await deactivate_expired()

    alerts = await get_active_alerts()
    logger.info("Alertas ativos: %d", len(alerts))

    for alert in alerts:
        alert = dict(alert)
        is_flexible = bool(alert.get("flexible", 0))
        try:
            result = await search_cheapest_flight(
                origin=alert["origin_code"],
                destination=alert["dest_code"],
                depart_date=alert.get("depart_date"),
                flexible=is_flexible,
            )

            if result is None:
                logger.warning("Nenhum voo encontrado para alerta %d", alert["id"])
                continue

            price      = result["price"]
            airline    = result["airline"]
            found_date = result.get("depart_date")
            best       = alert["best_price"]

            if best is None:
                await update_best_price(alert["id"], price, airline, found_date)
                await _send_first_price(context.bot, alert, result, is_flexible)
            elif price < best:
                diff = best - price
                await update_best_price(alert["id"], price, airline, found_date)
                await _send_price_drop(context.bot, alert, result, diff, is_flexible)
            else:
                await save_price_check(alert["id"], price, airline, found_date)
                logger.info("Alerta %d: sem queda (atual %.2f, melhor %.2f)", alert["id"], price, best)

        except Exception as e:
            logger.error("Erro ao verificar alerta %d: %s", alert["id"], e)


async def _send_first_price(bot, alert: dict, result: dict, flexible: bool):
    price_str  = _fmt_price(result["price"], result["currency"])
    found_date = result.get("depart_date")

    if flexible:
        date_line = (
            f"📅 Melhor data: *{_fmt_date(found_date)}*"
            if found_date else "📅 Próximos 60 dias"
        )
        intro  = "🔍 *Promoção encontrada!*"
        footer = "Vou continuar monitorando e te aviso se aparecer algo mais barato!"
    else:
        found_date = alert.get("depart_date")
        date_line  = f"📅 {_fmt_date(found_date)}"
        intro  = "✈️ *Primeiro preço encontrado!*"
        footer = "Vou te avisar se o preço cair!"

    text = (
        f"{intro}\n\n"
        f"🛫 {alert['origin_name']} ({alert['origin_code']}) → "
        f"{alert['dest_name']} ({alert['dest_code']})\n"
        f"{date_line}\n\n"
        f"💰 *{price_str}* por pessoa\n"
        f"🏷️ {result['airline']}\n\n"
        f"{footer}"
    )
    buttons = _booking_buttons(alert["origin_code"], alert["dest_code"], found_date)
    await bot.send_message(
        chat_id=alert["chat_id"], text=text,
        parse_mode="Markdown", reply_markup=buttons,
    )


async def _send_price_drop(bot, alert: dict, result: dict, diff: float, flexible: bool):
    price_str  = _fmt_price(result["price"], result["currency"])
    diff_str   = _fmt_price(diff, result["currency"])
    found_date = result.get("depart_date")

    if flexible:
        date_line = (
            f"📅 Data: *{_fmt_date(found_date)}*"
            if found_date else "📅 Datas flexíveis"
        )
        header = "🚨 *NOVA PROMOÇÃO — PREÇO MAIS BAIXO!*"
    else:
        found_date = alert.get("depart_date")
        date_line  = f"📅 {_fmt_date(found_date)}"
        header = "🚨 *PREÇO CAIU!*"

    text = (
        f"{header}\n\n"
        f"🛫 {alert['origin_name']} ({alert['origin_code']}) → "
        f"{alert['dest_name']} ({alert['dest_code']})\n"
        f"{date_line}\n\n"
        f"💰 *{price_str}* por pessoa\n"
        f"📉 Baixou *{diff_str}* desde a última verificação!\n"
        f"🏷️ {result['airline']}\n\n"
        f"_Corre antes que suba!_ 🏃"
    )
    buttons = _booking_buttons(alert["origin_code"], alert["dest_code"], found_date)
    await bot.send_message(
        chat_id=alert["chat_id"], text=text,
        parse_mode="Markdown", reply_markup=buttons,
    )

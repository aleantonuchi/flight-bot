import os
import threading
import warnings
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

warnings.filterwarnings("ignore", message=".*per_message=False.*", category=Warning)

from telegram import Update
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_TOKEN, CHECK_INTERVAL_SECONDS, PORT
from database import init_db
from handlers import (
    start,
    novo_alerta,
    receber_origem,
    selecionar_origem,
    receber_destino,
    selecionar_destino,
    receber_tipo_data,
    selecionar_tipo_data,
    receber_data,
    receber_duracao,
    selecionar_duracao,
    cancelar_conversa,
    listar_alertas,
    cancelar_alerta_cmd,
    confirmar_cancelamento,
    agente_ia,
    limpar_conversa,
    ORIGEM, DESTINO, TIPO_DATA, DATA, DURACAO,
)
from scheduler import check_all_prices

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ─────────────────────────── Health Server ────────────────────────────────────
# Necessário para o Render (e UptimeRobot) saberem que o bot está vivo.

class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass  # não polui os logs


def _start_health_server():
    server = HTTPServer(("0.0.0.0", PORT), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Health server rodando na porta %d", PORT)


# ─────────────────────────── Error handler ────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    from telegram.error import NetworkError, TimedOut
    err = context.error
    if isinstance(err, Conflict):
        return
    if isinstance(err, (NetworkError, TimedOut)):
        logger.warning("Erro de rede transitório: %s", err)
        return
    logger.error("Erro inesperado: %s", err, exc_info=err)


# ─────────────────────────── Post init ───────────────────────────────────────

async def post_init(app: Application):
    await init_db()
    logger.info("Banco de dados iniciado.")
    app.job_queue.run_repeating(
        check_all_prices,
        interval=CHECK_INTERVAL_SECONDS,
        first=60,
        name="price_checker",
    )
    logger.info("Scheduler iniciado (intervalo: %ds).", CHECK_INTERVAL_SECONDS)


# ─────────────────────────── Main ────────────────────────────────────────────

def main():
    _start_health_server()

    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN não definido no .env")

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_error_handler(error_handler)

    conv = ConversationHandler(
        entry_points=[CommandHandler("novo", novo_alerta)],
        states={
            ORIGEM: [
                CallbackQueryHandler(selecionar_origem, pattern=r"^orig\|"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_origem),
            ],
            DESTINO: [
                CallbackQueryHandler(selecionar_destino, pattern=r"^dest\|"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_destino),
            ],
            TIPO_DATA: [
                CallbackQueryHandler(selecionar_tipo_data, pattern=r"^tipo\|"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_tipo_data),
            ],
            DATA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_data),
            ],
            DURACAO: [
                CallbackQueryHandler(selecionar_duracao, pattern=r"^dur\|"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_duracao),
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversa)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CommandHandler("alertas", listar_alertas))
    app.add_handler(CommandHandler("cancelar", cancelar_alerta_cmd))
    app.add_handler(CommandHandler("limpar", limpar_conversa))
    app.add_handler(CallbackQueryHandler(confirmar_cancelamento, pattern=r"^del\|"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, agente_ia))

    logger.info("Bot iniciado. Aguardando mensagens...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

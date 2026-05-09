import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database import create_alert, get_user_alerts, deactivate_alert
from airports import find_airports
from config import MAX_MONITOR_DAYS, AI_PROVIDER, GEMINI_API_KEY, GROQ_API_KEY, ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# Estados da conversa
ORIGEM, DESTINO, TIPO_DATA, DATA, DURACAO = range(5)

KEY_ORIGIN   = "origin"
KEY_DEST     = "dest"
KEY_DATE     = "date"
KEY_FLEXIBLE = "flexible"


# ─────────────────────────── /start ───────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Bem-vindo ao seu Agente de Viagens!*\n\n"
        "Sou o *Viajeiro* — um especialista em viagens com IA. Posso:\n\n"
        "✈️ Sugerir destinos e roteiros personalizados\n"
        "🏨 Recomendar hospedagens por orçamento\n"
        "💰 Buscar passagens aéreas em tempo real\n"
        "🔔 Criar alertas de preço automáticos\n"
        "🗺️ Planejar sua viagem dos sonhos\n\n"
        "📌 *Comandos:*\n"
        "/novo — Criar um alerta de preço\n"
        "/alertas — Ver seus alertas ativos\n"
        "/cancelar — Cancelar um alerta\n"
        "/limpar — Reiniciar conversa\n\n"
        "Ou simplesmente *me escreva o que você quer* e eu te ajudo! 🚀"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ─────────────────────────── /novo ────────────────────────────

async def novo_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "✈️ *Novo alerta de passagem*\n\n"
        "De onde você vai sair?\n"
        "_Digite o país, cidade ou código IATA._\n"
        "_Exemplos: Brasil, São Paulo, GRU, Estados Unidos_",
        parse_mode="Markdown",
    )
    return ORIGEM


async def receber_origem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = find_airports(update.message.text.strip())
    if not results:
        await update.message.reply_text(
            "❌ Não encontrei aeroportos para essa busca. Tente novamente.\n"
            "_Ex: Brasil, Estados Unidos, São Paulo, GRU, Paris_",
            parse_mode="Markdown",
        )
        return ORIGEM

    if len(results) == 1:
        context.user_data[KEY_ORIGIN] = results[0]
        await update.message.reply_text(
            f"✅ Origem: *{results[0]['label']}*\n\n"
            "Para onde você quer ir?\n"
            "_Digite o país, cidade ou código IATA_",
            parse_mode="Markdown",
        )
        return DESTINO

    keyboard = [
        [InlineKeyboardButton(r["label"], callback_data=f"orig|{r['code']}|{r['name']}")]
        for r in results
    ]
    await update.message.reply_text(
        "Encontrei mais de um aeroporto. Qual deles?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ORIGEM


async def selecionar_origem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, code, name = q.data.split("|", 2)
    context.user_data[KEY_ORIGIN] = {"code": code, "name": name, "label": f"{code} — {name}"}
    await q.edit_message_text(
        f"✅ Origem: *{code} — {name}*\n\n"
        "Para onde você quer ir?\n"
        "_Digite o nome da cidade ou código IATA_",
        parse_mode="Markdown",
    )
    return DESTINO


async def receber_destino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = find_airports(update.message.text.strip())
    if not results:
        await update.message.reply_text(
            "❌ Não encontrei aeroportos para essa busca. Tente novamente.\n"
            "_Ex: Portugal, Estados Unidos, Miami, CDG_",
            parse_mode="Markdown",
        )
        return DESTINO

    if len(results) == 1:
        context.user_data[KEY_DEST] = results[0]
        await _perguntar_data(update, results[0]["label"])
        return TIPO_DATA

    keyboard = [
        [InlineKeyboardButton(r["label"], callback_data=f"dest|{r['code']}|{r['name']}")]
        for r in results
    ]
    await update.message.reply_text(
        "Encontrei mais de um aeroporto. Qual deles?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return DESTINO


async def selecionar_destino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, code, name = q.data.split("|", 2)
    dest = {"code": code, "name": name, "label": f"{code} — {name}"}
    context.user_data[KEY_DEST] = dest
    keyboard = [[
        InlineKeyboardButton("📅 Tenho uma data",      callback_data="tipo|data"),
        InlineKeyboardButton("🔓 Qualquer promoção",   callback_data="tipo|flex"),
    ]]
    await q.edit_message_text(
        f"✅ Destino: *{code} — {name}*\n\n"
        "Você tem uma data específica ou quer receber qualquer promoção?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return TIPO_DATA


async def _perguntar_data(update, dest_label: str):
    keyboard = [[
        InlineKeyboardButton("📅 Tenho uma data",     callback_data="tipo|data"),
        InlineKeyboardButton("🔓 Qualquer promoção",  callback_data="tipo|flex"),
    ]]
    await update.message.reply_text(
        f"✅ Destino: *{dest_label}*\n\n"
        "Você tem uma data específica ou quer receber qualquer promoção?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def receber_tipo_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o botão de tipo de data (vindo de mensagem de texto — fallback)."""
    await update.message.reply_text(
        "Por favor, use os botões acima para escolher. 👆"
    )
    return TIPO_DATA


async def selecionar_tipo_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tipo = q.data.split("|")[1]

    if tipo == "flex":
        context.user_data[KEY_FLEXIBLE] = True
        context.user_data[KEY_DATE] = None
        keyboard = [[
            InlineKeyboardButton("1 dia",  callback_data="dur|1"),
            InlineKeyboardButton("2 dias", callback_data="dur|2"),
            InlineKeyboardButton("3 dias", callback_data="dur|3"),
        ]]
        await q.edit_message_text(
            "🔓 *Modo promoção livre!*\n\n"
            "Vou monitorar os preços nos próximos 60 dias e te avisar quando encontrar uma boa oferta.\n\n"
            "Por quantos dias devo monitorar?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return DURACAO
    else:
        context.user_data[KEY_FLEXIBLE] = False
        await q.edit_message_text(
            "📅 *Data específica*\n\n"
            "Qual é a data de ida?\n"
            "_Digite no formato DD/MM/AAAA (ex: 20/06/2026)_",
            parse_mode="Markdown",
        )
        return DATA


async def receber_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    try:
        dt = datetime.strptime(raw, "%d/%m/%Y")
    except ValueError:
        await update.message.reply_text(
            "❌ Formato inválido. Use DD/MM/AAAA (ex: 20/06/2026)"
        )
        return DATA

    if dt.date() < datetime.utcnow().date():
        await update.message.reply_text("❌ A data não pode estar no passado. Digite outra data.")
        return DATA

    context.user_data[KEY_DATE] = dt.strftime("%Y-%m-%d")

    keyboard = [[
        InlineKeyboardButton("1 dia",  callback_data="dur|1"),
        InlineKeyboardButton("2 dias", callback_data="dur|2"),
        InlineKeyboardButton("3 dias", callback_data="dur|3"),
    ]]
    await update.message.reply_text(
        f"✅ Data: *{raw}*\n\nPor quantos dias devo monitorar o preço?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return DURACAO


async def receber_duracao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    if not raw.isdigit() or not (1 <= int(raw) <= MAX_MONITOR_DAYS):
        await update.message.reply_text(f"❌ Digite 1, 2 ou 3.")
        return DURACAO
    return await _finalizar_alerta(update, context, int(raw))


async def selecionar_duracao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    dias = int(q.data.split("|")[1])
    return await _finalizar_alerta(update, context, dias, cq=q)


async def _finalizar_alerta(update, context, dias, cq=None):
    origin    = context.user_data.get(KEY_ORIGIN)
    dest      = context.user_data.get(KEY_DEST)
    date_iso  = context.user_data.get(KEY_DATE)

    flexible = context.user_data.get(KEY_FLEXIBLE, False)
    if not origin or not dest or (not flexible and not date_iso):
        msg = "❌ Algo deu errado. Use /novo para recomeçar."
        if cq:
            await cq.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return ConversationHandler.END

    expires_at = (datetime.utcnow() + timedelta(days=dias)).isoformat()
    user       = update.effective_user
    username   = user.username or user.full_name

    alert_id = await create_alert(
        chat_id     = update.effective_chat.id,
        username    = username,
        origin_code = origin["code"],
        origin_name = origin["name"],
        dest_code   = dest["code"],
        dest_name   = dest["name"],
        depart_date = date_iso,
        flexible    = flexible,
        expires_at  = expires_at,
    )

    if flexible:
        text = (
            f"✅ *Alerta #{alert_id} criado — Modo Promoção Livre!*\n\n"
            f"🛫 {origin['code']} → {dest['code']}\n"
            f"🔓 Qualquer data nos próximos 60 dias\n"
            f"⏱️ Monitora por *{dias} dia(s)*\n\n"
            "Vou verificar os preços a cada hora e te aviso quando encontrar uma boa oferta! 🔔"
        )
    else:
        date_br = date_iso[8:10] + "/" + date_iso[5:7] + "/" + date_iso[:4]
        text = (
            f"✅ *Alerta #{alert_id} criado!*\n\n"
            f"🛫 {origin['code']} → {dest['code']}\n"
            f"📅 {date_br}\n"
            f"⏱️ Monitora por *{dias} dia(s)*\n\n"
            "Vou verificar os preços a cada hora e te aviso aqui quando encontrar uma boa oferta! 🔔"
        )
    if cq:
        await cq.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────── /alertas ─────────────────────────

async def listar_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alerts = await get_user_alerts(update.effective_chat.id)
    if not alerts:
        await update.message.reply_text("Você não tem alertas ativos.\nUse /novo para criar um!")
        return

    lines = ["📋 *Seus alertas ativos:*\n"]
    for row in alerts:
        a = dict(row)
        exp    = a["expires_at"][:10]
        exp_br = exp[8:10] + "/" + exp[5:7] + "/" + exp[:4]

        if a["best_price"]:
            price_str = f"R$ {a['best_price']:,.2f}".replace(",","X").replace(".",",").replace("X",".")
        else:
            price_str = "ainda verificando…"

        if a.get("flexible"):
            date_label = "🔓 Qualquer data"
            if a.get("best_date"):
                bd = a["best_date"]
                date_label += f" (melhor: {bd[8:10]}/{bd[5:7]}/{bd[:4]})"
        else:
            d = a.get("depart_date") or ""
            date_label = f"📅 {d[8:10]}/{d[5:7]}/{d[:4]}" if d else "📅 —"

        lines.append(
            f"*#{a['id']}* {a['origin_code']} → {a['dest_code']} | {date_label}\n"
            f"   💰 Melhor: {price_str}\n"
            f"   ⏳ Até: {exp_br}\n"
        )
    lines.append("\nPara cancelar: /cancelar")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─────────────────────────── /cancelar ────────────────────────

async def cancelar_alerta_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alerts = await get_user_alerts(update.effective_chat.id)
    if not alerts:
        await update.message.reply_text("Você não tem alertas ativos para cancelar.")
        return

    keyboard = [[
        InlineKeyboardButton(
            f"#{dict(a)['id']} {dict(a)['origin_code']}→{dict(a)['dest_code']} "
            f"{dict(a)['depart_date'][8:10]}/{dict(a)['depart_date'][5:7]}",
            callback_data=f"del|{dict(a)['id']}"
        )
    ] for a in alerts]
    await update.message.reply_text(
        "Qual alerta deseja cancelar?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def confirmar_cancelamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    alert_id = int(q.data.split("|")[1])
    await deactivate_alert(alert_id, update.effective_chat.id)
    await q.edit_message_text(f"✅ Alerta #{alert_id} cancelado.")


# ─────────────────────────── fallback ─────────────────────────

async def cancelar_conversa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Operação cancelada.")
    return ConversationHandler.END


# ─────────────────────────── AI Agent ─────────────────────────

def _ai_key_configured() -> bool:
    keys = {"gemini": GEMINI_API_KEY, "groq": GROQ_API_KEY, "anthropic": ANTHROPIC_API_KEY}
    return bool(keys.get(AI_PROVIDER.lower(), ""))


async def agente_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Encaminha mensagens livres ao agente de viagem com IA."""
    if not _ai_key_configured():
        await update.message.reply_text(
            f"⚠️ A chave da API de IA não está configurada.\n"
            f"Provedor atual: *{AI_PROVIDER}*\n\n"
            f"Adicione a key no arquivo .env e reinicie o bot.",
            parse_mode="Markdown",
        )
        return

    from ai_agent import chat as ai_chat
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        reply = await ai_chat(chat_id, text)
    except Exception as e:
        logger.error("Erro no agente IA: %s", e)
        reply = "❌ Ocorreu um erro ao processar sua mensagem. Tente novamente."

    await update.message.reply_text(reply, parse_mode="Markdown")


async def limpar_conversa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Limpa o histórico de conversa do agente de IA."""
    if _ai_key_configured():
        from ai_agent import clear_history
        clear_history(update.effective_chat.id)
    await update.message.reply_text(
        "🧹 Conversa reiniciada! Pode começar do zero.\n\n"
        "📌 *Comandos:*\n"
        "/novo — Criar um alerta de preço\n"
        "/alertas — Ver seus alertas\n"
        "/cancelar — Cancelar um alerta\n"
        "/limpar — Reiniciar conversa com o assistente",
        parse_mode="Markdown",
    )

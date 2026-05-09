"""
Agente de viagem com IA — suporta múltiplos provedores:
  - gemini  (Google Gemini, grátis)
  - groq    (Groq + Llama, grátis)
  - anthropic (pago, melhor qualidade)

Configure AI_PROVIDER e a respectiva API key no .env.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from config import AI_PROVIDER, GEMINI_API_KEY, GROQ_API_KEY, ANTHROPIC_API_KEY
from flight_search import search_cheapest_flight

logger = logging.getLogger(__name__)

# Histórico de conversa: chat_id -> list de mensagens
_conversations: dict[int, list] = {}

SYSTEM_PROMPT = """Você é um agente de viagem especializado, amigável e apaixonado por viagens.
Seu nome é Viajeiro e você atende pelo Telegram.

Você tem profundo conhecimento sobre:
- Destinos turísticos ao redor do mundo (praias, cidades, monumentos, cultura, gastronomia)
- Roteiros de viagem otimizados por tempo e orçamento
- Dicas de hospedagem (hotéis, hostels, Airbnb) por perfil de viajante e orçamento
- Melhores épocas para visitar cada destino
- Documentação necessária (vistos, passaportes, vacinas)
- Dicas de segurança, transporte local, moeda e câmbio
- Passagens aéreas — rotas, companhias, estratégias para encontrar preços baixos
- Lua de mel, viagens em família, mochilão, viagens solo, cruzeiros

Quando o usuário pedir sugestões de destino ou roteiro, seja específico e detalhado:
- Sugira destinos concretos com breve descrição
- Estime custos em Reais quando possível
- Recomende onde ficar e o que fazer
- Mencione que pode monitorar passagens com /novo

Quando o usuário quiser buscar preços de voos, use a ferramenta search_flight.
Para buscas sem data fixa, use flexible=true.
Para datas específicas, passe depart_date no formato YYYY-MM-DD.

Responda sempre em português brasileiro de forma calorosa, como um amigo especialista.
Use emojis moderadamente para tornar a conversa mais agradável.
Seja conciso mas completo.

IMPORTANTE: Você NÃO pode fazer reservas nem comprar passagens diretamente.
Quando encontrar voos, oriente o usuário a usar os links de compra ou o comando /novo para criar alertas."""


# ─────────────────────────── Tool executor ────────────────────────────────────

async def _run_search_flight(origin: str, destination: str,
                              depart_date: str = None, flexible: bool = False) -> str:
    try:
        result = await search_cheapest_flight(
            origin=origin,
            destination=destination,
            depart_date=depart_date,
            flexible=flexible,
        )
        if result is None:
            return json.dumps({"error": "Nenhum voo encontrado para essa rota/data."})
        return json.dumps({
            "price": result["price"],
            "currency": result.get("currency", "BRL"),
            "airline": result["airline"],
            "depart_date": result.get("depart_date"),
        }, ensure_ascii=False)
    except Exception as e:
        logger.error("Erro ao buscar voo: %s", e)
        return json.dumps({"error": str(e)})


# ─────────────────────────── Gemini ───────────────────────────────────────────

def _chat_gemini(chat_id: int, user_message: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)

    def search_flight(origin: str, destination: str,
                      depart_date: str = None, flexible: bool = False) -> str:
        """Busca a passagem mais barata entre dois aeroportos.

        Args:
            origin: Código IATA do aeroporto de origem (ex: GRU, GIG, BSB)
            destination: Código IATA do aeroporto de destino (ex: LIS, CDG, MAD, JFK)
            depart_date: Data de partida no formato YYYY-MM-DD. Omita para busca flexível.
            flexible: Se True, busca nos próximos 60 dias e retorna a data mais barata.

        Returns:
            JSON com price, currency, airline e depart_date do voo encontrado.
        """
        return asyncio.get_event_loop().run_until_complete(
            _run_search_flight(origin, destination, depart_date, flexible)
        )

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools=[search_flight],
        system_instruction=SYSTEM_PROMPT,
    )

    # Gemini usa um objeto chat com history
    if chat_id not in _conversations:
        _conversations[chat_id] = []

    chat_session = model.start_chat(history=_conversations[chat_id])
    response = chat_session.send_message(user_message)

    # Salva histórico atualizado
    _conversations[chat_id] = chat_session.history[-40:]

    return response.text


# ─────────────────────────── Groq ─────────────────────────────────────────────

async def _chat_groq(chat_id: int, user_message: str) -> str:
    from groq import AsyncGroq

    client = AsyncGroq(api_key=GROQ_API_KEY)

    TOOLS_GROQ = [
        {
            "type": "function",
            "function": {
                "name": "search_flight",
                "description": "Busca a passagem mais barata disponível entre dois aeroportos.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {"type": "string", "description": "Código IATA de origem (ex: GRU)"},
                        "destination": {"type": "string", "description": "Código IATA de destino (ex: LIS)"},
                        "depart_date": {"type": "string", "description": "Data YYYY-MM-DD. Omita para busca flexível."},
                        "flexible": {"type": "boolean", "description": "Se true, busca nos próximos 60 dias."},
                    },
                    "required": ["origin", "destination"],
                },
            },
        }
    ]

    if chat_id not in _conversations:
        _conversations[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    _conversations[chat_id].append({"role": "user", "content": user_message})
    messages = _conversations[chat_id].copy()

    while True:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=TOOLS_GROQ,
            tool_choice="auto",
            max_tokens=1024,
        )

        msg = response.choices[0].message
        messages.append(msg)

        if msg.tool_calls:
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                result = await _run_search_flight(
                    origin=args["origin"],
                    destination=args["destination"],
                    depart_date=args.get("depart_date"),
                    flexible=args.get("flexible", False),
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            _conversations[chat_id] = messages[-40:]
            return msg.content or "Desculpe, não consegui gerar uma resposta."


# ─────────────────────────── Anthropic ────────────────────────────────────────

async def _chat_anthropic(chat_id: int, user_message: str) -> str:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    TOOLS_ANT = [
        {
            "name": "search_flight",
            "description": "Busca a passagem mais barata disponível entre dois aeroportos.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Código IATA de origem (ex: GRU)"},
                    "destination": {"type": "string", "description": "Código IATA de destino (ex: LIS)"},
                    "depart_date": {"type": "string", "description": "Data YYYY-MM-DD."},
                    "flexible": {"type": "boolean", "description": "Se true, busca nos próximos 60 dias."},
                },
                "required": ["origin", "destination"],
            },
        }
    ]

    if chat_id not in _conversations:
        _conversations[chat_id] = []

    _conversations[chat_id].append({"role": "user", "content": user_message})
    messages = _conversations[chat_id].copy()

    while True:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS_ANT,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "tool_use":
            tool_results = []
            for b in response.content:
                if b.type == "tool_use":
                    result = await _run_search_flight(
                        origin=b.input["origin"],
                        destination=b.input["destination"],
                        depart_date=b.input.get("depart_date"),
                        flexible=b.input.get("flexible", False),
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": b.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            text = "\n".join(b.text for b in response.content if hasattr(b, "text") and b.text)
            _conversations[chat_id] = messages[-40:]
            return text.strip() or "Desculpe, não consegui gerar uma resposta."


# ─────────────────────────── Interface pública ────────────────────────────────

async def chat(chat_id: int, user_message: str) -> str:
    """Envia mensagem ao agente e retorna a resposta (provedor configurado no .env)."""
    provider = AI_PROVIDER.lower()

    if provider == "gemini":
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _chat_gemini, chat_id, user_message)

    if provider == "groq":
        return await _chat_groq(chat_id, user_message)

    if provider == "anthropic":
        return await _chat_anthropic(chat_id, user_message)

    return "❌ Provedor de IA não configurado. Defina AI_PROVIDER no .env (gemini, groq ou anthropic)."


def clear_history(chat_id: int) -> None:
    """Limpa o histórico de conversa de um usuário."""
    _conversations.pop(chat_id, None)

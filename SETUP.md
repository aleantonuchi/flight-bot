# Flight Alert Bot — Setup

## 1. Criar o Bot no Telegram

1. Abra o Telegram e procure por **@BotFather**
2. Envie `/newbot`
3. Escolha um nome (ex: `Meu Monitor de Passagens`)
4. Escolha um username (ex: `meu_voos_bot`)
5. Copie o **token** que ele te enviar

## 2. Obter as credenciais da Amadeus (dados reais de voos)

1. Acesse https://developers.amadeus.com e crie uma conta gratuita
2. Vá em **My Apps → Create new app**
3. Copie o **Client ID** e o **Client Secret**

> O plano gratuito dá 2.000 chamadas/mês — suficiente para monitorar
> vários alertas verificando a cada hora.

## 3. Configurar o .env

Crie um arquivo `.env` na pasta do projeto:

```
TELEGRAM_BOT_TOKEN=seu_token_do_botfather
AMADEUS_CLIENT_ID=seu_client_id
AMADEUS_CLIENT_SECRET=seu_client_secret
```

## 4. Rodar o bot

```bash
cd flight-alerts
"C:/Program Files (x86)/Microsoft Visual Studio/Shared/Python39_64/python.exe" main.py
```

## Comandos disponíveis no bot

| Comando    | Descrição                                      |
|------------|------------------------------------------------|
| `/start`   | Apresentação e lista de comandos               |
| `/novo`    | Criar alerta — bot pergunta origem, destino, data e duração |
| `/alertas` | Ver todos os alertas ativos e melhores preços  |
| `/cancelar`| Cancelar um alerta                             |

## Como funciona

1. Você cria um alerta pelo bot informando origem, destino e data
2. A cada **1 hora** o bot busca o preço mais barato na Amadeus (base de dados das companhias aéreas)
3. Quando o preço *cair* em relação à última verificação, você recebe um alerta no Telegram
4. Após o período definido (até 3 dias), o monitoramento encerra automaticamente

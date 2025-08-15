import logging
import os
import re
import asyncio
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Carregar variáveis de ambiente ---
load_dotenv()
TOKEN_BOT = os.getenv('TOKEN_BOT')
API_URL_TOKEN = os.getenv('API_URL_TOKEN')
API_URL_CONSULTA = os.getenv('API_URL_CONSULTA')
API_USER = os.getenv('API_USER')
API_PASS = os.getenv('API_PASS')

# --- Configuração de logs ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Variáveis globais ---
token_api = None
token_expira = None

# --- Função para limpar e validar placa ---
def limpar_placa(placa: str) -> str:
    placa_limpa = re.sub(r'[^A-Za-z0-9]', '', placa).upper()
    return placa_limpa

def placa_valida(placa: str) -> bool:
    padrao_antigo = r"^[A-Z]{3}[0-9]{4}$"
    padrao_mercosul = r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$"
    return bool(re.match(padrao_antigo, placa) or re.match(padrao_mercosul, placa))

# --- Função para obter token da API (com cache) ---
async def get_api_token():
    global token_api, token_expira
    agora = datetime.now()
    if token_api and token_expira and agora < token_expira:
        logger.info("Token API reutilizado do cache.")
        return token_api

    # Log das variáveis de ambiente usadas na autenticação
    logger.info(f"API_USER: {API_USER!r}, API_PASS: {API_PASS!r}, API_URL_TOKEN: {API_URL_TOKEN!r}")

    # Log explicando se algum valor está vazio
    if not API_USER:
        logger.error("API_USER está vazio!")
    if not API_PASS:
        logger.error("API_PASS está vazio!")
    if not API_URL_TOKEN:
        logger.error("API_URL_TOKEN está vazio!")

    # Verificação de variáveis de ambiente
    if not API_USER or not API_PASS or not API_URL_TOKEN:
        logger.error("Variável de ambiente faltando: API_USER, API_PASS ou API_URL_TOKEN está vazia.")
        return None

    async with httpx.AsyncClient(timeout=10) as client:  # aumente para 10 segundos
        try:
            logger.info(f"Testando autenticação via POST e GET no endpoint: {API_URL_TOKEN}")

            payload1 = {"identificador": API_USER, "segredo": API_PASS}
            logger.info(f"Tentando POST com payload: {payload1}")
            resp1 = await client.post(API_URL_TOKEN, json=payload1)
            logger.info(f"POST status: {resp1.status_code}, body: {resp1.text}")

            payload2 = {"user": API_USER, "password": API_PASS}
            logger.info(f"Tentando POST com payload: {payload2}")
            resp2 = await client.post(API_URL_TOKEN, json=payload2)
            logger.info(f"POST status: {resp2.status_code}, body: {resp2.text}")

            params = {"user": API_USER, "password": API_PASS}
            logger.info(f"Tentando GET com params: {params}")
            resp3 = await client.get(API_URL_TOKEN, params=params)
            logger.info(f"GET status: {resp3.status_code}, body: {resp3.text}")

        except httpx.ReadTimeout:
            logger.error("Timeout ao tentar conectar na API de autenticação. Verifique o endpoint e a rede.")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao conectar na API: {e}")
            return None

        for resp in [resp1, resp2, resp3]:
            if resp.status_code == 200:
                try:
                    dados = resp.json()
                    logger.info(f"JSON retornado: {dados}")
                except Exception as e:
                    logger.error(f"Erro ao decodificar JSON: {e}")
                    logger.error(f"Conteúdo bruto: {resp.text}")
                    return None
                token_api = dados.get("token")
                token_expira = agora + timedelta(minutes=30)
                logger.info("Token API obtido com sucesso.")
                return token_api

        logger.error("Nenhuma tentativa de autenticação retornou sucesso.")
        return None

# --- Função para buscar placa ---
async def buscar_placa_api(placa: str):
    token = await get_api_token()
    if not token:
        logger.error("Token API não disponível.")
        return None

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=3) as client:
        resp = await client.get(f"{API_URL_CONSULTA}/{placa}", headers=headers)
        logger.info(f"Consulta API para placa {placa}: {resp.status_code} - {resp.text}")
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            return {}
        else:
            logger.error(f"Erro API: {resp.text}")
            return None

# --- Comando /start ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = (
        "Olá! 👋\n"
        "Para consultar uma placa, digite /buscar e siga as instruções.\n"
        "Você pode consultar uma placa por vez ou várias placas separadas por vírgula ou linha."
    )
    await update.message.reply_text(mensagem)
    logger.info(f"Bot enviou mensagem inicial para usuário {update.effective_user.id}: {mensagem}")

# --- Comando /buscar ---
async def buscar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Digite sua placa para consulta:")
    logger.info(f"Bot enviou mensagem: Digite sua placa para consulta para usuário {update.effective_user.id}")
    context.user_data["modo_busca"] = "unica"

# --- Mensagem de placa ---
async def placa_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    logger.info(f"Mensagem recebida do usuário {update.effective_user.id}: {texto}")
    placas = [limpar_placa(p) for p in texto.replace(",", "\n").split("\n") if p.strip()]

    # Pesquisa única
    if context.user_data.get("modo_busca") == "unica" and len(placas) == 1:
        placa = placas[0]
        if not placa_valida(placa):
            await update.message.reply_text("Placa não está em formato adequado")
            logger.info(f"Bot enviou mensagem: Placa não está em formato adequado para usuário {update.effective_user.id}")
            return

        dados = await buscar_placa_api(placa)
        if dados is None:
            await update.message.reply_text("Erro ao consultar API.")
            logger.info(f"Bot enviou mensagem: Erro ao consultar API para usuário {update.effective_user.id}")
        elif dados == {}:
            await update.message.reply_text("❌❌ Placa não encontrada ❌❌")
            logger.info(f"Bot enviou mensagem: Placa não encontrada para usuário {update.effective_user.id}")
        else:
            resposta = (
                f"✅✅ Veículo encontrado ✅✅\n"
                f"🎯 Sistema MAPION\n\n"
                f"🚗 Placa: {placa}\n"
                f"ℹ️ Número do chassi: {dados.get('chassi', 'N/D')}\n"
                f"🏢 Responsável: {dados.get('responsavel', 'N/D')}\n"
                f"📞 Telefone: {dados.get('telefone', 'N/D')}\n\n"
                f"⚠️ Entre em contato com o responsável e verifique se está apto e qual o status do processo."
            )
            await update.message.reply_text(resposta)
            logger.info(f"Bot enviou resposta para placa {placa} ao usuário {update.effective_user.id}: {resposta}")

        # Timer de expiração
        asyncio.create_task(expirar_pesquisa(update, 600))

    # Pesquisa em lote
    else:
        resultados = []
        for placa in placas:
            if not placa_valida(placa):
                resultados.append(f"{placa} → Formato inválido")
                continue
            dados = await buscar_placa_api(placa)
            if dados == {}:
                resultados.append(f"{placa} → Não encontrada")
            elif dados is None:
                resultados.append(f"{placa} → Erro API")
            else:
                resultados.append(f"{placa} → {dados.get('responsavel', 'N/D')} ({dados.get('telefone', 'N/D')})")
        resposta_lote = "\n".join(resultados)
        await update.message.reply_text(resposta_lote)
        logger.info(f"Bot enviou resposta de lote ao usuário {update.effective_user.id}: {resposta_lote}")
        asyncio.create_task(expirar_pesquisa(update, 600))

# --- Mensagem de expiração ---
async def expirar_pesquisa(update: Update, delay: int):
    await asyncio.sleep(delay)
    await update.message.reply_text(
        "O tempo de pesquisa expirou!\n"
        "Para procurar mais placas digite \"/buscar\" novamente!"
    )
    logger.info(f"Bot enviou mensagem de expiração para usuário {update.effective_user.id}")

# --- Função principal ---
def main():
    app = Application.builder().token(TOKEN_BOT).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("buscar", buscar_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, placa_handler))
    logger.info("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()

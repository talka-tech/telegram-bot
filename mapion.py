import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuração do sistema de logs para depuração
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ATENÇÃO: Substitua pelo seu token verdadeiro. Este token foi invalidado.
TOKEN = "8491897926:AAER9AGY2n6SXRwAejTb57DaIQQaB32Dn68"

# Função para o comando /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Usuário {user.first_name} ({user.id}) iniciou uma conversa.")
    
    # Define o layout do teclado com os comandos
    teclado = [
        ["/ajuda", "/data"]
    ]
    markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True)
    
    await update.message.reply_text(
        f'Olá, {user.first_name}! Eu sou o Mapion. Use os botões abaixo para interagir.',
        reply_markup=markup
    )

# Função para o comando /ajuda
async def ajuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Usuário {user.first_name} pediu ajuda.")
    texto_ajuda = (
        "Comandos disponíveis:\n"
        "/start - Inicia a conversa e mostra o teclado\n"
        "/ajuda - Mostra esta mensagem de ajuda\n"
        "/data - Exibe a data e hora atuais"
    )
    await update.message.reply_text(texto_ajuda)

# Função para o comando /data
async def data_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Usuário {user.first_name} pediu a data.")
    agora = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
    await update.message.reply_text(f"Data e hora atuais: {agora}")

# Função para lidar com fotos
async def foto_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Usuário {user.first_name} enviou uma foto.")
    await update.message.reply_text('Bela foto! Mas eu ainda só sei trabalhar com texto e comandos.')

# Função para lidar com mensagens de texto (eco)
async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Recebida a mensagem '{update.message.text}' do usuário {user.first_name}.")
    await update.message.reply_text(f"Eco: {update.message.text}")

def main() -> None:
    """Inicia o bot e configura todos os manipuladores."""
    application = Application.builder().token(TOKEN).build()

    # Adiciona os manipuladores de comando
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ajuda", ajuda_command))
    application.add_handler(CommandHandler("data", data_command))
    
    # Adiciona manipuladores de mensagem
    application.add_handler(MessageHandler(filters.PHOTO, foto_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler))

    logger.info("Bot iniciado e aguardando mensagens...")
    
    # Inicia o bot
    application.run_polling()

if __name__ == '__main__':
    main()

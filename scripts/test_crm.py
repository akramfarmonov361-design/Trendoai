import sys
sys.path.append(".")
# Load env explicitly if needed, but it should be loaded in app.py
from dotenv import load_dotenv
load_dotenv()
from utils.logger import setup_logger
logger = setup_logger("test_crm")


from bot_service import handle_all, bot
from app import app, db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'

class MockUser:
    id = 999888777
    username = "test_user_ai"
    first_name = "Toshmat"
    last_name = "Aka"

class MockChat:
    id = 999888777

class MockMessage:
    def __init__(self, text):
        self.text = text
        self.from_user = MockUser()
        self.chat = MockChat()

class MockBot:
    def send_chat_action(self, chat_id, action): logger.info(f"[MOCK] Action: bot is {action}...")
    def reply_to(self, message, text, **kwargs): logger.info(f"\n[BOT NATIVE REPLY TO USER]:\n{text}")
    def send_message(self, chat_id, text, **kwargs): logger.info(f"\n[BOT ADMIN SMS FIRE]: Notified Admin({chat_id}) -> \n{text}")

if not bot:
    import bot_service
    bot_service.bot = MockBot()
    bot = bot_service.bot
else:
    bot.send_chat_action = lambda chat_id, action: logger.info(f"[MOCK] Action: bot is {action}...")
    bot.reply_to = lambda message, text, **kwargs: logger.info(f"\n[BOT NATIVE REPLY TO USER]:\n{text}")
    bot.send_message = lambda chat_id, text, **kwargs: logger.info(f"\n[BOT ADMIN SMS FIRE]: Notified Admin({chat_id}) -> \n{text}")

def test_pipeline():
    logger.info("\n=== LIVE TEST BOSHLANDI ===")
    user_msg = "Assalomu alaykum. Men biznesim uchun telegram bot yasattirmoqchi edim. Raqamimga aloqaga chiqing, nomerim +998901234567, ismim Toshmat."
    logger.info(f"USER YOZDI: {user_msg}\n")
    
    # Init DB locally just in case it wasn't
    with app.app_context():
        db.create_all()

    # Call echo_all, which internally parses lead and interacts with DB
    msg = MockMessage(user_msg)
    import bot_service; bot_service.get_ai_response = lambda msg: 'Assalomu alaykum! Tez orada...[LEAD: Toshmat, +998901234567, Telegram bot]'; handle_all(msg)

if __name__ == "__main__":
    test_pipeline()

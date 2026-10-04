import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from web3 import Web3
import os

# ================= الإعدادات المخفية (Railway) =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")

# ================= إعداداتك =================
MY_WALLET_ADDRESS = "0x96aafcE765B0a03433483eDF4CC7311A5e7adADD"
ADMIN_ID = 822007358

# ================= BSC =================
BSC_RPC = "https://bsc-dataseed.binance.org/"

# USDT BEP-20
USDT_CONTRACT_ADDRESS = "0x55d398326f99059fF775485246999027B3197955"

# ================= ABI =================
USDT_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [
            {"name": "", "type": "bool"}
        ],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"}
        ],
        "name": "balanceOf",
        "outputs": [
            {"name": "balance", "type": "uint256"}
        ],
        "type": "function"
    }
]

# ================= التحقق من الإعدادات =================
if not BOT_TOKEN or not PRIVATE_KEY:
    print("⚠️ تحذير: BOT_TOKEN أو PRIVATE_KEY مش موجودين.")

# ================= إنشاء البوت =================
bot = telebot.TeleBot(BOT_TOKEN)

# ================= الاتصال بـ BSC =================
w3 = Web3(
    Web3.HTTPProvider(BSC_RPC)
)

my_address = w3.to_checksum_address(
    MY_WALLET_ADDRESS
)

usdt_contract = w3.eth.contract(
    address=w3.to_checksum_address(
        USDT_CONTRACT_ADDRESS
    ),
    abi=USDT_ABI
)

user_data = {}


# =========================================================
# لوحة الأزرار
# =========================================================

def create_main_menu():

    markup = ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    btn_send = KeyboardButton("💸 Send")
    btn_balance = KeyboardButton("💰 Balance")
    btn_wallet = KeyboardButton("💼 My Wallet")

    # الصف الأول
    markup.add(
        btn_send,
        btn_balance
    )

    # الصف الثاني
    markup.add(
        btn_wallet
    )

    return markup


# =========================================================
# /start
# =========================================================

@bot.message_handler(commands=['start'])
def send_welcome(message):

    if message.chat.id != ADMIN_ID:
        return

    markup = create_main_menu()

    bot.send_message(
        message.chat.id,
        "أهلاً بك يا سيّد! 👋\n\n"
        "اختر العملية التي تريدها:",
        reply_markup=markup
    )


# =========================================================
# /balance
# =========================================================

@bot.message_handler(commands=['balance'])
def check_balance(message):

    if message.chat.id != ADMIN_ID:
        return

    try:

        usdt_balance_raw = usdt_contract.functions.balanceOf(
            my_address
        ).call()

        usdt_balance = usdt_balance_raw / (10 ** 18)

        bot.reply_to(
            message,
            f"💵 راه عندك دوق: {usdt_balance:.6f} USDT"
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ ماقدرتش نتحقق من الرصيد:\n{str(e)}"
        )


# =========================================================
# زر 💰 Balance
# =========================================================

@bot.message_handler(func=lambda message: message.text == "💰 Balance")
def balance_button(message):

    if message.chat.id != ADMIN_ID:
        return

    # نفس وظيفة /balance
    check_balance(message)


# =========================================================
# /send
# =========================================================

@bot.message_handler(commands=['send'])
def start_send(message):

    if message.chat.id != ADMIN_ID:
        return

    msg = bot.reply_to(
        message,
        "🔗 هات لادراس BEP 20:"
    )

    bot.register_next_step_handler(
        msg,
        process_address_step
    )


# =========================================================
# زر 💸 Send
# =========================================================

@bot.message_handler(func=lambda message: message.text == "💸 Send")
def send_button(message):

    if message.chat.id != ADMIN_ID:
        return

    # نفس وظيفة /send
    start_send(message)


# =========================================================
# زر 💼 My Wallet
# =========================================================

@bot.message_handler(func=lambda message: message.text == "💼 My Wallet")
def wallet_button(message):

    if message.chat.id != ADMIN_ID:
        return

    bot.reply_to(
        message,
        "💼 My Wallet\n\n"
        f"`{MY_WALLET_ADDRESS}`",
        parse_mode="Markdown"
    )


# =========================================================
# إدخال عنوان المحفظة
# =========================================================

def process_address_step(message):

    if message.chat.id != ADMIN_ID:
        return

    address = message.text.strip()

    if not w3.is_address(address):

        bot.reply_to(
            message,
            "❌ العنوان لي بعثتو غالط!\n\n"
            "تأكد منه وعاود ابدأ من جديد بـ /send"
        )

        return

    user_data[message.chat.id] = {
        'target_address': address
    }

    msg = bot.reply_to(
        message,
        f"✅ راني حفظت العنوان:\n"
        f"`{address}`\n\n"
        f"💵 قولي شحال ترسل:",
        parse_mode="Markdown"
    )

    bot.register_next_step_handler(
        msg,
        process_amount_step
    )


# =========================================================
# إدخال الكمية وإرسال USDT
# =========================================================

def process_amount_step(message):

    if message.chat.id != ADMIN_ID:
        return

    try:

        amount_text = message.text.strip()

        amount = float(amount_text)

        if amount <= 0:

            bot.reply_to(
                message,
                "❌ لازم تكون الكمية أكبر من 0."
            )

            return

        # ================= العنوان =================

        target_address = w3.to_checksum_address(
            user_data[message.chat.id]['target_address']
        )

        # ================= كمية USDT =================

        amount_in_wei = int(
            amount * (10 ** 18)
        )

        # ================= رصيد USDT =================

        usdt_balance = usdt_contract.functions.balanceOf(
            my_address
        ).call()

        if usdt_balance < amount_in_wei:

            current_balance = usdt_balance / (10 ** 18)

            bot.reply_to(
                message,
                f"❌ الصولد تاعك تاع USDT ما يكفيش!\n\n"
                f"💵 راه عندك دوق: {current_balance:.6f} USDT\n"
                f"💸 راك حاب تبعث: {amount} USDT"
            )

            return

        # ================= Nonce =================

        nonce = w3.eth.get_transaction_count(
            my_address
        )

        # ================= بناء المعاملة =================

        tx = usdt_contract.functions.transfer(
            target_address,
            amount_in_wei
        ).build_transaction({

            'chainId': 56,

            'gas': 60000,

            'gasPrice': w3.eth.gas_price,

            'nonce': nonce
        })

        # ================= توقيع =================

        signed_tx = w3.eth.account.sign_transaction(
            tx,
            private_key=PRIVATE_KEY
        )

        # ================= إرسال =================

        tx_hash = w3.eth.send_raw_transaction(
            signed_tx.raw_transaction
        )

        # ================= انتظار التأكيد =================

        receipt = w3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=120
        )

        tx_hash_hex = w3.to_hex(tx_hash)

        # ================= نجاح =================

        if receipt['status'] == 1:

            new_balance_raw = usdt_contract.functions.balanceOf(
                my_address
            ).call()

            new_balance = new_balance_raw / (10 ** 18)

            success_msg = (
                "✅ **تم الإرسال وتأكيد العملية بنجاح!**\n\n"
                f"💵 الكمية: {amount} USDT\n\n"
                f"📍 إلى المحفظة:\n"
                f"`{target_address}`\n\n"
                f"🔗 رابط التأكيد:\n"
                f"https://bscscan.com/tx/{tx_hash_hex}\n\n"
                f"💰 **الرصيد الحالي:** "
                f"{new_balance:.6f} USDT"
            )

            bot.reply_to(
                message,
                success_msg,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

        else:

            bot.reply_to(
                message,
                "❌ للأسف فشلت المعاملة في الشبكة!\n\n"
                f"🔗 شيك المعاملة:\n"
                f"https://bscscan.com/tx/{tx_hash_hex}",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

    except ValueError:

        bot.reply_to(
            message,
            "❌ الكمية لي كتبتها مش صحيحة!\n\n"
            "لازم تكتب رقم كيما:\n"
            "`10`\n"
            "`134.5`\n\n"
            "عاود ابدأ بـ /send",
            parse_mode="Markdown"
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ صار خطأ:\n`{str(e)}`",
            parse_mode="Markdown"
        )


# =========================================================
# تشغيل البوت
# =========================================================

print("🤖 البوت يعمل في الصمت وبدون رسائل مزعجة...")

if __name__ == '__main__':
    bot.infinity_polling()

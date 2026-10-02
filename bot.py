import telebot
from web3 import Web3
import os

# ================= الإعدادات المخفية (Railway) =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")

# ================= الإعدادات الخاصة بك =================
MY_WALLET_ADDRESS = "0x96aafcE765B0a03433483eDF4CC7311A5e7adADD"
ADMIN_ID = 822007358

# ================= إعدادات BSC =================
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

# ================= إنشاء البوت والاتصال بـ BSC =================
bot = telebot.TeleBot(BOT_TOKEN)

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
# /start
# =========================================================

@bot.message_handler(commands=['start'])
def send_welcome(message):

    if message.chat.id != ADMIN_ID:
        return

    bot.reply_to(
        message,
        "أهلاً بك يا سيّد! 👋\n\n"
        "الأوامر المتاحة:\n\n"
        "💵 /balance — معرفة رصيد USDT\n"
        "💸 /send — إرسال USDT"
    )


# =========================================================
# /balance
# =========================================================

@bot.message_handler(commands=['balance'])
def check_balance(message):

    # الأدمن فقط
    if message.chat.id != ADMIN_ID:
        return

    try:

        # قراءة رصيد USDT
        usdt_balance_raw = usdt_contract.functions.balanceOf(
            my_address
        ).call()

        # USDT على BSC يستخدم 18 decimals
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
# إدخال عنوان المحفظة
# =========================================================

def process_address_step(message):

    address = message.text.strip()

    # التحقق من صحة العنوان
    if not w3.is_address(address):

        bot.reply_to(
            message,
            "❌ العنوان لي بعثتو غالط!\n\n"
            "تأكد منه وعاود ابدأ من جديد بـ /send"
        )

        return

    # حفظ العنوان
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

    try:

        # ================= قراءة الكمية =================

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

        # ================= تحويل USDT إلى أصغر وحدة =================

        amount_in_wei = int(
            amount * (10 ** 18)
        )

        # ================= التحقق من رصيد USDT =================

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

        # ================= توقيع المعاملة =================

        signed_tx = w3.eth.account.sign_transaction(
            tx,
            private_key=PRIVATE_KEY
        )

        # ================= إرسال المعاملة =================

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

            # قراءة الرصيد الجديد
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

        # ================= فشل المعاملة =================

        else:

            bot.reply_to(
                message,
                "❌ للأسف فشلت المعاملة في الشبكة!\n\n"
                f"🔗 شيك المعاملة:\n"
                f"https://bscscan.com/tx/{tx_hash_hex}",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

    # ================= خطأ في الكمية =================

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

    # ================= أخطاء أخرى =================

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

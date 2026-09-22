import telebot
from web3 import Web3
import os

# ================= الإعدادات المخفية (تأتي من Railway) =================
# لا تكتب التوكن والمفتاح هنا، بل أضفها في قسم Variables في Railway
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")

# ================= الإعدادات الخاصة بك =================
MY_WALLET_ADDRESS = "0x96aafcE765B0a03433483eDF4CC7311A5e7adADD"
ADMIN_ID = 822007358

# ================= إعدادات البلوكتشين (لا تغيرها) =================
BSC_RPC = "https://bsc-dataseed.binance.org/"
USDT_CONTRACT_ADDRESS = "0x55d398326f99059fF775485246999027B3197955" # USDT BEP-20 Contract

USDT_ABI = [
    {
        "constant": False,
        "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

# التحقق من وجود المتغيرات السرية لتفادي الأخطاء
if not BOT_TOKEN or not PRIVATE_KEY:
    print("⚠️ تحذير: BOT_TOKEN أو PRIVATE_KEY غير موجودين. تأكد من إضافتهما في Railway Variables.")

# ربط البوت والبلوكتشين
bot = telebot.TeleBot(BOT_TOKEN)
w3 = Web3(Web3.HTTPProvider(BSC_RPC))

my_address = w3.to_checksum_address(MY_WALLET_ADDRESS)
usdt_contract = w3.eth.contract(address=w3.to_checksum_address(USDT_CONTRACT_ADDRESS), abi=USDT_ABI)

# قاموس لتخزين بيانات المحادثة مؤقتاً
user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # حماية البوت ليخدمك أنت فقط
    if message.chat.id != ADMIN_ID:
        return
    bot.reply_to(message, "مرحباً بك يا مدير! 👋\n\nأرسل الأمر /send للبدء في تحويل USDT.")

# ----------------- الخطوة 1: بدء الأمر -----------------
@bot.message_handler(commands=['send'])
def start_send(message):
    if message.chat.id != ADMIN_ID:
        return
    
    msg = bot.reply_to(message, "🔗 حسناً، يرجى إرسال **عنوان محفظة المستلم** الذي تريد الإرسال إليه:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_address_step)

# ----------------- الخطوة 2: استلام العنوان -----------------
def process_address_step(message):
    address = message.text.strip()
    
    # التحقق من صحة العنوان
    if not w3.is_address(address):
        bot.reply_to(message, "❌ العنوان غير صحيح! يرجى التأكد منه والبدء من جديد بكتابة /send")
        return
        
    # حفظ العنوان مؤقتاً
    user_data[message.chat.id] = {'target_address': address}
    msg = bot.reply_to(message, f"✅ تم حفظ العنوان:\n`{address}`\n\n💵 الآن أرسل **الكمية** (مثال: 134.5):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_amount_step)

# ----------------- الخطوة 3: استلام الكمية والتنفيذ -----------------
def process_amount_step(message):
    try:
        # تحويل النص إلى رقم
        amount = float(message.text.strip())
        
        # استرجاع العنوان
        target_address = w3.to_checksum_address(user_data[message.chat.id]['target_address'])
        
        bot.reply_to(message, f"⏳ جاري إرسال {amount} USDT...\nيرجى الانتظار قليلاً.")
        
        # تحويل الكمية إلى صيغة البلوكتشين (Wei)
        amount_in_wei = int(amount * (10 ** 18))
        
        # جلب الـ Nonce الخاص بمحفظتك
        nonce = w3.eth.get_transaction_count(my_address)
        
        # بناء المعاملة الذكية
        tx = usdt_contract.functions.transfer(target_address, amount_in_wei).build_transaction({
            'chainId': 56, # شبكة BSC
            'gas': 60000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })
        
        # توقيع المعاملة بالمفتاح الخاص
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        
        # إرسال المعاملة للبلوكتشين
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hash_hex = w3.to_hex(tx_hash)
        
        bot.reply_to(message, f"✅ **تم الإرسال بنجاح!**\n\nالكمية: {amount} USDT\nإلى: `{target_address}`\n\nرابط التأكيد (BscScan):\nhttps://bscscan.com/tx/{tx_hash_hex}", parse_mode="Markdown", disable_web_page_preview=True)
        
    except ValueError:
        bot.reply_to(message, "❌ الكمية غير صحيحة! يجب أن تكتب رقماً (مثل 10 أو 134.5). ابدأ من جديد بكتابة /send")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء تنفيذ المعاملة:\n`{str(e)}`\n\n(تأكد من وجود رصيد كافي من USDT، وكمية قليلة من BNB لدفع رسوم الغاز في محفظتك)", parse_mode="Markdown")

# تشغيل البوت
print("البوت يعمل الآن ومستعد لتلقي الأوامر...")
if __name__ == '__main__':
    bot.infinity_polling()

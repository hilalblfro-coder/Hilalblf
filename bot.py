import telebot
from web3 import Web3
import os

# ================= الإعدادات المخفية (تأتي من Railway) =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")

# ================= الإعدادات الخاصة بك =================
MY_WALLET_ADDRESS = "0x96aafcE765B0a03433483eDF4CC7311A5e7adADD"
ADMIN_ID = 822007358

# ================= إعدادات البلوكتشين =================
BSC_RPC = "https://bsc-dataseed.binance.org/"
USDT_CONTRACT_ADDRESS = "0x55d398326f99059fF775485246999027B3197955" # USDT BEP-20

# ABI الخاص بالتحويل ومعرفة الرصيد
USDT_ABI = [
    {
        "constant": False,
        "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    }
]

if not BOT_TOKEN or not PRIVATE_KEY:
    print("⚠️ تحذير: BOT_TOKEN أو PRIVATE_KEY مش موجودين.")

bot = telebot.TeleBot(BOT_TOKEN)
w3 = Web3(Web3.HTTPProvider(BSC_RPC))

my_address = w3.to_checksum_address(MY_WALLET_ADDRESS)
usdt_contract = w3.eth.contract(address=w3.to_checksum_address(USDT_CONTRACT_ADDRESS), abi=USDT_ABI)

user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.id != ADMIN_ID:
        return
    bot.reply_to(message, "أهلاً بك يا سيّد! 👋\n\nابعث الأمر /send باش نبدؤوا نبعثو USDT.")

@bot.message_handler(commands=['send'])
def start_send(message):
    if message.chat.id != ADMIN_ID:
        return
    
    # التعديل الأول هنا
    msg = bot.reply_to(message, "🔗 هات لادراس BEP 20:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_address_step)

def process_address_step(message):
    address = message.text.strip()
    
    if not w3.is_address(address):
        bot.reply_to(message, "❌ العنوان لي بعثتو غالط! تأكد منه وعاود ابدأ من جديد بـ /send")
        return
        
    user_data[message.chat.id] = {'target_address': address}
    
    # التعديل الثاني هنا
    msg = bot.reply_to(message, f"✅ راني حفظت العنوان:\n`{address}`\n\n💵 قولي شحال ترسل:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_amount_step)

def process_amount_step(message):
    try:
        amount = float(message.text.strip())
        target_address = w3.to_checksum_address(user_data[message.chat.id]['target_address'])
        
        bot.reply_to(message, "⏳ راني نتحقق من الصولد و الشبكة...")

        amount_in_wei = int(amount * (10 ** 18))

        # 1. التحقق من رصيد USDT
        usdt_balance = usdt_contract.functions.balanceOf(my_address).call()
        if usdt_balance < amount_in_wei:
            bot.reply_to(message, f"❌ الصولد تاعك تاع USDT ما يكفيش!\nعندك في المحفظة: {usdt_balance / (10**18)} USDT\nراك حاب تبعث: {amount} USDT")
            return

        # 2. التحقق من رصيد BNB للرسوم
        bnb_balance = w3.eth.get_balance(my_address)
        if bnb_balance < w3.to_wei(0.0005, 'ether'):
            bot.reply_to(message, "❌ صولد الـ BNB ما يكفيش باش تخلص حق الغاز (Gas Fees)!")
            return

        bot.reply_to(message, f"⏳ جاري إرسال {amount} USDT والانتظار حتى تؤكد الشبكة...")

        nonce = w3.eth.get_transaction_count(my_address)
        
        tx = usdt_contract.functions.transfer(target_address, amount_in_wei).build_transaction({
            'chainId': 56,
            'gas': 60000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # 3. الانتظار حتى تأكيد المعاملة في البلوكتشين
        bot.reply_to(message, "⏳ المعاملة راها تتأكد في البلوكتشين، اصبر عليا ثواني برك...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        tx_hash_hex = w3.to_hex(tx_hash)

        # 4. التأكد من نجاح العملية
        if receipt['status'] == 1:
            bot.reply_to(message, f"✅ **تم الإرسال وتأكيد العملية بنجاح!**\n\nالكمية: {amount} USDT\nإلى المحفظة: `{target_address}`\n\nرابط التأكيد (BscScan):\nhttps://bscscan.com/tx/{tx_hash_hex}", parse_mode="Markdown", disable_web_page_preview=True)
        else:
            bot.reply_to(message, f"❌ للأسف فشلت المعاملة في الشبكة (Transaction Failed)!\nشيك الرابط:\nhttps://bscscan.com/tx/{tx_hash_hex}", parse_mode="Markdown")

    except ValueError:
        bot.reply_to(message, "❌ الكمية لي كتبتها مش صحيحة! لازم تكتب رقم (كيما 10 أو 134.5). عاود ابدأ بـ /send")
    except Exception as e:
        bot.reply_to(message, f"❌ صار خطأ:\n`{str(e)}`", parse_mode="Markdown")

print("البوت راه يمشي بالدارجة ومستعد...")
if __name__ == '__main__':
    bot.infinity_polling()

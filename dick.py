import asyncio
from threading import Thread
from flask import Flask
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

# ─── Flask Keep-Alive ───────────────────────────────────────
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
# ────────────────────────────────────────────────────────────

# تنظیمات اصلی گپ و عملیات
TARGET_CHAT_ID = -1004346160765
OWNER_ID = 8616643544
SPAM_TEXT = "test"
TOTAL_MESSAGES = 500
DELAY_BETWEEN = 0.01

ACCOUNTS_DATA = [
    {
        "session": "acc1",
        "api_id": 32784253,
        "api_hash": "78fd270f778ab1c59d845314238b658a",
        "phone": "+989143222307"
    },
    {
        "session": "acc2",
        "api_id": 25079096,
        "api_hash": "efd3281aa624562e3cd990c5f44d9560",
        "phone": "+989379958956"
    },
    {
        "session": "acc3",
        "api_id": 22412795,
        "api_hash": "bc83db1ef79b4ce881d12ee56398a346",
        "phone": "+989210387470"
    },
    {
        "session": "acc4",
        "api_id": 31147796,
        "api_hash": "13080d29c22cd31e4bb543403a871f08",
        "phone": "+12344070511"
    },
    {
        "session": "acc5",
        "api_id": 39322690,
        "api_hash": "f3c404beaa583264ad8dcaf81025496a",
        "phone": "+13092339513"
    }
]

clients = []
is_running = False

async def round_robin_spam(chat_id, total, text, delay):
    global is_running
    is_running = True
    num_clients = len(clients)
    
    print(f"[*] Starting cycle: {total} messages across {num_clients} accounts...")
    
    for i in range(total):
        if not is_running:
            print("[!] Operation stopped manually.")
            break
            
        current_client = clients[i % num_clients]
        
        try:
            await current_client.send_message(chat_id, text)
            print(f"[{i+1}/{total}] Sent by Acc #{i % num_clients + 1}")
            await asyncio.sleep(delay)
        except FloodWaitError as e:
            print(f"[!] Acc #{i % num_clients + 1} FloodWait: sleeping {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"[!] Error on Acc #{i % num_clients + 1}: {e}")

    is_running = False
    print("[+] Finished spam cycle.")

async def main():
    global clients, is_running
    
    for acc in ACCOUNTS_DATA:
        client = TelegramClient(acc["session"], acc["api_id"], acc["api_hash"])
        await client.start(phone=acc["phone"])
        clients.append(client)
        me = await client.get_me()
        print(f"[✓] Logged in: {me.first_name} (ID: {me.id})")

    owner_client = clients[0]

    @owner_client.on(events.NewMessage(chats=TARGET_CHAT_ID, from_users=OWNER_ID))
    async def handler(event):
        global is_running
        
        if event.raw_text == '.startgacha':
            await event.delete()
            if not is_running:
                asyncio.create_task(
                    round_robin_spam(TARGET_CHAT_ID, TOTAL_MESSAGES, SPAM_TEXT, DELAY_BETWEEN)
                )
                
        elif event.raw_text == '.stop':
            await event.delete()
            is_running = False

    print("\n[READY] Self-bot is active. Send `.startgacha` in the group to begin.")
    await asyncio.gather(*(c.run_until_disconnected() for c in clients))

if __name__ == '__main__':
    keep_alive()  # ← فقط این یه خط اضافه شد اینجا
    asyncio.run(main())

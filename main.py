import asyncio
from telethon import TelegramClient, events
from telethon.errors import (
    FloodWaitError, AuthKeyDuplicatedError,
    ChatWriteForbiddenError, UserNotParticipantError,
    ChannelPrivateError, ChatAdminRequiredError
)

# ─── تنظیمات اصلی ───────────────────────────────────────────
OWNER_IDS = [8616643544, 7867345927, 8435841113]
SPAM_TEXT = "Yo"
TOTAL_MESSAGES = 500
DELAY_BETWEEN = 0.5
ANTI_SPAM_BOT_ID = 6157455819
FLOOD_REST = 300
BATCH_SIZE = 100
BATCH_REST = 120

ACCOUNTS_DATA = [
    {"session": "acc1", "api_id": 31097906, "api_hash": "b9a8797d98c9118cbf3c5f1cdec71dff", "phone": "+989198779413"},
    {"session": "acc2", "api_id": 25079096, "api_hash": "efd3281aa624562e3cd990c5f44d9560", "phone": "+989379958956"},
    {"session": "acc3", "api_id": 22412795, "api_hash": "bc83db1ef79b4ce881d12ee56398a346", "phone": "+989210387470"},
    {"session": "acc4", "api_id": 31147796, "api_hash": "13080d29c22cd31e4bb543403a871f08", "phone": "+12344070511"},
    {"session": "acc5", "api_id": 39322690, "api_hash": "f3c404beaa583264ad8dcaf81025496a", "phone": "+13092339513"},
    {"session": "acc6", "api_id": 37100132, "api_hash": "acc9a02c9fd74d68de02b2404dc2fec7", "phone": "+15827772263"},
]

clients = []
running_chats = {}
flooded_clients = set()

async def rest_flooded_client(client, acc_num):
    flooded_clients.add(id(client))
    print(f"[~] Acc #{acc_num} resting {FLOOD_REST}s...")
    await asyncio.sleep(FLOOD_REST)
    flooded_clients.discard(id(client))
    print(f"[+] Acc #{acc_num} back in pool!")

async def round_robin_spam(chat_id, total, text, delay):
    # همه کلاینت‌ها رو میذاریم — تو حلقه خودش چک میکنه
    all_clients = clients.copy()

    if not all_clients:
        print(f"[!] No clients available!")
        return

    running_chats[chat_id] = {"is_running": True, "sent_count": 0}
    # اکانت‌هایی که تو این گروه نیستن
    banned_clients = set()

    print(f"[*] Chat {chat_id}: starting {total} messages...")

    i = 0
    while i < total:
        if not running_chats.get(chat_id, {}).get("is_running"):
            print(f"[!] Chat {chat_id} stopped.")
            break

        # اکانت‌های فعال (نه فلاد، نه banned)
        active = [c for c in all_clients if id(c) not in flooded_clients and id(c) not in banned_clients]

        if not active:
            print(f"[!] No active accounts for chat {chat_id}!")
            break

        current = active[i % len(active)]
        acc_num = all_clients.index(current) + 1

        try:
            await current.send_message(chat_id, text)
            running_chats[chat_id]["sent_count"] += 1
            sent = running_chats[chat_id]["sent_count"]
            print(f"[Chat {chat_id}] [{sent}/{total}] Acc #{acc_num} | Remaining: {total - sent}")
            await asyncio.sleep(delay)
            i += 1

            # هر BATCH_SIZE پیام استراحت
            if sent % BATCH_SIZE == 0 and sent < total:
                print(f"[~] {BATCH_SIZE} msgs done. Resting {BATCH_REST}s...")
                await asyncio.sleep(BATCH_REST)

        except FloodWaitError as e:
            print(f"[!] Acc #{acc_num} flooded! Rest {FLOOD_REST}s, others continue.")
            asyncio.create_task(rest_flooded_client(current, acc_num))

        except (ChatWriteForbiddenError, UserNotParticipantError, ChannelPrivateError, ChatAdminRequiredError):
            me = await current.get_me()
            print(f"[~] Acc #{acc_num} ({me.first_name}) not in chat {chat_id} — skipped permanently.")
            banned_clients.add(id(current))

        except AuthKeyDuplicatedError:
            print(f"[CRITICAL] Acc #{acc_num} session invalid! Stopping.")
            running_chats[chat_id]["is_running"] = False
            break

        except Exception as e:
            print(f"[!] Error Acc #{acc_num}: {e}")
            await asyncio.sleep(0.5)
            i += 1

    sent = running_chats.get(chat_id, {}).get("sent_count", 0)
    running_chats.pop(chat_id, None)
    print(f"[+] Chat {chat_id} done. Total sent: {sent}")

    try:
        await clients[0].send_message(OWNER_IDS[0], f"✅ Chat {chat_id} finished! Sent: {sent}")
    except Exception as e:
        print(f"[!] Notify failed: {e}")

async def main():
    global clients

    for acc in ACCOUNTS_DATA:
        client = TelegramClient(acc["session"], acc["api_id"], acc["api_hash"])
        await client.start(phone=acc["phone"])
        clients.append(client)
        me = await client.get_me()
        print(f"[✓] Logged in: {me.first_name} (ID: {me.id})")

    owner_client = clients[0]

    @owner_client.on(events.NewMessage(from_users=OWNER_IDS))
    async def command_handler(event):
        chat_id = event.chat_id

        if event.raw_text.startswith('.startgacha'):
            await event.delete()
            if running_chats.get(chat_id, {}).get("is_running"):
                print(f"[!] Chat {chat_id} already running.")
                return
            parts = event.raw_text.split()
            total = min(int(parts[1]), 500) if len(parts) > 1 and parts[1].isdigit() else TOTAL_MESSAGES
            asyncio.create_task(round_robin_spam(chat_id, total, SPAM_TEXT, DELAY_BETWEEN))

        elif event.raw_text == '.stop':
            await event.delete()
            if chat_id in running_chats:
                running_chats[chat_id]["is_running"] = False
                print(f"[!] Chat {chat_id} stopped.")

        elif event.raw_text == '.status':
            if running_chats.get(chat_id, {}).get("is_running"):
                sent = running_chats[chat_id]["sent_count"]
                flooded = len(flooded_clients)
                await event.reply(f"🟢 Running | Sent: {sent} | Flooded: {flooded}")
            else:
                await event.reply("🔴 Stopped")

    @owner_client.on(events.NewMessage())
    async def anti_spam_handler(event):
        chat_id = event.chat_id
        if event.sender_id == ANTI_SPAM_BOT_ID and running_chats.get(chat_id, {}).get("is_running"):
            running_chats[chat_id]["is_running"] = False
            print(f"[!] Anti-spam in {chat_id}! Stopped.")
            try:
                await owner_client.send_message(OWNER_IDS[0], f"⛔ Anti-spam in {chat_id}! Stopped.")
            except:
                pass

    print("\n[READY] .startgacha [1-500] | .stop | .status")
    await asyncio.gather(*(c.run_until_disconnected() for c in clients))

if __name__ == '__main__':
    asyncio.run(main())

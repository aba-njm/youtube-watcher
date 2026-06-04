import os
import asyncio
import feedparser
import time
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- جلب البيانات من خزنة جيت هاب السرية ---
api_id = int(os.environ.get('API_ID', 0)) 
api_hash = os.environ.get('API_HASH', 'hash')
session_string = os.environ.get('TELEGRAM_SESSION', '') # النص المشفر البديل لملف الجلسة

target_bot = '@Put_Bot_Username_Here'     # يوزر بوت التحميل
second_account = '@Your_Second_Account'   # يوزر حسابك لاستلام التقرير
# ----------------------------------------------------------------------

# تشغيل تليجرام بالنص المشفر آمن 100%
client = TelegramClient(StringSession(session_string), api_id, api_hash)

def get_downloaded_links():
    if not os.path.exists('history.txt'): return []
    with open('history.txt', 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def save_to_history(link):
    with open('history.txt', 'a', encoding='utf-8') as f:
        f.write(link + '\n')

async def main():
    await client.start()
    print("🚀 بدء فحص القنوات الأوتوماتيكي...")

    downloaded = get_downloaded_links()
    
    with open('channels.txt', 'r', encoding='utf-8') as f:
        channels = [line.strip() for line in f if line.strip()]

    new_videos_found = 0

    for channel_rss in channels:
        feed = feedparser.parse(channel_rss)
        if not feed.entries: continue
            
        latest_video = feed.entries[0]
        video_link = latest_video.link
        
        if video_link in downloaded:
            continue # الفيديو تم تحميله من قبل، تخطي
            
        print(f"🆕 فيديو جديد رصدته: {latest_video.title}")
        
        try:
            sent_msg = await client.send_message(target_bot, video_link)
            start_time = time.time()
            is_done = False
            
            while (time.time() - start_time) < 90:
                await asyncio.sleep(2)
                async for message in client.iter_messages(target_bot, limit=5):
                    if message.id <= sent_msg.id: continue
                    
                    if message.buttons:
                        pressed = False
                        for row in message.buttons:
                            for btn in row:
                                if any(q in btn.text for q in ['1080', '720', '480']):
                                    await btn.click()
                                    pressed = True; break
                            if pressed: break
                        if not pressed: await message.click(0)
                        is_done = True; break
                if is_done: break

            if is_done:
                save_to_history(video_link)
                new_videos_found += 1
                await asyncio.sleep(4)
                async for m in client.iter_messages(target_bot, limit=3):
                    if m.buttons:
                        for row in m.buttons:
                            for btn in row:
                                if 'original' in btn.text.lower():
                                    await btn.click(); break
        except Exception as e:
            print(f"❌ خطأ: {e}")
        await asyncio.sleep(5)

    if new_videos_found > 0:
        await client.send_message(second_account, f"✅ تم تحميل {new_videos_found} فيديو جديد بنجاح.")

with client:
    client.loop.run_until_complete(main())
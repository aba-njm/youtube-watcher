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

target_bot =  -5232399039    # يوزر بوت التحميل
second_account = '@al_rawl'   # يوزر حسابك لاستلام التقرير
# ----------------------------------------------------------------------
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
    print("🚀 بدء فحص القنوات الأوتوماتيكي التدريجي (حد 100 فيديو)...")

    downloaded = get_downloaded_links()
    
    with open('channels.txt', 'r', encoding='utf-8') as f:
        channels = [line.strip() for line in f if line.strip()]

    new_videos_found = 0
    MAX_VIDEOS_PER_RUN = 100  # 💡 تم تعديل الحد الأقصى لـ 100 فيديو في كل 15 دقيقة

    for channel_rss in channels:
        if new_videos_found >= MAX_VIDEOS_PER_RUN:
            print(f"⚠️ تم الوصول للحد الأقصى ({MAX_VIDEOS_PER_RUN} فيديو) في هذه الدورة. إيقاف مؤقت ذكي لحفظ البيانات...")
            break

        feed = feedparser.parse(channel_rss)
        if not feed.entries: continue
            
        for entry in reversed(feed.entries):
            if new_videos_found >= MAX_VIDEOS_PER_RUN: break
                
            video_link = entry.link
            if video_link in downloaded: continue 
                
            print(f"🆕 فيديو جديد رصدته: {entry.title}")
            
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
                                    if any(q in btn.text for q in ['1080', '720', '480', '360']):
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
            
            await asyncio.sleep(6) # مهلة أمان بين الفيديوهات

    if new_videos_found > 0:
        await client.send_message(second_account, f"✅ دورة ناجحة: تم تحميل {new_videos_found} فيديو، وسيتم استكمال الباقي تلقائياً بعد 15 دقيقة.")

with client:
    client.loop.run_until_complete(main())

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

target_bot = -5232399039    # يوزر بوت التحميل (المجموعة أو الشات)
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
    print("🚀 بدء فحص القنوات بنظام الضغط الفوري المباشر على أول زر...")

    downloaded = get_downloaded_links()
    
    with open('channels.txt', 'r', encoding='utf-8') as f:
        channels = [line.strip() for line in f if line.strip()]

    new_videos_found = 0
    MAX_VIDEOS_PER_RUN = 100 
    
    # 🛑 الكلمات الدليلية لكشف الروابط المعطوبة أو المحظورة من البوت
    error_keywords = ['عذراً', 'خطأ', 'فشل', 'private', 'unavailable', 'deleted', 'invalid', 'copyright', 'لم يتم العثور']
    
    # 🟢 الكلمات المفتاحية المخصصة للنجاح النصي
    success_keywords = ['جاري التحميل', 'بدأ التحميل', 'تنزيل', 'تم البدء', 'تحميل الفيديو']

    for channel_rss in channels:
        if new_videos_found >= MAX_VIDEOS_PER_RUN:
            print(f"⚠️ تم الوصول للحد الأقصى ({MAX_VIDEOS_PER_RUN} فيديو). إيقاف مؤقت...")
            break

        feed = feedparser.parse(channel_rss)
        if not feed.entries: continue
            
        for entry in reversed(feed.entries):
            if new_videos_found >= MAX_VIDEOS_PER_RUN: break
                
            original_link = entry.link
            was_short = 'shorts' in original_link.lower()
            
            video_link = original_link
            if '/shorts/' in video_link:
                video_link = video_link.replace('?', '&').replace('/shorts/', '/watch?v=')
                
            if video_link in downloaded: continue 
                
            print(f"\n🆕 محتوى جديد رصدته: {entry.title}")
            
            try:
                sent_msg = await client.send_message(target_bot, video_link)
                start_time = time.time()
                is_done = False
                is_skipped = False
                
                if was_short:
                    # ⭐ نظام معالجة الـ Shorts
                    print("⚡ هذا الرابط فيديو قصير (Shorts)، بانتظار استجابة البوت الأولى...")
                    while (time.time() - start_time) < 30:
                        await asyncio.sleep(2)
                        async for message in client.iter_messages(target_bot, limit=3):
                            if message.id <= sent_msg.id: continue
                            is_done = True
                            break
                        if is_done: break
                    
                    if is_done:
                        print("⏳ الانتظار 12 ثانية للتأكد من تحميل الـ Short بنجاح...")
                        await asyncio.sleep(12)
                        save_to_history(video_link)
                        new_videos_found += 1
                        
                else:
                    # ⭐ نظام معالجة الفيديو العادي (اضغط أول زر فوراً)
                    downloaded_quality = "أول زر متاح في القائمة"
                    
                    while (time.time() - start_time) < 90:
                        await asyncio.sleep(2)
                        async for message in client.iter_messages(target_bot, limit=5):
                            if message.id <= sent_msg.id: continue
                            
                            msg_text = message.text.lower() if message.text else ""
                            
                            # 1️⃣ فحص رسائل الفشل
                            if any(word in msg_text for word in error_keywords):
                                print(f"⚠️ تخطي: الرابط معطل أو غير متاح في البوت.")
                                save_to_history(video_link)
                                new_videos_found += 1
                                is_skipped = True
                                is_done = True
                                break
                            
                            # 2️⃣ فحص رسائل النجاح النصية
                            if any(word in msg_text for word in success_keywords):
                                print(f"🎯 تم رصد رسالة نجاح نصية معينة: ({msg_text})")
                                is_done = True
                                break
                            
                            # 3️⃣ 🔥 الضغط الفوري على أول زر يظهر في الرسالة
                            if message.buttons:
                                first_button = message.buttons[0][0] # التقط أول زر في السطر الأول مباشرة
                                button_text = first_button.text if first_button.text else "غير معروف"
                                
                                print(f"🎯 تم العثور على أزرار! الضغط فوراً على أول زر متاح: ({button_text})")
                                await first_button.click()
                                downloaded_quality = button_text
                                is_done = True
                                break
                                
                        if is_done: break

                    if is_done and not is_skipped:
                        save_to_history(video_link)
                        new_videos_found += 1
                        print(f"✅ تم حفظ الفيديو بنجاح في السجل بعد التفاعل مع البوت بجودة: {downloaded_quality}")
                    
                    # نضغط زر original فقط للفيديوهات العادية السليمة
                    if is_done and not is_skipped and not was_short:
                        print("⏳ الانتظار 5 ثواني للتأكد من ظهور خيارات الصوت (Original)...")
                        await asyncio.sleep(5)
                        async for m in client.iter_messages(target_bot, limit=3):
                            if m.buttons:
                                audio_pressed = False
                                for row in m.buttons:
                                    for btn in row:
                                        if 'original' in btn.text.lower():
                                            print(f"🎵 تم اختيار الصوت الأصلي: {btn.text}")
                                            await btn.click()
                                            audio_pressed = True
                                            break
                                    if audio_pressed: break
                                if audio_pressed: break
            except Exception as e:
                print(f"❌ خطأ: {e}")
            
            await asyncio.sleep(6)

    # 📊 إرسال التقارير النهائية للحساب الثاني
    if new_videos_found > 0:
        await client.send_message(second_account, f"✅ دورة ناجحة ومباشرة: تم معالجة {new_videos_found} فيديو بالضغط التلقائي السريع على الزر الأول.")

with client:
    client.loop.run_until_complete(main())

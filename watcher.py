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
    print("🚀 بدء التشغيل: تم دمج نظام الفيديوهات والـ Shorts معاً للضغط الإجباري على الأزرار...")

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
            
            # 🔄 توحيد وتحويل روابط Shorts برمجياً إلى روابط عادية لضمان قبول البوت
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
                downloaded_quality = "غير معروفة"
                
                # 🔥 نظام فحص موحد وصارم لجميع الروابط بدون أي تخطي تلقائي
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
                        
                        # 3️⃣ 🎯 نظام القنص المباشر لزر جودة 854p📹 (سيعمل على الفيديوهات والـ Shorts بدون تفرقة)
                        if message.buttons:
                            btn_target = None
                            
                            for row in message.buttons:
                                for btn in row:
                                    btn_text = btn.text if btn.text else ""
                                    
                                    # التفتيش على مسمى الجودة المطلوبة
                                    if "854p" in btn_text or "854" in btn_text:
                                        btn_target = btn
                                        break
                                if btn_target: break
                            
                            # الضغط الفوري عند العثور على الزر
                            if btn_target:
                                print(f"✅ تم العثور على زر الجودة المطلوبة وضغطه: ({btn_target.text})")
                                await btn_target.click()
                                downloaded_quality = btn_target.text
                                is_done = True
                                break
                            
                            # حماية احتياطية: إذا مرت 40 ثانية وظهرت أزرار أخرى ولم نجد زر 854، يضغط الزر الأول
                            if (time.time() - start_time) > 40:
                                print("ℹ️ مرت 40 ثانية ولم نجد زر 854، الضغط على أول زر متاح تفادياً للتعليق...")
                                await message.click(0)
                                downloaded_quality = "تلقائي (الزر الأول احتياطياً)"
                                is_done = True
                                break
                            
                    if is_done: break

                if is_done and not is_skipped:
                    save_to_history(video_link)
                    new_videos_found += 1
                    print(f"💾 تم حفظ الرابط بنجاح في السجل بعد التفاعل بجودة: {downloaded_quality}")
                    
                    # الضغط على زر الصوت الأصلي الاحتياطي بعد معالجة الأزرار بنجاح
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
                print(f"❌ خطأ أثناء معالجة الرابط: {e}")
            
            await asyncio.sleep(6) # مهلة أمان بين الفيديوهات

    if new_videos_found > 0:
        await client.send_message(second_account, f"✅ دورة موحدة ناجحة: تم معالجة {new_videos_found} فيديو وقصير (Shorts) بنجاح كامل وضغط أزرار مستقر.")

with client:
    client.loop.run_until_complete(main())

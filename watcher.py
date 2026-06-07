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
    print("🚀 بدء فحص القنوات الأوتوماتيكي التدريجي الذكي...")

    downloaded = get_downloaded_links()
    
    with open('channels.txt', 'r', encoding='utf-8') as f:
        channels = [line.strip() for line in f if line.strip()]

    new_videos_found = 0
    MAX_VIDEOS_PER_RUN = 100 
    
    # 📝 قائمة لجمع الفيديوهات التي لا تدعم جودة 1080 في البوت الحالي
    missing_1080_videos = []

    for channel_rss in channels:
        if new_videos_found >= MAX_VIDEOS_PER_RUN:
            print(f"⚠️ تم الوصول للحد الأقصى ({MAX_VIDEOS_PER_RUN} فيديو) in هذه الدورة. إيقاف مؤقت ذكي...")
            break

        feed = feedparser.parse(channel_rss)
        if not feed.entries: continue
            
        for entry in reversed(feed.entries):
            if new_videos_found >= MAX_VIDEOS_PER_RUN: break
                
            original_link = entry.link
            
            # 💡 فحص ما إذا كان الرابط في الأصل فيديو قصير Shorts
            was_short = 'shorts' in original_link.lower()
            
            # 🔄 تحويل روابط Shorts برمجياً إلى روابط عادية watch?v= لضمان القبول
            video_link = original_link
            if '/shorts/' in video_link:
                video_link = video_link.replace('?', '&').replace('/shorts/', '/watch?v=')
                
            # الفحص في السجل يتم بالرابط المعدّل النهائي لمنع التكرار تماماً
            if video_link in downloaded: continue 
                
            print(f"🆕 محتوى جديد رصدته: {entry.title}")
            
            try:
                sent_msg = await client.send_message(target_bot, video_link)
                start_time = time.time()
                is_done = False
                
                if was_short:
                    # ⭐ نظام معالجة الـ Shorts (مع مهلة أمان مضافة للبوت)
                    print("⚡ هذا الرابط فيديو قصير (Shorts)، بانتظار استجابة البوت الأولى...")
                    while (time.time() - start_time) < 30:
                        await asyncio.sleep(2)
                        async for message in client.iter_messages(target_bot, limit=3):
                            if message.id <= sent_msg.id: continue
                            is_done = True
                            break
                        if is_done: break
                    
                    if is_done:
                        # ⏱️ حظر أمان إضافي لحل مشكلة السرعة: ننتظر 12 ثانية كاملة ليعالج البوت الـ Short براحته
                        print("⏳ الانتظار 12 ثانية للتأكد من استيعاب البوت وتحميل الـ Short بنجاح...")
                        await asyncio.sleep(12)
                        save_to_history(video_link)
                        new_videos_found += 1
                        
                else:
                    # ⭐ نظام معالجة الفيديو العادي وفحص جودة 1080
                    has_1080 = False
                    downloaded_quality = "تلقائية / غير معروفة" # جودة افتراضية في حال لم نلتقط اسم الزر
                    
                    while (time.time() - start_time) < 90:
                        await asyncio.sleep(2)
                        async for message in client.iter_messages(target_bot, limit=5):
                            if message.id <= sent_msg.id: continue
                            
                            if message.buttons:
                                pressed = False
                                # 🔍 الفحص الأول: هل توجد جودة 1080؟
                                for row in message.buttons:
                                    for btn in row:
                                        if '1080' in btn.text:
                                            await btn.click()
                                            has_1080 = True
                                            pressed = True
                                            downloaded_quality = btn.text
                                            break
                                    if pressed: break
                                
                                # 🔍 إذا لم يجد 1080، يضغط على أول جودة متاحة (720، 480 الخ) ويحفظ اسم الجودة
                                if not pressed:
                                    for row in message.buttons:
                                        for btn in row:
                                            if any(q in btn.text for q in ['720', '480', '360']):
                                                await btn.click()
                                                downloaded_quality = btn.text
                                                pressed = True
                                                break
                                        if pressed: break
                                
                                if not pressed: 
                                    await message.click(0) # ضغطة احتياطية لأي زر متاح
                                    downloaded_quality = "تلقائي (أول زر متاح)"
                                    
                                is_done = True
                                break
                        if is_done: break

                    if is_done:
                        # ✅ حفظ الفيديو في الـ history في الحالتين لمنع التكرار
                        save_to_history(video_link)
                        new_videos_found += 1

                        if not has_1080:
                            # 🚫 إذا لم تتوفر جودة 1080، يتم إضافته للتقرير مع توضيح الجودة التي سُحب بها حالياً
                            print(f"⚠️ الفيديو لا يدعم جودة 1080 في هذا البوت! تمت إضافته لقائمة التقرير مع جودته المتاحة.")
                            missing_1080_videos.append(f"🔗 <b>{entry.title}</b>\n📥 الجودة التي حُمِّل بها: <code>{downloaded_quality}</code>\n{video_link}")
                    
                    # نضغط زر original فقط للفيديوهات العادية التي نجحت
                    if is_done and not was_short:
                        await asyncio.sleep(4)
                        async for m in client.iter_messages(target_bot, limit=3):
                            if m.buttons:
                                for row in m.buttons:
                                    for btn in row:
                                        if 'original' in btn.text.lower():
                                            await btn.click()
                                            break
            except Exception as e:
                print(f"❌ خطأ: {e}")
            
            await asyncio.sleep(6) # مهلة أمان بين الفيديوهات الرئيسية

    # 📊 إرسال التقارير النهائية للحساب الثاني
    if new_videos_found > 0:
        await client.send_message(second_account, f"✅ دورة ناجحة: تم معالجة {new_videos_found} فيديو بنجاح واستقرار (بما فيها الـ Shorts المعدلة).")

    if missing_1080_videos:
        # تنسيق رسالة النواقص بشكل احترافي ومقروء
        report_header = "⚠️ <b>فيديوهات لم تتوفر بجودة 1080 في البوت الحالي (تم حفظها في السجل لعدم التكرار):</b>\n(يمكنك نسخها وإرسالها للبوت البديل بجودة أعلى)\n\n"
        report_body = "\n\n".join(missing_1080_videos)
        
        await client.send_message(second_account, f"{report_header}{report_body}", parse_mode='html')
        print(f"📥 تم إرسال تقرير بـ {len(missing_1080_videos)} فيديو لا تدعم جودة 1080 لحسابك.")

with client:
    client.loop.run_until_complete(main())

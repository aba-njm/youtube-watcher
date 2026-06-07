import os
import asyncio
import feedparser
import time
import re  # مكتبة الريجكس لاستخراج الأرقام الصافية من الأزرار
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
    print("🚀 بدء التشغيل الفائق: فحص ذكي وبحد أقصى 1000 فيديو مع صيد أعلى رقم جودة حقيقي...")

    downloaded = get_downloaded_links()
    
    with open('channels.txt', 'r', encoding='utf-8') as f:
        channels = [line.strip() for line in f if line.strip()]

    new_videos_found = 0
    MAX_VIDEOS_PER_RUN = 800  # 📈 تم رفع الحد الأقصى إلى 1000 فيديو هنا
    
    # 🛑 الكلمات الدليلية لكشف الروابط المعطوبة أو المحظورة من البوت
    error_keywords = ['عذراً', 'خطأ', 'فشل', 'private', 'unavailable', 'deleted', 'invalid', 'copyright', 'لم يتم العثور']
    
    # 🟢 الكلمات المفتاحية المخصصة للنجاح النصي
    success_keywords = ['جاري التحميل', 'بدأ التحميل', 'تنزيل', 'تم البدء', 'تحميل الفيديو']

    for channel_rss in channels:
        if new_videos_found >= MAX_VIDEOS_PER_RUN:
            print(f"⚠️ تم الوصول للحد الأقصى الجديد ({MAX_VIDEOS_PER_RUN} فيديو). إيقاف مؤقت...")
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
                        
                        # 3️⃣ 🔥 نظام الفحص المباشر (Substring Match) وصيد أعلى رقم جودة حقيقي
                        if message.buttons:
                            detected_buttons = []
                            
                            # قائمة بالجودات المتعارف عليها للتحقق من الأرقام المستخرجة بدقة
                            valid_resolutions = [144, 240, 360, 480, 576, 720, 854, 1080, 1440, 2160, 4320]
                            
                            for row in message.buttons:
                                for btn in row:
                                    btn_text = btn.text if btn.text else ""
                                    
                                    # استخراج كافة الأرقام الصافية المتواجدة داخل نص الزر وتجاهل أي إيموجي أو أحرف
                                    numbers_in_btn = re.findall(r'\d+', btn_text)
                                    
                                    for num_str in numbers_in_btn:
                                        num_val = int(num_str)
                                        # التأكد من أن الرقم المستخرج يمثل جودة حقيقية وليس رقماً عشوائياً أو ترتيبياً مثل (1)
                                        if num_val in valid_resolutions:
                                            detected_buttons.append((num_val, btn))
                            
                            # إذا تم العثور على أزرار جودة مطابقة
                            if detected_buttons:
                                # ترتيب الأزرار تنازلياً للحصول على أعلى رقم في المقدمة [0]
                                detected_buttons.sort(key=lambda x: x[0], reverse=True)
                                highest_res, btn_to_click = detected_buttons[0]
                                
                                print(f"🎯 تم صيد أعلى رقم جودة متاح حقيقياً وضغطه: ({btn_to_click.text}) -> الجودة المعتمدة: {highest_res}p")
                                await btn_to_click.click()
                                downloaded_quality = f"{highest_res}p"
                                is_done = True
                                break
                            
                            # حماية احتياطية: إذا مرت 40 ثانية وظهرت أزرار أخرى ولم يتم استخراج رقم جودة قياسي، يضغط الزر الأول
                            if (time.time() - start_time) > 40:
                                print("ℹ️ مرت 40 ثانية ولم نحدد رقم جودة حقيقي صريح، الضغط على أول زر متاح احتياطياً...")
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
        await client.send_message(second_account, f"✅ دورة سوبر ناجحة: تم معالجة {new_videos_found} فيديو (الحد الأقصى 1000) مع تصفية ذكية لأعلى أرقام الجودات.")

with client:
    client.loop.run_until_complete(main())

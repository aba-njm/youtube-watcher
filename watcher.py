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
    print("🚀 بدء التشغيل الفائق: فحص ذكي مخصص للتقارير الدقيقة وبحد أقصى 800 فيديو...")

    downloaded = get_downloaded_links()
    
    with open('channels.txt', 'r', encoding='utf-8') as f:
        channels = [line.strip() for line in f if line.strip()]

    new_videos_found = 0
    MAX_VIDEOS_PER_RUN = 800  
    
    # 📝 قائمة تجميع تقارير الفيديوهات المستهدفة (الفاشلة + الجودات المنخفضة جداً)
    report_items = []
    
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
                highest_res_found = None # لتتبع القيمة الرقمية للجودة بدقة
                
                while (time.time() - start_time) < 90:
                    await asyncio.sleep(2)
                    async for message in client.iter_messages(target_bot, limit=5):
                        if message.id <= sent_msg.id: continue
                        
                        msg_text = message.text.lower() if message.text else ""
                        
                        # 1️⃣ فحص رسائل الفشل (إضافة الرابط للتقرير بدون العنوان)
                        if any(word in msg_text for word in error_keywords):
                            print(f"⚠️ تخطي: الرابط معطل أو غير متاح في البوت.")
                            save_to_history(video_link)
                            new_videos_found += 1
                            is_skipped = True
                            is_done = True
                            
                            # 📝 تسجيل روابط الفشل في التقرير
                            report_items.append(f"❌ <b>فشل التحميل (رابط معطل أو محظور من البوت):</b>\n🔗 {video_link}")
                            break
                        
                        # 2️⃣ فحص رسائل النجاح النصية
                        if any(word in msg_text for word in success_keywords):
                            print(f"🎯 تم رصد رسالة نجاح نصية معينة: ({msg_text})")
                            downloaded_quality = "تلقائي (رسالة نجاح)"
                            is_done = True
                            break
                        
                        # 3️⃣ 🔥 نظام الفحص المباشر وصيد أعلى رقم جودة حقيقي
                        if message.buttons:
                            detected_buttons = []
                            valid_resolutions = [144, 240, 360, 480, 576, 720, 854, 1080, 1440, 2160, 4320]
                            
                            for row in message.buttons:
                                for btn in row:
                                    btn_text = btn.text if btn.text else ""
                                    numbers_in_btn = re.findall(r'\d+', btn_text)
                                    
                                    for num_str in numbers_in_btn:
                                        num_val = int(num_str)
                                        if num_val in valid_resolutions:
                                            detected_buttons.append((num_val, btn))
                            
                            if detected_buttons:
                                detected_buttons.sort(key=lambda x: x[0], reverse=True)
                                highest_res, btn_to_click = detected_buttons[0]
                                
                                print(f"🎯 تم صيد أعلى رقم جودة متاح حقيقياً وضغطه: ({btn_to_click.text}) -> الجودة المعتمدة: {highest_res}p")
                                await btn_to_click.click()
                                downloaded_quality = btn_to_click.text 
                                highest_res_found = highest_res # حفظ الرقم للفحص اللاحق
                                is_done = True
                                break
                            
                            if (time.time() - start_time) > 40:
                                print("ℹ️ مرت 40 ثانية ولم نحدد رقم جودة حقيقي صريح، الضغط على أول زر متاح احتياطياً...")
                                await message.click(0)
                                downloaded_quality = "تلقائي (الزر الأول احتياطياً)"
                                highest_res_found = 0 # إعطائه قيمة صفر ليعامل كجودة منخفضة مبهمة ويتم الإبلاغ عنها
                                is_done = True
                                break
                            
                    if is_done: break

                if is_done and not is_skipped:
                    save_to_history(video_link)
                    new_videos_found += 1
                    print(f"💾 تم حفظ الرابط بنجاح في السجل بعد التفاعل بجودة: {downloaded_quality}")
                    
                    # 🎯 الفحص الذكي للجودات المنخفضة: أقل من 1080 بشرط ألا تكون 720 وألا تكون 854 (وبدون عنوان الفيديو)
                    if highest_res_found is not None and highest_res_found < 1080 and highest_res_found not in [720, 854]:
                        print(f"⚠️ جودة الفيديو منخفضة جداً ({downloaded_quality}). تم تسجيله للتقرير...")
                        report_items.append(f"⚠️ <b>جودة منخفضة جداً:</b> <code>{downloaded_quality}</code>\n🔗 {video_link}")
                    
                    # الضغط على زر الصوت الأصلي الاحتياطي
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
            
            await asyncio.sleep(6)

    # 📊 إرسال إشعار نهاية الدورة الناجحة للحساب الثاني
    if new_videos_found > 0:
        await client.send_message(second_account, f"✅ دورة سوبر ناجحة: تم إنهاء فحص ومعالجة الفيديوهات المتاحة بنجاح.")

    # ✉️ إرسال تقرير الحالات الخاصة (المعطوبة والمنخفضة) المفلترة بدون عناوين وبشكل منسق
    if report_items:
        report_header = "📊 <b>تقرير الحالات الخاصة (روابط فاشلة / جودات أقل من 720p):</b>\n\n"
        report_body = "\n\n" + "\n\n" .join(report_items)
        
        # تقسيم التقرير تلقائياً إذا كان كبيراً جداً تفادياً لقيود تلغرام للرسائل الطويلة
        if len(report_header + report_body) > 4000:
            chunks = [report_items[i:i + 20] for i in range(0, len(report_items), 20)]
            for idx, chunk in enumerate(chunks):
                chunk_body = "\n\n".join(chunk)
                await client.send_message(second_account, f"{report_header} (جزء {idx+1}):\n\n{chunk_body}", parse_mode='html')
        else:
            await client.send_message(second_account, f"{report_header}{report_body}", parse_mode='html')
        print(f"📥 تم إرسال تقرير الفلترة الدقيقة بنجاح لحسابك الثاني.")

with client:
    client.loop.run_until_complete(main())

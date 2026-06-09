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
    
    # ⏱️ تسجيل وقت بداية تشغيل السكربت بالثواني
    script_start_time = time.time()
    MAX_RUN_TIME = 19800  # 5.5 ساعات بالثواني (حماية قبل حد الـ 6 ساعات)
    
    print("🚀 بدء التشغيل الفائق: نظام المراقبة المكشوف والمفصل لكافة القنوات...")

    downloaded = get_downloaded_links()
    print(f"💾 تم تحميل {len(downloaded)} رابط سابق من سجل الذاكرة (history.txt).")
    
    with open('channels.txt', 'r', encoding='utf-8') as f:
        channels = [line.strip() for line in f if line.strip()]
    print(f"📋 تم رصد {len(channels)} قناة مستهدفة داخل ملف channels.txt")

    new_videos_found = 0
    MAX_VIDEOS_PER_RUN = 1000
    
    # قائمة تجميع تقارير الفيديوهات المستهدفة (الفاشلة + الجودات المنخفضة جداً)
    report_items = []
    
    # 🛑 الكلمات الدليلية لكشف الروابط المعطوبة أو المحظورة من البوت
    error_keywords = ['عذراً', 'خطأ', 'فشل', 'private', 'unavailable', 'deleted', 'invalid', 'copyright', 'لم يتم العثور']
    
    # 🟢 الكلمات المفتاحية المخصصة للنجاح النصي
    success_keywords = ['جاري التحميل', 'بدأ التحميل', 'تنزيل', 'تم البدء', 'تحميل الفيديو']

    time_limit_reached = False 

    # البدء في الدوران على القنوات مع طباعة عدّاد صريح لكل قناة
    for idx, channel_rss in enumerate(channels, 1):
        if new_videos_found >= MAX_VIDEOS_PER_RUN or time_limit_reached:
            break

        print(f"\n📡 [{idx}/{len(channels)}] جاري فحص القناة: {channel_rss}")
        
        feed = feedparser.parse(channel_rss)
        if not feed.entries: 
            print(f"⚠️ تنبيه: لم يتم العثور على فيديوهات في هذه القناة (قد يكون الرابط معطلاً أو يوتيوب يفرض حظراً مؤقتاً).")
            continue
            
        print(f"📊 القناة تحتوي على {len(feed.entries)} فيديو حالياً بداخلها. جاري المقارنة مع السجل...")
        skipped_in_channel = 0
        
        for entry in reversed(feed.entries):
            # ⏱️ [فحص الوقت] إذا تجاوزنا 5.5 ساعة، نوقف الفحص فوراً لنحفظ ما تم إنجازه
            if (time.time() - script_start_time) > MAX_RUN_TIME:
                print("⚠️ تنبيه أمان: شارفنا على حد الـ 6 ساعات لجيت هاب! إيقاف منظم الآن لحفظ السجل...")
                time_limit_reached = True
                break

            if new_videos_found >= MAX_VIDEOS_PER_RUN: break
                
            original_link = entry.link
            
            # 🔄 توحيد وتحويل روابط Shorts برمجياً إلى روابط عادية لضمان قبول البوت
            video_link = original_link
            if '/shorts/' in video_link:
                video_link = video_link.replace('?', '&').replace('/shorts/', '/watch?v=')
                
            if video_link in downloaded: 
                skipped_in_channel += 1
                continue 
                
            print(f"🔥 [فيديو جديد مكتشف] رصدته الآن: {entry.title}")
            
            try:
                sent_msg = await client.send_message(target_bot, video_link)
                start_time = time.time()
                is_done = False
                is_skipped = False
                downloaded_quality = "غير معروفة"
                highest_res_found = None 
                
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
                                highest_res_found = highest_res 
                                is_done = True
                                break
                            
                            if (time.time() - start_time) > 40:
                                print("ℹ️ مرت 40 ثانية ولم نحدد رقم جودة حقيقي صريح، الضغط على أول زر متاح احتياطياً...")
                                await message.click(0)
                                downloaded_quality = "تلقائي (الزر الأول احتياطياً)"
                                highest_res_found = 0 
                                is_done = True
                                break
                            
                    if is_done: break

                if is_done and not is_skipped:
                    save_to_history(video_link)
                    new_videos_found += 1
                    print(f"💾 تم حفظ الرابط بنجاح في السجل بعد التفاعل بجودة: {downloaded_quality}")
                    
                    if highest_res_found is not None and highest_res_found < 1080 and highest_res_found not in [720, 854]:
                        print(f"⚠️ جودة الفيديو منخفضة جداً ({downloaded_quality}). تم تسجيله للتقرير...")
                        report_items.append(f"⚠️ <b>جودة منخفضة جداً:</b> <code>{downloaded_quality}</code>\n🔗 {video_link}")
                    
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
            
        if skipped_in_channel > 0:
            print(f"ℹ️ نتيجة الفحص: تم تخطي {skipped_in_channel} فيديو من هذه القناة لأنها محملة مسبقاً بالكامل.")

    # 📊 إرسال إشعار نهاية الدورة الناجحة للحساب الثاني
    if new_videos_found > 0:
        status_msg = "⚠️ تم التوقف لحماية الوقت وضمان الحفظ" if time_limit_reached else "بنجاح كامل"
        await client.send_message(second_account, f"✅ دورة سوبر ناجحة: تم إنهاء فحص ومعالجة {new_videos_found} فيديو جديد {status_msg}.")

    # ✉️ إرسال تقرير الحالات الخاصة (المعطوبة والمنخفضة)
    if report_items:
        report_header = "📊 <b>تقرير الحالات الخاصة (روابط فاشلة / جودات أقل من 720p):</b>\n\n"
        report_body = "\n\n" + "\n\n" .join(report_items)
        
        if len(report_header + report_body) > 4000:
            chunks = [report_items[i:i + 20] for i in range(0, len(report_items), 20)]
            for idx, chunk in enumerate(chunks):
                chunk_body = "\n\n".join(chunk)
                await client.send_message(second_account, f"{report_header} (جزء {idx+1}):\n\n{chunk_body}", parse_mode='html')
        else:
            await client.send_message(second_account, f"{report_header}{report_body}", parse_mode='html')
        print(f"📥 تم إرسال تقرير الفلترة بنجاح.")

with client:
    client.loop.run_until_complete(main())

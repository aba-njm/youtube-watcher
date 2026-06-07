import os
import asyncio
import feedparser
import time
import re
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
    print("🚀 بدء فحص القنوات بنظام الصيد الصارم والمقاوم للإيموجيات...")

    downloaded = get_downloaded_links()
    
    with open('channels.txt', 'r', encoding='utf-8') as f:
        channels = [line.strip() for line in f if line.strip()]

    new_videos_found = 0
    MAX_VIDEOS_PER_RUN = 100 
    
    # 📝 قائمة لجمع الفيديوهات التي لا تدعم جودة 1080 في البوت الحالي
    missing_1080_videos = []
    
    # 🛑 الكلمات الدليلية لكشف الروابط المعطوبة أو المحظورة من البوت
    error_keywords = ['عذراً', 'خطأ', 'فشل', 'private', 'unavailable', 'deleted', 'invalid', 'copyright', 'لم يتم العثور']
    
    # 🟢 الكلمات المفتاحية المخصصة للنجاح النصي
    success_keywords = ['جاري التحميل', 'بدأ التحميل', 'تنزيل', 'تم البدء', 'تحميل الفيديو']

    for channel_rss in channels:
        if new_videos_found >= MAX_VIDEOS_PER_RUN:
            print(f"⚠️ تم الوصول للحد الأقصى ({MAX_VIDEOS_PER_RUN} فيديو). إيقاف مؤقت ذكي...")
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
                    # ⭐ نظام معالجة الفيديو العادي الذكي جداً ضد الإيموجيات
                    has_1080 = False
                    downloaded_quality = "تلقائية / غير معروفة"
                    
                    while (time.time() - start_time) < 90:
                        await asyncio.sleep(2)
                        async for message in client.iter_messages(target_bot, limit=5):
                            if message.id <= sent_msg.id: continue
                            
                            msg_text = message.text.lower() if message.text else ""
                            
                            # 1️⃣ فحص رسائل الفشل والتعطيل أولاً لتجنب تعليق السكربت
                            if any(word in msg_text for word in error_keywords):
                                print(f"⚠️ تخطي: الرابط معطل أو غير متاح في البوت.")
                                save_to_history(video_link)
                                new_videos_found += 1
                                is_skipped = True
                                is_done = True
                                break
                            
                            # 2️⃣ فحص رسائل النجاح المخصصة النصية
                            if any(word in msg_text for word in success_keywords):
                                print(f"🎯 تم رصد رسالة نجاح نصية معينة: ({msg_text})")
                                downloaded_quality = "تلقائي (عبر رسالة البوت)"
                                has_1080 = True 
                                is_done = True
                                break
                            
                            # 3️⃣ 🔥 النظام الجديد والمضمون: كسر حماية الإيموجيات وصيد الجودة الأعلى مباشرة
                            if message.buttons:
                                resolution_buttons = []
                                # قائمة الجودات القياسية مرتبة من الأعلى للأقل لضمان الدقة
                                known_resolutions = ['4320', '2160', '1440', '1080', '854', '720', '576', '480', '360', '240', '144']
                                
                                for row in message.buttons:
                                    for btn in row:
                                        btn_text = btn.text if btn.text else ""
                                        
                                        # الفحص السحري: هل يحتوي نص الزر (مهما كان فيه إيموجيات أو أحرف) على أحد هذه الأرقام؟
                                        detected_res = None
                                        for res in known_resolutions:
                                            if res in btn_text:
                                                detected_res = int(res)
                                                break # التقطنا الرقم الحقيقي بنجاح وتخطينا الإيموجي والـ p
                                        
                                        # خيار احتياطي مضاف: إذا لم يجد رقم قياسي، يبحث عن أي رقم ملتصق بحرف p
                                        if not detected_res:
                                            match_p = re.search(r'(\d+)\s*[pP]', btn_text)
                                            if match_p:
                                                detected_res = int(match_p.group(1))
                                        
                                        # إذا تأكدنا من جودة الزر نضعه في قائمة التصفية
                                        if detected_res:
                                            resolution_buttons.append((detected_res, btn))
                                
                                if resolution_buttons:
                                    # ترتيب الأزرار المكتشفة تنازلياً لاختيار الأعلى قيمة فوراً
                                    resolution_buttons.sort(key=lambda x: x[0], reverse=True)
                                    highest_res, btn_to_click = resolution_buttons[0]
                                    
                                    print(f"🎯 تم صيد أعلى جودة مكتشفة بنجاح واختيارها: {btn_to_click.text} ({highest_res}p)")
                                    await btn_to_click.click()
                                    downloaded_quality = btn_to_click.text
                                    
                                    if highest_res >= 1080:
                                        has_1080 = True
                                        
                                    is_done = True
                                    break
                                else:
                                    # حماية احتياطية بعد 40 ثانية
                                    if (time.time() - start_time) > 40:
                                        print("ℹ️ لم يتم العثور على زر جودة صريح، الضغط على أول زر متاح...")
                                        await message.click(0)
                                        downloaded_quality = "تلقائي (أول زر متاح)"
                                        is_done = True
                                        break
                        if is_done: break

                    if is_done and not is_skipped:
                        save_to_history(video_link)
                        new_videos_found += 1

                        if not has_1080:
                            print(f"⚠️ الفيديو لا يدعم جودة 1080 (أعلى جودة مضغوطة: {downloaded_quality}). تمت إضافته لقائمة التقرير.")
                            missing_1080_videos.append(f"🔗 <b>{entry.title}</b>\n📥 الجودة التي حُمِّل بها: <code>{downloaded_quality}</code>\n{video_link}")
                    
                    # نضغط زر original فقط للفيديوهات العادية السليمة
                    if is_done and not is_skipped and not was_short and "رسالة" not in downloaded_quality:
                        print("⏳ الانتظار للتأكد من ظهور خيارات الصوت (Original)...")
                        await asyncio.sleep(6)
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
        await client.send_message(second_account, f"✅ دورة ناجحة: تم معالجة {new_videos_found} فيديو واستقرار كامل للنظام.")

    if missing_1080_videos:
        report_header = "⚠️ <b>فيديوهات لم تتوفر بجودة 1080 في البوت الحالي (تم حفظها في السجل لعدم التكرار):</b>\n(يمكنك نسخها وإرسالها للبوت البديل بجودة أعلى)\n\n"
        report_body = "\n\n".join(missing_1080_videos)
        
        await client.send_message(second_account, f"{report_header}{report_body}", parse_mode='html')
        print(f"📥 تم إرسال تقرير بـ {len(missing_1080_videos)} فيديو لا تدعم جودة 1080 لحسابك.")

with client:
    client.loop.run_until_complete(main())

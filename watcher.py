import os
import asyncio
import feedparser
import time
import re  # مكتبة الريجكس المحدثة للفحص الديناميكي
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
    print("🚀 بدء فحص القنوات الأوتوماتيكي بنظام صيد الجودة الديناميكي الأعلى...")

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
    success_keywords = ['🈺️']

    for channel_rss in channels:
        if new_videos_found >= MAX_VIDEOS_PER_RUN:
            print(f"⚠️ تم الوصول للحد الأقصى ({MAX_VIDEOS_PER_RUN} فيديو) في هذه الدورة. إيقاف مؤقت ذكي...")
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
                    # ⭐ نظام معالجة الفيديو العادي المطور وفحص جودة 1080 والرسائل النصية
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
                                save_to_history(video_link) # حفظه لتجنب تكرار فحص رابط معطوب مستقبلاً
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
                            
                            # 3️⃣ 🔥 النظام الجديد: صيد أزرار الجودة واختيار الأعلى ديناميكياً (يدعم 854p وأي جودة أخرى)
                            if message.buttons:
                                resolution_buttons = []
                                for row in message.buttons:
                                    for btn in row:
                                        # فحص وجود صيغة واضحة مثل 854p أو 1080p
                                        match_p = re.search(r'(\d+)\s*p', btn.text, re.IGNORECASE)
                                        # فحص وجود أرقام جودات معروفة ومألوفة بدون حرف الـ p
                                        match_num = re.search(r'\d+', btn.text)
                                        
                                        if match_p:
                                            res_val = int(match_p.group(1))
                                        elif match_num and int(match_num.group()) in [144, 240, 360, 480, 576, 720, 854, 1080, 1440, 2160, 4320]:
                                            res_val = int(match_num.group())
                                        else:
                                            continue
                                        
                                        # إضافة الجودة المكتشفة مع زرها إلى القائمة المؤقتة
                                        resolution_buttons.append((res_val, btn))
                                
                                if resolution_buttons:
                                    # ترتيب الأزرار تنازلياً ليكون الزر ذو الجودة الأعلى في البداية [0]
                                    resolution_buttons.sort(key=lambda x: x[0], reverse=True)
                                    highest_res, btn_to_click = resolution_buttons[0]
                                    
                                    print(f"🎯 تم العثور على أعلى جودة متاحة واختيارها تلقائياً: {btn_to_click.text} ({highest_res}p)")
                                    await btn_to_click.click()
                                    downloaded_quality = btn_to_click.text
                                    
                                    # فحص إذا كانت الجودة المختارة تلبي رغبتك (1080 أو أعلى) لكي لا تذهب للتقرير كـ ناقصة
                                    if highest_res >= 1080:
                                        has_1080 = True
                                        
                                    is_done = True
                                    break
                                else:
                                    # حماية ذكية: إذا مرت 40 ثانية وظهرت أزرار ليست لها علاقة بالجودة
                                    if (time.time() - start_time) > 40:
                                        print("ℹ️ لم يتم العثور على زر جودة صريح بعد 40 ثانية، الضغط على أول زر متاح...")
                                        await message.click(0)
                                        downloaded_quality = "تلقائي (أول زر متاح)"
                                        is_done = True
                                        break
                        if is_done: break

                    if is_done and not is_skipped:
                        # ✅ حفظ الفيديو الناجح في الـ history لمنع التكرار
                        save_to_history(video_link)
                        new_videos_found += 1

                        if not has_1080:
                            # 🚫 إذا كانت أعلى جودة متاحة أقل من 1080 (مثل 854p أو 720p)، يتم إضافته للتقرير لتنبيهك
                            print(f"⚠️ الفيديو لا يدعم جودة 1080 (أعلى جودة كانت {downloaded_quality}). تمت إضافته لقائمة التقرير.")
                            missing_1080_videos.append(f"🔗 <b>{entry.title}</b>\n📥 الجودة التي حُمِّل بها: <code>{downloaded_quality}</code>\n{video_link}")
                    
                    # نضغط زر original فقط للفيديوهات العادية السليمة التي لم تخرج برسالة نجاح نصية
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
            
            await asyncio.sleep(6) # مهلة أمان بين الفيديوهات الرئيسية

    # 📊 إرسال التقارير النهائية للحساب الثاني
    if new_videos_found > 0:
        await client.send_message(second_account, f"✅ دورة ناجحة: تم معالجة {new_videos_found} فيديو واستقرار كامل للنظام.")

    if missing_1080_videos:
        # تنسيق رسالة النواقص بشكل احترافي ومقروء
        report_header = "⚠️ <b>فيديوهات لم تتوفر بجودة 1080 في البوت الحالي (تم حفظها في السجل لعدم التكرار):</b>\n(يمكنك نسخها وإرسالها للبوت البديل بجودة أعلى)\n\n"
        report_body = "\n\n".join(missing_1080_videos)
        
        await client.send_message(second_account, f"{report_header}{report_body}", parse_mode='html')
        print(f"📥 تم إرسال تقرير بـ {len(missing_1080_videos)} فيديو لا تدعم جودة 1080 لحسابك.")

with client:
    client.loop.run_until_complete(main())

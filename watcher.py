import os
import asyncio
import json
import time
import re  # مكتبة الريجكس لاستخراج الأرقام الصافية ومعرفات القنوات
import urllib.request  # مكتبة مدمجة لطلب الداتا من جوجل رسميًا
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- جلب البيانات من خزنة جيت هاب السرية ---
api_id = int(os.environ.get('API_ID', 0)) 
api_hash = os.environ.get('API_HASH', 'hash')
session_string = os.environ.get('TELEGRAM_SESSION', '') 
youtube_api_key = os.environ.get('YOUTUBE_API_KEY', '') # 🔑 مفتاح اليوتيوب الرسمي الجديد

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
    
    # ⏱️ تسجيل وقت بداية تشغيل السكربت بالثواني للحماية
    script_start_time = time.time()
    MAX_RUN_TIME = 19800  # 5.5 ساعات بالثواني (حماية قبل حد الـ 6 ساعات)
    
    print("🚀 بدء التشغيل الفائق والمستقر بنظام YouTube Data API v3 الرسمي والمضاد للحظر...")

    if not youtube_api_key:
        print("❌ خطأ حرج: لم يتم العثور على YOUTUBE_API_KEY في خزنة جيت هاب السرية! يرجى إضافته أولاً.")
        return

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

    for idx, channel_line in enumerate(channels, 1):
        if new_videos_found >= MAX_VIDEOS_PER_RUN or time_limit_reached:
            break

        # استخراج الـ Channel ID من رابط الـ RSS المتواجد حالياً في ملفك تلقائياً
        channel_id_match = re.search(r'channel_id=([A-Za-z0-9_-]+)', channel_line)
        if channel_id_match:
            channel_id = channel_id_match.group(1)
        else:
            channel_id = channel_line.strip() # إذا كان السطر يحتوي على الآيدي مباشرة
            
        print(f"\n📡 [{idx}/{len(channels)}] جاري جلب بيانات القناة رسمياً عبر جوجل: {channel_id}")
        
        # تحويل كود القناة لجلب قائمة المرفوعات المباشرة لضمان توفير استهلاك الكوتا المجانية (تستهلك 1 دقيقة فقط)
        if channel_id.startswith('UC'):
            uploads_playlist_id = 'UU' + channel_id[2:]
        else:
            uploads_playlist_id = channel_id

        api_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=10&key={youtube_api_key}"
        
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            loop = asyncio.get_running_loop()
            json_bytes = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=15).read())
            api_data = json.loads(json_bytes.decode('utf-8'))
            
            entries = []
            for item in api_data.get('items', []):
                snippet = item.get('snippet', {})
                video_id = snippet.get('resourceId', {}).get('videoId')
                title = snippet.get('title', 'محتوى بدون عنوان')
                if video_id:
                    entries.append({
                        'title': title,
                        'link': f"https://www.youtube.com/watch?v={video_id}"
                    })
        except Exception as api_error:
            print(f"❌ خطأ حماية أو استجابة من سيرفرات Google API للمطورين: {api_error}")
            continue

        if not entries: 
            print(f"⚠️ تنبيه: لم يتم العثور على أي فيديوهات منشورة حديثاً في هذه القناة حالياً.")
            continue
            
        print(f"📊 تم جلب أحدث {len(entries)} فيديو رسمي بنجاح تام من جوجل. جاري مطابقتها مع السجل...")
        skipped_in_channel = 0
        
        for entry in reversed(entries):
            if (time.time() - script_start_time) > MAX_RUN_TIME:
                print("⚠️ تنبيه أمان: شارفنا على حد الـ 6 ساعات لجيت هاب! إيقاف منظم الآن لحفظ السجل...")
                time_limit_reached = True
                break

            if new_videos_found >= MAX_VIDEOS_PER_RUN: break
                
            video_link = entry['link']
            
            if video_link in downloaded: 
                skipped_in_channel += 1
                continue 
                
            print(f"🔥 [فيديو جديد تم اصطياده] معالجة: {entry['title']}")
            
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
                        
                        if any(word in msg_text for word in error_keywords):
                            print(f"⚠️ تخطي: الرابط معطل أو غير متاح في البوت.")
                            save_to_history(video_link)
                            new_videos_found += 1
                            is_skipped = True
                            is_done = True
                            report_items.append(f"❌ <b>فشل التحميل (رابط معطل أو محظور من البوت):</b>\n🔗 {video_link}")
                            break
                        
                        if any(word in msg_text for word in success_keywords):
                            print(f"🎯 تم رصد رسالة نجاح نصية معينة: ({msg_text})")
                            downloaded_quality = "تلقائي (رسالة نجاح)"
                            is_done = True
                            break
                        
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

    if new_videos_found > 0:
        status_msg = "⚠️ تم التوقف لحماية الوقت وضمان الحفظ" if time_limit_reached else "بنجاح كامل"
        await client.send_message(second_account, f"✅ دورة سوبر ناجحة: تم إنهاء فحص ومعالجة {new_videos_found} فيديو جديد {status_msg}.")

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

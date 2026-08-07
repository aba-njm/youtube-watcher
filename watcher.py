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

# 🔒 تم تشفير وإخفاء الحسابات والبوتات هنا بنجاح
target_bot = int(os.environ.get('TARGET_BOT', 0))       # آيدي المجموعة أو الشات الخاص بالبوت
second_account = os.environ.get('SECOND_ACCOUNT', '')   # يوزر حسابك لاستلام التقارير
# ----------------------------------------------------------------------
client = TelegramClient(StringSession(session_string), api_id, api_hash)

def get_downloaded_links():
    if not os.path.exists('history.txt'): return set()  
    with open('history.txt', 'r', encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}  # تقرأ الـ IDs المخزنة مباشرة وتضعها في set لسرعة فائقة

def save_to_history(video_id):
    with open('history.txt', 'a', encoding='utf-8') as f:
        f.write(video_id + '\n')  # تحفظ الـ ID الصافي فقط (11 حرفاً) بدلاً من الرابط الكامل

async def main():
    await client.start()

    script_start_time = time.time()
    MAX_RUN_TIME = 19800  # 5.5 ساعات

    print("🚀 بدء التشغيل بنظام الإحصائيات الشاملة لتتبع القنوات...")

    # التحقق من وجود المتغيرات السرية الأساسية
    if not youtube_api_key or not target_bot or not second_account:
        print("❌ خطأ حرج: لم يتم العثور على بعض المتغيرات السرية (YOUTUBE_API_KEY أو TARGET_BOT أو SECOND_ACCOUNT) في جيت هاب!")
        return

    downloaded = get_downloaded_links()  # مجموعة تحتوي على الـ IDs التي تم تحميلها سابقاً

    with open('channels.txt', 'r', encoding='utf-8') as f:
        channels = [line.strip() for line in f if line.strip()]

    new_videos_found = 0
    MAX_VIDEOS_PER_RUN = 1000

    # عدادات مراقبة القنوات لتضمينها في تقرير تليجرام 📊
    successful_channels = 0
    failed_channels = 0

    report_items = []
    error_keywords = ['عذراً', 'خطأ', 'فشل', 'private', 'unavailable', 'deleted', 'invalid', 'copyright', 'لم يتم العثور']
    success_keywords = ['جاري التحميل', 'بدأ التحميل', 'تنزيل', 'تم البدء', 'تحميل الفيديو']

    time_limit_reached = False 

    for idx, channel_line in enumerate(channels, 1):
        if new_videos_found >= MAX_VIDEOS_PER_RUN or time_limit_reached:
            break

        # استخراج الـ Channel ID تلقائياً
        channel_id_match = re.search(r'channel_id=([A-Za-z0-9_-]+)', channel_line)
        if channel_id_match:
            channel_id = channel_id_match.group(1)
        else:
            # إذا كان الرابط يحتوي على معرّف القناة مباشرة مثل /channel/UC...
            channel_id_direct = re.search(r'channel/(UC[A-Za-z0-9_-]+)', channel_line)
            if channel_id_direct:
                channel_id = channel_id_direct.group(1)
            else:
                channel_id = channel_line.strip()

        print(f"\n📡 [{idx}/{len(channels)}] جاري جلب بيانات القناة: {channel_id}")

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
                    entries.append({'title': title, 'id': video_id, 'link': f"https://www.youtube.com/watch?v={video_id}"})

            successful_channels += 1 # احتساب نجاح الاتصال بالقناة
        except Exception as api_error:
            print(f"❌ خطأ في القناة أو صيغة الرابط خاطئة: {api_error}")
            failed_channels += 1 # احتساب فشل القناة بسبب الصيغة أو الحظر
            continue

        if not entries: continue

        for entry in reversed(entries):
            if (time.time() - script_start_time) > MAX_RUN_TIME:
                time_limit_reached = True
                break

            if new_videos_found >= MAX_VIDEOS_PER_RUN: break

            v_id = entry['id']
            video_link = entry['link']

            # المقارنة الآن تتم بالـ ID الصافي وليس الرابط الكامل لتوفير الذاكرة والوقت
            if v_id in downloaded: continue 

            print(f"🔥 [فيديو جديد] معالجة: {entry['title']}")

            try:
                sent_msg = await client.send_message(target_bot, video_link)
                start_time = time.time()
                is_done = False
                is_skipped = False
                skip_low_quality_report = False  # علم لتخطي تقرير الجودة المنخفضة للـ Shorts
                downloaded_quality = "غير معروفة"
                highest_res_found = None 

                while (time.time() - start_time) < 90:
                    await asyncio.sleep(2)
                    async for message in client.iter_messages(target_bot, limit=5):
                        if message.id <= sent_msg.id: continue

                        msg_text = message.text.lower() if message.text else ""

                        if any(word in msg_text for word in error_keywords):
                            save_to_history(v_id)      # حفظ الـ ID فقط
                            downloaded.add(v_id)       # تحديث الذاكرة فوراً
                            new_videos_found += 1
                            is_skipped = True
                            is_done = True
                            report_items.append(f"❌ <b>فشل التحميل من قِبل البوت:</b>\n📝 {entry['title']}\n🔗 {video_link}")
                            break

                        if any(word in msg_text for word in success_keywords):
                            downloaded_quality = "تلقائي (رسالة نجاح)"
                            is_done = True
                            break

                        if message.buttons:
                            detected_buttons = []
                            valid_resolutions = [144, 240, 360, 480, 576, 640, 720, 854, 1080, 1440, 2160, 4320]

                            for row in message.buttons:
                                for btn in row:
                                    btn_text = btn.text if btn.text else ""
                                    numbers_in_btn = re.findall(r'\d+', btn_text)
                                    for num_str in numbers_in_btn:
                                        num_val = int(num_str)
                                        if num_val in valid_resolutions:
                                            detected_buttons.append((num_val, btn))

                            if detected_buttons:
                                # تحويل المصفوفة مؤقتاً لقاموس لتسريع الفحص المباشر والمستهدف 🚀
                                res_dict = {x[0]: x[1] for x in detected_buttons}
                                btn_to_click = None
                                highest_res = None

                                # 🟢 الفحص المباشر بدون مقارنة أو فرز الأرقام الأخرى الأعلى:
                                if 854 in res_dict:
                                    btn_to_click = res_dict[854]
                                    highest_res = 854
                                elif 640 in res_dict:
                                    btn_to_click = res_dict[640]
                                    highest_res = 640
                                    skip_low_quality_report = True  # تخطي الإبلاغ لأن الـ 640p هي خيار متعمد هنا
                                else:
                                    # في حال لم تتواجد الجودات الخاصة بالـ Shorts، يعود النظام لترتيب واختيار الأعلى تلقائياً
                                    detected_buttons.sort(key=lambda x: x[0], reverse=True)
                                    highest_res, btn_to_click = detected_buttons[0]

                                await btn_to_click.click()
                                downloaded_quality = btn_to_click.text 
                                highest_res_found = highest_res 
                                is_done = True
                                break

                            if (time.time() - start_time) > 40:
                                await message.click(0)
                                downloaded_quality = "تلقائي (الزر الأول احتياطياً)"
                                highest_res_found = 0 
                                is_done = True
                                break

                    if is_done: break

                # معالجة النتائج بعد انتهاء حلقة الفحص والانتظار
                if is_done and not is_skipped:
                    save_to_history(v_id)      # حفظ الـ ID فقط
                    downloaded.add(v_id)       # تحديث الذاكرة فوراً
                    new_videos_found += 1

                    # إدراج الجودات المنخفضة في التقرير بشرط ألا تكون جودة Shorts مسموحة ومستهدفة (640p)
                    if highest_res_found is not None and highest_res_found < 1080 and highest_res_found not in [720, 854]:
                        if not skip_low_quality_report:
                            report_items.append(f"⚠️ <b>جودة منخفضة جداً:</b> <code>{downloaded_quality}</code>\n🔗 {video_link}")

                    await asyncio.sleep(5)
                    async for m in client.iter_messages(target_bot, limit=3):
                        if m.buttons:
                            audio_pressed = False
                            for row in m.buttons:
                                for btn in row:
                                    if 'original' in btn.text.lower():
                                        await btn.click()
                                        audio_pressed = True
                                        break
                                if audio_pressed: break
                            if audio_pressed: break
                
                elif not is_done:
                    # في حال انتهت الـ 90 ثانية ولم يستجب البوت بأي رسائل نجاح، فشل، أو أزرار
                    report_items.append(f"❌ <b>فشل التحميل (انتهت مهلة الـ 90 ثانية دون استجابة البوت):</b>\n📝 {entry['title']}\n🔗 {video_link}")

            except Exception as e:
                print(f"❌ خطأ أثناء معالجة الرابط: {e}")
                report_items.append(f"❌ <b>خطأ نظام داخلي أثناء معالجة الرابط:</b>\n<code>{str(e)}</code>\n🔗 {video_link}")

            await asyncio.sleep(6)

    # 📊 صياغة وإرسال التقرير الإحصائي الشامل والجديد لحسابك الثاني عبر التليجرام
    status_msg = "⚠️ تم التوقف جزئياً لحماية الوقت" if time_limit_reached else "بنجاح كامل"

    detailed_summary = (
        f"📊 <b>تقرير تفصيلي لإنهاء الدورة ({status_msg}):</b>\n\n"
        f"📋 إجمالي القنوات في القائمة: <code>{len(channels)}</code>\n"
        f"✅ قنوات تم فحصها بنجاح تام: <code>{successful_channels}</code>\n"
        f"❌ قنوات فشلت (روابط خاطئة أو مشاكل ID): <code>{failed_channels}</code>\n"
        f"🔥 فيديوهات جديدة تم إرسالها ومعالجتها: <code>{new_videos_found}</code>"
    )
    await client.send_message(second_account, detailed_summary, parse_mode='html')

    # ✉️ إرسال تقرير الحالات الخاصة (الروابط الفاشلة / الجودات المنخفضة المرفوضة) بدون أخطاء السنتاكس 🛠️
    if report_items:
        report_header = "📊 <b>تقرير الحالات الخاصة (الروابط الفاشلة / الجودات المنخفضة المرفوضة):</b>\n\n"
        report_body = "\n\n" + "\n\n" .join(report_items)
        if len(report_header + report_body) > 4000:
            chunks = [report_items[i:i + 20] for i in range(0, len(report_items), 20)]
            for idx, chunk in enumerate(chunks):
                chunk_body = "\n\n".join(chunk)
                await client.send_message(second_account, f"{report_header} (جزء {idx+1}):\n\n{chunk_body}", parse_mode='html')
        else:
            await client.send_message(second_account, f"{report_header}{report_body}", parse_mode='html')

with client:
    client.loop.run_until_complete(main())

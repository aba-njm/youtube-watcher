import os
import asyncio
import json
import time
import re
import html
import urllib.request
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- جلب البيانات من خزنة جيت هاب السرية ---
api_id = int(os.environ.get('API_ID', 0)) 
api_hash = os.environ.get('API_HASH', 'hash')
session_string = os.environ.get('TELEGRAM_SESSION', '') 
youtube_api_key = os.environ.get('YOUTUBE_API_KEY', '')

# معالجة المعرفات سواء كانت أرقاماً أو معرّفات نصية (@)
def parse_peer(env_val):
    val = env_val.strip()
    if val.isdigit() or (val.startswith('-') and val[1:].isdigit()):
        return int(val)
    return val

raw_target_bot = parse_peer(os.environ.get('TARGET_BOT', '0'))
raw_second_account = parse_peer(os.environ.get('SECOND_ACCOUNT', ''))

client = TelegramClient(StringSession(session_string), api_id, api_hash)

def get_downloaded_links():
    if not os.path.exists('history.txt'): return set()  
    with open('history.txt', 'r', encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}

def save_to_history(video_id):
    with open('history.txt', 'a', encoding='utf-8') as f:
        f.write(video_id + '\n')

# 🛠️ دالة إرسال التقارير الطويلة بأمان عبر حساب الحروف وليس عدد العناصر
async def send_safe_report(client, peer, header, items):
    if not items:
        return

    current_chunk = ""
    part = 1
    MAX_LENGTH = 3200  # حد أمان ممتاز لمنع تجاوز 4096 حرفاً

    for item in items:
        if len(current_chunk) + len(item) + 2 > MAX_LENGTH:
            msg = f"{header} (جزء {part}):\n\n{current_chunk}"
            await client.send_message(peer, msg, parse_mode='html')
            current_chunk = item
            part += 1
        else:
            if current_chunk:
                current_chunk += "\n\n" + item
            else:
                current_chunk = item

    if current_chunk:
        msg = f"{header} (جزء {part}):\n\n{current_chunk}" if part > 1 else f"{header}\n\n{current_chunk}"
        await client.send_message(peer, msg, parse_mode='html')

async def main():
    await client.start()

    # 🛠️ حل مشكلة (Invalid Peer): التعرف على الكائنات فورياً من التليجرام
    try:
        target_bot = await client.get_entity(raw_target_bot)
        second_account = await client.get_entity(raw_second_account)
    except Exception as e:
        print(f"❌ خطأ حرج في التعرف على البوت أو الحساب الثاني: {e}")
        return

    script_start_time = time.time()
    MAX_RUN_TIME = 19800  # 5.5 ساعات

    print("🚀 بدء التشغيل بنظام الإحصائيات الشاملة لتتبع القنوات...")

    if not youtube_api_key or not target_bot or not second_account:
        print("❌ خطأ حرج: لم يتم العثور على المتغيرات السرية!")
        return

    if not os.path.exists('channels.txt'):
        print("❌ خطأ: ملف channels.txt غير موجود!")
        return

    downloaded = get_downloaded_links()

    with open('channels.txt', 'r', encoding='utf-8') as f:
        channels = [line.strip() for line in f if line.strip()]

    new_videos_found = 0
    MAX_VIDEOS_PER_RUN = 1000

    successful_channels = 0
    failed_channels = 0

    report_items = []
    error_keywords = ['عذراً', 'خطأ', 'فشل', 'private', 'unavailable', 'deleted', 'invalid', 'copyright', 'لم يتم العثور']
    success_keywords = ['جاري التحميل', 'بدأ التحميل', 'تنزيل', 'تم البدء', 'تحميل الفيديو']

    time_limit_reached = False 

    for idx, channel_line in enumerate(channels, 1):
        if new_videos_found >= MAX_VIDEOS_PER_RUN or time_limit_reached:
            break

        channel_id_match = re.search(r'channel_id=([A-Za-z0-9_-]+)', channel_line)
        if channel_id_match:
            channel_id = channel_id_match.group(1)
        else:
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

            successful_channels += 1
        except Exception as api_error:
            print(f"❌ خطأ في القناة أو صيغة الرابط خاطئة: {api_error}")
            failed_channels += 1
            continue

        if not entries: continue

        for entry in reversed(entries):
            if (time.time() - script_start_time) > MAX_RUN_TIME:
                time_limit_reached = True
                break

            if new_videos_found >= MAX_VIDEOS_PER_RUN: break

            v_id = entry['id']
            video_link = entry['link']
            safe_title = html.escape(entry['title'])

            if v_id in downloaded: continue 

            print(f"🔥 [فيديو جديد] معالجة: {entry['title']}")

            try:
                sent_msg = await client.send_message(target_bot, video_link)
                start_time = time.time()
                is_done = False
                is_skipped = False
                skip_low_quality_report = False
                downloaded_quality = "غير معروفة"
                highest_res_found = None 

                while (time.time() - start_time) < 90:
                    await asyncio.sleep(2)
                    async for message in client.iter_messages(target_bot, limit=5):
                        if message.id <= sent_msg.id: continue

                        msg_text = message.text.lower() if message.text else ""

                        if any(word in msg_text for word in error_keywords):
                            save_to_history(v_id)
                            downloaded.add(v_id)
                            new_videos_found += 1
                            is_skipped = True
                            is_done = True
                            report_items.append(f"❌ <b>فشل التحميل من قِبل البوت:</b>\n📝 {safe_title}\n🔗 {video_link}")
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
                                res_dict = {x[0]: x[1] for x in detected_buttons}
                                btn_to_click = None
                                highest_res = None

                                if 854 in res_dict:
                                    btn_to_click = res_dict[854]
                                    highest_res = 854
                                elif 640 in res_dict:
                                    btn_to_click = res_dict[640]
                                    highest_res = 640
                                    skip_low_quality_report = True
                                else:
                                    detected_buttons.sort(key=lambda x: x[0], reverse=True)
                                    highest_res, btn_to_click = detected_buttons[0]

                                await btn_to_click.click()
                                downloaded_quality = html.escape(btn_to_click.text)
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

                if is_done and not is_skipped:
                    save_to_history(v_id)
                    downloaded.add(v_id)
                    new_videos_found += 1

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
                    report_items.append(f"❌ <b>فشل التحميل (انتهت مهلة الـ 90 ثانية دون استجابة):</b>\n📝 {safe_title}\n🔗 {video_link}")

            except Exception as e:
                print(f"❌ خطأ أثناء معالجة الرابط: {e}")
                report_items.append(f"❌ <b>خطأ نظام داخلي:</b>\n<code>{html.escape(str(e))}</code>\n🔗 {video_link}")

            await asyncio.sleep(6)

    # 📊 صياغة وإرسال التقرير الإحصائي
    status_msg = "⚠️ تم التوقف جزئياً لحماية الوقت" if time_limit_reached else "بنجاح كامل"

    detailed_summary = (
        f"📊 <b>تقرير تفصيلي لإنهاء الدورة ({status_msg}):</b>\n\n"
        f"📋 إجمالي القنوات في القائمة: <code>{len(channels)}</code>\n"
        f"✅ قنوات تم فحصها بنجاح تام: <code>{successful_channels}</code>\n"
        f"❌ قنوات فشلت: <code>{failed_channels}</code>\n"
        f"🔥 فيديوهات جديدة تم إرسالها ومعالجتها: <code>{new_videos_found}</code>"
    )
    await client.send_message(second_account, detailed_summary, parse_mode='html')

    # ✉️ إرسال تقرير الحالات الخاصة بأمان تام عبر دالة التقسيم القائمة على طول النص
    if report_items:
        report_header = "📊 <b>تقرير الحالات الخاصة (الروابط الفاشلة / الجودات المنخفضة المرفوضة):</b>"
        await send_safe_report(client, second_account, report_header, report_items)

with client:
    client.loop.run_until_complete(main())

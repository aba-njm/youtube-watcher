import os
import asyncio
import json
import time
import re  # مكتبة الريجكس لاستخراج الأرقام الصافية وتجاوز الإيموجيات
import urllib.request
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError

# --- دالة مساعدة لتحويل المعرفات ---
def parse_entity(val):
    if not val:
        return None
    val_str = str(val).strip()
    if val_str.isdigit() or (val_str.startswith('-') and val_str[1:].isdigit()):
        return int(val_str)
    return val_str

# --- جلب البيانات من البيئة ---
api_id = int(os.environ.get('API_ID', 0)) 
api_hash = os.environ.get('API_HASH', 'hash')
session_string = os.environ.get('TELEGRAM_SESSION', '') 
youtube_api_key = os.environ.get('YOUTUBE_API_KEY', '')

target_bot = parse_entity(os.environ.get('TARGET_BOT', ''))
second_account = parse_entity(os.environ.get('SECOND_ACCOUNT', ''))

# ----------------------------------------------------------------------
client = TelegramClient(StringSession(session_string), api_id, api_hash)

def get_downloaded_links():
    if not os.path.exists('history.txt'): return set()  
    with open('history.txt', 'r', encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}

def save_to_history(video_id):
    with open('history.txt', 'a', encoding='utf-8') as f:
        f.write(video_id + '\n')

async def send_safe_message(entity, text, parse_mode='html'):
    """دالة مساعدة لإرسال الرسائل وتفادي انهيار السكربت عند خطأ الصلاحيات"""
    if not entity:
        print("⚠️ لم يتم تحديد المستلم للإرسال.")
        return False
    try:
        await client.send_message(entity, text, parse_mode=parse_mode)
        return True
    except RPCError as e:
        print(f"❌ خطأ تلغرام أثناء الإرسال إلى {entity}: {e}")
    except Exception as e:
        print(f"❌ خطأ غير متوقع أثناء الإرسال إلى {entity}: {e}")
    return False

async def main():
    await client.start()

    script_start_time = time.time()
    MAX_RUN_TIME = 18000  # 5 ساعات

    print("🚀 بدء التشغيل بالمنطق الصارم (الانتظار حتى وصول الحقوق أو الفشل التام)...")

    if not youtube_api_key or not target_bot or not second_account:
        print("❌ خطأ حرج: لم يتم العثور على بعض المتغيرات السرية في البيئة!")
        return

    if not os.path.exists('channels.txt'):
        print("❌ خطأ حرج: ملف channels.txt غير موجود!")
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

            if v_id in downloaded: continue 

            print(f"🔥 [فيديو جديد] معالجة: {entry['title']}")

            try:
                sent_msg = await client.send_message(target_bot, video_link)
            except Exception as e:
                print(f"❌ فشل إرسال الرابط للبوت ({target_bot}): {e}")
                report_items.append(f"❌ <b>فشل إرسال الرابط إلى البوت:</b>\n<code>{str(e)}</code>\n🔗 {video_link}")
                continue

            # --- حلقة الانتظار التسلسلي الصارم للمقطع الحالي ---
            video_start_time = time.time()
            button_clicked = False
            is_completed = False
            downloaded_quality = "غير معروفة"
            PROCESS_TIMEOUT = 480  # مهلة أقصاها 8 دقائق للفيديو الواحد

            while (time.time() - video_start_time) < PROCESS_TIMEOUT:
                await asyncio.sleep(4)  # فحص كل 4 ثوانٍ
                
                try:
                    async for message in client.iter_messages(target_bot, limit=5):
                        if message.id <= sent_msg.id: 
                            continue

                        msg_text = (message.text or message.caption or "").lower()

                        # 🟢 الحالة (2): شرط النجاح القاطع - ظهور حقوق البوت
                        if "@botyoutubedownloadbot" in msg_text:
                            downloaded.add(v_id)
                            save_to_history(v_id)
                            new_videos_found += 1
                            is_completed = True
                            print(f"✅ تم استلام الفيديو بنجاح واكتمال التحميل ({downloaded_quality}): {entry['title']}")
                            break

                        # 🔴 الحالة (1 - أ): استثناء رسالة الحجم الكبير جداً
                        if any(k in msg_text for k in ["حجمه كبير", "لا يمكن إرساله عبر التلغرام", "كبيرًا جدًا"]):
                            save_to_history(v_id)
                            downloaded.add(v_id)
                            new_videos_found += 1
                            is_completed = True
                            report_items.append(f"⚠️ <b>تم تحميل الفيديو ولكن حجمه كبير جداً:</b>\n📝 {entry['title']}\n🔗 {video_link}")
                            print(f"⚠️ حجم كبير جداً: {entry['title']}")
                            break

                        # 🔴 الحالة (1 - ب): الفشل الصريح بحضور إيموجي 😐 أو كلمات الأخطاء
                        if '😐' in msg_text or any(word in msg_text for word in error_keywords):
                            save_to_history(v_id)
                            downloaded.add(v_id)
                            new_videos_found += 1
                            is_completed = True
                            report_items.append(f"❌ <b>فشل التحميل من قِبل البوت:</b>\n📝 {entry['title']}\n🔗 {video_link}")
                            print(f"❌ فشل التحميل من البوت: {entry['title']}")
                            break

                        # 🔘 ضغط زر الجودة (يتم لمرة واحدة فقط ويستمر في الانتظار دون الخروج من الحلقة)
                        if not button_clicked and message.buttons:
                            detected_buttons = []
                            valid_resolutions = [144, 240, 360, 480, 576, 640, 720, 854, 1080, 1440, 2160, 4320]

                            for row in message.buttons:
                                for btn in row:
                                    btn_text = btn.text if btn.text else ""
                                    match = re.search(r'(\d+)', btn_text)
                                    if match:
                                        num_val = int(match.group(1))
                                        if num_val in valid_resolutions:
                                            detected_buttons.append((num_val, btn))

                            if detected_buttons:
                                detected_buttons.sort(key=lambda x: x[0], reverse=True)
                                highest_res, btn_to_click = detected_buttons[0]
                                await btn_to_click.click()
                                downloaded_quality = f"{highest_res}p"
                                button_clicked = True
                                print(f"🔘 تم ضغط زر الجودة ({downloaded_quality})، وجاري انتظار الرفع...")
                            else:
                                await message.click(0)
                                downloaded_quality = "زر تلقائي"
                                button_clicked = True
                                print("🔘 تم اختيار أول زر احتياطياً، وجاري انتظار الرفع...")

                except Exception as loop_err:
                    print(f"⚠️ تنبيه أثناء الفحص الدوري: {loop_err}")

                if is_completed:
                    break

            if not is_completed:
                report_items.append(f"❌ <b>فشل التحميل (انتهت مهلة 8 دقائق دون استلام حقوق البوت):</b>\n📝 {entry['title']}\n🔗 {video_link}")

            # استراحة بسيطة قبل الفيديو التالي
            await asyncio.sleep(2)

    # 📊 صياغة وإرسال التقرير الإحصائي الشامل لحسابك الثاني
    status_msg = "⚠️ تم التوقف جزئياً لحماية الوقت" if time_limit_reached else "بنجاح كامل"

    detailed_summary = (
        f"📊 <b>تقرير تفصيلي لإنهاء الدورة ({status_msg}):</b>\n\n"
        f"📋 إجمالي القنوات في القائمة: <code>{len(channels)}</code>\n"
        f"✅ قنوات تم فحصها بنجاح تام: <code>{successful_channels}</code>\n"
        f"❌ قنوات فشلت (روابط خاطئة أو مشاكل ID): <code>{failed_channels}</code>\n"
        f"🔥 فيديوهات جديدة تم إرسالها ومعالجتها: <code>{new_videos_found}</code>"
    )
    await send_safe_message(second_account, detailed_summary, parse_mode='html')

    # ✉️ إرسال تقرير الحالات الفاشلة وتجزئة الرسائل
    if report_items:
        header = "📊 <b>تقرير الحالات الخاصة والروابط الفاشلة:</b>\n\n"
        current_chunk = header

        for item in report_items:
            if len(current_chunk) + len(item) + 2 > 3800:
                await send_safe_message(second_account, current_chunk, parse_mode='html')
                current_chunk = header + item + "\n\n"
            else:
                current_chunk += item + "\n\n"

        if current_chunk != header:
            await send_safe_message(second_account, current_chunk, parse_mode='html')

with client:
    client.loop.run_until_complete(main())

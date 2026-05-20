import os
from pathlib import Path
from dotenv import load_dotenv

from pick_topic import pick_next_topic, update_progress
from generate_script_hindi import make_script
from make_tts_gtts import text_to_speech_hi
from make_subtitles import build_srt
from make_video_ffmpeg import build_video
from upload_youtube import upload
from make_thumbnail import make_thumbnail_from_bg # NEW  ← rename import if you saved differently
# If you named the file make_thumbnail.py, import like:
# from make_thumbnail import make_thumbnail_from_bg

load_dotenv()

WROOT = Path("work")
ASSETS = Path("assets")
BG_DIR = ASSETS / "bg"
INTRO = ASSETS / "brand" / "intro.mp4"
OUTRO = ASSETS / "brand" / "outro.mp4"

def _env_int(name, default):
    try: return int(os.getenv(name, str(default)))
    except: return default

def main():
    day, row = pick_next_topic()
    topic = str(row["topic"])
    keywords = str(row.get("keywords",""))
    print(f"[Day {day}] Topic: {topic}")

    outdir = WROOT / f"day_{day:03d}"
    outdir.mkdir(parents=True, exist_ok=True)
    script_file = outdir / "script_hi.txt"
    audio_file  = outdir / "narration_hi.mp3"
    srt_file    = outdir / "subtitles.srt"
    video_file  = outdir / "video.mp4"
    thumb_file  = outdir / "thumbnail.jpg"   # NEW

    # Script
    script_text = make_script(topic, keywords)
    script_file.write_text(script_text, encoding="utf-8")

    # TTS
    print("→ Generating narration (gTTS)…")
    text_to_speech_hi(script_text, audio_file)

    # Subtitles (~5 min evenly)
    print("→ Building subtitles (SRT)…")
    audio_seconds = 300.0
    build_srt(script_text, audio_seconds, srt_file)

    # Thumbnail from bg
    print("→ Making thumbnail…")
    make_thumbnail_from_bg(BG_DIR, topic, thumb_file)  # NEW

    # Video
    print("→ Rendering video (FFmpeg)…")
    build_video(
        intro=INTRO if INTRO.exists() else None,
        bg_dir=BG_DIR,
        audio=audio_file,
        srt=srt_file,
        outro=OUTRO if OUTRO.exists() else None,
        out_mp4=video_file
    )

    # Upload
    print("→ Uploading to YouTube…")
    publish_hour   = _env_int("PUBLISH_HOUR", 10)
    publish_minute = _env_int("PUBLISH_MINUTE", 0)
    privacy_status = os.getenv("VIDEO_PRIVACY_STATUS", "private")
    playlist_id    = os.getenv("PLAYLIST_ID") or None
    tz_name        = os.getenv("TIMEZONE", "Asia/Kolkata")

    title = f"{topic} | Criminal Law in Hindi (5 मिनट)"
    description = (
        f"इस वीडियो में: {topic} को सरल हिंदी में—परिभाषा, कब लागू, प्रक्रिया, छोटा उदाहरण और निष्कर्ष।\n"
        "अस्वीकरण: यह वीडियो केवल शैक्षिक उद्देश्य के लिए है, कानूनी सलाह नहीं। अपने मामले के लिए वकील से परामर्श लें।\n"
        "#CriminalLaw #Hindi #IndianLaw\n"
    )
    tags = ["Criminal Law Hindi","Indian Law","Court Process"] + [k.strip() for k in keywords.split(",") if k.strip()]

    url = upload(
        video_path=video_file,
        title=title,
        description=description,
        tags=tags,
        privacy_status=privacy_status,
        publish_hour=publish_hour,
        publish_minute=publish_minute,
        playlist_id=playlist_id,
        timezone_name=tz_name,
        thumbnail_path=thumb_file,    # NEW
        captions_path=srt_file        # NEW
    )
    print("✅ Uploaded:", url)
    update_progress(day, url=url, status="published")

if __name__ == "__main__":
    main()

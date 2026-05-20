# src/upload_youtube.py
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

load_dotenv()

# Scopes: upload videos + manage channel (needed for captions/thumbnail)
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

CLIENT_SECRET = Path("client_secret.json")
TOKEN_FILE = Path("work/token.json")


def _get_service():
    """Return an authenticated YouTube Data API client."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
        # If the local-server flow gives trouble, switch to: flow.run_console()
        creds = flow.run_local_server(port=0)
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def _publish_time_utc(hour: int, minute: int, tz_name: str = "Asia/Kolkata") -> str:
    """Return an RFC3339 timestamp in UTC for tomorrow/today at given local time."""
    try:
        from zoneinfo import ZoneInfo  # py3.9+
        tz = ZoneInfo(tz_name)
    except Exception:
        # Fallback to IST if zoneinfo missing
        tz = timezone(timedelta(hours=5, minutes=30))

    now_local = datetime.now(tz)
    pub = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if pub <= now_local:
        pub = pub + timedelta(days=1)  # schedule next day if time already passed
    return pub.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def upload(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str] | None,
    privacy_status: str = "private",  # private | public | unlisted
    publish_hour: int = 10,
    publish_minute: int = 0,
    playlist_id: str | None = None,
    timezone_name: str = "Asia/Kolkata",
    thumbnail_path: Path | None = None,
    captions_path: Path | None = None,  # .srt
) -> str:
    """
    Upload a video and (optionally) attach thumbnail & captions.
    Returns the public watch URL.
    """
    yt = _get_service()

    snippet = {
        "title": title[:100],
        "description": description or "",
        "categoryId": "27",  # Education
    }
    if tags:
        snippet["tags"] = tags[:20]

    status = {"privacyStatus": privacy_status}
    if privacy_status == "private":
        status["publishAt"] = _publish_time_utc(publish_hour, publish_minute, timezone_name)

    # 1) Upload the video
    insert_req = yt.videos().insert(
        part="snippet,status",
        body={"snippet": snippet, "status": status},
        media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True),
    )
    resp = insert_req.execute()
    video_id = resp["id"]

    # 2) Try to set a custom thumbnail (skip gracefully if permission denied)
    if thumbnail_path and thumbnail_path.exists():
        try:
            yt.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path)),
            ).execute()
        except Exception as e:
            # Most common cause: channel not verified for custom thumbnails while app is unverified
            print("⚠️  Skipping thumbnail upload (permission or verification required):", e)

    # 3) Upload captions (Hindi SRT) – optional
    if captions_path and captions_path.exists():
        try:
            yt.captions().insert(
                part="snippet",
                body={
                    "snippet": {
                        "language": "hi",
                        "name": "Hindi",
                        "videoId": video_id,
                        "isDraft": False,
                    }
                },
                media_body=MediaFileUpload(str(captions_path), mimetype="application/octet-stream"),
            ).execute()
        except Exception as e:
            print("⚠️  Skipping captions upload:", e)

    # 4) Add to playlist (optional)
    if playlist_id:
        try:
            yt.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }
                },
            ).execute()
        except Exception as e:
            print("⚠️  Skipping playlist add:", e)

    return f"https://www.youtube.com/watch?v={video_id}"

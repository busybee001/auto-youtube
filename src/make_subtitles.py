from pathlib import Path
import pysrt
import re

def _split_sentences(text: str):
    # Simple Hindi-friendly split on । ! ? (keeps it robust enough)
    parts = re.split(r'[।!?]\s*', text)
    return [p.strip() for p in parts if p.strip()]

def build_srt(text: str, audio_seconds: float, out_srt: Path):
    """
    Create evenly-timed SRT subtitles for the given Hindi text.
    """
    lines = _split_sentences(text)
    n = max(len(lines), 1)
    per = max(audio_seconds / n, 2.0)  # at least 2s per caption
    subs = pysrt.SubRipFile()
    t = 0.0

    for i, line in enumerate(lines, start=1):
        start_s = int(t)
        end_s   = int(min(t + per, audio_seconds))
        subs.append(pysrt.SubRipItem(
            index=i,
            start=pysrt.SubRipTime(seconds=start_s),
            end=pysrt.SubRipTime(seconds=end_s),
            text=line
        ))
        t += per

    out_srt.parent.mkdir(parents=True, exist_ok=True)
    subs.save(str(out_srt), encoding="utf-8")

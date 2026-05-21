# src/make_thumbnail.py
from pathlib import Path
import subprocess, shlex
from PIL import Image, ImageDraw, ImageFont

def _probe_duration(mp4: Path) -> float:
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(str(mp4))}'
    out = subprocess.check_output(cmd, shell=True).decode().strip()
    return float(out or 0.0)

def _grab_frame(mp4: Path, when_s: float, out_jpg: Path):
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    # Force single-image write to avoid the "pattern" error
    cmd = (
        f'ffmpeg -y -ss {when_s:.2f} -i {shlex.quote(str(mp4))} '
        f'-frames:v 1 -q:v 2 -f image2 -update 1 {shlex.quote(str(out_jpg))}'
    )
    subprocess.run(cmd, shell=True, check=True)

def _best_font():
    # Try a Devanagari-capable font; fall back gracefully
    candidates = [
        Path("assets/fonts/NotoSansDevanagari-Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc"),
        Path("/Library/Fonts/NotoSansDevanagari-Bold.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"),
    ]
    for p in candidates:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), 72)
            except Exception:
                continue
    return ImageFont.load_default()

def _wrap_lines(text: str, max_chars=18, max_lines=3):
    words = text.split()
    lines, line = [], ""
    for w in words:
        trial = (line + " " + w).strip()
        if len(trial) > max_chars and line:
            lines.append(line)
            line = w
        else:
            line = trial
    if line:
        lines.append(line)
    return lines[:max_lines]

def _multiline_bbox(draw: ImageDraw.ImageDraw, text: str, font, spacing=8):
    """
    Pillow versions differ: multiline_textbbox exists on newer versions.
    Fallback: compute line-by-line using textbbox.
    """
    if hasattr(draw, "multiline_textbbox"):
        left, top, right, bottom = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
        return right - left, bottom - top

    # Fallback (approx): sum heights and take max width
    widths = []
    heights = []
    total_h = 0
    for i, line in enumerate(text.split("\n")):
        l, t, r, b = draw.textbbox((0, 0), line, font=font)
        w = r - l
        h = b - t
        widths.append(w)
        heights.append(h)
        total_h += h
        if i < len(text.split("\n")) - 1:
            total_h += spacing
    return max(widths) if widths else 0, total_h

def make_thumbnail_from_bg(bg_dir: Path, topic_text: str, out_jpg: Path):
    bgs = sorted(bg_dir.glob("*.mp4"))
    if not bgs:
        raise RuntimeError("No background .mp4 files found in assets/bg/")
    bg = bgs[0]
    dur = _probe_duration(bg)
    if dur <= 0:
        dur = 5.0
    # take a middle-ish frame
    _grab_frame(bg, dur / 2, out_jpg)

    # overlay text
    img = Image.open(out_jpg).convert("RGB")
    W, H = img.size
    draw = ImageDraw.Draw(img)
    font = _best_font()

    lines = _wrap_lines(topic_text, 18, 3)
    text = "\n".join(lines)

    # dark bar at bottom
    bar_h = int(H * 0.28)
    overlay = Image.new("RGBA", (W, bar_h), (0, 0, 0, 140))
    img.paste(overlay, (0, H - bar_h), overlay)

    # center text
    tw, th = _multiline_bbox(draw, text, font, spacing=8)
    x = max((W - tw) // 2, 20)
    y = H - bar_h + max((bar_h - th) // 2, 10)

    # subtle shadow then white text
    draw.multiline_text((x+2, y+2), text, font=font, fill=(0, 0, 0), spacing=8, align="center")
    draw.multiline_text((x, y), text, font=font, fill=(255, 255, 255), spacing=8, align="center")

    img.save(out_jpg, "JPEG", quality=90)

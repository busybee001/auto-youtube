import subprocess, shlex
from pathlib import Path

def _ffmpeg_ok():
    try:
        subprocess.run(["ffmpeg","-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False

def _probe_duration(media: Path) -> float:
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(str(media))}'
    out = subprocess.check_output(cmd, shell=True).decode().strip()
    return float(out)

def build_video(intro: Path|None, bg_dir: Path, audio: Path, srt: Path|None, outro: Path|None, out_mp4: Path):
    """
    Renders: [intro (optional)] + [looped bg covering narration] + [outro (optional)]
    Attaches your narration as audio. SRT is saved separately for YouTube.
    """
    if not _ffmpeg_ok():
        raise RuntimeError("FFmpeg not found. Install it and ensure 'ffmpeg' is on PATH.")

    # narration length
    try:
        duration = _probe_duration(audio)
    except Exception:
        duration = 300.0  # fallback to ~5 min

    # pick a bg clip and loop it to match duration
    bgs = sorted((bg_dir or Path(".")).glob("*.mp4"))
    if not bgs:
        raise RuntimeError("Put at least one background MP4 in assets/bg/")
    bg = bgs[0]

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    tmp_bg = out_mp4.parent / "bg_loop.mp4"
    loop_cmd = f'ffmpeg -y -stream_loop -1 -i {shlex.quote(str(bg))} -t {duration:.2f} -c:v libx264 -pix_fmt yuv420p -an {shlex.quote(str(tmp_bg))}'
    subprocess.run(loop_cmd, shell=True, check=True)

    inputs = []
    maps = []
    # order: intro? + bg_loop + outro?
    concat_list = []

    def add_input(p: Path):
        inputs.append(f'-i {shlex.quote(str(p))}')
        concat_list.append(len(concat_list))

    if intro and intro.exists():
        add_input(intro)
    add_input(tmp_bg)
    if outro and outro.exists():
        add_input(outro)

    n = len(concat_list)
    filter_complex = f'concat=n={n}:v=1:a=0[v]'
    audio_in = f'-i {shlex.quote(str(audio))}'

    cmd = f'ffmpeg -y {" ".join(inputs)} {audio_in} -filter_complex "{filter_complex}" -map "[v]" -map {n}:a -c:v libx264 -preset veryfast -crf 22 -c:a aac -b:a 192k {shlex.quote(str(out_mp4))}'
    subprocess.run(cmd, shell=True, check=True)

    # SRT stays as a sidecar file for YouTube upload (no burn-in here).

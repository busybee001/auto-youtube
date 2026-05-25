from gtts import gTTS
from pathlib import Path

def text_to_speech_hi(text: str, out_mp3: Path):
    """
    Convert Hindi text to speech (MP3) using free gTTS.
    """
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    tts = gTTS(text=text, lang='hi', slow=False)
    tts.save(str(out_mp3))

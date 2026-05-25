import pandas as pd
from pathlib import Path
import json

TOPICS = Path("data/topics.csv")
PROGRESS = Path("data/progress.json")

def pick_next_topic():
    # Ensure progress file exists
    if not PROGRESS.exists():
        PROGRESS.write_text('{"last_published_day": 0}', encoding="utf-8")

    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    last = int(progress.get("last_published_day", 0))

    # Read topics with proper dtype for 'url' column
    df = pd.read_csv(TOPICS, dtype={"url": "string"})
    df["status"] = df["status"].fillna("pending")
    df = df.sort_values("day")

    # Pick next pending topic after the last published one
    next_row = df[(df["day"] > last) & (df["status"] != "published")].head(1)
    if next_row.empty:
        # Loop back to first pending topic, or start from first if all done
        next_row = df[df["status"] != "published"].head(1)
        if next_row.empty:
            next_row = df.head(1)

    day = int(next_row.iloc[0]["day"])
    row = next_row.iloc[0].to_dict()
    return day, row


def update_progress(day, url=None, status="published"):
    df = pd.read_csv(TOPICS, dtype={"url": "string"})
    idx = df.index[df["day"] == day]

    if len(idx):
        i = idx[0]
        df.at[i, "status"] = status
        # ✅ fixed to safely cast URL to string
        df.at[i, "url"] = str(url) if url is not None else ""

        df.to_csv(TOPICS, index=False)

    # Save progress info
    progress = {"last_published_day": int(day)}
    PROGRESS.write_text(json.dumps(progress), encoding="utf-8")

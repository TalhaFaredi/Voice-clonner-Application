"""YouTube link -> transcript + frames. No API keys needed."""
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import imageio_ffmpeg
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

from config import JOBS_DIR

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
MAX_FRAMES = 80
KEEP_JOBS = 5


def video_id_from(url: str) -> str | None:
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    url = url.strip()
    return url if re.fullmatch(r"[A-Za-z0-9_-]{11}", url) else None


def get_transcript(video_id: str):
    """Return (segments, error). English preferred, else the first available track."""
    api = YouTubeTranscriptApi()
    try:
        try:
            fetched = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        except Exception:
            fetched = next(iter(api.list(video_id))).fetch()
        segs = [{"start": round(s.start, 1), "text": s.text.replace("\n", " ").strip()} for s in fetched]
        return segs, None
    except Exception as e:
        return [], f"Transcript unavailable: {type(e).__name__}"


def _new_job() -> Path:
    old = sorted((p for p in JOBS_DIR.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime)
    for p in old[: max(0, len(old) - (KEEP_JOBS - 1))]:
        shutil.rmtree(p, ignore_errors=True)
    job = JOBS_DIR / uuid.uuid4().hex[:10]
    job.mkdir()
    return job


def extract_frames(video_id: str, interval: int | None):
    """Download a low-res copy and grab one frame every `interval` seconds."""
    job = _new_job()
    opts = {
        "format": "bv*[height<=480]/b[height<=480]/worst",
        "outtmpl": str(job / "video.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)

    duration = info.get("duration") or 0
    if not interval:
        interval = max(5, round(duration / 40)) if duration else 10
    if duration and duration / interval > MAX_FRAMES:
        interval = int(duration / MAX_FRAMES) + 1

    video = next(job.glob("video.*"))
    subprocess.run(
        [FFMPEG, "-loglevel", "error", "-i", str(video),
         "-vf", f"fps=1/{interval},scale=640:-2", "-frames:v", str(MAX_FRAMES), "-q:v", "4",
         str(job / "frame_%04d.jpg")],
        check=True,
    )
    video.unlink(missing_ok=True)

    frames = [
        {"time": i * interval, "url": f"/media/jobs/{job.name}/{f.name}"}
        for i, f in enumerate(sorted(job.glob("frame_*.jpg")))
    ]
    return info, interval, frames

#!/usr/bin/env python3
"""
Scruffy research intake (needs network access, yt-dlp, and optionally ffmpeg).

Pulls YouTube design videos into the knowledge base:
  transcripts/<id>_<slug>.md   chapter-aligned transcript with frame refs
  frames/<id>/SSSS_slug.jpg    one frame per chapter/topic (at t+2s)

Usage:
  python3 intake.py --help                         # usage only; no network
  python3 intake.py <url> [<url> ...]              # specific videos (any creator)
  python3 intake.py --channel <channel_url>        # sweep another creator
  python3 intake.py --no-frames <url>              # transcript only

Requires: yt-dlp on PATH; ffmpeg on PATH unless --no-frames is used.
Install them using the package manager appropriate to the local environment.
Existing transcript files are skipped (sources are immutable once ingested).
"""
import argparse, json, re, subprocess, sys, tempfile
from urllib.parse import urlparse
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PROCESS_TIMEOUT = 300

def video_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("invalid video id")
    return value

def valid_url(value):
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise argparse.ArgumentTypeError("provide an http or https URL")
    return value

def yaml_string(value):
    return json.dumps(str(value), ensure_ascii=True)

def sh(*args, **kw):
    kw.setdefault("timeout", PROCESS_TIMEOUT)
    return subprocess.run(args, capture_output=True, text=True, **kw)

def slug(s, n=40):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")[:n] or "untitled"

def list_channel(url):
    r = sh("yt-dlp", "--flat-playlist", "-J", "--", url)
    if r.returncode != 0:
        sys.exit(f"channel listing failed: {r.stderr[-500:]}")
    data = json.loads(r.stdout)
    return ["https://www.youtube.com/watch?v=" + video_id(e["id"]) for e in data.get("entries", []) if e.get("id")]

def parse_vtt(path):
    """VTT -> [(sec, text)], de-duplicated auto-caption stutter."""
    cues, last = [], ""
    t = None
    for line in Path(path).read_text(errors="replace").splitlines():
        m = re.match(r"(\d+):(\d+):(\d+)\.\d+\s+-->", line)
        if m:
            t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]); continue
        txt = re.sub(r"<[^>]+>", "", line).strip()
        if t is None or not txt or txt == last or txt.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        cues.append((t, txt)); last = txt
    # merge into ~20s paragraphs
    out, cur = [], None
    for t, txt in cues:
        if cur is None: cur = [t, txt]
        elif t - cur[0] >= 20: out.append(tuple(cur)); cur = [t, txt]
        elif not cur[1].endswith(txt): cur[1] += " " + txt
    if cur: out.append(tuple(cur))
    return out

def mmss(t):
    return f"{t//60}:{t%60:02d}"

def process(url, frames=True):
    r = sh("yt-dlp", "-J", "--no-playlist", "--", url)
    if r.returncode != 0:
        raise ValueError(f"metadata failed: {url}")
    meta = json.loads(r.stdout)
    vid = video_id(meta["id"])
    title = meta.get("title") or vid
    md_path = BASE / "transcripts" / f"{vid}_{slug(title)}.md"
    existing = list((BASE / "transcripts").glob(f"{vid}_*.md"))
    if existing:
        print(f"  -- exists, skipping transcript: {existing[0].name}")
        md_path = existing[0]
    chapters = [{"t": int(c["start_time"]), "label": c["title"]} for c in (meta.get("chapters") or [])]

    captured_frames = set()
    with tempfile.TemporaryDirectory() as td:
        segs = []
        if not existing:
            captions = sh("yt-dlp", "--skip-download", "--write-auto-sub", "--write-sub",
               "--sub-lang", "en.*", "--sub-format", "vtt", "-o", f"{td}/cap", "--", url)
            if captions.returncode != 0:
                raise ValueError(f"caption download failed: {vid}")
            vtts = list(Path(td).glob("cap*.vtt"))
            if vtts:
                segs = parse_vtt(vtts[0])
            else:
                print(f"  !! no captions for {vid}")

        # topic boundaries: chapters, else every 60s
        bounds = chapters or [{"t": t, "label": f"Segment {i+1}"}
                              for i, t in enumerate(range(0, int(meta.get("duration") or 0), 60))]

        if frames and bounds:
            fdir = BASE / "frames" / vid; fdir.mkdir(parents=True, exist_ok=True)
            vpath = f"{td}/v.mp4"
            dl = sh("yt-dlp", "-f", "worstvideo[height>=480][ext=mp4]/worstvideo[ext=mp4]/worst[ext=mp4]",
                    "--no-playlist", "-o", vpath, "--", url)
            if dl.returncode == 0 and Path(vpath).exists():
                for b in bounds:
                    out = fdir / f"{b['t']:04d}_{slug(b['label'],30)}.jpg"
                    if out.exists() and out.stat().st_size:
                        captured_frames.add(b['t'])
                        continue
                    # Only promote successful, nonempty captures to durable evidence.
                    temporary = Path(td) / "capture.jpg"
                    if temporary.exists():
                        temporary.unlink()
                    result = sh("ffmpeg", "-ss", str(b["t"] + 2), "-i", vpath,
                                "-frames:v", "1", "-q:v", "3", str(temporary), "-y")
                    if result.returncode == 0 and temporary.exists() and temporary.stat().st_size:
                        out.write_bytes(temporary.read_bytes())
                        captured_frames.add(b['t'])
                    else:
                        print(f"  !! frame failed at {b['t']}s")
                print(f"  frames: {len(captured_frames)}/{len(bounds)} captured -> frames/{vid}/")
            else:
                print(f"  !! video download failed, frames skipped: {dl.stderr[-200:]}")

    if existing or not segs:
        return
    # write transcript md, sections split at chapter boundaries
    lines = ["---", "type: transcript", f"video_id: {yaml_string(vid)}",
             f"title: {yaml_string(title)}", f"channel: {yaml_string(meta.get('channel',''))}",
             f"url: {yaml_string('https://www.youtube.com/watch?v=' + vid)}",
             f"duration: {yaml_string(mmss(int(meta.get('duration') or 0)))}", "captions: downloaded English subtitles",
             "chapters: " + json.dumps(chapters, ensure_ascii=True),
             f"frames_dir: {yaml_string('../frames/' + vid + '/')}", "---", "", f"# {title}", ""]
    ci = 0
    for t, txt in segs:
        while ci < len(bounds) and t >= bounds[ci]["t"]:
            b = bounds[ci]
            lines += ["", f"## [{mmss(b['t'])}] {b['label']}"]
            if b['t'] in captured_frames:
                lines.append(f"<!-- frame: ../frames/{vid}/{b['t']:04d}_{slug(b['label'],30)}.jpg -->")
            else:
                lines.append("<!-- frame: not captured -->")
            lines.append("")
            ci += 1
        lines.append(f"[{mmss(t)}] {txt}")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with md_path.open("x", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")
    print(f"  wrote {md_path.name} ({len(segs)} paragraphs, {len(chapters)} chapters)")

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("urls", nargs="*", type=valid_url, help="explicit video URLs")
    parser.add_argument("--channel", type=valid_url, help="explicit channel URL to sweep")
    parser.add_argument("--no-frames", action="store_true", help="download transcripts only")
    args = parser.parse_args(argv)
    if bool(args.urls) == bool(args.channel):
        parser.error("provide video URLs or --channel URL (not both)")
    try:
        urls = list_channel(args.channel) if args.channel else args.urls
        print(f"{len(urls)} video(s) to process")
        for url in urls:
            print(url)
            process(url, frames=not args.no_frames)
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

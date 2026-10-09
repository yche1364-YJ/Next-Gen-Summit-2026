#!/usr/bin/env python3
"""Build the game gallery website from submissions/.

For every submissions/<id>/ folder (game.zip + info.json) this script:
  * exports the Godot project for the web (single-threaded build),
  * takes a screenshot to use as a thumbnail,
  * keeps only the game's own files (index.pck, index.html, icons): every game
    shares ONE copy of the Godot engine in site/engine/, so 30 games take about
    100 MB instead of 1.2 GB,
  * and writes site/index.html, the gallery page.

Results are cached by the ZIP's SHA-256, so only new or updated games are rebuilt.

Environment variables:
  GODOT          path to the Godot 4.7 editor binary
  TEMPLATES      folder containing web_nothreads_release.zip
  CACHE_IN       previous build cache (may be missing)
  CACHE_OUT      where to write the new build cache
  SITE           output folder for the website
  REPO           owner/name (for links)
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBMISSIONS = ROOT / "submissions"
GODOT = os.environ.get("GODOT", "godot")
TEMPLATES = Path(os.environ.get("TEMPLATES", "templates"))
CACHE_IN = Path(os.environ.get("CACHE_IN", "build-cache-in"))
CACHE_OUT = Path(os.environ.get("CACHE_OUT", "build-cache-out"))
SITE = Path(os.environ.get("SITE", "site"))
REPO = os.environ.get("REPO", "yche1364-YJ/Next-Gen-Summit-2026")

ENGINE_FILES = ["godot.js", "godot.wasm", "godot.audio.worklet.js", "godot.audio.position.worklet.js"]
GAME_FILES = ["index.html", "index.pck", "index.png", "index.icon.png", "index.apple-touch-icon.png", "thumb.png"]


def log(*args: object) -> None:
    print(*args, flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], timeout: int) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, text=True, errors="replace")
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(errors="replace")
        return 124, out + f"\n[timed out after {timeout}s]"


def safe_extract(zip_path: Path, dest: Path) -> Path:
    """Extract a ZIP safely and return the folder that contains project.godot."""
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            target = (dest / member.filename).resolve()
            if not str(target).startswith(str(dest.resolve()) + os.sep) and target != dest.resolve():
                raise ValueError(f"unsafe path in ZIP: {member.filename}")
        zf.extractall(dest)
    projects = sorted(dest.rglob("project.godot"), key=lambda p: len(p.parts))
    if not projects:
        raise ValueError("project.godot not found")
    return projects[0].parent


def set_main_scene(project_dir: Path, scene: str) -> None:
    cfg = project_dir / "project.godot"
    text = cfg.read_text(encoding="utf-8")
    line = f'run/main_scene="res://{scene}"'
    if re.search(r"^run/main_scene=.*$", text, flags=re.MULTILINE):
        text = re.sub(r"^run/main_scene=.*$", line, text, flags=re.MULTILINE)
    elif "[application]" in text:
        text = text.replace("[application]", "[application]\n\n" + line, 1)
    else:
        text += f"\n[application]\n\n{line}\n"
    cfg.write_text(text, encoding="utf-8")


def patch_html(html_path: Path) -> None:
    """Point the exported page at the shared engine in ../../engine/."""
    text = html_path.read_text(encoding="utf-8")
    text = text.replace('<script src="index.js"></script>', '<script src="../../engine/godot.js"></script>')
    m = re.search(r"GODOT_CONFIG = (\{.*?\});", text)
    if not m:
        raise ValueError("GODOT_CONFIG not found in exported HTML")
    config = json.loads(m.group(1))
    sizes = config.get("fileSizes", {})
    config["executable"] = "../../engine/godot"
    config["mainPack"] = "index.pck"
    config["fileSizes"] = {
        "index.pck": sizes.get("index.pck", 0),
        "../../engine/godot.wasm": sizes.get("index.wasm", 0),
    }
    text = text[: m.start(1)] + json.dumps(config, separators=(",", ":")) + text[m.end(1):]
    back = (
        '<a href="../../" id="back-to-gallery" style="position:fixed;right:12px;bottom:12px;z-index:10;'
        "padding:8px 14px;border-radius:999px;background:rgba(7,8,26,.75);color:#fff;"
        'font:600 14px system-ui,sans-serif;text-decoration:none;opacity:.8">← All games</a>'
    )
    text = text.replace("</body>", back + "\n</body>", 1)
    html_path.write_text(text, encoding="utf-8")


def build_game(sub: Path, info: dict, out: Path) -> tuple[bool, str]:
    tmp = Path(tempfile.mkdtemp(prefix="game-"))
    try:
        project = safe_extract(sub / "game.zip", tmp / "src")
        shutil.copyfile(ROOT / "tools" / "export_presets.cfg", project / "export_presets.cfg")
        shutil.rmtree(project / ".godot", ignore_errors=True)
        if info.get("scene"):
            set_main_scene(project, info["scene"])

        code, output = run([GODOT, "--headless", "--path", str(project), "--import"], 600)
        web = tmp / "web"
        web.mkdir()
        code, output = run([GODOT, "--headless", "--path", str(project), "--export-release", "Web", str(web / "index.html")], 600)
        if not (web / "index.pck").exists() or not (web / "index.html").exists():
            return False, output[-3000:]

        # Thumbnail: run the game for a moment and keep the last frame.
        shots = tmp / "shots"
        shots.mkdir()
        run(
            ["xvfb-run", "-a", "-s", "-screen 0 1280x720x24", GODOT, "--path", str(project),
             "--rendering-driver", "opengl3", "--audio-driver", "Dummy", "--resolution", "640x360",
             "--fixed-fps", "10", "--quit-after", "25", "--write-movie", str(shots / "t.png")],
            180,
        )
        frames = sorted(shots.glob("t*.png"))
        if frames:
            shutil.copyfile(frames[-1], web / "thumb.png")

        patch_html(web / "index.html")
        out.mkdir(parents=True, exist_ok=True)
        for name in GAME_FILES:
            if (web / name).exists():
                shutil.copyfile(web / name, out / name)
        return True, output[-1500:]
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def install_engine() -> None:
    engine = SITE / "engine"
    engine.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TEMPLATES / "web_nothreads_release.zip") as zf:
        for name in ENGINE_FILES:
            (engine / name).write_bytes(zf.read(name))


def esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def card(info: dict, ok: bool, has_thumb: bool) -> str:
    gid = esc(info["id"])
    title = esc(info.get("title") or "Untitled game")
    team = esc(info.get("team", ""))
    members = esc(info.get("members", ""))
    desc = esc(info.get("description", "")).replace("\n", "<br>")
    controls = esc(info.get("controls", "")).replace("\n", "<br>")
    source = f"https://github.com/{REPO}/raw/main/submissions/{gid}/game.zip"
    search = esc(" ".join([info.get("title", ""), info.get("team", ""), info.get("members", "")]).lower())
    if ok:
        thumb = f'<img src="games/{gid}/thumb.png" alt="" loading="lazy">' if has_thumb else '<div class="ph">🎮</div>'
        media = f'<a class="thumb" href="games/{gid}/" aria-label="Play {title}">{thumb}<span class="play">▶ Play</span></a>'
        play = f'<a class="btn primary" href="games/{gid}/">▶ Play</a>'
    else:
        media = '<div class="thumb"><div class="ph">🛠️<small>Coming soon</small></div></div>'
        play = '<span class="btn disabled">Coming soon</span>'
    return f"""
    <article class="card" data-search="{search}">
      {media}
      <div class="body">
        <h2>{title}</h2>
        <p class="team"><strong>{team}</strong>{' · ' + members if members else ''}</p>
        <p class="desc">{desc}</p>
        {f'<div class="controls"><span>Controls</span>{controls}</div>' if controls else ''}
        <div class="actions">
          {play}
          <a class="btn" href="{source}">Download source</a>
        </div>
      </div>
    </article>"""


def write_gallery(entries: list[tuple[dict, bool, bool]]) -> None:
    cards = "\n".join(card(i, ok, th) for i, ok, th in entries)
    count = sum(1 for _, ok, _ in entries if ok)
    empty = "" if entries else '<p class="empty">No games yet — be the first to submit yours!</p>'
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Threadbare + Godot Challenge · Game Gallery</title>
<meta name="description" content="Games made by students in the Threadbare + Godot Challenge, Next-Gen Summit 2026.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎮</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root {{ --bg:#07081a; --panel:#12142e; --line:#262a52; --text:#f2f3ff; --muted:#a9acd6; --pink:#ff5c7a; --yellow:#ffd60a; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:Poppins,system-ui,sans-serif; }}
  a {{ color:inherit; }}
  .banner {{ display:block; width:100%; aspect-ratio:5/1; object-fit:cover; object-position:center; border-bottom:1px solid var(--line); }}
  header {{ max-width:1200px; margin:0 auto; padding:28px 16px 8px; display:flex; flex-wrap:wrap; gap:16px; align-items:start; justify-content:space-between; }}
  h1 {{ margin:0; font-size:clamp(1.6rem,3.5vw,2.4rem); line-height:1.15; }}
  h1 .plus {{ color:var(--pink); }} h1 .ch {{ color:var(--yellow); }}
  .sub {{ margin:6px 0 0; color:var(--muted); }}
  .tools {{ display:flex; flex-direction:column; align-items:stretch; gap:12px; width:min(320px,100%); }}
  .btn.submit {{ justify-content:center; padding:14px 24px; font-size:1.15rem; }}
  input[type=search] {{ background:var(--panel); border:1px solid var(--line); color:var(--text); border-radius:999px; padding:10px 16px; font:inherit; width:100%; }}
  .resources {{ margin:0; color:var(--muted); font-size:.9rem; padding-left:16px; }}
  .resources a {{ color:var(--text); font-weight:600; }}
  .btn {{ display:inline-flex; align-items:center; gap:6px; padding:9px 14px; border-radius:999px; border:1px solid var(--line); background:var(--panel); text-decoration:none; font-weight:600; font-size:.9rem; white-space:nowrap; }}
  .btn:hover {{ border-color:var(--muted); }}
  .btn.primary {{ background:var(--pink); border-color:var(--pink); color:#fff; }}
  .btn.ghost {{ background:transparent; color:var(--muted); }}
  .btn.disabled {{ opacity:.55; }}
  main {{ max-width:1200px; margin:0 auto; padding:16px 16px 48px; display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:20px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:18px; overflow:hidden; display:flex; flex-direction:column; }}
  .thumb {{ position:relative; display:block; aspect-ratio:16/9; background:#000; }}
  .thumb img {{ width:100%; height:100%; object-fit:cover; display:block; image-rendering:auto; }}
  .ph {{ width:100%; height:100%; display:grid; place-items:center; align-content:center; font-size:3rem; color:var(--muted); }}
  .ph small {{ font-size:.9rem; }}
  .play {{ position:absolute; inset:auto 12px 12px auto; background:rgba(7,8,26,.85); padding:6px 12px; border-radius:999px; font-weight:700; font-size:.9rem; }}
  .thumb:hover .play {{ background:var(--pink); }}
  .body {{ padding:16px 18px 18px; display:flex; flex-direction:column; gap:8px; flex:1; }}
  h2 {{ margin:0; font-size:1.2rem; }}
  .team {{ margin:0; color:var(--muted); font-size:.92rem; }}
  .team strong {{ color:var(--yellow); font-weight:600; }}
  .desc {{ margin:0; font-size:.95rem; line-height:1.5; }}
  .controls {{ font-size:.85rem; color:var(--muted); border-left:3px solid var(--line); padding-left:10px; }}
  .controls span {{ display:block; text-transform:uppercase; letter-spacing:.06em; font-size:.72rem; font-weight:700; }}
  .actions {{ margin-top:auto; padding-top:8px; display:flex; flex-wrap:wrap; gap:8px; }}
  .empty {{ grid-column:1/-1; text-align:center; color:var(--muted); padding:48px 0; }}
  footer {{ max-width:1200px; margin:0 auto; padding:0 16px 40px; color:var(--muted); font-size:.85rem; }}
  footer a {{ color:var(--text); }}
</style>
</head>
<body>
<img class="banner" src="assets/cover.png" alt="Threadbare + Godot Challenge">
<header>
  <div>
    <h1>Threadbare <span class="plus">+</span> Godot <span class="ch">Challenge</span></h1>
    <p class="sub">Next-Gen Summit 2026</p>
  </div>
  <div class="tools">
    <a class="btn primary submit" href="https://github.com/{REPO}/issues/new?template=submit-game.yml">Submit your game</a>
    <input type="search" id="q" placeholder="Search games, teams…" aria-label="Search games">
    <p class="resources">Resources: <a href="https://github.com/{REPO}">GitHub</a></p>
  </div>
</header>
<main id="grid">
{cards}
{empty}
</main>
<footer>
  Built with <a href="https://godotengine.org">Godot Engine</a>, based on
  <a href="https://github.com/endlessm/moddable-platformer">Moddable Platformer</a> by Endless Access (MIT).
  · <a href="https://github.com/{REPO}">Project repository</a>
</footer>
<script>
  const q = document.getElementById('q');
  q.addEventListener('input', () => {{
    const s = q.value.trim().toLowerCase();
    document.querySelectorAll('.card').forEach(c => {{ c.hidden = s && !c.dataset.search.includes(s); }});
  }});
</script>
</body>
</html>
"""
    (SITE / "index.html").write_text(page, encoding="utf-8")


def main() -> int:
    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "assets").mkdir(parents=True)
    (SITE / ".nojekyll").write_text("")
    shutil.copyfile(ROOT / "gallery" / "cover.png", SITE / "assets" / "cover.png")
    install_engine()
    CACHE_OUT.mkdir(parents=True, exist_ok=True)

    entries: list[tuple[dict, bool, bool]] = []
    report = ["| Game | Team | Status |", "|---|---|---|"]
    subs = sorted(p for p in SUBMISSIONS.iterdir() if (p / "info.json").exists() and (p / "game.zip").exists()) if SUBMISSIONS.exists() else []
    for sub in subs:
        info = json.loads((sub / "info.json").read_text(encoding="utf-8"))
        info["id"] = sub.name
        digest = sha256(sub / "game.zip")
        cached = CACHE_IN / sub.name / digest
        new_cache = CACHE_OUT / sub.name / digest
        out = SITE / "games" / sub.name
        if (cached / "index.pck").exists():
            shutil.copytree(cached, out)
            ok, status = True, "✅ (cached)"
            log(f"[cached] {sub.name}")
        else:
            log(f"[build ] {sub.name} …")
            ok, output = build_game(sub, info, out)
            status = "✅ built" if ok else "❌ failed"
            if not ok:
                log(f"::warning title=Build failed: {sub.name}::{output[-500:]!s}".replace("\n", " "))
                log(output)
        if ok:
            shutil.copytree(out, new_cache, dirs_exist_ok=True)
        entries.append((info, ok, (out / "thumb.png").exists()))
        report.append(f"| [{info.get('title','')}](https://github.com/{REPO}/issues/{info.get('issue')}) | {info.get('team','')} | {status} |")

    entries.sort(key=lambda e: int(e[0].get("issue", 0)))
    write_gallery(entries)
    (SITE / "games.json").write_text(json.dumps([e[0] for e in entries], indent=2, ensure_ascii=False), encoding="utf-8")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    text = f"## Game gallery build\n\n{len(entries)} submission(s)\n\n" + "\n".join(report) + "\n"
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text)
    log(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

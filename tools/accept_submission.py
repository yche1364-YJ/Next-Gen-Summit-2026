#!/usr/bin/env python3
"""Accept an approved game submission from a GitHub issue.

Run by .github/workflows/accept-submission.yml when a teacher adds the
`approved` label to a `submission` issue. It:

1. reads the issue form (title, team, members, description, controls, scene, ZIP link);
2. downloads the attached ZIP and checks that it is a Godot project;
3. saves it to submissions/<NNN>-<slug>/game.zip with an info.json next to it.

It never extracts or runs the student's project; that happens later, in the
read-only gallery build.

Outputs (written to $GITHUB_OUTPUT):
  ok=true|false, id=<submission id>, message=<markdown for the issue comment>
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

MAX_ZIP_BYTES = 50 * 1024 * 1024
ROOT = Path(__file__).resolve().parent.parent
SUBMISSIONS = ROOT / "submissions"


def section(body: str, label: str) -> str:
    """Return the text under '### <label>' in an issue-form body."""
    pattern = rf"^###\s+{re.escape(label)}\s*\n(.*?)(?=^###\s|\Z)"
    m = re.search(pattern, body, flags=re.MULTILINE | re.DOTALL)
    if not m:
        return ""
    value = m.group(1).strip()
    return "" if value == "_No response_" else value


def clean(text: str, limit: int) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"\s+\n", "\n", text).strip()
    return text[:limit]


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40].strip("-") or "game"


def find_zip_url(text: str, repo: str) -> str | None:
    allowed = [
        r"https://github\.com/user-attachments/files/\d+/[^\s)\]>\"']+",
        rf"https://github\.com/{re.escape(repo)}/files/\d+/[^\s)\]>\"']+",
        # Lets a teacher point at a ZIP already stored in this repository.
        rf"https://github\.com/{re.escape(repo)}/raw/[^\s)\]>\"']+\.zip",
        rf"https://raw\.githubusercontent\.com/{re.escape(repo)}/[^\s)\]>\"']+\.zip",
    ]
    for pattern in allowed:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            return m.group(0)
    return None


def download(url: str, dest: Path, token: str | None) -> None:
    attempts = [None, token] if token else [None]
    last_error: Exception | None = None
    for auth in attempts:
        req = urllib.request.Request(url, headers={"User-Agent": "game-gallery-bot"})
        if auth:
            req.add_header("Authorization", f"Bearer {auth}")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
                size = 0
                while chunk := resp.read(1 << 16):
                    size += len(chunk)
                    if size > MAX_ZIP_BYTES:
                        raise ValueError("The ZIP file is larger than 50 MB.")
                    out.write(chunk)
            return
        except ValueError:
            raise
        except Exception as exc:  # try again with the token
            last_error = exc
    raise RuntimeError(f"Could not download the ZIP file ({last_error}).")


def inspect_zip(path: Path, scene: str) -> tuple[str, str]:
    """Check the ZIP is a Godot project. Returns (project_dir_prefix, scene_path)."""
    if not zipfile.is_zipfile(path):
        raise ValueError("The attached file is not a ZIP file.")
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        bad = [n for n in names if n.startswith("/") or ".." in Path(n).parts]
        if bad:
            raise ValueError("The ZIP file contains unsafe file paths.")
        projects = [n for n in names if n == "project.godot" or n.endswith("/project.godot")]
        if not projects:
            raise ValueError(
                "We couldn't find `project.godot` in the ZIP. Please use "
                "**Project → Tools → Download Project Source** in the Godot editor."
            )
        projects.sort(key=lambda n: n.count("/"))
        prefix = projects[0][: -len("project.godot")]

        scene = scene.strip().strip("`").strip()
        scene = re.sub(r"^res://", "", scene)
        if scene and not scene.endswith(".tscn"):
            scene += ".tscn"
        # main.tscn (or nothing) means "use the project's own main scene".
        if not scene or scene == "main.tscn":
            return prefix, ""
        if prefix + scene not in names:
            raise ValueError(
                f"We couldn't find the scene `{scene}` in your project. "
                "Check the spelling in **Scene to play** (for example `main.tscn`)."
            )
        return prefix, scene


def write_outputs(**values: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    lines = []
    for key, value in values.items():
        lines.append(f"{key}<<__EOF__\n{value}\n__EOF__")
    text = "\n".join(lines) + "\n"
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(text)
    else:
        print(text)


def main() -> int:
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    issue = event["issue"]
    repo = os.environ["GITHUB_REPOSITORY"]
    owner, name = repo.split("/")
    pages_url = f"https://{owner.lower()}.github.io/{name}/"
    body = issue.get("body") or ""
    number = int(issue["number"])

    title = clean(section(body, "Game title"), 60) or clean(issue["title"].replace("[Game]", ""), 60)
    team = clean(section(body, "Team name"), 60)
    members = clean(section(body, "Team members"), 120)
    description = clean(section(body, "About the game"), 600)
    controls = clean(section(body, "Controls"), 300)
    scene_field = section(body, "Scene to play") or "main.tscn"
    zip_field = section(body, "Game ZIP file") or body

    url = find_zip_url(zip_field, repo) or find_zip_url(body, repo)
    if not url:
        write_outputs(
            ok="false",
            id="",
            message=(
                "⚠️ **We couldn't find your game's ZIP file.**\n\n"
                "Please **edit this issue** (click `···` → **Edit**) and drag your ZIP file into "
                "the **Game ZIP file** box. Wait until a link appears, then click **Save**.\n\n"
                "Then reply here to let your teacher know."
            ),
        )
        return 0

    tmp = Path(tempfile.mkdtemp())
    zip_path = tmp / "game.zip"
    try:
        download(url, zip_path, os.environ.get("GITHUB_TOKEN"))
        _, scene = inspect_zip(zip_path, scene_field)
    except Exception as exc:  # report the problem on the issue
        write_outputs(
            ok="false",
            id="",
            message=(
                f"⚠️ **There's a problem with your ZIP file:** {exc}\n\n"
                "Please fix it, **edit this issue** to attach the new ZIP, and reply here "
                "to let your teacher know."
            ),
        )
        return 0

    sub_id = f"{number:03d}-{slugify(title)}"
    SUBMISSIONS.mkdir(exist_ok=True)
    for old in SUBMISSIONS.glob(f"{number:03d}-*"):
        if old.is_dir():
            shutil.rmtree(old)
    dest = SUBMISSIONS / sub_id
    dest.mkdir(parents=True)
    shutil.copyfile(zip_path, dest / "game.zip")

    info = {
        "id": sub_id,
        "issue": number,
        "title": title,
        "team": team,
        "members": members,
        "description": description,
        "controls": controls,
        "scene": scene,
        "submitted_by": issue.get("user", {}).get("login", ""),
        "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (dest / "info.json").write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    play_url = f"{pages_url}games/{sub_id}/"
    md = lambda s: s.replace("<", "&lt;").replace(">", "&gt;")  # noqa: E731
    title_md, team_md = md(title), md(team)
    write_outputs(
        ok="true",
        id=sub_id,
        message=(
            f"✅ **Approved — thank you, {team_md or 'team'}!**\n\n"
            f"Your game **{title_md}** is being published. In about **5–10 minutes** you can play it here:\n\n"
            f"🎮 **{play_url}**\n\n"
            f"🕹️ All games: {pages_url}\n\n"
            "Want to update your game? Edit this issue, replace the ZIP file, and reply here so your teacher can approve it again."
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

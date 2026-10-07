# Teacher guide: collecting and presenting the games

This repository turns student submissions into a **[Game Gallery](https://yche1364-yj.github.io/Next-Gen-Summit-2026/)** website where every team's game can be played in the browser. On presentation day you open one page and click through the teams.

Students can't publish playable games from the Godot web editor themselves (the web editor can't export yet), so the repository does it for them automatically.

## How it works

```
Student team                     You (teacher)                    GitHub (automatic)
────────────                     ─────────────                    ──────────────────
1. Download Project Source  ─┐
2. Fill in the issue form    ├─► 3. Review the issue
   and attach the ZIP       ─┘   4. Add the `approved` label ─►  5. Save the ZIP to submissions/
                                                                  6. Export the game for the web
                                                                  7. Update the gallery website
                                                                  8. Comment the play link on the issue
```

Approving takes you a few seconds per team; the game is online about **5–10 minutes** later.

## One-time setup

| | Status |
|---|---|
| Issue form, labels (`submission`, `approved`, `published`, `needs-fix`), workflows | ✅ Done |
| **GitHub Pages:** Settings → Pages → **Source: GitHub Actions** | Do this once |
| Gallery address | https://yche1364-yj.github.io/Next-Gen-Summit-2026/ |

## Timeline for 50–60 students (25–30 teams of two)

| When | What |
|---|---|
| **1–2 classes before the deadline** | Share [SUBMIT.md](SUBMIT.md). Ask **one person per team** to create a GitHub account ([Step 1](SUBMIT.md#step-1-create-a-github-account)). Email verification can be slow, so don't leave it to the last day. Collect the names of teams that can't create an account. |
| **Submission day** | Teams download their ZIP and submit the form ([Steps 2–3](SUBMIT.md#step-2-download-your-game-as-a-zip)). Approve submissions as they arrive. |
| **Before presentation day** | Check every team shows **▶ Play** in the gallery. Test the gallery on the presentation computer and projector. |

## Reviewing submissions

1. Open the **[Issues](https://github.com/yche1364-YJ/Next-Gen-Summit-2026/issues?q=is%3Aissue+label%3Asubmission)** tab and filter by the `submission` label.
2. Open a submission and check:
   - the title, team name and description are appropriate;
   - **members are first names or nicknames only**;
   - a ZIP link is in **Game ZIP file**.
3. On the right side, click **Labels** → tick **`approved`**.

The **Accept game submission** workflow then:
- ✅ if everything is fine: saves the ZIP, starts the gallery build, comments the play link and adds `published`;
- ⚠️ if there's a problem (no ZIP, not a Godot project, wrong scene name): comments what to fix, removes `approved` and adds `needs-fix`.

When a team has fixed or updated their submission, **remove `approved` and add it again** to re-publish it. The new version replaces the old one.

You can watch progress in the **[Actions](https://github.com/yche1364-YJ/Next-Gen-Summit-2026/actions)** tab.

### Teams without a GitHub account

Submit for them: open **[Submit our game](https://github.com/yche1364-YJ/Next-Gen-Summit-2026/issues/new?template=submit-game.yml)** yourself, fill in their details, attach their ZIP, then approve it. One issue per team.

## If a game shows "Coming soon"

The game was accepted but couldn't be exported. Open the latest **Build game gallery** run in the [Actions](https://github.com/yche1364-YJ/Next-Gen-Summit-2026/actions/workflows/build-gallery.yml) tab — the summary lists which game failed and why. Common causes:

- **Wrong scene:** the team built their game in another scene. Ask them to edit the **Scene to play** field, then re-approve.
- **Broken project:** a script error stops the game. Ask the team to press F5 in the web editor, fix the error, and upload a new ZIP.

To rebuild everything by hand: Actions → **Build game gallery** → **Run workflow**.

## Removing a game

Go to the `submissions/` folder, open the game's folder, delete both files (`game.zip`, `info.json`) with the **`···`** → **Delete file** menu, and commit. The gallery rebuilds without it. Close the issue as well.

## Presentation day tips

- Open the [gallery](https://yche1364-yj.github.io/Next-Gen-Summit-2026/) and press **F11** for full screen.
- Games are listed in submission order. Use the search box to jump to a team.
- Click **▶ Play**, click once on the game, then press any key to start. Use **← All games** (bottom-right) or the browser's Back button to return.
- The first game takes a little longer to load (the browser downloads the Godot engine once, about 40 MB); the others start quickly.
- Test the presentation computer in advance: use an up-to-date **Chrome or Edge**, and check the sound.

## Good to know

- **Cost:** GitHub Actions and GitHub Pages are free for public repositories.
- **Size:** every game shares one copy of the Godot engine, so each game adds only about 1–3 MB. 30 games fit easily within GitHub Pages' 1 GB limit.
- **Build time:** only new or changed games are rebuilt — about 1 minute per game.
- **Privacy:** issues, ZIPs and the gallery are public. Only first names or nicknames should be used. Check your school's rules about publishing student work.
- **Safety:** nothing is published until you add `approved`, and only people with write access to the repository can add labels. Only approve submissions from your own students.

## Files

| Path | Purpose |
|---|---|
| `.github/ISSUE_TEMPLATE/submit-game.yml` | The submission form |
| `.github/workflows/accept-submission.yml` | Runs when you add `approved`: saves the ZIP and replies |
| `.github/workflows/build-gallery.yml` | Exports the games and publishes the website |
| `tools/accept_submission.py` | Reads the form and checks the ZIP |
| `tools/build_gallery.py` | Exports the games and generates the gallery page |
| `tools/export_presets.cfg` | Web export settings used for every game |
| `gallery/cover.png` | Banner image at the top of the gallery |
| `submissions/` | One folder per accepted game (`game.zip` + `info.json`) |

# Teacher area

[← Back to the student page](../../README.md)

Everything you need to run the challenge: collect the games, approve them, and present them in the **[Game Gallery](https://yche1364-yj.github.io/Next-Gen-Summit-2026/)**.

**Contents**
1. [How submissions work](#1-how-submissions-work)
2. [Set up the upload page (one time, about 15 minutes)](#2-set-up-the-upload-page-one-time-about-15-minutes)
3. [Approve submissions](#3-approve-submissions)
4. [Timeline](#4-timeline)
5. [Presentation day](#5-presentation-day)
6. [Fixing problems](#6-fixing-problems)
7. [Original project, credits and license](#7-original-project-credits-and-license)

---

## 1. How submissions work

Students **don't need a GitHub account**. They upload on a simple web page, and you approve on GitHub.

```
Student team                 Upload page + Google script         You (teacher)            GitHub (automatic)
────────────                 ───────────────────────────         ─────────────            ──────────────────
1. Download Project Source
2. Open upload.html,     ──► 3. Check the class code
   type the class code,      4. Save the ZIP to pending/
   choose the ZIP            5. Open a "submission" issue  ──►  6. Add `approved`  ──►  7. Export the game
                                                                                           8. Update the gallery
```

- Nothing appears in the gallery until **you** add the `approved` label.
- A game is online about **5–10 minutes** after you approve it.
- If a team uploads again with the **same team name**, approving the new upload **replaces** their old game.

## 2. Set up the upload page (one time, about 15 minutes)

Do this **before** the students need to upload, for example the week before. Until it's done, the upload page shows *"Uploads aren't open yet."*

The upload page sends each ZIP to a small Google Apps Script that you own. The script stores the ZIP in this repository with a GitHub token. **The token stays inside your Google script.** Don't paste it anywhere else, and don't send it to anyone (including Claude).

> Use a **personal Gmail account**. Some school Google Workspace accounts don't allow "Anyone" access to a web app, and then students can't upload.

### A. Create a GitHub token (5 min)

1. Signed in to GitHub, open **[New fine-grained token](https://github.com/settings/personal-access-tokens/new)**.
2. **Token name:** `Game upload page`. **Expiration:** a date after the challenge ends.
3. **Repository access:** **Only select repositories** → `yche1364-YJ/Next-Gen-Summit-2026`.
4. **Permissions → Repository permissions:**
   - **Contents:** Read and write
   - **Issues:** Read and write
5. Click **Generate token** and **copy** it (it starts with `github_pat_`). Keep the tab open for the next step.

### B. Create the Google Apps Script (5 min)

1. Open **[script.google.com](https://script.google.com/)** → **New project**. Rename it `Game upload receiver`.
2. Delete the sample code in `Code.gs`. Open **[upload-script.gs](upload-script.gs)**, click **Copy raw file**, and paste it into `Code.gs`. Click **💾 Save**.
3. Click **⚙️ Project Settings** (left) → scroll to **Script Properties** → **Add script property**, and add:

   | Property | Value |
   |---|---|
   | `GITHUB_TOKEN` | the token from step A |
   | `CLASS_CODE` | a short code for your students, e.g. `bounce26` |

   Click **Save script properties**.

### C. Publish it as a web app (3 min)

1. Click **Deploy → New deployment**. Next to **Select type**, click ⚙️ → **Web app**.
2. **Execute as:** **Me**. **Who has access:** **Anyone**.
3. Click **Deploy**. Google asks you to **Authorize access**: choose your account → **Advanced** → **Go to Game upload receiver (unsafe)** → **Allow**. (It says "unsafe" only because you wrote the script yourself.)
4. Copy the **Web app URL** (it ends with `/exec`).
5. Optional check: open that URL in a new tab. You should see `"Upload receiver is running."`

### D. Connect the upload page (2 min)

1. In this repository, open **[gallery/upload-config.js](../../gallery/upload-config.js)** → click ✏️ **Edit**.
2. Paste the Web app URL between the quotes:
   ```js
   window.UPLOAD_URL = "https://script.google.com/macros/s/…/exec";
   ```
3. Click **Commit changes**. The gallery website updates in a few minutes.

(Or send the Web app URL to Claude and ask to put it in. The URL is safe to share; the token is not.)

### Test it

Open the **[upload page](https://yche1364-yj.github.io/Next-Gen-Summit-2026/upload.html)**, use your class code, team name `Teacher Test`, and upload [moddable-platformer-bouncy.zip](../../downloads/moddable-platformer-bouncy.zip). A new issue appears in **[Issues](https://github.com/yche1364-YJ/Next-Gen-Summit-2026/issues)**. Close it without approving (or approve it to see the whole process, then [remove the game](#remove-a-game)).

### The class code is filled in for students

`gallery/upload-config.js` also has `window.CLASS_CODE`, set to the same code as `CLASS_CODE` in the Google script. The upload page fills it in automatically, so students never type it. **If you change `CLASS_CODE` in the script, change it in `upload-config.js` too.** To make students type the code instead, set `window.CLASS_CODE = "";`.

Note: this file is public, so anyone who looks at the repository can see the code. Nothing reaches the gallery without your approval.

### Share a link with the code already filled in

Add `?code=` and your class code to the upload page address, for example:

```
https://yche1364-yj.github.io/Next-Gen-Summit-2026/upload.html?code=bounce26
```

Students who open this link don't need to type the code (the box is hidden). Share it only with your class (on the board, in your class chat, or as a QR code), not in public places.

### Change the class code

Apps Script → ⚙️ **Project Settings** → **Script Properties** → edit `CLASS_CODE`. It works immediately; you don't need to deploy again.

### Close uploads after the deadline

Change `CLASS_CODE` in the Google script to something new (and **don't** update `upload-config.js`). Students then get "Wrong class code". To reopen, change it back.

> **If you edit the script code later,** use **Deploy → Manage deployments → ✏️ → Version: New version → Deploy**, so the URL stays the same.

## 3. Approve submissions

1. Open the **[submissions](https://github.com/yche1364-YJ/Next-Gen-Summit-2026/issues?q=is%3Aissue+is%3Aopen+label%3Asubmission)** in the Issues tab.
2. Open one and check:
   - the title, team name and description are appropriate;
   - **members are first names only**.
3. On the right, click **Labels** → tick **`approved`**. That's it.

What happens next:
- ✅ **OK:** the game is saved, the gallery rebuilds, and a comment with the play link is added (label `published`).
- ⚠️ **Problem** (for example, not a Godot project): a comment explains it, and the label changes to `needs-fix`. Tell the team to fix it and upload again.

**Updated games:** when a team uploads again, you get a new issue. Approve it, and it replaces their old game (matched by team name). Close the old issue.

You can watch the progress in the **[Actions](https://github.com/yche1364-YJ/Next-Gen-Summit-2026/actions)** tab.

## 4. Timeline

For 50–60 students (25–30 teams of two):

| When | What |
|---|---|
| **The week before** | [Set up the upload page](#2-set-up-the-upload-page-one-time-about-15-minutes) and test it. |
| **First class** | Students follow [Step 1 and Step 2](../../README.md). Remind them to save with **Download Project Source** at the end of every class. |
| **Submission day** | Share the [upload page](https://yche1364-yj.github.io/Next-Gen-Summit-2026/upload.html) (the class code is filled in automatically). Each team uploads once ([student guide](../submit-guide.md)). Approve the issues as they arrive. |
| **Before presentation day** | Check every team shows **▶ Play** in the gallery. Change the class code to close uploads. Test the gallery on the presentation computer. |

## 5. Presentation day

- Open the [gallery](https://yche1364-yj.github.io/Next-Gen-Summit-2026/) and press **F11** for full screen.
- Games are listed in submission order. Use the search box to find a team.
- Click **▶ Play**, click once on the game, then press a key to start. Use **← All games** (bottom right) or the browser's Back button to go back.
- The first game takes a little longer to load (the browser downloads the Godot engine once, about 40 MB). The rest start quickly.
- Use an up-to-date **Chrome or Edge**, and check the sound beforehand.

## 6. Fixing problems

**The upload page says "Uploads aren't open yet."** `gallery/upload-config.js` is still empty. Do [step D](#d-connect-the-upload-page-2-min).

**Students get "The upload page is not set up yet."** A script property is missing. Check `GITHUB_TOKEN` and `CLASS_CODE` in Apps Script.

**Students get an error such as "Bad credentials" or "Resource not accessible".** The token has expired or lacks a permission. Create a new one ([step A](#a-create-a-github-token-5-min)) and replace `GITHUB_TOKEN`.

**The upload page doesn't work at all.** Collect the team's ZIP, team name, first names, title and description, then upload it yourself on the upload page.

**A game shows "Coming soon".** It was accepted but couldn't be exported. Open the latest **[Build game gallery](https://github.com/yche1364-YJ/Next-Gen-Summit-2026/actions/workflows/build-gallery.yml)** run: the summary lists which game failed and why. Usually it's a script error (the team should press F5, fix it and upload again) or the game starts in the wrong scene (the team should right-click their scene → **Set as Main Scene**, check with F5, and upload again). To rebuild by hand: **Run workflow**.

### Remove a game

Open the `submissions/` folder, open the game's folder, and delete both files (`game.zip`, `info.json`) with **`···` → Delete file**. The gallery rebuilds without it. Close its issue too.

### Clean up uploads

Uploaded ZIPs are stored in `pending/` until approval. Approving moves the ZIP into `submissions/`. ZIPs that were never approved (tests, wrong uploads) stay in `pending/`; you can delete them after the challenge.

### Good to know

- **Cost:** Google Apps Script, GitHub Actions and GitHub Pages are free.
- **Size:** all games share one copy of the Godot engine, so each adds only 1–3 MB.
- **Privacy:** uploaded ZIPs, issues and the gallery are **public**. Use first names only, and check your school's rules on publishing student work.
- **Safety:** only people with the class code can upload, and nothing is published until you approve it.

<details>
<summary>Files in this repository</summary>

| Path | Purpose |
|---|---|
| `README.md` | The student page (3 steps) |
| `docs/bouncy-guide.md` | Full Bouncy Pad guide |
| `docs/submit-guide.md` | Upload guide for students |
| `docs/bouncy-code/` | The Bouncy component's source files |
| `docs/teachers/upload-script.gs` | The Google Apps Script for the upload page |
| `downloads/` | The starter project ZIP and the Bouncy asset ZIP |
| `gallery/` | Gallery banner, upload page (`upload.html`) and its setting (`upload-config.js`) |
| `pending/` | Uploaded ZIPs waiting for approval |
| `submissions/` | One folder per approved game (`game.zip` + `info.json`) |
| `tools/accept_submission.py` | Reads a submission issue and checks the ZIP |
| `tools/build_gallery.py` | Exports the games and builds the gallery website |
| `.github/workflows/` | `accept-submission.yml` (runs on `approved`) and `build-gallery.yml` |

</details>

## 7. Original project, credits and license

- **Starter project:** [Moddable Platformer](https://github.com/endlessm/moddable-platformer) by [Endless Access](https://github.com/endlessm), released under the **MIT License**. Our version adds the **Bouncy Pad** component (`components/bouncy/`), a trampoline and a bouncy platform in the main level, and a bouncy wall. Everything else is unchanged.
- **Threadbare:** the open-source game made with Godot by Endless Access, [here](https://access.endlessstudios.com/games/threadbare).
- **Godot Engine:** [godotengine.org](https://godotengine.org/), MIT License. The [web editor](https://editor.godotengine.org/releases/latest/) is provided by the Godot project.
- **License for our additions:** the Bouncy component and the gallery tools are MIT too, so students may reuse and remix them. When sharing the project elsewhere, keep the original `LICENSE` file from Moddable Platformer inside the project.

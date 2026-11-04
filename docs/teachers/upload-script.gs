/**
 * Threadbare + Godot Challenge — game upload receiver (Google Apps Script)
 *
 * The upload page (upload.html on the gallery website) sends each team's ZIP
 * here. This script stores the ZIP in the GitHub repository and opens a
 * "submission" issue for the teacher to approve — so students never need a
 * GitHub account.
 *
 * Team members' FULL NAMES are private: they are saved only in a Google Sheet
 * in the teacher's Drive ("Threadbare submissions (private)", created on the
 * first upload, for microcredentials) and never sent to GitHub. Only the
 * nicknames are public.
 *
 * Setup instructions: docs/teachers/README.md → "Set up the upload page".
 *
 * Script properties (Project Settings → Script properties):
 *   GITHUB_TOKEN  a fine-grained GitHub token for this repository only,
 *                 with "Contents" and "Issues" set to Read and write
 *   CLASS_CODE    the code students type on the upload page (change it any time)
 *   REPO          optional, defaults to yche1364-YJ/Next-Gen-Summit-2026
 *   (SHEET_ID is filled in by the script itself.)
 */

var DEFAULT_REPO = 'yche1364-YJ/Next-Gen-Summit-2026';
var MAX_BYTES = 20 * 1024 * 1024; // 20 MB
var SHEET_NAME = 'Threadbare submissions (private)';
var SHEET_HEADERS = ['Uploaded at', 'Team name / number', 'Mentor', 'Game title',
  'Full names (private)', 'Nicknames (public)', 'Playtesting', 'GitHub issue', 'Play link (after approval)'];

function doPost(e) {
  try {
    var props = PropertiesService.getScriptProperties();
    var token = props.getProperty('GITHUB_TOKEN');
    var repo = props.getProperty('REPO') || DEFAULT_REPO;
    var classCode = String(props.getProperty('CLASS_CODE') || '').trim().toLowerCase();
    if (!token || !classCode) {
      return reply({ ok: false, error: 'The upload page is not set up yet. Please tell your teacher.' });
    }

    var data = JSON.parse(e.postData.contents);
    if (String(data.classCode || '').trim().toLowerCase() !== classCode) {
      return reply({ ok: false, error: 'Wrong class code. Check the code your teacher gave you.' });
    }

    var title = clean(data.title, 60);
    var team = clean(data.team, 60);
    var mentor = clean(data.mentor, 80);
    // New page: people = [{name (private), nickname (public)}].
    // An older page (still open in a browser) sends only "members".
    var legacy = !Array.isArray(data.people);
    var people = legacy ? [] : data.people.map(function (p) {
      return { name: clean(p && p.name, 80), nickname: clean(p && p.nickname, 30) };
    }).filter(function (p) { return p.name || p.nickname; }).slice(0, 6);
    if (!legacy) {
      if (!mentor || people.length === 0) {
        return reply({ ok: false, error: 'Please fill in every box.' });
      }
      for (var i = 0; i < people.length; i++) {
        if (!people[i].name || !people[i].nickname) {
          return reply({ ok: false, error: 'Each team member needs a full name and a nickname.' });
        }
        if (revealsName(people[i])) {
          return reply({ ok: false, error: 'Please use a nickname, not your real name.' });
        }
      }
    }
    var members = legacy ? clean(data.members, 120)
      : people.map(function (p) { return p.nickname; }).join(', ');
    var description = clean(data.description, 600);
    var controls = clean(data.controls, 300);
    var scene = clean(data.scene, 80) || 'main.tscn';
    if (!title || !team || !members || !description) {
      return reply({ ok: false, error: 'Please fill in every box.' });
    }

    var zipBase64 = String(data.zip || '');
    var bytes = Utilities.base64Decode(zipBase64);
    if (bytes.length < 100) {
      return reply({ ok: false, error: 'Please choose your game ZIP file.' });
    }
    if (bytes.length > MAX_BYTES) {
      return reply({ ok: false, error: 'The ZIP file is too big (max 20 MB).' });
    }
    if (!(bytes[0] === 0x50 && bytes[1] === 0x4b)) {
      return reply({ ok: false, error: 'That file is not a ZIP file. In Godot, use Project → Tools → Download Project Source.' });
    }

    var stamp = Utilities.formatDate(new Date(), 'UTC', 'yyyyMMdd-HHmmss');
    var path = 'pending/' + stamp + '-' + slugify(team) + '.zip';
    github(token, 'PUT', '/repos/' + repo + '/contents/' + path, {
      message: 'Upload game from ' + team,
      content: zipBase64
    });

    var rawUrl = 'https://github.com/' + repo + '/raw/main/' + path;
    var body = [
      '### Game title', title,
      '### Team name', team,
      '### Team members', members,
      '### Mentor', mentor || '_No response_',
      '### About the game', description,
      '### Controls', controls || '_No response_',
      '### Playtesting on the big screen', data.playtest ? 'Yes' : 'No',
      '### Scene to play', scene,
      '### Game ZIP file', '[' + slugify(team) + '.zip](' + rawUrl + ')',
      '### Checklist', '- [X] Submitted with the upload page (no GitHub account needed)'
    ].join('\n\n');
    var issue = github(token, 'POST', '/repos/' + repo + '/issues', {
      title: '[Game] ' + title,
      body: body,
      labels: data.playtest ? ['submission', 'playtesting'] : ['submission']
    });

    // Private record (full names) in the teacher's Google Sheet.
    if (!legacy) {
      var issueUrl = 'https://github.com/' + repo + '/issues/' + issue.number;
      privateSheet(props).appendRow([
        new Date(), team, mentor, title,
        people.map(function (p) { return p.name; }).join('\n'),
        members, data.playtest ? 'Yes' : 'No', issueUrl, playLink(repo, issue.number, title)
      ]);
    }

    return reply({ ok: true, number: issue.number });
  } catch (err) {
    return reply({ ok: false, error: 'Upload failed. Please try again, or tell your teacher. (' + err + ')' });
  }
}

// Opening the web app URL in a browser shows this — handy to check it's deployed.
function doGet() {
  return reply({ ok: true, message: 'Upload receiver is running.' });
}

// The game's address in the Gallery (works once the teacher approves it).
// Same rule as tools/accept_submission.py: <issue number>-<slug of title>.
function playLink(repo, number, title) {
  var parts = repo.split('/');
  var slug = String(title).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
    .slice(0, 40).replace(/^-+|-+$/g, '') || 'game';
  var id = ('00' + number).slice(-3) + '-' + slug;
  if (String(number).length > 3) id = number + '-' + slug;
  return 'https://' + parts[0].toLowerCase() + '.github.io/' + parts[1] + '/games/' + id + '/';
}

// True if the nickname is the person's full name or one part of it.
function revealsName(p) {
  var nick = p.nickname.toLowerCase().replace(/\s+/g, ' ').trim();
  var full = p.name.toLowerCase().replace(/\s+/g, ' ').trim();
  if (nick === full) return true;
  return full.split(' ').some(function (part) { return part.length > 1 && part === nick; });
}

// The private Google Sheet, created on the first upload. The lock stops two
// uploads at the same moment from creating two sheets.
function privateSheet(props) {
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var ss = null;
    var id = props.getProperty('SHEET_ID');
    try { if (id) ss = SpreadsheetApp.openById(id); } catch (e) { ss = null; }
    if (!ss) {
      ss = SpreadsheetApp.create(SHEET_NAME);
      var sh = ss.getSheets()[0];
      sh.setName('Submissions');
      sh.appendRow(SHEET_HEADERS);
      sh.setFrozenRows(1);
      sh.getRange(1, 1, 1, SHEET_HEADERS.length).setFontWeight('bold');
      props.setProperty('SHEET_ID', ss.getId());
    }
    return ss.getSheets()[0];
  } finally {
    lock.releaseLock();
  }
}

function clean(value, maxLength) {
  return String(value || '')
    .replace(/\r/g, '')
    .replace(/^\s*#+/gm, '')   // no markdown headings: they would confuse the form parser
    .replace(/[<>]/g, '')
    .trim()
    .slice(0, maxLength);
}

function slugify(text) {
  var slug = String(text).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  return (slug || 'team').slice(0, 40);
}

function github(token, method, path, payload) {
  // Many teams may upload at the same moment. GitHub can then answer
  // 409 (two saves at once), 5xx, or a short rate limit (403/429), so wait a
  // little and try again instead of failing.
  var lastError = '';
  for (var attempt = 1; attempt <= 8; attempt++) {
    var res = UrlFetchApp.fetch('https://api.github.com' + path, {
      method: method,
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      headers: {
        Authorization: 'Bearer ' + token,
        Accept: 'application/vnd.github+json'
      },
      muteHttpExceptions: true
    });
    var code = res.getResponseCode();
    var text = res.getContentText();
    if (code < 300) {
      return JSON.parse(text);
    }
    lastError = 'GitHub ' + code + ': ' + text.slice(0, 200);
    var retry = code === 409 || code === 429 || code >= 500 ||
      (code === 403 && /rate limit/i.test(text));
    if (!retry) break;
    Utilities.sleep(1500 * attempt + Math.floor(Math.random() * 2000));
  }
  throw new Error(lastError);
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

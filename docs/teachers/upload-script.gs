/**
 * Threadbare + Godot Challenge — game upload receiver (Google Apps Script)
 *
 * The upload page (upload.html on the gallery website) sends each team's ZIP
 * here. This script stores the ZIP in the GitHub repository and opens a
 * "submission" issue for the teacher to approve — so students never need a
 * GitHub account.
 *
 * Setup instructions: docs/teachers/README.md → "Set up the upload page".
 *
 * Script properties (Project Settings → Script properties):
 *   GITHUB_TOKEN  a fine-grained GitHub token for this repository only,
 *                 with "Contents" and "Issues" set to Read and write
 *   CLASS_CODE    the code students type on the upload page (change it any time)
 *   REPO          optional, defaults to yche1364-YJ/Next-Gen-Summit-2026
 */

var DEFAULT_REPO = 'yche1364-YJ/Next-Gen-Summit-2026';
var MAX_BYTES = 20 * 1024 * 1024; // 20 MB

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
    var members = clean(data.members, 120);
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
      '### About the game', description,
      '### Controls', controls || '_No response_',
      '### Scene to play', scene,
      '### Game ZIP file', '[' + slugify(team) + '.zip](' + rawUrl + ')',
      '### Checklist', '- [X] Submitted with the upload page (no GitHub account needed)'
    ].join('\n\n');
    var issue = github(token, 'POST', '/repos/' + repo + '/issues', {
      title: '[Game] ' + title,
      body: body,
      labels: ['submission']
    });

    return reply({ ok: true, number: issue.number });
  } catch (err) {
    return reply({ ok: false, error: 'Upload failed. Please try again, or tell your teacher. (' + err + ')' });
  }
}

// Opening the web app URL in a browser shows this — handy to check it's deployed.
function doGet() {
  return reply({ ok: true, message: 'Upload receiver is running.' });
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
  if (code >= 300) {
    throw new Error('GitHub ' + code + ': ' + res.getContentText().slice(0, 200));
  }
  return JSON.parse(res.getContentText());
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

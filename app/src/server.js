const express = require("express");
const cookieParser = require("cookie-parser");

const app = express();
const PORT = process.env.PORT || 3000;
const API_BASE_URL = process.env.API_BASE_URL || "http://api.acme.local:3000";
const SECURITY_MODE = process.env.SECURITY_MODE || "vulnerable";
const IS_REMEDIATED = SECURITY_MODE === "remediated";

app.use(express.urlencoded({ extended: false }));
app.use(express.json());
app.use(cookieParser());

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function parseToken(token) {
  if (!token) {
    return null;
  }

  try {
    const [, payload] = token.split(".");
    return JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
  } catch (error) {
    return null;
  }
}

async function readJson(response) {
  const text = await response.text();

  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch (error) {
    return { raw: text };
  }
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const data = await readJson(response);

  if (!response.ok) {
    throw new Error(data.error || data.raw || `${response.status} ${response.statusText}`);
  }

  return data;
}

async function loadComments() {
  try {
    const data = await apiRequest("/api/comments");
    return data.comments || [];
  } catch (error) {
    return [];
  }
}

function renderHome({ tokenPayload, comments, notice, error }) {
  const renderValue = (value) => (IS_REMEDIATED ? escapeHtml(value ?? "") : String(value ?? ""));
  const renderCommentValue = (value) => (IS_REMEDIATED ? String(value ?? "") : String(value ?? ""));
  const sessionCard = tokenPayload
    ? `
      <section class="panel">
        <h2>Current Session</h2>
        <p><strong>User:</strong> ${renderValue(tokenPayload.username)}</p>
        <p><strong>Role from token:</strong> ${renderValue(tokenPayload.role)}</p>
        <p><strong>User ID:</strong> ${renderValue(tokenPayload.sub)}</p>
        <p>${
          IS_REMEDIATED
            ? "Remediated mode sets the session cookie as HttpOnly and stricter than the training baseline."
            : "This lab intentionally stores the JWT in a JavaScript-readable cookie named <code>session</code>."
        }</p>
      </section>
    `
    : `
      <section class="panel">
        <h2>Current Session</h2>
        <p>No active session yet. Try <code>alice / welcome123</code> or <code>admin / adminpass</code>.</p>
      </section>
    `;

  const commentList = comments.length
    ? comments
        .map(
          (comment) => `
            <article class="comment">
              <div class="comment-meta">
                <strong>${renderCommentValue(comment.author)}</strong>
                <span>${renderValue(comment.created_at)}</span>
              </div>
              <div class="comment-body">${renderCommentValue(comment.content)}</div>
            </article>
          `
        )
        .join("")
    : "<p class=\"empty\">No comments yet.</p>";

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Acme Employee Hub</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 2rem;
        background: #eef2f7;
        color: #192231;
      }
      h1, h2 {
        margin-top: 0;
      }
      .layout {
        display: grid;
        gap: 1rem;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      }
      .panel {
        background: #fff;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(25, 34, 49, 0.08);
      }
      label {
        display: block;
        margin: 0.5rem 0 0.25rem;
        font-weight: 600;
      }
      input, textarea, button {
        width: 100%;
        box-sizing: border-box;
        padding: 0.75rem;
        border-radius: 8px;
        border: 1px solid #ccd5e0;
        margin-bottom: 0.75rem;
      }
      button {
        background: #0c6cf2;
        color: #fff;
        border: none;
        cursor: pointer;
      }
      .notice {
        padding: 0.75rem 1rem;
        background: #daf5e6;
        border-radius: 8px;
      }
      .error {
        padding: 0.75rem 1rem;
        background: #ffdada;
        border-radius: 8px;
      }
      .comment {
        padding: 0.75rem;
        border: 1px solid #dde6f2;
        border-radius: 8px;
        margin-bottom: 0.75rem;
        background: #fbfdff;
      }
      .comment-meta {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 0.5rem;
      }
      .link-list a {
        display: inline-block;
        margin-right: 1rem;
        margin-bottom: 0.5rem;
      }
      code {
        background: #f4f7fb;
        padding: 0.15rem 0.35rem;
        border-radius: 4px;
      }
    </style>
  </head>
  <body>
    <h1>Acme Employee Hub</h1>
    <p>This intentionally vulnerable portal mirrors a company front end that talks to a separate API and admin surface.</p>
    ${notice ? `<div class="notice">${renderValue(notice)}</div>` : ""}
    ${error ? `<div class="error">${renderValue(error)}</div>` : ""}
    <div class="layout">
      <section class="panel">
        <h2>Login</h2>
        <form method="post" action="/login">
          <label for="username">Username</label>
          <input id="username" name="username" value="alice">
          <label for="password">Password</label>
          <input id="password" name="password" type="password" value="welcome123">
          <button type="submit">Get JWT Session</button>
        </form>
        <a href="/logout">Log out</a>
      </section>

      ${sessionCard}

      <section class="panel">
        <h2>Comment Feed</h2>
        <form method="post" action="/comment">
          <label for="displayName">Display Name</label>
          <input id="displayName" name="displayName" value="alice">
          <label for="content">Comment / Profile Update</label>
          <textarea id="content" name="content" rows="5" placeholder="Post an announcement or test payload"></textarea>
          <button type="submit">Post Comment</button>
        </form>
      </section>

      <section class="panel">
        <h2>Profile Preview</h2>
        <p>This preview route reflects the <code>bio</code> field directly into the page.</p>
        <form method="get" action="/profile">
          <label for="bio">Profile Bio</label>
          <textarea id="bio" name="bio" rows="4" placeholder="Tell your team something about you"></textarea>
          <button type="submit">Preview Profile</button>
        </form>
      </section>
    </div>

    <section class="panel" style="margin-top: 1rem;">
      <h2>Internal Service Links</h2>
      <div class="link-list">
        <a href="http://api.acme.local:8081/api/user?id=1">api.acme.local user 1</a>
        <a href="http://api.acme.local:8081/api/user?id=3">api.acme.local user 3</a>
        <a href="http://admin.acme.local:8082/">admin.acme.local</a>
        <a href="http://storage.acme.local:9001/">storage.acme.local console</a>
        <a href="http://storage.acme.local:9000/public-assets/security-note.txt">public MinIO object</a>
      </div>
    </section>

    <section class="panel" style="margin-top: 1rem;">
      <h2>Latest Comments</h2>
      ${commentList}
    </section>
  </body>
</html>`;
}

app.get("/", async (req, res) => {
  const comments = await loadComments();
  const tokenPayload = parseToken(req.cookies.session);
  res.send(
    renderHome({
      tokenPayload,
      comments,
      notice: req.query.notice || "",
      error: req.query.error || ""
    })
  );
});

app.post("/login", async (req, res) => {
  try {
    const data = await apiRequest("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: req.body.username,
        password: req.body.password
      })
    });

    res.cookie("session", data.token, {
      httpOnly: IS_REMEDIATED,
      sameSite: IS_REMEDIATED ? "strict" : "lax"
    });

    res.redirect(
      `/?notice=${encodeURIComponent(
        IS_REMEDIATED
          ? "Logged in. The session cookie is now HttpOnly in remediated mode."
          : "Logged in. The JWT cookie is readable by JavaScript."
      )}`
    );
  } catch (error) {
    res.redirect(`/?error=${encodeURIComponent(error.message)}`);
  }
});

app.post("/comment", async (req, res) => {
  try {
    const headers = { "Content-Type": "application/json" };

    if (req.cookies.session) {
      headers.Authorization = `Bearer ${req.cookies.session}`;
    }

    await apiRequest("/comment", {
      method: "POST",
      headers,
      body: JSON.stringify({
        displayName: req.body.displayName,
        content: req.body.content
      })
    });

    res.redirect("/?notice=Comment stored.");
  } catch (error) {
    res.redirect(`/?error=${encodeURIComponent(error.message)}`);
  }
});

app.get("/logout", (_req, res) => {
  res.clearCookie("session");
  res.redirect("/?notice=Logged out.");
});

app.get("/profile", (req, res) => {
  const bio = req.query.bio || "";
  const renderedBio = IS_REMEDIATED ? escapeHtml(bio) : bio;
  const guidance = IS_REMEDIATED
    ? "Your profile bio is rendered below with HTML escaping in remediated mode."
    : "Your profile bio is rendered below without sanitization.";

  res.send(`<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Acme Profile Preview</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        margin: 2rem;
        background: #f5f8fc;
      }
      .card {
        max-width: 720px;
        background: #fff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(25, 34, 49, 0.08);
      }
      .preview {
        margin-top: 1rem;
        padding: 1rem;
        border: 1px solid #d5dbe5;
        border-radius: 8px;
      }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Profile Preview</h1>
      <p>${guidance}</p>
      <div class="preview">${renderedBio}</div>
      <p><a href="/">Back to Acme Employee Hub</a></p>
    </div>
  </body>
</html>`);
});

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "app" });
});

app.listen(PORT, () => {
  console.log(`Frontend listening on port ${PORT}`);
});

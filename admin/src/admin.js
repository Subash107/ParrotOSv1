const express = require("express");
const jwt = require("jsonwebtoken");
const mysql = require("mysql2/promise");

const app = express();
const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || "secret123";
const SECURITY_MODE = process.env.SECURITY_MODE || "vulnerable";
const IS_REMEDIATED = SECURITY_MODE === "remediated";

const pool = mysql.createPool({
  host: process.env.DB_HOST || "database",
  port: Number(process.env.DB_PORT || 3306),
  user: process.env.DB_USER || "acme",
  password: process.env.DB_PASSWORD || "acmepass",
  database: process.env.DB_NAME || "acme",
  waitForConnections: true,
  connectionLimit: 10
});

app.use(express.json());
app.use(express.urlencoded({ extended: false }));

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getBearerTokenPayload(req) {
  const authHeader = req.get("authorization") || "";

  if (!authHeader.toLowerCase().startsWith("bearer ")) {
    return null;
  }

  try {
    return jwt.verify(authHeader.slice(7), JWT_SECRET);
  } catch (error) {
    return null;
  }
}

async function getAuthenticatedAdmin(req) {
  const payload = getBearerTokenPayload(req);

  if (!payload) {
    return null;
  }

  const [rows] = await pool.query(
    "SELECT id, username, role, email, department FROM users WHERE id = ? LIMIT 1",
    [payload.sub]
  );

  if (!rows.length || rows[0].role !== "admin") {
    return null;
  }

  return {
    sub: rows[0].id,
    username: rows[0].username,
    role: rows[0].role,
    email: rows[0].email,
    department: rows[0].department,
    tokenPayload: payload
  };
}

app.use(async (req, res, next) => {
  if (req.path === "/health") {
    return next();
  }

  if (!IS_REMEDIATED) {
    if ((req.get("role") || "").toLowerCase() !== "admin") {
      return res.status(403).send("Missing required header: role: admin");
    }

    return next();
  }

  const adminUser = await getAuthenticatedAdmin(req);

  if (!adminUser) {
    return res.status(401).send("Provide a valid admin bearer token in remediated mode.");
  }

  req.authUser = adminUser;
  next();
});

function renderDashboard(users, comments, authUser) {
  const renderValue = (value) => escapeHtml(value ?? "");
  const userRows = users
    .map(
      (user) => `
        <tr>
          <td>${renderValue(user.id)}</td>
          <td>${renderValue(user.username)}</td>
          <td>${renderValue(user.email)}</td>
          <td>${renderValue(user.password || "redacted")}</td>
          <td>${renderValue(user.role)}</td>
          <td>${renderValue(user.department)}</td>
          <td>${renderValue(user.api_key || "redacted")}</td>
        </tr>
      `
    )
    .join("");

  const commentRows = comments
    .map(
      (comment) => `
        <tr>
          <td>${renderValue(comment.id)}</td>
          <td>${renderValue(comment.author)}</td>
          <td>${renderValue(comment.content)}</td>
          <td>${renderValue(comment.created_at)}</td>
        </tr>
      `
    )
    .join("");

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Acme Admin Console</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 2rem;
        background: #111827;
        color: #f9fafb;
      }
      .panel {
        background: #1f2937;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
      }
      th, td {
        border: 1px solid #374151;
        padding: 0.65rem;
        text-align: left;
        vertical-align: top;
      }
      a {
        color: #93c5fd;
      }
      code {
        background: #374151;
        padding: 0.15rem 0.35rem;
        border-radius: 4px;
      }
    </style>
  </head>
  <body>
    <div class="panel">
      <h1>Acme Admin Console</h1>
      <p>${
        IS_REMEDIATED
          ? `Authenticated via verified admin token for ${renderValue(authUser && authUser.username)}.`
          : "This dashboard trusts the request header <code>role: admin</code> and performs no other authentication."
      }</p>
      <p>Storage console: <a href="${process.env.STORAGE_CONSOLE_URL}">${process.env.STORAGE_CONSOLE_URL}</a></p>
      <p>Storage credentials: <code>${
        IS_REMEDIATED ? "redacted" : process.env.STORAGE_ACCESS_KEY
      }</code> / <code>${IS_REMEDIATED ? "redacted" : process.env.STORAGE_SECRET_KEY}</code></p>
      <p>JSON export endpoint: <a href="/export">/export</a></p>
    </div>

    <div class="panel">
      <h2>User Directory</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Username</th>
            <th>Email</th>
            <th>Password</th>
            <th>Role</th>
            <th>Department</th>
            <th>API Key</th>
          </tr>
        </thead>
        <tbody>${userRows}</tbody>
      </table>
    </div>

    <div class="panel">
      <h2>Recent Comments</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Author</th>
            <th>Content</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>${commentRows}</tbody>
      </table>
    </div>
  </body>
</html>`;
}

app.get("/", async (_req, res) => {
  const [users] = await pool.query(
    IS_REMEDIATED
      ? "SELECT id, username, email, role, department FROM users ORDER BY id"
      : "SELECT id, username, email, password, role, department, api_key FROM users ORDER BY id"
  );
  const [comments] = await pool.query(
    "SELECT id, author, content, created_at FROM comments ORDER BY created_at DESC LIMIT 20"
  );

  res.send(
    renderDashboard(
      users,
      comments,
      _req.authUser
    )
  );
});

app.get("/export", async (_req, res) => {
  const [users] = await pool.query(
    IS_REMEDIATED
      ? "SELECT id, username, email, role, department, bio FROM users ORDER BY id"
      : "SELECT id, username, email, password, role, department, api_key, bio FROM users ORDER BY id"
  );
  const [comments] = await pool.query(
    "SELECT id, user_id, author, content, created_at FROM comments ORDER BY created_at DESC LIMIT 50"
  );

  res.json({
    storage: IS_REMEDIATED
      ? {
          consoleUrl: process.env.STORAGE_CONSOLE_URL,
          publicBucket: "public-assets",
          access: "restricted"
        }
      : {
          consoleUrl: process.env.STORAGE_CONSOLE_URL,
          accessKey: process.env.STORAGE_ACCESS_KEY,
          secretKey: process.env.STORAGE_SECRET_KEY,
          publicBucket: "public-assets"
        },
    users,
    comments: IS_REMEDIATED
      ? comments.map((comment) => ({
          ...comment,
          author: escapeHtml(comment.author),
          content: escapeHtml(comment.content)
        }))
      : comments
  });
});

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "admin" });
});

app.use((error, _req, res, _next) => {
  console.error(error);
  res.status(500).send(`Admin failure: ${error.message}`);
});

app.listen(PORT, () => {
  console.log(`Admin console listening on port ${PORT}`);
});

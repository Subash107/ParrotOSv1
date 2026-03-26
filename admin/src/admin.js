const express = require("express");
const mysql = require("mysql2/promise");

const app = express();
const PORT = process.env.PORT || 3000;

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

app.use((req, res, next) => {
  if (req.path === "/health") {
    return next();
  }

  if ((req.get("role") || "").toLowerCase() !== "admin") {
    return res.status(403).send("Missing required header: role: admin");
  }

  next();
});

function renderDashboard(users, comments) {
  const userRows = users
    .map(
      (user) => `
        <tr>
          <td>${user.id}</td>
          <td>${user.username}</td>
          <td>${user.email}</td>
          <td>${user.password}</td>
          <td>${user.role}</td>
          <td>${user.department}</td>
          <td>${user.api_key}</td>
        </tr>
      `
    )
    .join("");

  const commentRows = comments
    .map(
      (comment) => `
        <tr>
          <td>${comment.id}</td>
          <td>${comment.author}</td>
          <td>${comment.content}</td>
          <td>${comment.created_at}</td>
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
      <p>This dashboard trusts the request header <code>role: admin</code> and performs no other authentication.</p>
      <p>Storage console: <a href="${process.env.STORAGE_CONSOLE_URL}">${process.env.STORAGE_CONSOLE_URL}</a></p>
      <p>Storage credentials: <code>${process.env.STORAGE_ACCESS_KEY}</code> / <code>${process.env.STORAGE_SECRET_KEY}</code></p>
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
    "SELECT id, username, email, password, role, department, api_key FROM users ORDER BY id"
  );
  const [comments] = await pool.query(
    "SELECT id, author, content, created_at FROM comments ORDER BY created_at DESC LIMIT 20"
  );

  res.send(renderDashboard(users, comments));
});

app.get("/export", async (_req, res) => {
  const [users] = await pool.query(
    "SELECT id, username, email, password, role, department, api_key, bio FROM users ORDER BY id"
  );
  const [comments] = await pool.query(
    "SELECT id, user_id, author, content, created_at FROM comments ORDER BY created_at DESC LIMIT 50"
  );

  res.json({
    storage: {
      consoleUrl: process.env.STORAGE_CONSOLE_URL,
      accessKey: process.env.STORAGE_ACCESS_KEY,
      secretKey: process.env.STORAGE_SECRET_KEY,
      publicBucket: "public-assets"
    },
    users,
    comments
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

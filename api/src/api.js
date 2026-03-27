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

  const token = authHeader.slice(7);

  try {
    return jwt.verify(token, JWT_SECRET);
  } catch (error) {
    return null;
  }
}

async function getAuthenticatedUser(req) {
  const payload = getBearerTokenPayload(req);

  if (!payload) {
    return null;
  }

  if (!IS_REMEDIATED) {
    return payload;
  }

  const [rows] = await pool.query(
    "SELECT id, username, role, email, department FROM users WHERE id = ? LIMIT 1",
    [payload.sub]
  );

  if (!rows.length) {
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

app.post("/login", async (req, res) => {
  const { username, password } = req.body;

  if (!username || !password) {
    return res.status(400).json({ error: "username and password are required" });
  }

  const [rows] = await pool.query(
    "SELECT id, username, role, email, department FROM users WHERE username = ? AND password = ? LIMIT 1",
    [username, password]
  );

  if (!rows.length) {
    return res.status(401).json({ error: "invalid credentials" });
  }

  const user = rows[0];
  const token = jwt.sign(
    {
      sub: user.id,
      username: user.username,
      role: user.role,
      department: user.department
    },
    JWT_SECRET,
    IS_REMEDIATED ? { expiresIn: "15m" } : undefined
  );

  res.json({
    token,
    user,
    note: IS_REMEDIATED
      ? "Remediated mode issues expiring tokens and verifies authorization server-side."
      : "This intentionally weak token has no expiration and trusts the embedded role claim."
  });
});

app.get("/api/user", async (req, res) => {
  const requestedId = Number(req.query.id || 1);

  if (IS_REMEDIATED) {
    const user = await getAuthenticatedUser(req);

    if (!user) {
      return res.status(401).json({ error: "authentication required" });
    }

    if (user.role !== "admin" && requestedId !== user.sub) {
      return res.status(403).json({ error: "forbidden" });
    }

    const [safeRows] = await pool.query(
      "SELECT id, username, email, role, department, bio, created_at FROM users WHERE id = ? LIMIT 1",
      [requestedId]
    );

    if (!safeRows.length) {
      return res.status(404).json({ error: "user not found" });
    }

    return res.json(safeRows[0]);
  }

  const [rows] = await pool.query(
    "SELECT id, username, email, password, role, department, api_key, bio, created_at FROM users WHERE id = ? LIMIT 1",
    [requestedId]
  );

  if (!rows.length) {
    return res.status(404).json({ error: "user not found" });
  }

  res.json(rows[0]);
});

app.get("/api/admin", async (req, res) => {
  const payload = await getAuthenticatedUser(req);

  if (!payload || payload.role !== "admin") {
    return res.status(403).json({ error: "admin role required" });
  }

  const [users] = await pool.query(
    IS_REMEDIATED
      ? "SELECT id, username, email, role, department FROM users ORDER BY id"
      : "SELECT id, username, email, role, department, api_key FROM users ORDER BY id"
  );
  const [comments] = await pool.query(
    "SELECT id, author, content, created_at FROM comments ORDER BY created_at DESC LIMIT 15"
  );

  res.json({
    requestedBy: payload,
    infrastructure: IS_REMEDIATED
      ? {
          storageEndpoint: process.env.STORAGE_ENDPOINT,
          storageConsoleUrl: process.env.STORAGE_CONSOLE_URL,
          deploymentNote: "Remediated mode withholds storage secrets from the admin API."
        }
      : {
          storageEndpoint: process.env.STORAGE_ENDPOINT,
          storageConsoleUrl: process.env.STORAGE_CONSOLE_URL,
          minioAccessKey: process.env.MINIO_ROOT_USER,
          minioSecretKey: process.env.MINIO_ROOT_PASSWORD,
          deploymentNote: "Vendor backup bucket remains public until next quarter."
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

app.post("/comment", async (req, res) => {
  const payload = await getAuthenticatedUser(req);
  const content = (req.body.content || "").trim();
  const displayName = (req.body.displayName || "").trim() || "guest";

  if (!content) {
    return res.status(400).json({ error: "comment content is required" });
  }

  const author = payload ? payload.username : displayName;
  const userId = payload ? payload.sub : null;
  const storedContent = content;

  const [result] = await pool.query(
    "INSERT INTO comments (user_id, author, content) VALUES (?, ?, ?)",
    [userId, author, storedContent]
  );

  const [rows] = await pool.query(
    "SELECT id, author, content, created_at FROM comments WHERE id = ? LIMIT 1",
    [result.insertId]
  );

  res.status(201).json({
    message: "comment stored",
    comment: IS_REMEDIATED
      ? {
          ...rows[0],
          author: escapeHtml(rows[0].author),
          content: escapeHtml(rows[0].content)
        }
      : rows[0]
  });
});

app.get("/api/comments", async (_req, res) => {
  const [rows] = await pool.query(
    "SELECT id, author, content, created_at FROM comments ORDER BY created_at DESC LIMIT 20"
  );

  res.json({
    comments: IS_REMEDIATED
      ? rows.map((comment) => ({
          ...comment,
          author: escapeHtml(comment.author),
          content: escapeHtml(comment.content)
        }))
      : rows
  });
});

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "api" });
});

app.use((error, _req, res, _next) => {
  console.error(error);
  res.status(500).json({
    error: "backend failure",
    detail: error.message
  });
});

app.listen(PORT, () => {
  console.log(`API listening on port ${PORT}`);
});

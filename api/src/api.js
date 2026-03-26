const express = require("express");
const jwt = require("jsonwebtoken");
const mysql = require("mysql2/promise");

const app = express();
const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || "secret123";

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

function getTokenPayload(req) {
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
    JWT_SECRET
  );

  res.json({
    token,
    user,
    note: "This intentionally weak token has no expiration and trusts the embedded role claim."
  });
});

app.get("/api/user", async (req, res) => {
  const requestedId = Number(req.query.id || 1);

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
  const payload = getTokenPayload(req);

  if (!payload || payload.role !== "admin") {
    return res.status(403).json({ error: "admin role required" });
  }

  const [users] = await pool.query(
    "SELECT id, username, email, role, department, api_key FROM users ORDER BY id"
  );
  const [comments] = await pool.query(
    "SELECT id, author, content, created_at FROM comments ORDER BY created_at DESC LIMIT 15"
  );

  res.json({
    requestedBy: payload,
    infrastructure: {
      storageEndpoint: process.env.STORAGE_ENDPOINT,
      storageConsoleUrl: process.env.STORAGE_CONSOLE_URL,
      minioAccessKey: process.env.MINIO_ROOT_USER,
      minioSecretKey: process.env.MINIO_ROOT_PASSWORD,
      deploymentNote: "Vendor backup bucket remains public until next quarter."
    },
    users,
    comments
  });
});

app.post("/comment", async (req, res) => {
  const payload = getTokenPayload(req);
  const content = (req.body.content || "").trim();
  const displayName = (req.body.displayName || "").trim() || "guest";

  if (!content) {
    return res.status(400).json({ error: "comment content is required" });
  }

  const author = payload ? payload.username : displayName;
  const userId = payload ? payload.sub : null;

  const [result] = await pool.query(
    "INSERT INTO comments (user_id, author, content) VALUES (?, ?, ?)",
    [userId, author, content]
  );

  const [rows] = await pool.query(
    "SELECT id, author, content, created_at FROM comments WHERE id = ? LIMIT 1",
    [result.insertId]
  );

  res.status(201).json({
    message: "comment stored",
    comment: rows[0]
  });
});

app.get("/api/comments", async (_req, res) => {
  const [rows] = await pool.query(
    "SELECT id, author, content, created_at FROM comments ORDER BY created_at DESC LIMIT 20"
  );

  res.json({ comments: rows });
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

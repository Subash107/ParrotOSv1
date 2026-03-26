CREATE DATABASE IF NOT EXISTS acme;
USE acme;

DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'user',
  department VARCHAR(64) NOT NULL,
  api_key VARCHAR(128) NOT NULL,
  bio TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE comments (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NULL,
  author VARCHAR(64) NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_comments_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE SET NULL
);

INSERT INTO users (username, password, email, role, department, api_key, bio) VALUES
  ('alice', 'welcome123', 'alice@acme.local', 'user', 'engineering', 'ENG-ALICE-7F2', 'Frontend engineer. Loves reusable components.'),
  ('bob', 'hunter2', 'bob@acme.local', 'user', 'finance', 'FIN-BOB-9381', 'Finance analyst with access to vendor spend sheets.'),
  ('admin', 'adminpass', 'admin@acme.local', 'admin', 'security', 'ADM-ROOT-KEY-2026', 'Security lead. Owns infrastructure reviews.');

INSERT INTO comments (user_id, author, content) VALUES
  (1, 'alice', 'Reminder: the vendor handoff file now lives in the public-assets bucket for quick sharing.'),
  (2, 'bob', '<strong>Quarter close</strong> is next Friday. Upload updated spreadsheets before noon.'),
  (3, 'admin', 'Please stop sharing screenshots of the admin portal in chat.');

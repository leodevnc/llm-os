"""Versioned virtual files; paths never reach the host filesystem."""

import re


def path(value, prefix=False):
    if not isinstance(value, str) or len(value) > 180:
        raise ValueError("Invalid virtual path")
    if prefix and value == "/":
        return value
    if not value.startswith("/") or "//" in value or "\\" in value:
        raise ValueError("Use an absolute virtual path")
    parts = value[1:].rstrip("/").split("/")
    if any(part in {"", ".", ".."} or not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts):
        raise ValueError("Invalid virtual path component")
    if not prefix and value.endswith("/"):
        raise ValueError("File path cannot end in a slash")
    return value


def initialize(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS vfs_files(path TEXT PRIMARY KEY,content TEXT NOT NULL,version INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS vfs_versions(
            path TEXT NOT NULL,version INTEGER NOT NULL,content TEXT NOT NULL,
            task_id TEXT NOT NULL,step INTEGER NOT NULL,
            PRIMARY KEY(path,version),UNIQUE(task_id,step));
    """)


def read(db, name):
    path(name)
    row = db.execute("SELECT * FROM vfs_files WHERE path=?", (name,)).fetchone()
    return dict(row) if row else {"error": "Virtual file not found", "path": name}


def listing(db, prefix):
    path(prefix, prefix=True)
    # Python filtering avoids SQL wildcard interpretation of underscores.
    return [dict(row) for row in db.execute("SELECT path,version,length(content) AS chars FROM vfs_files ORDER BY path")
            if row["path"].startswith(prefix)][:100]


def version(db, name):
    path(name)
    row = db.execute("SELECT version FROM vfs_files WHERE path=?", (name,)).fetchone()
    return row[0] if row else 0


def write(db, name, content, task_id, step):
    path(name)
    revision = version(db, name) + 1
    db.execute("INSERT INTO vfs_files VALUES(?,?,?) ON CONFLICT(path) DO UPDATE SET content=excluded.content,version=excluded.version",
               (name, content, revision))
    db.execute("INSERT INTO vfs_versions VALUES(?,?,?,?,?)", (name, revision, content, task_id, step))
    return {"path": name, "version": revision, "chars": len(content)}

"""Model-addressable document pages backed by a task's immutable snapshot."""

BUDGET = 12000


def initialize(db):
    db.execute("""CREATE TABLE IF NOT EXISTS context_pages(
        task_id TEXT NOT NULL,document_id TEXT NOT NULL,touched INTEGER NOT NULL,
        PRIMARY KEY(task_id,document_id))""")


def resident(db, task_id, snapshot):
    rows = db.execute("SELECT document_id,touched FROM context_pages WHERE task_id=? ORDER BY touched,document_id", (task_id,))
    return [{**snapshot[row["document_id"]], "touched": row["touched"]} for row in rows]


def info(db, task_id, snapshot):
    pages = resident(db, task_id, snapshot)
    return {"budget_chars": BUDGET, "used_chars": sum(len(page["content"]) for page in pages),
            "pages": [{"document_id": page["id"], "title": page["title"], "chars": len(page["content"])} for page in pages]}


def page_in(db, task_id, snapshot, document_id, step):
    if document_id not in snapshot:
        return {"error": "Document not in this task snapshot"}
    needed = len(snapshot[document_id]["content"])
    if needed > BUDGET:
        return {"error": "Document exceeds the resident-page budget"}
    pages = resident(db, task_id, snapshot)
    used = sum(len(page["content"]) for page in pages if page["id"] != document_id)
    evicted = []
    for page in pages:
        if used + needed <= BUDGET:
            break
        if page["id"] != document_id:
            db.execute("DELETE FROM context_pages WHERE task_id=? AND document_id=?", (task_id, page["id"]))
            used -= len(page["content"])
            evicted.append(page["id"])
    db.execute("INSERT INTO context_pages VALUES(?,?,?) ON CONFLICT(task_id,document_id) DO UPDATE SET touched=excluded.touched",
               (task_id, document_id, step))
    return {"loaded": document_id, "evicted": evicted, **info(db, task_id, snapshot)}


def page_out(db, task_id, snapshot, document_id):
    cursor = db.execute("DELETE FROM context_pages WHERE task_id=? AND document_id=?", (task_id, document_id))
    return {"unloaded": document_id, "was_resident": cursor.rowcount == 1, **info(db, task_id, snapshot)}

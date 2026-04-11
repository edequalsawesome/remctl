"""Shared reminder serialization helpers for RemCTL."""

from __future__ import annotations


def preload_extras(db, pks):
    """Batch-load subtask counts and hashtags to avoid N+1 queries."""
    if not pks:
        return {}, {}
    placeholders = ",".join("?" * len(pks))
    subtask_rows = db.execute(
        f"SELECT ZPARENTREMINDER, COUNT(*) FROM ZREMCDREMINDER "
        f"WHERE ZPARENTREMINDER IN ({placeholders}) AND ZMARKEDFORDELETION = 0 "
        f"AND ZCOMPLETED = 0 GROUP BY ZPARENTREMINDER",
        pks,
    ).fetchall()
    subtask_counts = {row[0]: row[1] for row in subtask_rows}
    hashtag_rows = db.execute(
        f"SELECT o.ZREMINDER3, h.ZNAME FROM ZREMCDOBJECT o "
        f"JOIN ZREMCDHASHTAGLABEL h ON o.ZHASHTAGLABEL = h.Z_PK "
        f"WHERE o.ZREMINDER3 IN ({placeholders})",
        pks,
    ).fetchall()
    hashtags = {}
    for row in hashtag_rows:
        hashtags.setdefault(row[0], []).append(row[1])
    return subtask_counts, hashtags


def serialize_reminder(
    row,
    *,
    ts,
    priority_names,
    db=None,
    section=None,
    subtask_counts=None,
    hashtags=None,
    rich_link_resolver=None,
    fallback_subtask_count=None,
    fallback_hashtags=None,
):
    """Convert a reminder row to a JSON-serializable dict."""
    subtask_counts = subtask_counts or {}
    hashtags = hashtags or {}

    subtask_count = subtask_counts.get(row["Z_PK"])
    if subtask_count is None:
        if db is not None and fallback_subtask_count is not None:
            subtask_count = fallback_subtask_count(db, row["Z_PK"])
        else:
            subtask_count = 0

    tags = hashtags.get(row["Z_PK"])
    if tags is None:
        if db is not None and fallback_hashtags is not None:
            tags = fallback_hashtags(db, row["Z_PK"])
        else:
            tags = []

    reminder = {
        "id": row["Z_PK"],
        "title": row["ZTITLE"],
        "list": row["list_name"],
        "completed": bool(row["ZCOMPLETED"]),
        "flagged": bool(row["ZFLAGGED"]),
        "priority": priority_names.get(row["ZPRIORITY"] or 0, "none"),
        "subtaskCount": subtask_count,
        "isSubtask": bool(row["ZPARENTREMINDER"]),
    }
    if section:
        reminder["section"] = section
    if row["ZNOTES"]:
        reminder["notes"] = row["ZNOTES"]

    url = row["ZICSURL"]
    if not url and db is not None and rich_link_resolver is not None:
        url = rich_link_resolver(db, row["Z_PK"])
    if url:
        reminder["url"] = url

    if row["ZDUEDATE"]:
        reminder["dueDate"] = ts(row["ZDUEDATE"]).isoformat()
    if row["ZCREATIONDATE"]:
        reminder["createdDate"] = ts(row["ZCREATIONDATE"]).isoformat()
    if row["ZCOMPLETIONDATE"]:
        reminder["completionDate"] = ts(row["ZCOMPLETIONDATE"]).isoformat()
    if row["ZPARENTREMINDER"]:
        reminder["parentID"] = row["ZPARENTREMINDER"]
    if tags:
        reminder["tags"] = tags
    if row["ZCKIDENTIFIER"]:
        reminder["deepLink"] = f"x-apple-reminderkit://REMCDReminder/{row['ZCKIDENTIFIER']}"
    return reminder


def serialize_reminders(
    rows,
    *,
    ts,
    priority_names,
    db=None,
    memberships=None,
    rich_link_resolver=None,
    fallback_subtask_count=None,
    fallback_hashtags=None,
):
    """Convert reminder rows with shared preloaded metadata."""
    subtask_counts, hashtags = preload_extras(db, [row["Z_PK"] for row in rows]) if db else ({}, {})
    memberships = memberships or {}
    return [
        serialize_reminder(
            row,
            ts=ts,
            priority_names=priority_names,
            db=db,
            section=memberships.get(row["ZCKIDENTIFIER"]),
            subtask_counts=subtask_counts,
            hashtags=hashtags,
            rich_link_resolver=rich_link_resolver,
            fallback_subtask_count=fallback_subtask_count,
            fallback_hashtags=fallback_hashtags,
        )
        for row in rows
    ]

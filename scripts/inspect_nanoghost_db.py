from __future__ import annotations

import sys
from pathlib import Path

import sqlite3


def main() -> int:
    name = (sys.argv[1] if len(sys.argv) > 1 else "cc").strip()
    do_probe = "--probe-write" in sys.argv[2:]
    inst = Path.home() / ".nanoghost" / "instances" / name
    db = inst / "data" / "agent_data.db"
    if not db.exists():
        db = inst / "data" / "agent.db"
    print("instance:", name)
    print("instance_dir:", inst)
    print("db:", db)
    if not db.exists():
        print("db_missing")
        return 2

    con = sqlite3.connect(str(db))
    cur = con.cursor()

    try:
        dbl = cur.execute("PRAGMA database_list").fetchall()
        print("database_list:", dbl)
        ic = cur.execute("PRAGMA integrity_check").fetchone()
        print("integrity_check:", ic[0] if ic else None)
        jm = cur.execute("PRAGMA journal_mode").fetchone()
        lm = cur.execute("PRAGMA locking_mode").fetchone()
        print("journal_mode:", jm[0] if jm else None)
        print("locking_mode:", lm[0] if lm else None)
    except Exception:
        pass

    if do_probe:
        import time
        import uuid
        sid = str(uuid.uuid4())
        mid = str(uuid.uuid4())
        now = time.time()
        cur.execute(
            "INSERT INTO agent_sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (sid, "probe", now, now),
        )
        cur.execute(
            "INSERT INTO agent_messages (id, session_id, role, type, content, steps_json, reasoning_content, root_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (mid, sid, "user", "text", "probe", None, None, None, now),
        )
        con.commit()
        cur.execute("DELETE FROM agent_messages WHERE id=?", (mid,))
        cur.execute("DELETE FROM agent_sessions WHERE id=?", (sid,))
        con.commit()
        print("probe_write_ok")

    tables = [r[0] for r in cur.execute("select name from sqlite_master where type='table' order by name").fetchall()]
    print("tables_count:", len(tables))
    print("tables:", tables)

    def show_table(t: str) -> None:
        row = cur.execute("select sql from sqlite_master where type='table' and name=?", (t,)).fetchone()
        if not row:
            print(f"\n[{t}] missing")
            return
        cols = cur.execute(f"PRAGMA table_info({t})").fetchall()
        colnames = [c[1] for c in cols]
        print(f"\n[{t}]")
        print("cols:", [(c[1], c[2]) for c in cols])
        try:
            cnt = cur.execute(f"select count(*) from {t}").fetchone()[0]
            print("count:", cnt)
        except Exception as e:
            print("count_error:", str(e))
            return
        if "created_at" in colnames:
            try:
                latest = cur.execute(f"select id, created_at from {t} order by created_at desc limit 5").fetchall()
                print("latest(id,created_at):", latest)
            except Exception:
                pass
        elif "finished_at" in colnames:
            try:
                latest = cur.execute(f"select id, finished_at from {t} order by finished_at desc limit 5").fetchall()
                print("latest(id,finished_at):", latest)
            except Exception:
                pass

    for t in [
        "agent_messages",
        "agent_memory_cards",
        "agent_memory_edges",
        "agent_memory_relations",
        "agent_long_term_memory",
        "agent_chat_summaries",
        "agent_sessions",
        "agent_chat_sessions",
        "agent_chat_mentions",
        "agent_edges_ml",
        "agent_images",
        "session_images",
    ]:
        show_table(t)

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

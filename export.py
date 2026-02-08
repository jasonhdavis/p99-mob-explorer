import csv
from pathlib import Path

def export_table_to_csv(conn, table: str, out_path: str):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    cur = conn.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(cur.fetchall())
    print(f"[export] wrote {out_path}")

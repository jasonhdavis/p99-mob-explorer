import argparse
from config import DB_PATH, DEFAULT_CATEGORY
from db import connect, init_db
from ingest import ingest_category
from parse import parse_pages
from export import export_table_to_csv

def main():
    p = argparse.ArgumentParser(prog="p99wiki")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_ing = sub.add_parser("ingest")
    p_ing.add_argument("--category", default=DEFAULT_CATEGORY)
    p_ing.add_argument("--max-pages", type=int, default=0)

    sub.add_parser("parse")

    p_exp = sub.add_parser("export")
    p_exp.add_argument("--table", default="npc_core")
    p_exp.add_argument("--out", default="exports/npc_core.csv")

    args = p.parse_args()

    conn = connect(DB_PATH)
    init_db(conn)

    if args.cmd == "ingest":
        ingest_category(conn, args.category, args.max_pages)
    elif args.cmd == "parse":
        parse_pages(conn)
    elif args.cmd == "export":
        export_table_to_csv(conn, args.table, args.out)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Schema Runner
Applies migrations and seed data to Oracle DB.
Usage: python db/run_migrations.py --host localhost --service ORCL --user hr --password secret
"""

import argparse
import sys
from pathlib import Path
import oracledb


def run_sql_file(cursor, filepath: Path):
    """Execute a SQL file, splitting on semicolons."""
    sql = filepath.read_text(encoding="utf-8")
    # Split statements and filter empty ones
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
    success, failed = 0, 0
    for stmt in statements:
        if not stmt:
            continue
        try:
            cursor.execute(stmt)
            success += 1
        except oracledb.DatabaseError as e:
            error = e.args[0]
            # ORA-00955 = object already exists (safe to skip for migrations)
            # ORA-02291 = FK violation (seed order issue)
            if hasattr(error, 'code') and error.code in (955, 1430):
                print(f"  ⚠️  Skipped (already exists): {stmt[:60]}...")
            else:
                print(f"  ❌ Failed: {stmt[:80]}")
                print(f"     Error: {e}")
                failed += 1
    return success, failed


def main():
    parser = argparse.ArgumentParser(description="Run Oracle migrations for Global Payroll System")
    parser.add_argument("--host",     required=True)
    parser.add_argument("--port",     type=int, default=1521)
    parser.add_argument("--service",  required=True)
    parser.add_argument("--user",     required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--seeds",    action="store_true", help="Also run seed data")
    args = parser.parse_args()

    dsn = oracledb.makedsn(args.host, args.port, service_name=args.service)
    print(f"🔌 Connecting to {args.host}:{args.port}/{args.service}...")

    try:
        conn = oracledb.connect(user=args.user, password=args.password, dsn=dsn)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

    print("✅ Connected\n")
    base = Path(__file__).parent

    migration_files = sorted((base / "migrations").glob("*.sql"))
    print(f"📦 Running {len(migration_files)} migration(s)...")
    for f in migration_files:
        print(f"  → {f.name}")
        ok, err = run_sql_file(conn.cursor(), f)
        conn.commit()
        print(f"     {ok} statements OK, {err} failed")

    if args.seeds:
        seed_files = sorted((base / "seeds").glob("*.sql"))
        print(f"\n🌱 Running {len(seed_files)} seed file(s)...")
        for f in seed_files:
            print(f"  → {f.name}")
            ok, err = run_sql_file(conn.cursor(), f)
            conn.commit()
            print(f"     {ok} statements OK, {err} failed")

    conn.close()
    print("\n🚀 Done! Global Payroll System schema is ready.")


if __name__ == "__main__":
    main()

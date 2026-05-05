"""
Idempotent Metabase bootstrap script.
Run once after Metabase starts. Safe to re-run: every step checks before acting.
"""
import json
import sys
import time
import urllib.error
import urllib.request

import os

BASE = "http://metabase:3000"

ADMIN_EMAIL    = os.environ["MB_ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["MB_ADMIN_PASSWORD"]


def api(method, path, body=None, session=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if session:
        headers["X-Metabase-Session"] = session
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code} on {method} {path}: {body[:200]}")
        raise


def wait_for_metabase():
    print("Waiting for Metabase to be ready...")
    for _ in range(60):
        try:
            props = api("GET", "/api/session/properties")
            if props.get("has-user-setup") is not None:
                print("  Metabase is up.")
                return props
        except Exception:
            pass
        time.sleep(5)
    print("ERROR: Metabase did not become ready in time.")
    sys.exit(1)


def get_session(email, password):
    resp = api("POST", "/api/session", {"username": email, "password": password})
    return resp["id"]


def main():
    props = wait_for_metabase()

    # ── 1. Initial setup (skipped if already done) ───────────────────────────
    if not props.get("has-user-setup"):
        token = props.get("setup-token")
        if not token:
            print("ERROR: no setup-token and has-user-setup is False.")
            sys.exit(1)
        print("Running first-time setup wizard...")
        api("POST", "/api/setup", {
            "token": token,
            "user": {
                "first_name": "Admin",
                "last_name": "Demo",
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            },
            "prefs": {"site_name": "Data Engineering Demo", "allow_tracking": False},
        })
        print("  Setup complete.")
    else:
        print("Setup already done, skipping.")

    session = get_session(ADMIN_EMAIL, ADMIN_PASSWORD)
    print(f"  Logged in.")

    # ── 2. Add Trino datasource (skip if already present) ────────────────────
    databases = api("GET", "/api/database", session=session)
    db_names = [d["name"] for d in databases.get("data", [])]
    if "Trino (Iceberg)" in db_names:
        db_id = next(d["id"] for d in databases["data"] if d["name"] == "Trino (Iceberg)")
        print(f"Trino datasource already exists (id={db_id}), skipping.")
    else:
        print("Creating Trino datasource...")
        db_payload = {
            "engine": "starburst",
            "name": "Trino (Iceberg)",
            "details": {
                "host": "trino",
                "port": 8080,
                "catalog": "iceberg",
                "schema": "demo",
                "user": "admin",
                "ssl": False,
            },
        }
        # Metabase validates the connection immediately; retry if Trino is still warming up
        db = None
        for attempt in range(12):
            try:
                db = api("POST", "/api/database", db_payload, session=session)
                break
            except Exception as exc:
                print(f"  Trino not ready yet ({exc}), retrying in 10s...")
                time.sleep(10)
        if db is None:
            print("ERROR: could not create Trino datasource after retries.")
            sys.exit(1)
        db_id = db["id"]
        print(f"  Created database id={db_id}")

    # ── 3. Sync schema and wait for rides table ───────────────────────────────
    api("POST", f"/api/database/{db_id}/sync_schema", session=session)
    print("Waiting for 'rides' table to sync...")
    table_id = None
    for attempt in range(60):
        tables = api("GET", "/api/table", session=session)
        table_list = tables if isinstance(tables, list) else []
        for t in table_list:
            if t.get("name") == "rides" and t.get("db_id") == db_id:
                if t.get("initial_sync_status") == "complete":
                    table_id = t["id"]
                    break
                elif attempt > 0 and attempt % 10 == 0:
                    api("POST", f"/api/database/{db_id}/sync_schema", session=session)
        if table_id:
            break
        time.sleep(5)
    if not table_id:
        print("ERROR: rides table did not sync in time.")
        sys.exit(1)
    print(f"  rides table synced (id={table_id})")

    # ── 4. Get field IDs ──────────────────────────────────────────────────────
    meta = api("GET", f"/api/table/{table_id}/query_metadata", session=session)
    fields = {f["name"]: f["id"] for f in meta["fields"]}
    print(f"  Fields: {fields}")

    # ── 5. Create dashboard (skip if already present) ─────────────────────────
    dashboards = api("GET", "/api/dashboard", session=session)
    dash_names = [d["name"] for d in (dashboards if isinstance(dashboards, list) else [])]
    if "Taxi Rides — Live Pipeline" in dash_names:
        print("Dashboard already exists, skipping card creation.")
        return

    print("Creating dashboard and cards...")
    dash = api("POST", "/api/dashboard", {
        "name": "Taxi Rides — Live Pipeline",
        "description": "Real-time taxi ride events: Kafka → Flink → Iceberg → Trino",
    }, session=session)
    dash_id = dash["id"]

    def card(name, display, agg, breakout=None, order_by=None, limit=None):
        q = {"source-table": table_id, "aggregation": agg}
        if breakout:
            q["breakout"] = breakout
        if order_by:
            q["order-by"] = order_by
        if limit:
            q["limit"] = limit
        c = api("POST", "/api/card", {
            "name": name,
            "display": display,
            "database_id": db_id,
            "dataset_query": {"type": "query", "database": db_id, "query": q},
            "visualization_settings": {},
        }, session=session)
        return c["id"]

    f = fields  # shorthand
    q5  = card("Total Rides Processed",       "scalar", [["count"]])
    q6  = card("Avg Trip Distance (km)",       "scalar", [["avg", ["field", f["distance_km"], None]]])
    q1  = card("Rides by Status",              "pie",    [["count"]], [["field", f["status"], None]])
    q2  = card("Avg Fare by Status (USD)",     "bar",    [["avg", ["field", f["fare_usd"], None]]], [["field", f["status"], None]])
    q3  = card("Rides per Minute (Live)",      "line",   [["count"]], [["field", f["started_at"], {"temporal-unit": "minute"}]])
    q4  = card("Top 10 Drivers by Revenue",    "bar",    [["sum", ["field", f["fare_usd"], None]]], [["field", f["driver_id"], None]],
               order_by=[["desc", ["aggregation", 0]]], limit=10)

    print(f"  Cards: total={q5} dist={q6} status={q1} fare={q2} time={q3} drivers={q4}")

    # Layout: 2 KPI scalars top, pie+bar middle, line full, drivers full
    dashcards = [
        {"id": -1, "card_id": q5,  "row": 0,  "col": 0,  "size_x": 6,  "size_y": 3,  "parameter_mappings": [], "visualization_settings": {}},
        {"id": -2, "card_id": q6,  "row": 0,  "col": 6,  "size_x": 6,  "size_y": 3,  "parameter_mappings": [], "visualization_settings": {}},
        {"id": -3, "card_id": q1,  "row": 3,  "col": 0,  "size_x": 8,  "size_y": 8,  "parameter_mappings": [], "visualization_settings": {}},
        {"id": -4, "card_id": q2,  "row": 3,  "col": 8,  "size_x": 10, "size_y": 8,  "parameter_mappings": [], "visualization_settings": {}},
        {"id": -5, "card_id": q3,  "row": 11, "col": 0,  "size_x": 18, "size_y": 8,  "parameter_mappings": [], "visualization_settings": {}},
        {"id": -6, "card_id": q4,  "row": 19, "col": 0,  "size_x": 18, "size_y": 8,  "parameter_mappings": [], "visualization_settings": {}},
    ]
    result = api("PUT", f"/api/dashboard/{dash_id}", {"dashcards": dashcards}, session=session)
    print(f"  Dashboard id={dash_id} created with {len(result.get('dashcards', []))} cards.")
    print(f"\nDone! Open http://localhost:3000/dashboard/{dash_id}#refresh=30")
    print(f"Login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    main()

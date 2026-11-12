"""Load the L4 sample data (data/sample/*.csv) into PostgreSQL.

Safe to run again: every insert uses an explicit primary key with
ON CONFLICT DO NOTHING, so a second run adds nothing (BT2 C5).
Run after scripts/migrate.py.

Usage: python scripts/seed.py
"""
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import get_settings  # noqa: E402
from src.db import DatabaseUnavailableError, get_connection  # noqa: E402
from src.services.password_hashing import hash_password, verify_password  # noqa: E402

SAMPLE = ROOT / "data" / "sample"
SLA_HOURS = {"CAO": 24, "TRUNG_BINH": 72, "THAP": 120}   # QT-04 (calendar hours, as in the dataset)
DEMO_APPOINTMENT_FIRST_ID = 900001
DEMO_SLOTS = [("09:00", "10:00"), ("14:00", "15:00"), ("10:00", "12:00")]

TABLES = ["issue_category", "technician", "technician_skill", "ticket",
          "ticket_status_log", "appointment", "app_user"]
# Demo login accounts (FR12): one center manager per demo center. The password is the
# documented demo password (DEMO_PASSWORD, default "manager123"); only its hash is stored.
DEMO_ACCOUNTS = [(1, "manager1", "CENTER_MANAGER", 1), (2, "manager2", "CENTER_MANAGER", 2)]


def rows(name):
    with (SAMPLE / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def none_if_empty(value):
    return value if value not in ("", None) else None


def as_bool(value):
    return str(value).strip().lower() == "true"


def seed():
    settings = get_settings()
    tz = ZoneInfo(settings.app_timezone)
    now = datetime.now(tz)

    categories = rows("issue_categories.csv")
    technicians = rows("technicians.csv")
    skills = rows("technician_skills.csv")
    tickets = rows("tickets.csv")
    logs = rows("ticket_status_log.csv")
    appointments = rows("appointments.csv")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Dataset timestamps have no zone: read them as business local time.
            cur.execute("SELECT set_config('TimeZone', %s, false)", (settings.app_timezone,))

            counts_before = count_rows(cur)

            cur.executemany(
                """INSERT INTO issue_category (category_id, category_name, default_priority, is_active)
                   VALUES (%s, %s, %s, %s) ON CONFLICT (category_id) DO NOTHING""",
                [(c["category_id"], c["category_name"], c["default_priority"], as_bool(c["is_active"]))
                 for c in categories],
            )

            cur.executemany(
                """INSERT INTO technician (technician_id, technician_code, ho_ten, center_id, level, is_active)
                   VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (technician_id) DO NOTHING""",
                [(t["technician_id"], t["technician_code"], t["ho_ten"], t["center_id"], t["level"],
                  as_bool(t["is_active"])) for t in technicians],
            )

            cur.executemany(
                """INSERT INTO technician_skill (technician_id, category_id, proficiency)
                   VALUES (%s, %s, %s) ON CONFLICT (technician_id, category_id) DO NOTHING""",
                [(s["technician_id"], s["category_id"], s["proficiency"]) for s in skills],
            )

            ticket_values = []
            for t in tickets:
                if t["received_minutes_ago"]:
                    # Generated unassigned ticket: received shortly before seeding.
                    received_at = now - timedelta(minutes=int(t["received_minutes_ago"]))
                    due_date = received_at + timedelta(hours=SLA_HOURS[t["priority"]])
                else:
                    received_at, due_date = t["received_at"], t["due_date"]
                ticket_values.append((
                    t["ticket_id"], t["ticket_code"], t["center_id"], t["customer_name"],
                    t["customer_phone"], t["serial_no"], t["issue_desc"], t["category_id"],
                    t["priority"], t["status"], none_if_empty(t["technician_id"]),
                    received_at, due_date, none_if_empty(t["closed_at"]), as_bool(t["is_warranty"]),
                ))
            cur.executemany(
                """INSERT INTO ticket (ticket_id, ticket_code, center_id, customer_name, customer_phone,
                       serial_no, issue_desc, category_id, priority, status, technician_id,
                       received_at, due_date, closed_at, is_warranty)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (ticket_id) DO NOTHING""",
                ticket_values,
            )

            cur.executemany(
                """INSERT INTO ticket_status_log (log_id, ticket_id, from_status, to_status,
                       changed_at, changed_by, note)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (log_id) DO NOTHING""",
                [(log["log_id"], log["ticket_id"], none_if_empty(log["from_status"]), log["to_status"],
                  log["changed_at"], log["changed_by"], none_if_empty(log["note"])) for log in logs],
            )

            cur.executemany(
                """INSERT INTO appointment (appointment_id, ticket_id, technician_id, center_id, loai,
                       trang_thai, ngay_hen, gio_bat_dau, gio_ket_thuc)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (appointment_id) DO NOTHING""",
                [(a["appointment_id"], a["ticket_id"], a["technician_id"], a["center_id"], a["loai"],
                  a["trang_thai"], a["ngay_hen"], a["gio_bat_dau"], a["gio_ket_thuc"]) for a in appointments],
            )

            sync_sequences(cur)

            # Creation log (NULL -> MOI) for generated tickets, once per ticket (QT-06).
            cur.execute(
                """INSERT INTO ticket_status_log (ticket_id, from_status, to_status, changed_at, changed_by)
                   SELECT t.ticket_id, NULL, 'MOI', t.received_at, 0
                   FROM ticket t
                   WHERE t.status = 'MOI'
                     AND NOT EXISTS (SELECT 1 FROM ticket_status_log l
                                     WHERE l.ticket_id = t.ticket_id AND l.to_status = 'MOI')"""
            )

            insert_demo_appointments(cur, tickets, now)
            sync_sequences(cur)
            reset = insert_demo_accounts(cur, settings.demo_password)

            counts_after = count_rows(cur)

    print("Seeding completed (rows added / total):")
    for table in TABLES:
        added = counts_after[table] - counts_before[table]
        print(f"  {table:18} +{added:<5} {counts_after[table]:>6}")
    if reset:
        print(f"Demo password changed to the DEMO_PASSWORD value for: {', '.join(reset)}")


def insert_demo_appointments(cur, tickets, now):
    """A few upcoming appointments per demo center so M3 has something to show.
    Fixed ids => inserted once, never duplicated on later runs."""
    demo = []
    appointment_id = DEMO_APPOINTMENT_FIRST_ID
    for center in ("1", "2"):
        assigned = sorted(
            (t for t in tickets if t["center_id"] == center and t["technician_id"]),
            key=lambda t: int(t["ticket_id"]),
        )[:3]
        for day_offset, (ticket, (start, end)) in enumerate(zip(assigned, DEMO_SLOTS), start=1):
            demo.append((appointment_id, ticket["ticket_id"], ticket["technician_id"], center,
                         "GIAO_MAY" if day_offset % 2 else "NHAN_MAY", "DA_XAC_NHAN",
                         (now + timedelta(days=day_offset)).date(), start, end))
            appointment_id += 1
    cur.executemany(
        """INSERT INTO appointment (appointment_id, ticket_id, technician_id, center_id, loai,
               trang_thai, ngay_hen, gio_bat_dau, gio_ket_thuc)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (appointment_id) DO NOTHING""",
        demo,
    )


def insert_demo_accounts(cur, password):
    """Create the demo accounts with DEMO_PASSWORD, and keep them in line with it.

    A re-run with the same DEMO_PASSWORD changes nothing (the stored hash still matches).
    When DEMO_PASSWORD has changed since the accounts were created, their hash is replaced,
    so changing the variable and restarting is how the demo password is changed (TD-45).
    Returns the usernames whose password was changed.
    """
    cur.execute("SELECT username, password_hash FROM app_user")
    existing = {row["username"]: row["password_hash"] for row in cur.fetchall()}
    changed = []
    for user_id, username, role, center_id in DEMO_ACCOUNTS:
        if username not in existing:
            cur.execute(
                """INSERT INTO app_user (user_id, username, password_hash, role, center_id)
                   VALUES (%s, %s, %s, %s, %s) ON CONFLICT (user_id) DO NOTHING""",
                (user_id, username, hash_password(password), role, center_id),
            )
        elif not verify_password(password, existing[username]):
            cur.execute("UPDATE app_user SET password_hash = %s WHERE username = %s",
                        (hash_password(password), username))
            changed.append(username)
    return changed


def sync_sequences(cur):
    """Explicit ids were inserted, so move each sequence past the max id."""
    for table, column in [("issue_category", "category_id"), ("technician", "technician_id"),
                          ("ticket", "ticket_id"), ("ticket_status_log", "log_id"),
                          ("appointment", "appointment_id")]:
        cur.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}', '{column}'), "
            f"COALESCE((SELECT MAX({column}) FROM {table}), 1))"
        )


def count_rows(cur):
    counts = {}
    for table in TABLES:
        cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
        counts[table] = cur.fetchone()["n"]
    return counts


if __name__ == "__main__":
    try:
        seed()
    except DatabaseUnavailableError as exc:
        print(f"Error: cannot connect to PostgreSQL ({exc}). Check DB_* values in .env.")
        sys.exit(1)

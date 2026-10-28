"""Build the small L4 sample in data/sample/ from the course dataset.

Inputs (not committed, regenerate with the commands in README section 7):
  data/raw/*.csv              tools/gen_dataset.py data/raw              (seed 20260901)
  data/raw/appointments.csv   tools/gen_sample.py --entity appointment
                              --rows 1200 --seed 42 --link data/raw/tickets_history.csv

Outputs (committed, a few hundred rows each, loaded by scripts/seed.py):
  issue_categories.csv, technicians.csv, technician_skills.csv   copied as-is
  tickets.csv           open tickets of centers 1-2 (workload for FR8)
                        + generated unassigned MOI tickets (the dataset has none)
  ticket_status_log.csv history rows of the open tickets
  appointments.csv      generated appointments that belong to those tickets

Same inputs + same seed => identical files (reproducible).
Usage: python scripts/build_sample.py
"""
import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "sample"

SEED = 42
CENTERS = ("1", "2")                     # the two demo managers' centers
OPEN_STATUSES = {"DA_PHAN_CONG", "DANG_XU_LY", "CHO_LINH_KIEN"}
ACTIVE_APPOINTMENT = {"DA_DAT", "DA_XAC_NHAN"}
NEW_TICKETS_PER_CENTER = 30
NEW_TICKET_FIRST_ID = 8001               # dataset ticket ids stop at 7800

# Customer snapshot fixture (SRS section 5 note 2: customers_raw cannot be
# joined to tickets_history.customer_id, so names/phones are generated).
HO = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ"]
DEM = ["Văn", "Thị", "Hữu", "Đức", "Minh", "Ngọc", "Thanh", "Quang", "Xuân", "Tuấn"]
TEN = ["An", "Bình", "Cường", "Dung", "Đạt", "Giang", "Hà", "Hải", "Hạnh", "Huy", "Khoa",
       "Lan", "Linh", "Long", "Mai", "Nam", "Phong", "Phúc", "Quân", "Sơn", "Tâm", "Thảo", "Trang", "Vy"]
CATEGORY_WEIGHTS = {"1": 1310, "2": 980, "3": 640, "4": 520, "5": 330, "6": 220}  # same mix as the dataset

TICKET_COLUMNS = [
    "ticket_id", "ticket_code", "center_id", "customer_name", "customer_phone", "serial_no",
    "issue_desc", "category_id", "priority", "status", "technician_id",
    "received_at", "due_date", "closed_at", "is_warranty", "received_minutes_ago",
]


def read(name):
    path = RAW / name
    if not path.exists():
        sys.exit(f"Missing {path}. Run the dataset commands in README section 7 first.")
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(name, columns, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})
    print(f"  {name:24} {len(rows):>5} rows")


def customer_snapshot(rnd):
    name = f"{rnd.choice(HO)} {rnd.choice(DEM)} {rnd.choice(TEN)}"
    phone = "09" + "".join(str(rnd.randint(0, 9)) for _ in range(8))
    return name, phone


def main():
    rnd = random.Random(SEED)

    categories = read("issue_categories.csv")
    technicians = read("technicians.csv")
    skills = read("technician_skills.csv")
    tickets = read("tickets_history.csv")
    logs = read("ticket_status_log.csv")
    appointments = read("appointments.csv")

    default_priority = {c["category_id"]: c["default_priority"] for c in categories}

    # 1. Open tickets of the demo centers: they give technicians a real workload.
    open_tickets = []
    for t in tickets:
        if t["center_id"] in CENTERS and t["status"] in OPEN_STATUSES:
            name, phone = customer_snapshot(rnd)
            open_tickets.append({**t, "customer_name": name, "customer_phone": phone})
    open_ids = {t["ticket_id"] for t in open_tickets}

    # 2. Unassigned MOI tickets. received_at is stored as "minutes before seeding"
    #    so the M1 list always shows fresh, not-yet-overdue SLA deadlines.
    descriptions = {}
    for t in tickets:
        descriptions.setdefault(t["category_id"], []).append(t["issue_desc"])
    new_tickets = []
    next_id = NEW_TICKET_FIRST_ID
    for center in CENTERS:
        for _ in range(NEW_TICKETS_PER_CENTER):
            category = rnd.choices(list(CATEGORY_WEIGHTS), weights=list(CATEGORY_WEIGHTS.values()))[0]
            priority = default_priority[category]
            if rnd.random() < 0.18:
                priority = rnd.choice(["CAO", "TRUNG_BINH", "THAP"])
            name, phone = customer_snapshot(rnd)
            new_tickets.append({
                "ticket_id": str(next_id),
                "ticket_code": f"BH-{next_id:06d}/2026",
                "center_id": center,
                "customer_name": name,
                "customer_phone": phone,
                "serial_no": f"SN{rnd.randint(10**11, 10**12 - 1)}",
                "issue_desc": rnd.choice(descriptions[category]),
                "category_id": category,
                "priority": priority,
                "status": "MOI",
                "technician_id": "",
                "is_warranty": "true" if rnd.random() < 0.85 else "false",
                "received_minutes_ago": str(rnd.randint(10, 48 * 60)),
            })
            next_id += 1

    # 3. Status history of the open tickets.
    sample_logs = [log for log in logs if log["ticket_id"] in open_ids]

    # 4. Appointments: keep those of sampled tickets; technician and center are
    #    taken from the ticket (gen_sample.py picks them at random), and any active
    #    appointment overlapping an earlier kept one is dropped (FR7).
    ticket_by_id = {t["ticket_id"]: t for t in open_tickets}
    kept, busy = [], {}
    for a in appointments:
        ticket = ticket_by_id.get(a["ticket_id"])
        if not ticket or not ticket["technician_id"]:
            continue
        row = {**a, "technician_id": ticket["technician_id"], "center_id": ticket["center_id"]}
        if row["trang_thai"] in ACTIVE_APPOINTMENT:
            key = (row["technician_id"], row["ngay_hen"])
            slots = busy.setdefault(key, [])
            if any(row["gio_bat_dau"] < end and row["gio_ket_thuc"] > start for start, end in slots):
                continue
            slots.append((row["gio_bat_dau"], row["gio_ket_thuc"]))
        kept.append(row)

    print(f"Writing {OUT}")
    write("issue_categories.csv", ["category_id", "category_name", "default_priority", "is_active"], categories)
    write("technicians.csv", ["technician_id", "technician_code", "ho_ten", "center_id", "level", "is_active"], technicians)
    write("technician_skills.csv", ["technician_id", "category_id", "proficiency"], skills)
    write("tickets.csv", TICKET_COLUMNS, open_tickets + new_tickets)
    write("ticket_status_log.csv",
          ["log_id", "ticket_id", "from_status", "to_status", "changed_at", "changed_by", "note"], sample_logs)
    write("appointments.csv",
          ["appointment_id", "ticket_id", "technician_id", "center_id", "loai", "trang_thai",
           "ngay_hen", "gio_bat_dau", "gio_ket_thuc"], kept)


if __name__ == "__main__":
    main()

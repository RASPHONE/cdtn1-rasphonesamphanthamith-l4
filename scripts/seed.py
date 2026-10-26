import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_connection

def split_sql(sql: str):
    """Removes SQL comments and splits into executable statements."""
    # Remove single-line comments (-- ...)
    sql = re.sub(r'--[^\n]*', '', sql)
    # Remove multi-line comments (/* ... */)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    statements = []
    current = []
    for line in sql.splitlines():
        line = line.strip()
        if not line:
            continue
        current.append(line)
        if line.endswith(';'):
            stmt = " ".join(current)
            statements.append(stmt)
            current = []
    if current:
        stmt = " ".join(current)
        if stmt:
            statements.append(stmt)
    return statements

def seed():
    print("Seeding database...")

    sql = """
    -- 1. Issue Categories (matches DDL: category_name, default_priority, is_active)
    INSERT INTO issue_category (category_id, category_name, default_priority, is_active) VALUES
    (1, 'MAN_HINH', 'CAO', TRUE),
    (2, 'PIN', 'TRUNG_BINH', TRUE),
    (3, 'SAC', 'TRUNG_BINH', TRUE),
    (4, 'PHAN_MEM', 'THAP', TRUE),
    (5, 'NUOC_VAO', 'CAO', TRUE),
    (6, 'KHAC', 'TRUNG_BINH', TRUE),
    (7, 'CU', 'THAP', FALSE)
    ON CONFLICT (category_id) DO NOTHING;

    -- 2. Technicians (matches DDL: technician_code, ho_ten, center_id, level, is_active)
    INSERT INTO technician (technician_id, technician_code, ho_ten, center_id, level, is_active) VALUES
    (1, 'KT001', 'Nguyen Van A', 1, 'TRUNG_CAP', TRUE),
    (2, 'KT002', 'Tran Van B', 1, 'CAO_CAP', TRUE),
    (3, 'KT003', 'Le Van C', 2, 'CAO_CAP', TRUE),
    (4, 'KT004', 'Pham Van D', 2, 'TRUNG_CAP', TRUE),
    (5, 'KT005', 'Hoang Van E', 1, 'SO_CAP', FALSE)
    ON CONFLICT (technician_id) DO NOTHING;

    -- 3. Technician Skills (matches DDL: technician_id, category_id, proficiency)
    INSERT INTO technician_skill (technician_id, category_id, proficiency) VALUES
    (1, 1, 4),
    (1, 2, 2),
    (2, 1, 3),
    (2, 3, 5),
    (3, 1, 4),
    (4, 2, 3)
    ON CONFLICT (technician_id, category_id) DO NOTHING;

    -- 4. Tickets (matches DDL: all NOT NULL columns)
    INSERT INTO ticket (
        ticket_id, ticket_code, center_id, customer_name, customer_phone,
        serial_no, issue_desc, category_id, priority, status,
        technician_id, received_at, due_date, closed_at, is_warranty, is_deleted
    ) VALUES
    (101, 'PB-1-00001', 1, 'Khach 1', '0901111111', 'SN100000000001', 'Man bi soc', 1, 'CAO', 'MOI', NULL, NOW() - INTERVAL '2 hours', NOW() + INTERVAL '22 hours', NULL, TRUE, FALSE),
    (102, 'PB-1-00002', 1, 'Khach 2', '0902222222', 'SN100000000002', 'Pin nhanh het', 2, 'THAP', 'MOI', NULL, NOW() - INTERVAL '1 hour', NOW() + INTERVAL '119 hours', NULL, TRUE, FALSE),
    (103, 'PB-1-00003', 1, 'Khach 3', '0903333333', 'SN100000000003', 'Man bi am vang', 1, 'TRUNG_BINH', 'DA_PHAN_CONG', 1, NOW() - INTERVAL '3 hours', NOW() + INTERVAL '69 hours', NULL, TRUE, FALSE),
    (104, 'PB-1-00004', 1, 'Khach 4', '0904444444', 'SN100000000004', 'Sac khong vao', 3, 'CAO', 'MOI', NULL, NOW() - INTERVAL '1 hour', NOW() + INTERVAL '23 hours', NULL, FALSE, FALSE),
    (105, 'PB-1-00005', 1, 'Khach 5', '0905555555', 'SN100000000005', 'Man bi nut', 1, 'CAO', 'DA_DONG', 1, NOW() - INTERVAL '5 days', NOW() - INTERVAL '4 days', NOW() - INTERVAL '3 days', TRUE, FALSE),
    (106, 'PB-1-00006', 1, 'Khach 6', '0906666666', 'SN100000000006', 'Man bi chuong', 1, 'CAO', 'MOI', NULL, NOW() - INTERVAL '1 hour', NOW() + INTERVAL '23 hours', NULL, TRUE, TRUE),
    (201, 'PB-2-00001', 2, 'Khach 7', '0907777777', 'SN200000000001', 'Man bi den', 1, 'CAO', 'MOI', NULL, NOW() - INTERVAL '2 hours', NOW() + INTERVAL '22 hours', NULL, TRUE, FALSE)
    ON CONFLICT (ticket_id) DO NOTHING;

    -- 5. Appointments (matches DDL: all NOT NULL columns + is_deleted)
    INSERT INTO appointment (
        appointment_id, ticket_id, technician_id, center_id, loai, trang_thai,
        ngay_hen, gio_bat_dau, gio_ket_thuc, is_deleted
    ) VALUES
    (201, 103, 1, 1, 'NHAN_MAY', 'DA_XAC_NHAN', CURRENT_DATE + INTERVAL '1 day', '09:00', '10:00', FALSE),
    (202, 103, 1, 1, 'GIAO_MAY', 'HOAN_TAT', CURRENT_DATE - INTERVAL '1 day', '14:00', '15:00', FALSE),
    (203, 103, 1, 1, 'NHAN_MAY', 'KHACH_HUY', CURRENT_DATE + INTERVAL '2 days', '11:00', '12:00', FALSE),
    (204, 103, 1, 1, 'NHAN_MAY', 'DA_DAT', CURRENT_DATE + INTERVAL '3 days', '08:00', '09:00', TRUE)
    ON CONFLICT (appointment_id) DO NOTHING;

    -- 6. Ticket Status Log (matches DDL: ticket_id, from_status, to_status, changed_by)
    INSERT INTO ticket_status_log (log_id, ticket_id, from_status, to_status, changed_by, note) VALUES
    (1, 103, 'MOI', 'DA_PHAN_CONG', 1, 'Phan cong lan dau'),
    (2, 105, 'MOI', 'DA_PHAN_CONG', 1, 'Phan cong lan dau'),
    (3, 105, 'DA_PHAN_CONG', 'DANG_XU_LY', 1, NULL),
    (4, 105, 'DANG_XU_LY', 'HOAN_TAT', 1, NULL),
    (5, 105, 'HOAN_TAT', 'DA_DONG', 1, NULL)
    ON CONFLICT (log_id) DO NOTHING;
    """

    statements = split_sql(sql)

    with get_connection() as conn:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
    print("Seeding completed successfully.")

if __name__ == "__main__":
    seed()

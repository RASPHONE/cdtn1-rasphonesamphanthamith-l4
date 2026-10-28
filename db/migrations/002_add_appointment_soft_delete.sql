-- db/migrations/002_add_appointment_soft_delete.sql — BT2 / TD-05
-- Adds soft-delete support to appointment and updates conflict index.

ALTER TABLE appointment
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

DROP INDEX IF EXISTS idx_appointment_overlap;

CREATE INDEX IF NOT EXISTS idx_appointment_active_overlap
ON appointment (technician_id, ngay_hen, gio_bat_dau, gio_ket_thuc)
WHERE is_deleted = FALSE
  AND trang_thai IN ('DA_DAT', 'DA_XAC_NHAN');

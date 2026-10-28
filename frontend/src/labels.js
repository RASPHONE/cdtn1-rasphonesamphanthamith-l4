// Vietnamese display text for codes coming from the API.
// Codes (MOI, GIAO_MAY, appointment_conflict, ...) stay exactly as in the ERD /
// API contract; only what the user reads is translated here, in one place.

export const PRIORITY_LABELS = {
  CAO: 'Cao',
  TRUNG_BINH: 'Trung bình',
  THAP: 'Thấp',
}

export const TICKET_STATUS_LABELS = {
  MOI: 'Mới',
  DA_PHAN_CONG: 'Đã phân công',
  DANG_XU_LY: 'Đang xử lý',
  CHO_LINH_KIEN: 'Chờ linh kiện',
  HOAN_TAT: 'Hoàn tất',
  DA_DONG: 'Đã đóng',
  DA_HUY: 'Đã huỷ',
}

export const APPOINTMENT_TYPE_LABELS = {
  GIAO_MAY: 'Giao máy',
  NHAN_MAY: 'Nhận máy',
  KIEM_TRA_TAI_CHO: 'Kiểm tra tại chỗ',
}

// v0.2 only creates these two types (FR6).
export const CREATABLE_APPOINTMENT_TYPES = ['GIAO_MAY', 'NHAN_MAY']

export const APPOINTMENT_STATUS_LABELS = {
  DA_DAT: 'Đã đặt',
  DA_XAC_NHAN: 'Đã xác nhận',
  HOAN_TAT: 'Hoàn tất',
  KHACH_HUY: 'Khách huỷ',
  KHACH_KHONG_DEN: 'Khách không đến',
}

// Badge colours per code
export const PRIORITY_TONE = { CAO: 'red', TRUNG_BINH: 'amber', THAP: 'gray' }
export const APPOINTMENT_STATUS_TONE = {
  DA_DAT: 'blue', DA_XAC_NHAN: 'green', HOAN_TAT: 'gray', KHACH_HUY: 'amber', KHACH_KHONG_DEN: 'red',
}

export const LEVEL_LABELS = {
  SO_CAP: 'Sơ cấp',
  TRUNG_CAP: 'Trung cấp',
  CAO_CAP: 'Cao cấp',
}

export const CATEGORY_LABELS = {
  MAN_HINH: 'Màn hình',
  PIN: 'Pin',
  SAC: 'Sạc',
  PHAN_MEM: 'Phần mềm',
  NUOC_VAO: 'Nước vào',
  KHAC: 'Khác',
}

// A category added later by INSERT (NFR7) still displays, with its raw name.
export const categoryLabel = (name) => CATEGORY_LABELS[name] || name

const ERROR_MESSAGES = {
  network_error: 'Không kết nối được tới máy chủ. Hãy kiểm tra backend đã chạy chưa rồi bấm Thử lại.',
  database_unavailable: 'Cơ sở dữ liệu tạm thời không khả dụng. Vui lòng thử lại sau ít phút.',
  unauthorized: 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
  invalid_credentials: 'Sai tên đăng nhập hoặc mật khẩu.',
  cross_center_access: 'Bạn không có quyền xem dữ liệu của trung tâm khác.',
  ticket_not_found: 'Không tìm thấy phiếu bảo hành.',
  appointment_not_found: 'Không tìm thấy lịch hẹn (có thể đã bị xoá).',
  technician_not_found: 'Không tìm thấy kỹ thuật viên.',
  technician_not_qualified:
    'Kỹ thuật viên không đủ điều kiện (khác trung tâm, đã ngừng hoạt động hoặc tay nghề dưới 3).',
  ticket_not_assignable: 'Phiếu không còn ở trạng thái cho phép thao tác này. Hãy tải lại trang.',
  reason_required: 'Cần nhập lý do đổi kỹ thuật viên (5–255 ký tự).',
  appointment_conflict: 'Kỹ thuật viên đã có lịch hẹn trùng thời gian. Vui lòng chọn khung giờ khác.',
  appointment_type_deferred: 'Loại lịch hẹn này chưa được hỗ trợ ở phiên bản v0.2.',
  appointment_in_past: 'Thời gian hẹn phải ở tương lai.',
  invalid_time_range: 'Giờ kết thúc phải sau giờ bắt đầu.',
  appointment_completed_cannot_delete: 'Lịch hẹn đã hoàn tất nên không thể xoá.',
  appointment_completed_cannot_update: 'Lịch hẹn đã hoàn tất nên không thể sửa.',
}

export function messageForError(code, body) {
  if (code === 'bad_request') {
    const fields = (body?.details || []).map((d) => d.field).filter(Boolean)
    return fields.length
      ? `Dữ liệu thiếu hoặc sai định dạng ở trường: ${fields.join(', ')}.`
      : 'Dữ liệu gửi lên thiếu hoặc sai định dạng.'
  }
  if (code === 'internal_error') {
    return `Lỗi hệ thống không mong muốn. Mã tra cứu: ${body?.request_id || 'không có'}.`
  }
  return ERROR_MESSAGES[code] || 'Đã xảy ra lỗi không xác định. Vui lòng thử lại.'
}

// ---------- formatting helpers ----------

export function formatDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export function formatDate(isoDate) {
  if (!isoDate) return '—'
  const [y, m, d] = isoDate.split('-')
  return `${d}/${m}/${y}`
}

export const formatTime = (value) => (value ? value.slice(0, 5) : '—')

// SLA reference point for each ticket: time left (or overdue) vs. due_date.
export function slaStatus(dueIso, now = new Date()) {
  const diffMinutes = Math.round((new Date(dueIso) - now) / 60000)
  const abs = Math.abs(diffMinutes)
  const text = abs >= 60 * 24
    ? `${Math.floor(abs / (60 * 24))} ngày ${Math.floor((abs % (60 * 24)) / 60)} giờ`
    : abs >= 60 ? `${Math.floor(abs / 60)} giờ ${abs % 60} phút` : `${abs} phút`
  if (diffMinutes < 0) return { overdue: true, text: `Quá hạn ${text}` }
  return { overdue: false, soon: diffMinutes <= 4 * 60, text: `Còn ${text}` }
}

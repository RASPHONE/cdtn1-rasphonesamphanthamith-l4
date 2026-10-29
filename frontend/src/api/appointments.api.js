import { request } from './client'

export const appointmentsApi = {
  // Query objects use the exact API / ERD field names (ngay_hen, trang_thai, ...).
  list: ({ page = 1, page_size = 20, ngay_hen, trang_thai, ticket_id } = {}) =>
    request('/api/appointments', { query: { page, page_size, ngay_hen, trang_thai, ticket_id } }),
  // FR7 pre-check before saving (UC4 step 5)
  checkConflicts: ({ technician_id, ngay_hen, gio_bat_dau, gio_ket_thuc, exclude_appointment_id }) =>
    request('/api/appointments/conflicts', {
      query: { technician_id, ngay_hen, gio_bat_dau, gio_ket_thuc, exclude_appointment_id },
    }),
  create: (payload) => request('/api/appointments', { method: 'POST', body: payload }),
  update: (appointmentId, payload) =>
    request(`/api/appointments/${appointmentId}`, { method: 'PATCH', body: payload }),
  // Soft delete (FR11): the row is kept with is_deleted = true.
  remove: (appointmentId) => request(`/api/appointments/${appointmentId}`, { method: 'DELETE' }),
}

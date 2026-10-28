import { request } from './client'

export const appointmentsApi = {
  list: ({ page = 1, pageSize = 20, ngayHen, trangThai, ticketId } = {}) =>
    request('/api/appointments', {
      query: { page, page_size: pageSize, ngay_hen: ngayHen, trang_thai: trangThai, ticket_id: ticketId },
    }),
  // FR7 pre-check before saving (UC4 step 5)
  checkConflicts: ({ technicianId, ngayHen, gioBatDau, gioKetThuc, excludeAppointmentId }) =>
    request('/api/appointments/conflicts', {
      query: {
        technician_id: technicianId,
        ngay_hen: ngayHen,
        gio_bat_dau: gioBatDau,
        gio_ket_thuc: gioKetThuc,
        exclude_appointment_id: excludeAppointmentId,
      },
    }),
  create: (payload) => request('/api/appointments', { method: 'POST', body: payload }),
  update: (appointmentId, payload) =>
    request(`/api/appointments/${appointmentId}`, { method: 'PATCH', body: payload }),
  // Soft delete (FR11): the row is kept with is_deleted = true.
  remove: (appointmentId) => request(`/api/appointments/${appointmentId}`, { method: 'DELETE' }),
}

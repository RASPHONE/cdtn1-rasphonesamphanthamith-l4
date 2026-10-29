import { request } from './client'

export const ticketsApi = {
  // M1 – FR1, FR9
  listUnassigned: ({ page = 1, page_size = 20, category_id, priority } = {}) =>
    request('/api/tickets/unassigned', { query: { page, page_size, category_id, priority } }),
  // M2/M3 read-only summary
  getTicket: (ticketId) => request(`/api/tickets/${ticketId}`),
  // M2 – FR2, FR8 (QT-08)
  listQualifiedTechnicians: (ticketId) => request(`/api/tickets/${ticketId}/qualified-technicians`),
  // M2 – FR3, FR4
  assignTechnician: (ticketId, technicianId) =>
    request(`/api/tickets/${ticketId}/assignment`, {
      method: 'POST',
      body: { technician_id: technicianId },
    }),
  // M2 – FR5 (QT-07: reason required)
  reassignTechnician: (ticketId, technicianId, reason) =>
    request(`/api/tickets/${ticketId}/assignment`, {
      method: 'PATCH',
      body: { technician_id: technicianId, reason },
    }),
}

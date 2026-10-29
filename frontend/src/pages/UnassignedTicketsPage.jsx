// M1 — Unassigned warranty ticket list (UC1 · US1, US8 · FR1, FR9)
import { useState } from 'react'
import { categoriesApi } from '../api/categories.api'
import { ticketsApi } from '../api/tickets.api'
import { Badge } from '../components/Badge'
import { DataState } from '../components/DataState'
import { Pagination } from '../components/Pagination'
import { useApi } from '../hooks/useApi'
import { PRIORITY_LABELS, PRIORITY_TONE, categoryLabel, formatDateTime, slaStatus } from '../labels'

const PAGE_SIZE = 20
const NO_FILTERS = { category_id: '', priority: '' }

export default function UnassignedTicketsPage({ onAssign }) {
  const [draftFilters, setDraftFilters] = useState(NO_FILTERS) // what the dropdowns show
  const [filters, setFilters] = useState(NO_FILTERS) // what was applied
  const [page, setPage] = useState(1)

  const categories = useApi(() => categoriesApi.listActive(), [])
  const tickets = useApi(
    () => ticketsApi.listUnassigned({ page, page_size: PAGE_SIZE, ...filters }),
    [page, filters.category_id, filters.priority],
  )

  const hasFilters = Boolean(filters.category_id || filters.priority)
  const applyFilters = () => { setPage(1); setFilters(draftFilters) }
  const clearFilters = () => { setPage(1); setDraftFilters(NO_FILTERS); setFilters(NO_FILTERS) }

  const items = tickets.data?.items || []
  const overdueOnPage = items.filter((t) => slaStatus(t.due_date).overdue).length

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold">M1 · Phiếu bảo hành chưa phân công</h2>
        <p className="text-sm text-gray-500">
          Sắp xếp theo hạn cam kết (due_date) tăng dần · chỉ phiếu bảo hành của trung tâm bạn.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3 rounded-lg border bg-white p-3">
        <label className="text-sm">
          Nhóm sự cố
          <select
            value={draftFilters.category_id}
            onChange={(e) => setDraftFilters({ ...draftFilters, category_id: e.target.value })}
            disabled={categories.loading || Boolean(categories.error)}
            className="mt-1 block w-44 rounded border p-2"
          >
            <option value="">Tất cả</option>
            {(categories.data || []).map((c) => (
              <option key={c.category_id} value={c.category_id}>{categoryLabel(c.category_name)}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Mức ưu tiên
          <select
            value={draftFilters.priority}
            onChange={(e) => setDraftFilters({ ...draftFilters, priority: e.target.value })}
            className="mt-1 block w-40 rounded border p-2"
          >
            <option value="">Tất cả</option>
            {Object.entries(PRIORITY_LABELS).map(([code, label]) => (
              <option key={code} value={code}>{label}</option>
            ))}
          </select>
        </label>
        <button onClick={applyFilters} className="rounded bg-blue-700 px-4 py-2 text-sm text-white hover:bg-blue-800">
          Áp dụng bộ lọc
        </button>
        {hasFilters && (
          <button onClick={clearFilters} className="rounded border px-4 py-2 text-sm hover:bg-gray-50">
            Xoá bộ lọc
          </button>
        )}
        {categories.error && (
          <span className="text-sm text-red-700">Không tải được danh sách nhóm sự cố.</span>
        )}
      </div>

      {tickets.data && items.length > 0 && (
        <p className="text-sm text-gray-700">
          <strong>{tickets.data.total}</strong> phiếu chờ phân công
          {hasFilters ? ' (theo bộ lọc)' : ''} ·{' '}
          <strong className={overdueOnPage ? 'text-red-700' : ''}>{overdueOnPage}</strong> /{' '}
          {items.length} phiếu trên trang này đã quá hạn cam kết SLA.
        </p>
      )}

      <DataState
        loading={tickets.loading}
        error={tickets.error}
        onRetry={tickets.reload}
        isEmpty={items.length === 0}
        empty={{
          filtered: hasFilters,
          message: 'Không có phiếu bảo hành nào đang chờ phân công.',
          hint: 'Mọi phiếu của trung tâm đã có kỹ thuật viên phụ trách.',
          filteredMessage: 'Không có phiếu nào khớp bộ lọc hiện tại.',
          onClearFilters: clearFilters,
        }}
      >
        <div className="overflow-x-auto rounded-lg border bg-white">
          <table className="w-full min-w-[960px] text-left text-sm">
            <thead className="bg-gray-100 text-gray-700">
              <tr>
                <th className="p-3">Mã phiếu</th>
                <th className="p-3">Khách hàng</th>
                <th className="p-3">SĐT</th>
                <th className="p-3">Serial/IMEI</th>
                <th className="p-3">Nhóm sự cố</th>
                <th className="p-3">Ưu tiên</th>
                <th className="p-3">Tiếp nhận</th>
                <th className="p-3">Hạn cam kết</th>
                <th className="p-3" />
              </tr>
            </thead>
            <tbody>
              {items.map((ticket) => {
                const sla = slaStatus(ticket.due_date)
                return (
                  <tr key={ticket.ticket_id} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-medium">{ticket.ticket_code}</td>
                    <td className="p-3">{ticket.customer_name}</td>
                    <td className="p-3 font-mono">{ticket.customer_phone}</td>
                    <td className="p-3 font-mono text-xs">{ticket.serial_no}</td>
                    <td className="p-3">{categoryLabel(ticket.category_name)}</td>
                    <td className="p-3">
                      <Badge tone={PRIORITY_TONE[ticket.priority]}>{PRIORITY_LABELS[ticket.priority]}</Badge>
                    </td>
                    <td className="p-3 whitespace-nowrap">{formatDateTime(ticket.received_at)}</td>
                    <td className="p-3 whitespace-nowrap">
                      {formatDateTime(ticket.due_date)}
                      <div className={`text-xs ${sla.overdue ? 'font-semibold text-red-700' : sla.soon ? 'text-amber-700' : 'text-gray-500'}`}>
                        {sla.text}
                      </div>
                    </td>
                    <td className="p-3">
                      <button
                        onClick={() => onAssign(ticket.ticket_id)}
                        className="rounded bg-blue-700 px-3 py-1 text-white hover:bg-blue-800"
                      >
                        Phân công
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <Pagination page={page} pageSize={PAGE_SIZE} total={tickets.data?.total || 0} onPageChange={setPage} />
      </DataState>
    </section>
  )
}

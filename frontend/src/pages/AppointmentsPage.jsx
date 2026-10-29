// M3 — Appointments (UC4 · US5, US6, US13 · FR6, FR7, FR11)
import { useEffect, useState } from 'react'
import { appointmentsApi } from '../api/appointments.api'
import { ticketsApi } from '../api/tickets.api'
import { Badge } from '../components/Badge'
import { DataState, Notice } from '../components/DataState'
import { Pagination } from '../components/Pagination'
import { useApi } from '../hooks/useApi'
import {
  APPOINTMENT_STATUS_LABELS, APPOINTMENT_STATUS_TONE, APPOINTMENT_TYPE_LABELS, CREATABLE_APPOINTMENT_TYPES,
  formatDate, formatTime,
} from '../labels'

const PAGE_SIZE = 10
const EMPTY_FORM = { loai: 'GIAO_MAY', ngay_hen: '', gio_bat_dau: '09:00', gio_ket_thuc: '10:00' }
const NO_FILTERS = { ngay_hen: '', trang_thai: '' }

export default function AppointmentsPage({ initialTicketId, onOpenTicket }) {
  // ----- target of the form: a ticket (create) or an existing appointment (edit)
  const [ticketIdInput, setTicketIdInput] = useState(initialTicketId ? String(initialTicketId) : '')
  const [targetTicketId, setTargetTicketId] = useState(initialTicketId || null)
  const [editing, setEditing] = useState(null) // appointment row being edited
  const [form, setForm] = useState(EMPTY_FORM)
  const [conflictResult, setConflictResult] = useState({ key: null, conflicts: [] })
  const [formResult, setFormResult] = useState(null)
  const [saving, setSaving] = useState(false)

  // ----- list
  const [filters, setFilters] = useState(NO_FILTERS)
  const [page, setPage] = useState(1)
  const [confirmDeleteId, setConfirmDeleteId] = useState(null)
  const [listResult, setListResult] = useState(null)

  const ticket = useApi(
    () => (targetTicketId ? ticketsApi.getTicket(targetTicketId) : Promise.resolve(null)),
    [targetTicketId],
  )
  const appointments = useApi(
    () => appointmentsApi.list({ page, page_size: PAGE_SIZE, ...filters }),
    [page, filters.ngay_hen, filters.trang_thai],
  )

  const technicianId = editing ? editing.technician_id : ticket.data?.technician_id
  const clientError = validateForm(form)

  // FR7 pre-check: ask the API for overlapping appointments while the user types.
  // The answer is stored with the inputs it was computed for (checkKey).
  const checkKey = technicianId && !clientError
    ? JSON.stringify([technicianId, form.ngay_hen, form.gio_bat_dau, form.gio_ket_thuc, editing?.appointment_id])
    : null
  const conflicts = checkKey && conflictResult.key === checkKey ? conflictResult.conflicts : []
  const checking = Boolean(checkKey) && conflictResult.key !== checkKey

  useEffect(() => {
    if (!checkKey) return undefined
    let cancelled = false
    const [technician_id, ngay_hen, gio_bat_dau, gio_ket_thuc, exclude_appointment_id] = JSON.parse(checkKey)
    const timer = setTimeout(() => {
      appointmentsApi
        .checkConflicts({ technician_id, ngay_hen, gio_bat_dau, gio_ket_thuc, exclude_appointment_id })
        .then((data) => { if (!cancelled) setConflictResult({ key: checkKey, conflicts: data.conflicts }) })
        // On failure the save-time check on the server stays authoritative.
        .catch(() => { if (!cancelled) setConflictResult({ key: checkKey, conflicts: [] }) })
    }, 300)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [checkKey])

  const loadTicket = (event) => {
    event.preventDefault()
    const id = parseInt(ticketIdInput, 10)
    if (!Number.isInteger(id) || id <= 0) { setFormResult({ kind: 'error', text: 'Mã số phiếu phải là số nguyên dương.' }); return }
    cancelEdit()
    setTargetTicketId(id)
  }

  const startEdit = (row) => {
    setEditing(row)
    setForm({ loai: row.loai, ngay_hen: row.ngay_hen, gio_bat_dau: formatTime(row.gio_bat_dau), gio_ket_thuc: formatTime(row.gio_ket_thuc) })
    setFormResult(null)
  }

  function cancelEdit() {
    setEditing(null)
    setForm(EMPTY_FORM)
    setFormResult(null)
  }

  const ticketReady = Boolean(ticket.data?.technician_id)
  const canSave = !saving && !clientError && !checking && conflicts.length === 0 && (editing || ticketReady)

  const handleSave = async (event) => {
    event.preventDefault()
    setSaving(true)
    setFormResult(null)
    try {
      if (editing) {
        await appointmentsApi.update(editing.appointment_id, form)
        setFormResult({ kind: 'success', text: `Đã cập nhật lịch hẹn #${editing.appointment_id}.` })
        setEditing(null)
      } else {
        const created = await appointmentsApi.create({ ticket_id: targetTicketId, ...form })
        setFormResult({ kind: 'success', text: `Đã tạo lịch hẹn #${created.appointment_id} (Đã xác nhận).` })
      }
      setForm(EMPTY_FORM)
      appointments.reload()
    } catch (err) {
      if (err.code === 'appointment_conflict') setConflictResult({ key: checkKey, conflicts: err.conflicts })
      setFormResult({ kind: 'error', text: err.message })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (row) => {
    setListResult(null)
    try {
      await appointmentsApi.remove(row.appointment_id)
      setListResult({ kind: 'success', text: `Đã xoá lịch hẹn #${row.appointment_id}.` })
      if (editing?.appointment_id === row.appointment_id) cancelEdit()
      appointments.reload()
    } catch (err) {
      setListResult({ kind: 'error', text: err.message })
    } finally {
      setConfirmDeleteId(null)
    }
  }

  const hasFilters = Boolean(filters.ngay_hen || filters.trang_thai)
  const setFilter = (key, value) => { setPage(1); setFilters({ ...filters, [key]: value }) }
  const items = appointments.data?.items || []

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* ------------------------------------------------ form */}
      <section className="h-fit min-w-0 space-y-4 rounded-lg border bg-white p-5 lg:col-span-1">
        <h2 className="text-lg font-bold">{editing ? `Sửa lịch hẹn #${editing.appointment_id}` : 'Đặt lịch hẹn mới'}</h2>

        {!editing && (
          <form onSubmit={loadTicket} className="flex items-end gap-2">
            <label className="flex-1 text-sm">
              Mã số phiếu (ticket_id)
              <input
                inputMode="numeric"
                value={ticketIdInput}
                onChange={(e) => setTicketIdInput(e.target.value)}
                placeholder="VD: lấy từ M2"
                className="mt-1 w-full rounded border p-2"
              />
            </label>
            <button className="rounded border px-3 py-2 text-sm hover:bg-gray-50">Tải phiếu</button>
          </form>
        )}

        {/* read-only summary: system-derived, not editable (wireframe M3) */}
        <TicketSummary editing={editing} ticket={ticket} />

        <form onSubmit={handleSave} className="space-y-3">
          <label className="block text-sm">
            Loại lịch hẹn
            <select
              value={form.loai}
              onChange={(e) => setForm({ ...form, loai: e.target.value })}
              className="mt-1 w-full rounded border p-2"
            >
              {CREATABLE_APPOINTMENT_TYPES.map((code) => (
                <option key={code} value={code}>{APPOINTMENT_TYPE_LABELS[code]}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            Ngày hẹn
            <input
              type="date"
              value={form.ngay_hen}
              onChange={(e) => setForm({ ...form, ngay_hen: e.target.value })}
              required
              className="mt-1 w-full rounded border p-2"
            />
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-sm">
              Giờ bắt đầu
              <input type="time" value={form.gio_bat_dau} required
                onChange={(e) => setForm({ ...form, gio_bat_dau: e.target.value })}
                className="mt-1 w-full rounded border p-2" />
            </label>
            <label className="text-sm">
              Giờ kết thúc
              <input type="time" value={form.gio_ket_thuc} required
                onChange={(e) => setForm({ ...form, gio_ket_thuc: e.target.value })}
                className="mt-1 w-full rounded border p-2" />
            </label>
          </div>

          {form.ngay_hen && clientError && <Notice kind="error">{clientError}</Notice>}

          {conflicts.length > 0 && (
            <Notice kind="warning">
              <p className="font-semibold">Trùng lịch – không thể lưu (FR7)</p>
              <ul className="mt-1 list-disc pl-5">
                {conflicts.map((c) => (
                  <li key={c.appointment_id}>
                    Lịch #{c.appointment_id}: {formatDate(c.ngay_hen)} {formatTime(c.gio_bat_dau)}–{formatTime(c.gio_ket_thuc)}
                  </li>
                ))}
              </ul>
            </Notice>
          )}
          {checking && <p className="text-xs text-gray-500">Đang kiểm tra trùng lịch…</p>}
          {formResult && <Notice kind={formResult.kind}>{formResult.text}</Notice>}

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={!canSave}
              className="flex-1 rounded bg-blue-700 py-2 text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {saving ? 'Đang lưu…' : editing ? 'Lưu thay đổi' : 'Lưu & xác nhận'}
            </button>
            {editing && (
              <button type="button" onClick={cancelEdit} className="rounded border px-3 py-2 hover:bg-gray-50">
                Huỷ sửa
              </button>
            )}
          </div>
        </form>
      </section>

      {/* ------------------------------------------------ list */}
      <section className="min-w-0 space-y-3 lg:col-span-2">
        <h2 className="text-2xl font-bold">M3 · Lịch hẹn của trung tâm</h2>

        <div className="flex flex-wrap items-end gap-3 rounded-lg border bg-white p-3">
          <label className="text-sm">
            Ngày hẹn
            <input type="date" value={filters.ngay_hen} onChange={(e) => setFilter('ngay_hen', e.target.value)}
              className="mt-1 block rounded border p-2" />
          </label>
          <label className="text-sm">
            Trạng thái
            <select value={filters.trang_thai} onChange={(e) => setFilter('trang_thai', e.target.value)}
              className="mt-1 block w-44 rounded border p-2">
              <option value="">Tất cả</option>
              {Object.entries(APPOINTMENT_STATUS_LABELS).map(([code, label]) => (
                <option key={code} value={code}>{label}</option>
              ))}
            </select>
          </label>
          {hasFilters && (
            <button onClick={() => { setPage(1); setFilters(NO_FILTERS) }} className="rounded border px-4 py-2 text-sm hover:bg-gray-50">
              Xoá bộ lọc
            </button>
          )}
        </div>

        {listResult && <Notice kind={listResult.kind}>{listResult.text}</Notice>}

        <DataState
          loading={appointments.loading}
          error={appointments.error}
          onRetry={appointments.reload}
          isEmpty={items.length === 0}
          empty={{
            filtered: hasFilters,
            message: 'Chưa có lịch hẹn nào.',
            hint: 'Chọn một phiếu đã phân công ở M2 rồi bấm “Đặt lịch hẹn”.',
            filteredMessage: 'Không có lịch hẹn nào khớp bộ lọc hiện tại.',
            onClearFilters: () => { setPage(1); setFilters(NO_FILTERS) },
          }}
        >
          <div className="overflow-x-auto rounded-lg border bg-white">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-gray-100 text-gray-700">
                <tr>
                  <th className="p-3">Phiếu</th>
                  <th className="p-3">Kỹ thuật viên</th>
                  <th className="p-3">Loại</th>
                  <th className="p-3">Ngày · giờ</th>
                  <th className="p-3">Trạng thái</th>
                  <th className="p-3" />
                </tr>
              </thead>
              <tbody>
                {items.map((row) => {
                  const completed = row.trang_thai === 'HOAN_TAT'
                  return (
                    <tr key={row.appointment_id} className={`border-t ${editing?.appointment_id === row.appointment_id ? 'bg-blue-50' : ''}`}>
                      <td className="p-3">
                        <button onClick={() => onOpenTicket(row.ticket_id)} className="text-blue-700 hover:underline">
                          {row.ticket_code}
                        </button>
                      </td>
                      <td className="p-3">{row.technician_ho_ten}</td>
                      <td className="p-3">{APPOINTMENT_TYPE_LABELS[row.loai] || row.loai}</td>
                      <td className="p-3 whitespace-nowrap">
                        {formatDate(row.ngay_hen)} · {formatTime(row.gio_bat_dau)}–{formatTime(row.gio_ket_thuc)}
                      </td>
                      <td className="p-3">
                        <Badge tone={APPOINTMENT_STATUS_TONE[row.trang_thai]}>
                          {APPOINTMENT_STATUS_LABELS[row.trang_thai] || row.trang_thai}
                        </Badge>
                      </td>
                      <td className="space-x-2 p-3 whitespace-nowrap">
                        <button disabled={completed} onClick={() => startEdit(row)}
                          title={completed ? 'Lịch đã hoàn tất' : ''}
                          className="text-blue-700 hover:underline disabled:cursor-not-allowed disabled:text-gray-400 disabled:no-underline">
                          Sửa
                        </button>
                        {confirmDeleteId === row.appointment_id ? (
                          <>
                            <button onClick={() => handleDelete(row)} className="font-semibold text-red-700 hover:underline">Xác nhận xoá</button>
                            <button onClick={() => setConfirmDeleteId(null)} className="text-gray-600 hover:underline">Không</button>
                          </>
                        ) : (
                          <button disabled={completed} onClick={() => setConfirmDeleteId(row.appointment_id)}
                            title={completed ? 'Lịch đã hoàn tất' : ''}
                            className="text-red-700 hover:underline disabled:cursor-not-allowed disabled:text-gray-400 disabled:no-underline">
                            Xoá
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={PAGE_SIZE} total={appointments.data?.total || 0} onPageChange={setPage} />
        </DataState>
      </section>
    </div>
  )
}

function TicketSummary({ editing, ticket }) {
  if (editing) {
    return (
      <Notice kind="info">
        Phiếu <strong>{editing.ticket_code}</strong> · KTV <strong>{editing.technician_ho_ten}</strong> · Trung tâm {editing.center_id}
      </Notice>
    )
  }
  if (ticket.loading) return <p className="text-sm text-gray-500">Đang tải phiếu…</p>
  if (ticket.error) return <Notice kind="error">{ticket.error.message}</Notice>
  if (!ticket.data) return <Notice kind="info">Nhập mã số phiếu hoặc mở M3 từ màn hình M2 để đặt lịch.</Notice>
  if (!ticket.data.technician_id) {
    return <Notice kind="warning">Phiếu {ticket.data.ticket_code} chưa có kỹ thuật viên. Hãy phân công ở M2 trước.</Notice>
  }
  return (
    <Notice kind="info">
      Phiếu <strong>{ticket.data.ticket_code}</strong> · KTV <strong>{ticket.data.technician_ho_ten}</strong> · Trung tâm {ticket.data.center_id}
    </Notice>
  )
}

// Format checks done before calling the API (the API re-checks everything).
function validateForm(form) {
  if (!form.ngay_hen || !form.gio_bat_dau || !form.gio_ket_thuc) return 'Vui lòng nhập đủ ngày và giờ hẹn.'
  if (form.gio_ket_thuc <= form.gio_bat_dau) return 'Giờ kết thúc phải sau giờ bắt đầu.'
  if (new Date(`${form.ngay_hen}T${form.gio_bat_dau}`) <= new Date()) return 'Thời gian hẹn phải ở tương lai.'
  return null
}

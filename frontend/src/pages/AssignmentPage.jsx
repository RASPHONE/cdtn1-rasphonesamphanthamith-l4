// M2 — Ticket detail & technician assignment (UC2, UC3 · US2, US3, US4 · FR2–FR5, FR8)
import { useState } from 'react'
import { ticketsApi } from '../api/tickets.api'
import { Badge } from '../components/Badge'
import { DataState, ErrorPanel, Notice } from '../components/DataState'
import { useApi } from '../hooks/useApi'
import {
  LEVEL_LABELS, PRIORITY_LABELS, PRIORITY_TONE, TICKET_STATUS_LABELS, categoryLabel, formatDateTime, slaStatus,
} from '../labels'

const REASON_MIN = 5
const REASON_MAX = 255

export default function AssignmentPage({ ticketId, onBack, onSchedule }) {
  const ticket = useApi(() => ticketsApi.getTicket(ticketId), [ticketId])
  const technicians = useApi(() => ticketsApi.listQualifiedTechnicians(ticketId), [ticketId])

  const [selectedId, setSelectedId] = useState(null)
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null) // { kind, text }

  const reloadAll = () => { ticket.reload(); technicians.reload() }

  if (ticket.loading) return <DataState loading />
  if (ticket.error) return <><BackLink onBack={onBack} /><ErrorPanel error={ticket.error} onRetry={reloadAll} /></>

  const current = ticket.data
  const isReassignment = current.technician_id !== null
  const items = technicians.data?.items || []
  const averageWorkload = items.length
    ? items.reduce((sum, t) => sum + t.workload, 0) / items.length
    : 0
  const trimmedReason = reason.trim()
  const reasonValid = trimmedReason.length >= REASON_MIN && trimmedReason.length <= REASON_MAX
  const canSubmit = selectedId !== null && !submitting && (!isReassignment || reasonValid)

  const handleConfirm = async () => {
    setSubmitting(true)
    setResult(null)
    try {
      if (isReassignment) {
        await ticketsApi.reassignTechnician(ticketId, selectedId, trimmedReason)
      } else {
        await ticketsApi.assignTechnician(ticketId, selectedId)
      }
      const chosen = items.find((t) => t.technician_id === selectedId)
      setResult({
        kind: 'success',
        text: `${isReassignment ? 'Đã đổi' : 'Đã phân công'} phiếu ${current.ticket_code} cho ${chosen?.ho_ten}.`,
      })
      setSelectedId(null)
      setReason('')
      reloadAll()
    } catch (err) {
      // UC3-7a / UC3-8a: show the reason, keep what the manager entered.
      setResult({ kind: 'error', text: err.message })
    } finally {
      setSubmitting(false)
    }
  }

  const sla = slaStatus(current.due_date)

  return (
    <section className="space-y-4">
      <BackLink onBack={onBack} />
      <h2 className="text-2xl font-bold">M2 · Phân công kỹ thuật viên – {current.ticket_code}</h2>

      {/* Ticket summary (read-only) */}
      <dl className="grid gap-x-6 gap-y-2 rounded-lg border bg-white p-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Nhóm sự cố">{categoryLabel(current.category_name)}</Field>
        <Field label="Ưu tiên"><Badge tone={PRIORITY_TONE[current.priority]}>{PRIORITY_LABELS[current.priority]}</Badge></Field>
        <Field label="Trạng thái">{TICKET_STATUS_LABELS[current.status] || current.status}</Field>
        <Field label="Hạn cam kết">
          {formatDateTime(current.due_date)}{' '}
          <span className={sla.overdue ? 'font-semibold text-red-700' : 'text-gray-500'}>({sla.text})</span>
        </Field>
        <Field label="Khách hàng">{current.customer_name}</Field>
        <Field label="SĐT"><span className="font-mono">{current.customer_phone}</span></Field>
        <Field label="Serial/IMEI"><span className="font-mono">{current.serial_no}</span></Field>
        <Field label="KTV phụ trách">{current.technician_ho_ten || 'Chưa phân công'}</Field>
        <Field label="Mô tả lỗi">{current.issue_desc}</Field>
      </dl>

      <div className="space-y-2">
        <h3 className="font-semibold">
          Kỹ thuật viên đủ điều kiện <span className="font-normal text-gray-500">(cùng trung tâm, đang hoạt động, tay nghề ≥ 3)</span>
        </h3>
        <DataState
          loading={technicians.loading}
          error={technicians.error}
          onRetry={technicians.reload}
          isEmpty={items.length === 0}
          empty={{
            filtered: false,
            message: 'Không có kỹ thuật viên nào đủ điều kiện cho nhóm sự cố này.',
            hint: 'Nút xác nhận bị vô hiệu. Hãy bổ sung tay nghề cho kỹ thuật viên hoặc chuyển phiếu.',
          }}
        >
          <div className="overflow-x-auto rounded-lg border bg-white">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="bg-gray-100 text-gray-700">
                <tr>
                  <th className="p-3">Chọn</th>
                  <th className="p-3">Kỹ thuật viên</th>
                  <th className="p-3">Cấp độ</th>
                  <th className="p-3">Tay nghề</th>
                  <th className="p-3">Phiếu đang xử lý</th>
                </tr>
              </thead>
              <tbody>
                {items.map((tech) => {
                  const isCurrent = tech.technician_id === current.technician_id
                  const diff = tech.workload - averageWorkload
                  return (
                    <tr key={tech.technician_id} className={`border-t ${isCurrent ? 'bg-gray-50 text-gray-500' : ''}`}>
                      <td className="p-3">
                        <input
                          type="radio"
                          name="technician"
                          aria-label={`Chọn ${tech.ho_ten}`}
                          disabled={isCurrent}
                          checked={selectedId === tech.technician_id}
                          onChange={() => setSelectedId(tech.technician_id)}
                        />
                      </td>
                      <td className="p-3">
                        {tech.ho_ten} <span className="text-gray-500">({tech.technician_code})</span>
                        {isCurrent && <Badge tone="blue"> đang phụ trách</Badge>}
                      </td>
                      <td className="p-3">{LEVEL_LABELS[tech.level] || tech.level}</td>
                      <td className="p-3">{tech.proficiency}/5</td>
                      <td className="p-3">
                        {tech.workload} phiếu{' '}
                        <span className={`text-xs ${diff > 0 ? 'text-red-700' : 'text-green-700'}`}>
                          ({diff >= 0 ? '+' : ''}{diff.toFixed(1)} so với TB {averageWorkload.toFixed(1)})
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </DataState>
      </div>

      {isReassignment && (
        <label className="block text-sm font-medium">
          Lý do đổi kỹ thuật viên <span className="text-red-700">*</span>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={REASON_MAX}
            rows={2}
            placeholder="Bắt buộc khi đổi kỹ thuật viên (QT-07)"
            className="mt-1 w-full rounded border p-2 font-normal"
          />
          <span className={`text-xs ${reason && !reasonValid ? 'text-red-700' : 'text-gray-500'}`}>
            {trimmedReason.length}/{REASON_MAX} ký tự · tối thiểu {REASON_MIN}
          </span>
        </label>
      )}

      {result && <Notice kind={result.kind}>{result.text}</Notice>}

      <div className="flex flex-wrap gap-3">
        <button
          onClick={handleConfirm}
          disabled={!canSubmit}
          className="rounded bg-green-700 px-4 py-2 text-white hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {submitting ? 'Đang lưu…' : isReassignment ? 'Xác nhận đổi kỹ thuật viên' : 'Xác nhận phân công'}
        </button>
        <button
          onClick={() => onSchedule(ticketId)}
          disabled={!isReassignment}
          title={isReassignment ? '' : 'Cần phân công kỹ thuật viên trước'}
          className="rounded border border-blue-700 px-4 py-2 text-blue-700 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Đặt lịch hẹn → M3
        </button>
      </div>
    </section>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-gray-500">{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

function BackLink({ onBack }) {
  return (
    <button onClick={onBack} className="text-sm text-blue-700 hover:underline">
      ← Quay lại danh sách M1
    </button>
  )
}

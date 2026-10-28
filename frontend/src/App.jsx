import { useEffect, useState } from 'react'
import { SESSION_EXPIRED_EVENT } from './api/client'
import { clearSession, getSession } from './api/session'
import AppointmentsPage from './pages/AppointmentsPage'
import AssignmentPage from './pages/AssignmentPage'
import LoginPage from './pages/LoginPage'
import UnassignedTicketsPage from './pages/UnassignedTicketsPage'

const ROLE_LABELS = { CENTER_MANAGER: 'Quản lý trung tâm', BOARD_OF_DIRECTORS: 'Ban giám đốc' }

export default function App() {
  const [session, setSession] = useState(getSession)
  const [loginNotice, setLoginNotice] = useState('')
  // screen: { name: 'm1' } | { name: 'm2', ticketId } | { name: 'm3', ticketId? }
  const [screen, setScreen] = useState({ name: 'm1' })

  useEffect(() => {
    const onExpired = () => {
      setSession(null)
      setLoginNotice('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.')
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [])

  if (!session) {
    return (
      <LoginPage
        notice={loginNotice}
        onLoggedIn={() => { setSession(getSession()); setLoginNotice(''); setScreen({ name: 'm1' }) }}
      />
    )
  }

  const logout = () => { clearSession(); setSession(null) }
  const navClass = (name) =>
    `rounded px-3 py-1.5 ${screen.name === name ? 'bg-white/20 font-semibold' : 'hover:bg-white/10'}`

  return (
    <div className="min-h-screen">
      <header className="bg-blue-800 text-white shadow">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div>
            <h1 className="font-bold">Mekong Mobile · L4</h1>
            <p className="text-xs text-blue-100">
              {ROLE_LABELS[session.role] || session.role} · Trung tâm {session.center_id} · {session.username}
            </p>
          </div>
          <nav className="flex flex-wrap items-center gap-2 text-sm">
            <button className={navClass('m1')} onClick={() => setScreen({ name: 'm1' })}>M1 · Phiếu chờ phân công</button>
            <button className={navClass('m3')} onClick={() => setScreen({ name: 'm3' })}>M3 · Lịch hẹn</button>
            <button onClick={logout} className="rounded bg-red-600 px-3 py-1.5 hover:bg-red-700">Đăng xuất</button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        {screen.name === 'm1' && (
          <UnassignedTicketsPage onAssign={(ticketId) => setScreen({ name: 'm2', ticketId })} />
        )}
        {screen.name === 'm2' && (
          <AssignmentPage
            key={screen.ticketId}
            ticketId={screen.ticketId}
            onBack={() => setScreen({ name: 'm1' })}
            onSchedule={(ticketId) => setScreen({ name: 'm3', ticketId })}
          />
        )}
        {screen.name === 'm3' && (
          <AppointmentsPage
            key={screen.ticketId || 'all'}
            initialTicketId={screen.ticketId}
            onOpenTicket={(ticketId) => setScreen({ name: 'm2', ticketId })}
          />
        )}
      </main>
    </div>
  )
}

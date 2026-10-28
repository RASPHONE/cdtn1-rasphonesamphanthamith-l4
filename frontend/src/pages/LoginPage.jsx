import { useState } from 'react'
import { authApi } from '../api/auth.api'
import { saveSession } from '../api/session'
import { Notice } from '../components/DataState'

export default function LoginPage({ onLoggedIn, notice }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const session = await authApi.login(username.trim(), password)
      saveSession({ ...session, username: username.trim() })
      onLoggedIn()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-lg bg-white p-8 shadow">
        <div>
          <h1 className="text-xl font-bold">Đăng nhập Quản lý trung tâm</h1>
          <p className="text-sm text-gray-500">Mekong Mobile · Phân công kỹ thuật viên & lịch hẹn</p>
        </div>

        {notice && <Notice kind="info">{notice}</Notice>}
        {error && <Notice kind="error">{error}</Notice>}

        <label className="block text-sm font-medium">
          Tên đăng nhập
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
            className="mt-1 w-full rounded border p-2"
          />
        </label>
        <label className="block text-sm font-medium">
          Mật khẩu
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            className="mt-1 w-full rounded border p-2"
          />
        </label>
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded bg-blue-700 py-2 font-medium text-white hover:bg-blue-800 disabled:opacity-50"
        >
          {submitting ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </button>
        <p className="text-xs text-gray-500">Tài khoản demo: xem README mục “Demo accounts”.</p>
      </form>
    </div>
  )
}

// The ONLY place in the frontend that knows about HTTP (fetch, headers, status codes).
// Pages call the functions in src/api/*.api.js, never fetch() directly.

import { clearSession, getToken } from './session'
import { messageForError } from '../labels'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor({ status, code, message, details, conflicts, requestId }) {
    super(message)
    this.status = status // HTTP status, 0 = server unreachable
    this.code = code // business code from the backend, e.g. "appointment_conflict"
    this.details = details || []
    this.conflicts = conflicts || []
    this.requestId = requestId
  }
}

export const SESSION_EXPIRED_EVENT = 'session-expired'

export async function request(path, { method = 'GET', body, query } = {}) {
  const url = new URL(`${BASE_URL}${path}`)
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value)
  })

  const token = getToken()
  let response
  try {
    response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    // Backend not running / network down: fetch itself throws.
    throw new ApiError({ status: 0, code: 'network_error', message: messageForError('network_error') })
  }

  if (response.status === 204) return null

  let data = null
  try {
    data = await response.json()
  } catch {
    // Response without a JSON body (e.g. a proxy error page).
  }

  if (!response.ok) {
    const code = data?.error || 'unknown_error'
    // An expired/invalid token on any call except the login itself ends the session.
    if (response.status === 401 && path !== '/api/auth/login') {
      clearSession()
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
    }
    throw new ApiError({
      status: response.status,
      code,
      message: messageForError(code, data),
      details: data?.details,
      conflicts: data?.conflicts,
      requestId: data?.request_id,
    })
  }

  return data
}

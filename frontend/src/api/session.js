// Session storage for the demo login.
// Limitation (documented in README): the token lives in localStorage, which a
// script injected through an XSS bug could read. Acceptable for the BT2 prototype;
// an HttpOnly cookie set by the server would be safer.

const KEY = 'l4_session'

export function saveSession(session) {
  localStorage.setItem(KEY, JSON.stringify(session))
}

export function getSession() {
  try {
    return JSON.parse(localStorage.getItem(KEY))
  } catch {
    return null
  }
}

export function getToken() {
  return getSession()?.access_token || null
}

export function clearSession() {
  localStorage.removeItem(KEY)
}

import { request } from './client'

export const authApi = {
  login: (username, password) =>
    request('/api/auth/login', { method: 'POST', body: { username, password } }),
}

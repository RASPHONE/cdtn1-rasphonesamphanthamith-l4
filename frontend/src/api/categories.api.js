import { request } from './client'

export const categoriesApi = {
  // Filter options come from the issue_category table (NFR7), not from code.
  listActive: () => request('/api/issue-categories'),
}

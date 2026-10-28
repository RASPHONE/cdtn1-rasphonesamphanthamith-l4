# Frontend — M1 · M2 · M3 (React 19 + Vite 8 + Tailwind CSS 4)

Center-manager screens for flow L4. Start the backend first (root README), then:

```bash
cp .env.example .env      # VITE_API_BASE_URL=http://localhost:8000
npm ci
npm run dev               # http://localhost:5173
```

| Folder | Role |
|---|---|
| `src/api/` | The only code that calls the backend (`client.js` = fetch, token, error translation). |
| `src/pages/` | One file per wireframe screen: `UnassignedTicketsPage` (M1), `AssignmentPage` (M2), `AppointmentsPage` (M3), `LoginPage`. |
| `src/components/` | Reusable UI: `DataState` (loading / empty / error), `Badge`, `Pagination`. |
| `src/hooks/useApi.js` | Loads one API call and exposes `loading`, `error`, `data`, `reload`. |
| `src/labels.js` | Vietnamese labels for API codes and error messages (single place). |

Naming: code identifiers are English camelCase; API fields keep the exact ERD
column names (`ngay_hen`, `gio_bat_dau`, `trang_thai`, ...).

Token storage: the demo JWT is kept in `localStorage` (`src/api/session.js`).
Limitation: readable by injected scripts if an XSS bug existed; acceptable for
the BT2 prototype, an HttpOnly cookie would be the production choice.

Checks: `npm run lint` · `npm run build`.

// The three states required by BT2 (loading / empty / error) for any list.
//
// empty.filtered = true  -> "no row matches the current filter" + clear-filter action
// empty.filtered = false -> "there is no data yet" (a different message, different action)
export function DataState({ loading, error, isEmpty, empty, onRetry, children }) {
  if (loading) {
    return (
      <div role="status" className="flex items-center justify-center gap-3 rounded-lg border bg-white py-12 text-blue-700">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        Đang tải dữ liệu…
      </div>
    )
  }

  if (error) return <ErrorPanel error={error} onRetry={onRetry} />

  if (isEmpty) {
    return (
      <div className="rounded-lg border border-dashed bg-white px-6 py-12 text-center text-gray-600">
        <p className="font-medium">{empty.filtered ? empty.filteredMessage : empty.message}</p>
        {empty.filtered && empty.onClearFilters && (
          <button
            onClick={empty.onClearFilters}
            className="mt-4 rounded border border-blue-600 px-3 py-1.5 text-sm text-blue-700 hover:bg-blue-50"
          >
            Xoá bộ lọc
          </button>
        )}
        {!empty.filtered && empty.hint && <p className="mt-2 text-sm text-gray-500">{empty.hint}</p>}
      </div>
    )
  }

  return children
}

export function ErrorPanel({ error, onRetry }) {
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
      <p className="font-semibold">Không tải được dữ liệu</p>
      <p className="mt-1 text-sm">{error.message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-3 rounded bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700">
          Thử lại
        </button>
      )}
    </div>
  )
}

export function Notice({ kind = 'error', children }) {
  const styles = {
    error: 'border-red-200 bg-red-50 text-red-800',
    warning: 'border-amber-300 bg-amber-50 text-amber-900',
    success: 'border-green-200 bg-green-50 text-green-800',
    info: 'border-blue-200 bg-blue-50 text-blue-900',
  }
  return (
    <div role={kind === 'error' ? 'alert' : 'status'} className={`rounded-lg border p-3 text-sm ${styles[kind]}`}>
      {children}
    </div>
  )
}

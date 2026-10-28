export function Pagination({ page, pageSize, total, onPageChange }) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  return (
    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-gray-600">
      <span>
        Trang {page}/{pageCount} · {total} dòng · {pageSize} dòng/trang
      </span>
      <div className="flex gap-2">
        <button
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="rounded border bg-white px-3 py-1 disabled:opacity-40"
        >
          ← Trước
        </button>
        <button
          disabled={page >= pageCount}
          onClick={() => onPageChange(page + 1)}
          className="rounded border bg-white px-3 py-1 disabled:opacity-40"
        >
          Sau →
        </button>
      </div>
    </div>
  )
}

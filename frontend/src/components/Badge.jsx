const TONES = {
  gray: 'bg-gray-100 text-gray-700',
  red: 'bg-red-100 text-red-800',
  amber: 'bg-amber-100 text-amber-800',
  green: 'bg-green-100 text-green-800',
  blue: 'bg-blue-100 text-blue-800',
}

export function Badge({ tone = 'gray', children }) {
  return <span className={`inline-block whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>{children}</span>
}

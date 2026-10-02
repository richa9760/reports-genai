/** Small inline feedback messages: loading, error, success and empty states. */
function Banner({ kind, children }) {
  if (!children) return null
  return <p className={`banner banner--${kind}`}>{children}</p>
}

export function LoadingMessage({ children = 'Loading...' }) {
  return <Banner kind="loading">{children}</Banner>
}

export function ErrorMessage({ children }) {
  return <Banner kind="error">{children}</Banner>
}

export function SuccessMessage({ children }) {
  return <Banner kind="success">{children}</Banner>
}

export function EmptyMessage({ children }) {
  return <Banner kind="empty">{children}</Banner>
}

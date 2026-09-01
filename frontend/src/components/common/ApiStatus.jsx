import { useEffect, useState } from 'react'
import { getHealth } from '../../api/client'

function Dot({ className }) {
  return <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${className}`} />
}

export default function ApiStatus() {
  const [state, setState] = useState({ loading: true, ok: false, detail: null })

  useEffect(() => {
    let cancelled = false
    getHealth()
      .then((data) => {
        if (!cancelled) setState({ loading: false, ok: true, detail: data })
      })
      .catch((err) => {
        if (!cancelled) setState({ loading: false, ok: false, detail: err.message })
      })
    return () => {
      cancelled = true
    }
  }, [])

  const shell =
    'inline-flex items-center gap-2 rounded-full bg-white px-3 py-1.5 text-xs font-medium ring-1 ring-inset'

  if (state.loading) {
    return (
      <span className={`${shell} text-slate-500 ring-slate-200`}>
        <Dot className="animate-pulse bg-slate-400" />
        Checking API…
      </span>
    )
  }

  if (!state.ok) {
    return (
      <span
        className={`${shell} text-red-700 ring-red-200`}
        title="Requests go to /api/v1 on this page's own origin, proxied to the backend by vite.config.js in dev or nginx in Docker. Check the backend is running and the proxy target is correct."
      >
        <Dot className="bg-red-500" />
        API unreachable
      </span>
    )
  }

  const dbStatus = state.detail?.dependencies?.database ?? 'unknown'
  const dbOk = dbStatus === 'up'

  return (
    <span className={`${shell} text-slate-600 ring-slate-200`}>
      <Dot className={dbOk ? 'bg-emerald-500' : 'bg-amber-500'} />
      API connected
      <span className="text-slate-300">·</span>
      <span className={dbOk ? 'text-slate-500' : 'text-amber-600'}>database {dbStatus}</span>
    </span>
  )
}

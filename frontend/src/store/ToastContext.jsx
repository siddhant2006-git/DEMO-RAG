import { createContext, useCallback, useContext, useRef, useState } from 'react'
import { AlertIcon, CheckIcon } from '../components/common/icons'

const ToastContext = createContext(null)

const VARIANTS = {
  success: {
    shell: 'bg-white ring-emerald-200',
    icon: 'bg-emerald-100 text-emerald-700',
    Icon: CheckIcon,
  },
  error: {
    shell: 'bg-white ring-red-200',
    icon: 'bg-red-100 text-red-700',
    Icon: AlertIcon,
  },
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const nextId = useRef(0)

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const notify = useCallback(
    (message, { type = 'success', duration = 4500 } = {}) => {
      const id = nextId.current++
      setToasts((prev) => [...prev, { id, message, type }])
      if (duration) setTimeout(() => dismiss(id), duration)
      return id
    },
    [dismiss],
  )

  return (
    <ToastContext.Provider value={{ notify, dismiss }}>
      {children}
      <div
        className="pointer-events-none fixed bottom-5 right-5 z-50 flex w-[22rem] max-w-[calc(100vw-2.5rem)] flex-col gap-2.5"
        aria-live="polite"
      >
        {toasts.map((t) => {
          const v = VARIANTS[t.type] ?? VARIANTS.success
          return (
            <div
              key={t.id}
              role="status"
              className={`pointer-events-auto flex items-start gap-3 rounded-xl p-3.5 shadow-lg ring-1 ring-inset ${v.shell}`}
              style={{ animation: 'toast-in 200ms cubic-bezier(0.16, 1, 0.3, 1)' }}
            >
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${v.icon}`}
              >
                <v.Icon className="h-3.5 w-3.5" />
              </span>
              <p className="flex-1 pt-0.5 text-sm leading-snug text-slate-700">{t.message}</p>
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                aria-label="Dismiss notification"
                className="-m-1 shrink-0 rounded p-1 text-lg leading-none text-slate-300 transition-colors hover:text-slate-600"
              >
                ×
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

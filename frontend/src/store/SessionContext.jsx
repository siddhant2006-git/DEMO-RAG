import { createContext, useContext, useEffect, useState } from 'react'

const SessionContext = createContext(null)

function readStored() {
  try {
    return JSON.parse(localStorage.getItem('tenderguard.session') || '{}')
  } catch {
    return {}
  }
}

export function SessionProvider({ children }) {
  const [session, setSession] = useState(readStored)

  useEffect(() => {
    try {
      localStorage.setItem('tenderguard.session', JSON.stringify(session))
    } catch {
      // best-effort persistence only
    }
  }, [session])

  const update = (patch) => setSession((prev) => ({ ...prev, ...patch }))
  const reset = () => setSession({})

  return <SessionContext.Provider value={{ ...session, update, reset }}>{children}</SessionContext.Provider>
}

export function useSession() {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used within SessionProvider')
  return ctx
}

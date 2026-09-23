import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../store/AuthContext'
import { CheckIcon, ShieldIcon } from '../components/common/icons'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await login(identifier, password)
      navigate(location.state?.from?.pathname || '/')
    } catch (requestError) {
      setError(requestError.response?.data?.message || 'Unable to sign in. Check your details.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="relative flex min-h-screen items-center overflow-hidden bg-brand-50 px-4 py-6 sm:px-8 lg:px-12">
      <div className="pointer-events-none absolute inset-0 opacity-70" aria-hidden="true">
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full border border-brand-200/70" />
        <div className="absolute -bottom-48 -right-24 h-136 w-136 rounded-full border border-brand-200/60" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(24,71,79,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(24,71,79,0.035)_1px,transparent_1px)] bg-size-[36px_36px]" />
      </div>

      <section className="relative mx-auto grid w-full max-w-5xl overflow-hidden rounded-2xl border border-brand-100 bg-white shadow-2xl shadow-brand-900/10 lg:grid-cols-[0.9fr_1.1fr]">
        <aside className="relative hidden overflow-hidden bg-brand-100 px-10 py-10 text-brand-950 lg:flex lg:flex-col lg:justify-between">
          <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full border border-brand-300/40" aria-hidden="true" />
          <div>
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-800 text-white shadow-lg shadow-brand-900/15">
                <ShieldIcon className="h-5 w-5" />
              </span>
              <div>
                <p className="text-base font-semibold tracking-tight">TenderGuard</p>
                <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-brand-700">Compliance workspace</p>
              </div>
            </div>
            <div className="mt-24 max-w-xs">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-700">Procurement, with proof</p>
              <h2 className="mt-4 font-serif text-4xl leading-[1.08] tracking-tight text-brand-950">
                Make every verdict defensible.
              </h2>
              <p className="mt-5 text-sm leading-7 text-brand-800/80">
                Keep tender requirements, vendor claims, and source evidence together in one clear review trail.
              </p>
            </div>
          </div>
          <div className="space-y-3 text-sm text-brand-800/80">
            <p className="flex items-center gap-2"><CheckIcon className="h-4 w-4 text-brand-600" /> Page-level evidence trails</p>
            <p className="flex items-center gap-2"><CheckIcon className="h-4 w-4 text-brand-600" /> Government record checks</p>
          </div>
        </aside>

        <div className="p-7 sm:p-10 lg:p-12">
          <div className="mb-8 lg:max-w-sm">
            <div className="mb-7 flex items-center gap-2.5 lg:hidden">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-800 text-white">
                <ShieldIcon className="h-4.5 w-4.5" />
              </span>
              <p className="text-sm font-semibold tracking-tight text-slate-900">TenderGuard</p>
            </div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-brand-600">Secure workspace access</p>
            <h1 className="mt-3 font-serif text-4xl font-semibold tracking-tight text-slate-900">Welcome back</h1>
            <p className="mt-3 text-sm leading-6 text-slate-500">Sign in to continue your compliance workspace.</p>
          </div>
          <form className="space-y-5 lg:max-w-sm" onSubmit={handleSubmit}>
            <label className="block">
              <span className="label">Username or email</span>
              <input className="input" value={identifier} onChange={(event) => setIdentifier(event.target.value)} required autoComplete="username" />
            </label>
            <label className="block">
              <span className="label">Password</span>
              <input className="input" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" />
            </label>
            {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-inset ring-red-200">{error}</p>}
            <button className="btn-primary w-full py-3" disabled={isSubmitting} type="submit">
              {isSubmitting ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
          <p className="mt-7 text-center text-sm text-slate-500 lg:max-w-sm">
            New to TenderGuard? <Link className="font-semibold text-brand-700 hover:text-brand-900" to="/register">Create an account</Link>
          </p>
        </div>
      </section>
    </main>
  )
}

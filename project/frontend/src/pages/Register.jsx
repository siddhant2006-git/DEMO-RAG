import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { registerUser } from '../api/client'

export default function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', fullName: '', password: '' })
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await registerUser(form)
      navigate('/login', { state: { registered: true } })
    } catch (requestError) {
      setError(requestError.response?.data?.message || 'Unable to create your account.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-brand-50 px-6 py-12">
      <section className="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-brand-600">TenderGuard</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">Create account</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-500">Set up an officer account for this workspace.</p>
        <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
          <label className="block"><span className="label">Full name</span><input className="input" value={form.fullName} onChange={(event) => update('fullName', event.target.value)} required /></label>
          <label className="block"><span className="label">Username</span><input className="input" value={form.username} onChange={(event) => update('username', event.target.value)} required minLength={3} autoComplete="username" /></label>
          <label className="block"><span className="label">Email</span><input className="input" type="email" value={form.email} onChange={(event) => update('email', event.target.value)} required autoComplete="email" /></label>
          <label className="block"><span className="label">Password</span><input className="input" type="password" value={form.password} onChange={(event) => update('password', event.target.value)} required minLength={8} autoComplete="new-password" /></label>
          {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
          <button className="btn-primary w-full" disabled={isSubmitting} type="submit">{isSubmitting ? 'Creating account...' : 'Create account'}</button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-500">Already registered? <Link className="font-semibold text-brand-700 hover:text-brand-900" to="/login">Sign in</Link></p>
      </section>
    </main>
  )
}

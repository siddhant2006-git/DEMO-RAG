import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { forgotPassword, register, resendVerification, resetPassword, verifyEmail } from '../api/client'
import { useAuth } from '../store/AuthContext'

function AuthFrame({ title, intro, children, compact = false }) {
  return (
    <main className="auth-page">
      <section className="auth-showcase">
        <div className="auth-brand"><span className="auth-brand-mark">TS</span><span>TenderShield</span></div>
        <p className="auth-eyebrow">Government procurement / vendor portal</p>
        <h1>Compliance clarity for every bid.</h1>
        <p className="auth-showcase-copy">Submit with confidence. TenderShield keeps your documents, tender requirements, and government validations in one secure workspace.</p>
        <div className="auth-illustration" aria-hidden="true"><div className="illustration-document"><i /><i /><i /></div><div className="illustration-shield">✓</div><div className="illustration-check">VERIFIED</div></div>
        <div className="auth-feature-grid"><span><b>✓</b><strong>Secure Document Verification</strong><small>Evidence-backed review</small></span><span><b>↗</b><strong>Tender Compliance Tracking</strong><small>One clear workspace</small></span><span><b>▣</b><strong>Government Record Validation</strong><small>Trusted source checks</small></span></div>
      </section>
      <section className="auth-panel">
        <div className={`auth-panel-inner ${compact ? 'auth-panel-compact' : ''}`}>
          <div className="auth-mobile-brand"><span className="auth-brand-mark">TS</span><strong>TenderShield</strong></div>
          <p className="auth-eyebrow">Vendor access</p>
          <h2>{intro}</h2>
          <p className="auth-panel-title">{title}</p>
          {children}
        </div>
      </section>
    </main>
  )
}

function Field({ label, type = 'text', value, onChange, placeholder, autoComplete, action }) {
  return <label className="auth-field"><span>{label}</span><span className="auth-input-wrap"><input className="input" type={type} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} autoComplete={autoComplete} required />{action}</span></label>
}

function FormMessage({ error, success }) {
  if (error) return <p className="auth-message auth-error" role="alert">{error}</p>
  if (success) return <p className="auth-message auth-success" role="status">{success}</p>
  return null
}

function getError(error) {
  const response = error.response?.data
  const validationErrors = response?.detail?.errors
  if (Array.isArray(validationErrors) && validationErrors.length > 0) {
    return validationErrors.map((validationError) => {
      const field = validationError.loc?.at(-1)
      const label = field
        ? field.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase())
        : 'Request'
      return `${label}: ${validationError.msg || 'is invalid'}`
    }).join('. ')
  }
  return response?.message || (typeof response?.detail === 'string' ? response.detail : null) || 'Something went wrong. Please try again.'
}

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [errorCode, setErrorCode] = useState('')
  const [verificationMessage, setVerificationMessage] = useState('')
  const [verificationUrl, setVerificationUrl] = useState(location.state?.verificationUrl || '')
  const [resending, setResending] = useState(false)
  const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault()
    setError('')
    setErrorCode('')
    setVerificationMessage('')
    setVerificationUrl('')
    setBusy(true)
    try {
      await login(form)
      navigate(location.state?.from || '/dashboard')
    } catch (requestError) {
      setError(getError(requestError))
      setErrorCode(requestError.response?.data?.code || '')
    } finally {
      setBusy(false)
    }
  }
  async function requestVerification() {
    setError('')
    setVerificationMessage('')
    setVerificationUrl('')
    setResending(true)
    try {
      const result = await resendVerification(form.email)
      setVerificationMessage(result.message)
      setVerificationUrl(result.verification_url || '')
    } catch (requestError) {
      setError(getError(requestError))
    } finally {
      setResending(false)
    }
  }
  const [showPassword, setShowPassword] = useState(false)
  return <AuthFrame title="Secure vendor access" intro="Vendor Login"><form className="auth-form" onSubmit={submit}><Field label="Email / Vendor ID" type="email" value={form.email} onChange={(email) => setForm({ ...form, email })} autoComplete="email" placeholder="name@company.com" /><Field label="Password" type={showPassword ? 'text' : 'password'} value={form.password} onChange={(password) => setForm({ ...form, password })} autoComplete="current-password" placeholder="Enter your password" action={<button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)}>{showPassword ? 'Hide' : 'Show'}</button>} /><div className="auth-options"><label><input type="checkbox" /> <span>Remember me</span></label><Link to="/forgot-password">Forgot Password?</Link></div><FormMessage error={error} success={verificationMessage} />{errorCode === 'EMAIL_NOT_VERIFIED' && <button type="button" className="btn-secondary auth-submit" onClick={requestVerification} disabled={resending || !form.email}>{resending ? 'Sending...' : 'Resend verification email'}</button>}{verificationUrl && <Link className="auth-outline-link" to={verificationUrl}>Verify email address</Link>}<button className="btn-primary auth-submit" disabled={busy}>{busy ? 'Signing In...' : 'Sign In'}</button><button type="button" className="btn-secondary gov-id-button">◎ <span>Sign in with Government ID</span></button><div className="auth-divider"><span>or</span></div><Link className="auth-outline-link" to="/register">Create Vendor Account</Link><p className="auth-security">▣ Your documents and verification data are securely protected.</p></form></AuthFrame>
}

export function Register() {
  const navigate = useNavigate(); const [form, setForm] = useState({ companyName: '', vendorId: '', authorizedName: '', email: '', mobile: '', password: '', confirmPassword: '', gstin: '', pan: '', udyamNumber: '', terms: false }); const [error, setError] = useState(''); const [success, setSuccess] = useState(''); const [busy, setBusy] = useState(false)
  async function submit(event) { event.preventDefault(); setError(''); setSuccess(''); if (form.password !== form.confirmPassword) { setError('Passwords do not match.'); return } setBusy(true); try { const result = await register(form); setSuccess(result.message); setTimeout(() => navigate('/login', { state: { verificationUrl: result.verification_url || '' } }), 1800) } catch (requestError) { setError(getError(requestError)) } finally { setBusy(false) } }
  const update = (key) => (value) => setForm({ ...form, [key]: value })
  return <AuthFrame compact title="Vendor registration" intro="Create Vendor Account"><form className="auth-form register-form" onSubmit={submit}><div className="auth-form-grid"><Field label="Company Name" value={form.companyName} onChange={update('companyName')} placeholder="Legal business name" /><Field label="Vendor ID / Registration Number" value={form.vendorId} onChange={update('vendorId')} placeholder="Registration number" /><Field label="Authorized Person Name" value={form.authorizedName} onChange={update('authorizedName')} placeholder="Full name" /><Field label="Official Email" type="email" value={form.email} onChange={update('email')} autoComplete="email" placeholder="name@company.com" /><Field label="Mobile Number" type="tel" value={form.mobile} onChange={update('mobile')} placeholder="+91 00000 00000" /><Field label="GSTIN" value={form.gstin} onChange={update('gstin')} placeholder="15-character GSTIN" /><Field label="PAN" value={form.pan} onChange={update('pan')} placeholder="Company PAN" /><Field label="Udyam Registration Number" value={form.udyamNumber} onChange={update('udyamNumber')} placeholder="UDYAM-XX-00-0000000" /></div><Field label="Password" type="password" value={form.password} onChange={update('password')} autoComplete="new-password" placeholder="12+ chars, upper, lower, number, symbol" /><Field label="Confirm Password" type="password" value={form.confirmPassword} onChange={update('confirmPassword')} autoComplete="new-password" placeholder="Repeat your password" /><label className="auth-terms"><input type="checkbox" checked={form.terms} onChange={(event) => setForm({ ...form, terms: event.target.checked })} required /><span>I agree to the <a href="/terms">Terms</a> and <a href="/privacy">Privacy Policy</a>.</span></label><FormMessage error={error} success={success} /><button className="btn-primary auth-submit" disabled={busy || !form.terms}>{busy ? 'Creating Account...' : 'Create Account'}</button><p className="auth-footnote">A verification link will be sent to your official email.</p><div className="auth-links"><span>Already registered? <Link to="/login">Sign in</Link></span></div></form></AuthFrame>
}

export function ForgotPassword() {
  const [email, setEmail] = useState(''); const [error, setError] = useState(''); const [success, setSuccess] = useState(''); const [busy, setBusy] = useState(false)
  async function submit(event) { event.preventDefault(); setError(''); setBusy(true); try { const result = await forgotPassword(email); setSuccess(result.message) } catch (requestError) { setError(getError(requestError)) } finally { setBusy(false) } }
  return <AuthFrame title="Account recovery" intro="Reset Password"><form className="auth-form" onSubmit={submit}><Field label="Official email" type="email" value={email} onChange={setEmail} autoComplete="email" placeholder="name@company.com" /><FormMessage error={error} success={success} /><button className="btn-primary auth-submit" disabled={busy}>{busy ? 'Sending...' : 'Send reset link'}</button><div className="auth-links"><Link to="/login">Back to sign in</Link></div></form></AuthFrame>
}

export function ResetPassword() {
  const [params] = useSearchParams(); const [form, setForm] = useState({ password: '', confirmPassword: '' }); const [error, setError] = useState(''); const [success, setSuccess] = useState(''); const [busy, setBusy] = useState(false)
  async function submit(event) { event.preventDefault(); setError(''); if (form.password !== form.confirmPassword) { setError('Passwords do not match.'); return } setBusy(true); try { const result = await resetPassword({ token: params.get('token') || '', ...form }); setSuccess(result.message) } catch (requestError) { setError(getError(requestError)) } finally { setBusy(false) } }
  return <AuthFrame title="Account recovery" intro="Choose a new password"><form className="auth-form" onSubmit={submit}><Field label="New password" type="password" value={form.password} onChange={(password) => setForm({ ...form, password })} autoComplete="new-password" placeholder="12+ chars, upper, lower, number, symbol" /><Field label="Confirm password" type="password" value={form.confirmPassword} onChange={(confirmPassword) => setForm({ ...form, confirmPassword })} autoComplete="new-password" placeholder="Repeat your password" /><FormMessage error={error} success={success} /><button className="btn-primary auth-submit" disabled={busy}>{busy ? 'Updating...' : 'Update password'}</button><div className="auth-links"><Link to="/login">Back to sign in</Link></div></form></AuthFrame>
}

export function VerifyEmail() {
  const [params] = useSearchParams(); const [message, setMessage] = useState('Verifying your email...'); const [error, setError] = useState('')
  useEffect(() => { verifyEmail(params.get('token') || '').then((result) => setMessage(result.message)).catch((requestError) => { setError(getError(requestError)); setMessage('This verification link could not be used.') }) }, [params])
  return <AuthFrame title="Account verification" intro="Confirm your email"><div className={`auth-message ${error ? 'auth-error' : 'auth-success'}`}>{error || message}</div><Link className="btn-primary auth-submit" to="/login">Continue to sign in</Link></AuthFrame>
}
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useSession } from '../../store/SessionContext'
import { BuildingIcon, CheckIcon, LockIcon, RefreshIcon, ShieldIcon } from './icons'

const STEPS = [
  { to: '/', label: 'Upload', isUnlocked: () => true, isDone: (s) => Boolean(s.bidId) },
  {
    to: '/requirements',
    label: 'Requirements',
    isUnlocked: (s) => Boolean(s.tenderId),
    isDone: () => false,
  },
  { to: '/compliance', label: 'Compliance', isUnlocked: (s) => Boolean(s.bidId), isDone: () => false },
  { to: '/evidence', label: 'Evidence', isUnlocked: (s) => Boolean(s.bidId), isDone: () => false },
  { to: '/reports', label: 'Reports', isUnlocked: (s) => Boolean(s.bidId), isDone: () => false },
]

function lockedReason(step, session) {
  if (step.to === '/requirements' || !session.tenderId) return 'Upload a tender first'
  return 'Upload a vendor bid first'
}

function StepBadge({ state, index }) {
  const base =
    'flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold transition-colors'
  if (state === 'active') return <span className={`${base} bg-white/20 text-white`}>{index}</span>
  if (state === 'done')
    return (
      <span className={`${base} bg-emerald-100 text-emerald-700`}>
        <CheckIcon className="h-3 w-3" />
      </span>
    )
  if (state === 'locked')
    return <span className={`${base} border border-slate-200 text-slate-300`}>{index}</span>
  return <span className={`${base} border border-slate-300 text-slate-500`}>{index}</span>
}

export default function NavBar() {
  const session = useSession()
  const navigate = useNavigate()
  const location = useLocation()

  function handleReset() {
    if (
      window.confirm(
        'Start a new session? This clears the current tender and bid from this browser.',
      )
    ) {
      session.reset()
      navigate('/')
    }
  }

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-y-3 px-6 py-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-800 text-white shadow-sm">
            <ShieldIcon className="h-[18px] w-[18px]" />
          </span>
          <div className="leading-tight">
            <p className="text-[15px] font-semibold tracking-tight text-slate-900">TenderGuard</p>
            <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
              Compliance Verification
            </p>
          </div>
        </div>

        <nav className="flex items-center" aria-label="Pipeline steps">
          {STEPS.map((step, i) => {
            const unlocked = step.isUnlocked(session)
            const isActive = location.pathname === step.to
            const state = isActive
              ? 'active'
              : !unlocked
                ? 'locked'
                : step.isDone(session)
                  ? 'done'
                  : 'idle'

            const inner = (
              <>
                <StepBadge state={state} index={i + 1} />
                <span className="hidden sm:inline">{step.label}</span>
                {state === 'locked' && <LockIcon className="hidden h-3 w-3 sm:inline" />}
              </>
            )

            return (
              <div key={step.to} className="flex items-center">
                {i > 0 && <span className="mx-0.5 h-px w-3 bg-slate-200 sm:w-4" aria-hidden="true" />}
                {unlocked ? (
                  <NavLink
                    to={step.to}
                    end={step.to === '/'}
                    className={`flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-all sm:px-3 ${
                      isActive
                        ? 'bg-brand-800 text-white shadow-sm'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                    }`}
                  >
                    {inner}
                  </NavLink>
                ) : (
                  <span
                    title={lockedReason(step, session)}
                    aria-disabled="true"
                    className="flex cursor-not-allowed items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm font-medium text-slate-300 sm:px-3"
                  >
                    {inner}
                  </span>
                )}
              </div>
            )
          })}
        </nav>
      </div>

      {session.tenderId && (
        <div className="border-t border-slate-100 bg-slate-50/80">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-6 py-2">
            <div className="flex min-w-0 flex-wrap items-center gap-x-5 gap-y-1 text-xs">
              <span className="flex min-w-0 items-center gap-1.5">
                <span className="font-medium uppercase tracking-wide text-slate-400">Tender</span>
                <span className="truncate font-semibold text-slate-700">
                  {session.tenderTitle ?? `${session.tenderId.slice(0, 8)}…`}
                </span>
              </span>
              {session.bidId && (
                <span className="flex min-w-0 items-center gap-1.5">
                  <BuildingIcon className="h-3.5 w-3.5 text-slate-400" />
                  <span className="font-medium uppercase tracking-wide text-slate-400">Vendor</span>
                  <span className="truncate font-semibold text-slate-700">
                    {session.vendorName ?? `${session.bidId.slice(0, 8)}…`}
                  </span>
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={handleReset}
              className="flex shrink-0 items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-slate-500 transition-colors hover:bg-slate-200/70 hover:text-slate-800"
            >
              <RefreshIcon className="h-3.5 w-3.5" />
              New session
            </button>
          </div>
        </div>
      )}
    </header>
  )
}

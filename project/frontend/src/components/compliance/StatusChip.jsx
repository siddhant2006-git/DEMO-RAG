import { AlertIcon, CheckIcon, WarningIcon } from '../common/icons'

const STYLES = {
  PASS: { cls: 'bg-emerald-50 text-emerald-700 ring-emerald-200/70', Icon: CheckIcon },
  FAIL: { cls: 'bg-red-50 text-red-700 ring-red-200/70', Icon: AlertIcon },
  NEEDS_REVIEW: { cls: 'bg-amber-50 text-amber-700 ring-amber-200/70', Icon: WarningIcon },
  // Not a distinct DB status (still NEEDS_REVIEW under the hood, weight 0) —
  // a rule-id convention (rule_id starts with "MANUAL-") flags a tender
  // requirement no rule pack entry covers at all, so it reads differently
  // from "a rule ran and couldn't resolve a value".
  MANUAL_CHECK: { cls: 'bg-violet-50 text-violet-700 ring-violet-200/70', Icon: WarningIcon },
}

const FALLBACK = { cls: 'bg-slate-100 text-slate-600 ring-slate-200', Icon: WarningIcon }

export default function StatusChip({ status, manual = false, size = 'sm' }) {
  const key = manual ? 'MANUAL_CHECK' : status
  const { cls, Icon } = STYLES[key] ?? FALLBACK
  const dims = size === 'lg' ? 'px-3 py-1 text-xs' : 'px-2 py-0.5 text-[11px]'
  const label = manual ? 'Manual check' : String(status ?? 'UNKNOWN').replace(/_/g, ' ')
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full font-bold uppercase tracking-wide ring-1 ring-inset ${cls} ${dims}`}
    >
      <Icon className={size === 'lg' ? 'h-3.5 w-3.5' : 'h-3 w-3'} />
      {label}
    </span>
  )
}

/* Severity is a secondary signal — muted so it never competes with the verdict
   chip, but BLOCKER stays loud because it alone can force the HIGH risk band. */
const SEVERITY = {
  BLOCKER: 'bg-red-100 text-red-800 ring-red-300',
  CRITICAL: 'bg-orange-50 text-orange-700 ring-orange-200',
  MAJOR: 'bg-slate-100 text-slate-600 ring-slate-200',
  MINOR: 'bg-slate-50 text-slate-500 ring-slate-200',
}

export function SeverityChip({ severity }) {
  const cls = SEVERITY[severity] ?? 'bg-slate-50 text-slate-500 ring-slate-200'
  return (
    <span
      className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ring-1 ring-inset ${cls}`}
    >
      {severity ?? '—'}
    </span>
  )
}

import { AlertIcon, CheckIcon, WarningIcon } from '../common/icons'

/* Band thresholds mirror backend/app/services/risk/scorer.py. A FAILed BLOCKER
   forces HIGH there regardless of the numeric score, so the band the API sends
   is authoritative — `band` overrides the local score lookup when provided. */
function bandFor(score) {
  if (score >= 66)
    return {
      label: 'HIGH',
      Icon: AlertIcon,
      text: 'text-red-700',
      ring: 'stroke-red-500',
      chip: 'bg-red-50 text-red-700 ring-red-200',
      note: 'Disqualifying issues found',
    }
  if (score >= 33)
    return {
      label: 'MEDIUM',
      Icon: WarningIcon,
      text: 'text-amber-700',
      ring: 'stroke-amber-500',
      chip: 'bg-amber-50 text-amber-700 ring-amber-200',
      note: 'Needs officer review',
    }
  return {
    label: 'LOW',
    Icon: CheckIcon,
    text: 'text-emerald-700',
    ring: 'stroke-emerald-500',
    chip: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    note: 'No blocking issues',
  }
}

const BANDS = [
  { label: 'LOW', from: 0, to: 33, color: 'bg-emerald-400' },
  { label: 'MEDIUM', from: 33, to: 66, color: 'bg-amber-400' },
  { label: 'HIGH', from: 66, to: 100, color: 'bg-red-400' },
]

// Score that sits mid-band, used to look up styling when the API sends an
// explicit band (a FAILed BLOCKER forces HIGH even on a low numeric score).
const BAND_ANCHOR = { LOW: 0, MEDIUM: 50, HIGH: 100 }

export default function RiskGauge({ score = 0, band: apiBand }) {
  const clamped = Math.min(100, Math.max(0, Number(score) || 0))
  const band = bandFor(apiBand in BAND_ANCHOR ? BAND_ANCHOR[apiBand] : clamped)

  // 3/4-circle arc: r=52, circumference ≈ 326.7, we use 75% of it.
  const R = 52
  const ARC = 2 * Math.PI * R * 0.75
  const filled = (clamped / 100) * ARC

  return (
    <div className="card-pad">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Risk score</p>
          <p className="mt-0.5 text-[11px] text-slate-400">Weighted across all rules</p>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ring-1 ring-inset ${band.chip}`}
        >
          <band.Icon className="h-3.5 w-3.5" />
          {band.label}
        </span>
      </div>

      <div className="mt-2 flex items-center gap-5">
        <div className="relative h-32 w-32 shrink-0">
          <svg viewBox="0 0 120 120" className="h-full w-full -rotate-[135deg]">
            <circle
              cx="60"
              cy="60"
              r={R}
              fill="none"
              strokeWidth="11"
              strokeLinecap="round"
              className="stroke-slate-100"
              strokeDasharray={`${ARC} 1000`}
            />
            <circle
              cx="60"
              cy="60"
              r={R}
              fill="none"
              strokeWidth="11"
              strokeLinecap="round"
              className={`${band.ring} transition-[stroke-dasharray] duration-700 ease-out`}
              strokeDasharray={`${filled} 1000`}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`tnum text-4xl font-bold leading-none ${band.text}`}>{clamped}</span>
            <span className="mt-1 text-[10px] font-medium uppercase tracking-wider text-slate-400">
              of 100
            </span>
          </div>
        </div>

        <div className="min-w-0 flex-1">
          <p className={`text-sm font-semibold ${band.text}`}>{band.note}</p>
          <div className="mt-3 space-y-1.5">
            {BANDS.map((b) => {
              const isCurrent = b.label === band.label
              return (
                <div key={b.label} className="flex items-center gap-2">
                  <span
                    className={`h-1.5 w-8 rounded-full ${b.color} ${isCurrent ? '' : 'opacity-30'}`}
                  />
                  <span
                    className={`text-[10px] font-medium uppercase tracking-wider ${
                      isCurrent ? 'text-slate-700' : 'text-slate-400'
                    }`}
                  >
                    {b.label}
                  </span>
                  <span className="tnum text-[10px] text-slate-400">
                    {b.from}–{b.to}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

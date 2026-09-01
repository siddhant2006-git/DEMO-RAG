import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCompliance, runCompliance, runVerification } from '../api/client'
import RiskGauge from '../components/compliance/RiskGauge'
import StatusChip, { SeverityChip } from '../components/compliance/StatusChip'
import {
  AlertIcon,
  ChevronRightIcon,
  RefreshIcon,
  ShieldIcon,
  SpinnerIcon,
} from '../components/common/icons'
import { useSession } from '../store/SessionContext'
import { useToast } from '../store/ToastContext'

const FILTERS = [
  { key: 'ALL', label: 'All' },
  { key: 'FAIL', label: 'Failed' },
  { key: 'NEEDS_REVIEW', label: 'Needs review' },
  { key: 'PASS', label: 'Passed' },
]

const STAT_TONES = {
  PASS: 'text-emerald-700 bg-emerald-50 ring-emerald-200/70',
  FAIL: 'text-red-700 bg-red-50 ring-red-200/70',
  NEEDS_REVIEW: 'text-amber-700 bg-amber-50 ring-amber-200/70',
}

function StatCard({ label, value, tone }) {
  return (
    <div className={`rounded-xl px-4 py-3 ring-1 ring-inset ${tone}`}>
      <p className="tnum text-2xl font-bold leading-none">{value ?? 0}</p>
      <p className="mt-1.5 text-[11px] font-semibold uppercase tracking-wider opacity-80">{label}</p>
    </div>
  )
}

function SkeletonTable() {
  return (
    <div className="card mt-5 animate-pulse overflow-hidden">
      <div className="h-10 border-b border-slate-200 bg-slate-50" />
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex items-center gap-4 border-b border-slate-100 px-4 py-3.5">
          <div className="h-3 w-24 rounded bg-slate-200" />
          <div className="h-3 flex-1 rounded bg-slate-100" />
          <div className="h-5 w-20 rounded-full bg-slate-100" />
        </div>
      ))}
    </div>
  )
}

function truncate(value, max = 42) {
  const s = String(value)
  return s.length > max ? `${s.slice(0, max)}…` : s
}

export default function ComplianceMatrix() {
  const session = useSession()
  const navigate = useNavigate()
  const { notify } = useToast()

  const [risk, setRisk] = useState(null)
  const [findings, setFindings] = useState([])
  const [filter, setFilter] = useState('ALL')
  const [loading, setLoading] = useState(false)
  const [verifyBusy, setVerifyBusy] = useState(false)
  const [complianceBusy, setComplianceBusy] = useState(false)
  const [error, setError] = useState(null)
  const [verifyResults, setVerifyResults] = useState(null)

  const busy = verifyBusy || complianceBusy

  const load = useCallback(async () => {
    if (!session.bidId) return
    setLoading(true)
    setError(null)
    try {
      const data = await getCompliance(session.bidId)
      setRisk(data.risk)
      setFindings(data.findings)
    } catch (err) {
      if (err.response?.status !== 404) setError(err.response?.data?.message || err.message)
    } finally {
      setLoading(false)
    }
  }, [session.bidId])

  useEffect(() => {
    load()
  }, [load])

  async function handleVerify() {
    setVerifyBusy(true)
    setError(null)
    try {
      const result = await runVerification(session.bidId)
      setVerifyResults(result.results)
      const down = result.results.filter((r) => r.status !== 'UP').length
      notify(
        down
          ? `Verification complete — ${down} portal${down === 1 ? '' : 's'} unreachable`
          : 'Verification complete — all portals reachable',
        { type: down ? 'error' : 'success' },
      )
    } catch (err) {
      const message = err.response?.data?.message || err.message
      setError(message)
      notify(message, { type: 'error' })
    } finally {
      setVerifyBusy(false)
    }
  }

  async function handleRunCompliance() {
    if (
      findings.length > 0 &&
      !window.confirm(
        'Re-running compliance replaces all existing findings for this bid — this cannot be undone. Continue?',
      )
    )
      return

    setComplianceBusy(true)
    setError(null)
    try {
      const data = await runCompliance(session.bidId)
      setRisk(data.risk)
      setFindings(data.findings)
      notify(
        `Compliance complete — ${data.findings.length} finding${data.findings.length === 1 ? '' : 's'}`,
      )
    } catch (err) {
      const message = err.response?.data?.message || err.message
      setError(message)
      notify(message, { type: 'error' })
    } finally {
      setComplianceBusy(false)
    }
  }

  if (!session.bidId) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-10">
        <h1 className="page-title">Compliance matrix</h1>
        <div className="card-pad mt-6 text-center">
          <p className="text-sm text-slate-500">
            Upload a tender and a vendor bid to see the compliance matrix.
          </p>
          <button className="btn-primary mt-4" onClick={() => navigate('/')}>
            Go to Upload
          </button>
        </div>
      </div>
    )
  }

  const counts = {
    ALL: findings.length,
    PASS: findings.filter((f) => f.status === 'PASS').length,
    FAIL: findings.filter((f) => f.status === 'FAIL').length,
    NEEDS_REVIEW: findings.filter((f) => f.status === 'NEEDS_REVIEW').length,
  }
  const visible = filter === 'ALL' ? findings : findings.filter((f) => f.status === filter)

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="page-title">Compliance matrix</h1>
          <p className="page-sub">
            <span className="font-medium text-slate-700">{session.vendorName}</span>
            <span className="mx-1.5 text-slate-300">vs.</span>
            <span className="font-medium text-slate-700">{session.tenderTitle}</span>
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button onClick={handleVerify} disabled={busy} className="btn-secondary">
            {verifyBusy ? <SpinnerIcon /> : <ShieldIcon />}
            {verifyBusy ? 'Verifying…' : 'Run verification'}
          </button>
          <button onClick={handleRunCompliance} disabled={busy} className="btn-primary">
            {complianceBusy ? <SpinnerIcon /> : <RefreshIcon />}
            {complianceBusy ? 'Running…' : findings.length ? 'Re-run compliance' : 'Run compliance'}
          </button>
        </div>
      </div>

      {error && (
        <p className="mt-5 flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700 ring-1 ring-inset ring-red-200">
          <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </p>
      )}

      {verifyResults && (
        <div className="card mt-6 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Government verification
          </p>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {verifyResults.map((r) => {
              const up = r.status === 'UP'
              return (
                <div
                  key={r.portal}
                  className={`rounded-lg p-3 ring-1 ring-inset ${
                    up ? 'bg-white ring-slate-200' : 'bg-amber-50/60 ring-amber-200'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-slate-800">{r.portal}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ring-1 ring-inset ${
                        up
                          ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                          : 'bg-amber-100 text-amber-800 ring-amber-300'
                      }`}
                    >
                      {r.status}
                    </span>
                  </div>
                  {up && r.normalized && Object.keys(r.normalized).length > 0 ? (
                    <dl className="mt-2.5 space-y-1 border-t border-slate-100 pt-2.5">
                      {Object.entries(r.normalized).map(([key, value]) => (
                        <div key={key} className="flex items-baseline justify-between gap-3 text-xs">
                          <dt className="shrink-0 text-slate-400">{key.replace(/_/g, ' ')}</dt>
                          <dd className="tnum truncate text-right font-medium text-slate-700">
                            {truncate(value, 24)}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  ) : (
                    <p className="mt-2 text-xs text-amber-700">
                      Portal unreachable — dependent rules become Needs Review, never a pass or fail.
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {risk && (
        <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,26rem)_1fr]">
          <RiskGauge score={risk.score} band={risk.band} />
          <div className="grid grid-cols-3 content-start gap-3">
            <StatCard label="Passed" value={risk.pass_count} tone={STAT_TONES.PASS} />
            <StatCard label="Failed" value={risk.fail_count} tone={STAT_TONES.FAIL} />
            <StatCard label="Review" value={risk.needs_review_count} tone={STAT_TONES.NEEDS_REVIEW} />
            <p className="col-span-3 mt-1 text-xs leading-relaxed text-slate-500">
              Every verdict below comes from the deterministic rule engine — no model decides a
              pass or fail. Select any row to see the claimed value, the government record, and the
              exact page it came from.
            </p>
          </div>
        </div>
      )}

      {loading && !findings.length && <SkeletonTable />}

      {!loading && !findings.length && (
        <div className="card-pad mt-6 text-center">
          <p className="text-sm font-medium text-slate-700">No findings yet</p>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
            Run verification to fetch the vendor's government records, then run compliance to
            evaluate the tender's rules against them.
          </p>
        </div>
      )}

      {findings.length > 0 && (
        <>
          <div className="mt-6 flex flex-wrap items-center gap-1.5">
            {FILTERS.map((f) => {
              const active = filter === f.key
              return (
                <button
                  key={f.key}
                  onClick={() => setFilter(f.key)}
                  className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                    active
                      ? 'bg-brand-800 text-white shadow-sm'
                      : 'bg-white text-slate-600 ring-1 ring-inset ring-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {f.label}
                  <span
                    className={`tnum rounded-full px-1.5 py-px text-[10px] ${
                      active ? 'bg-white/20' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {counts[f.key]}
                  </span>
                </button>
              )
            })}
          </div>

          <div className="card mt-4 overflow-hidden">
            <div className="max-h-[34rem] overflow-auto">
              <table className="w-full border-collapse">
                <thead className="sticky top-0 z-10 bg-slate-50/95 backdrop-blur">
                  <tr className="border-b border-slate-200">
                    <th className="th">Rule</th>
                    <th className="th">Requirement</th>
                    <th className="th">Status</th>
                    <th className="th">Severity</th>
                    <th className="th text-right">Claimed</th>
                    <th className="th text-right">Verified</th>
                    <th className="th w-8" />
                  </tr>
                </thead>
                <tbody>
                  {visible.map((f) => {
                    const claimed = f.claimed?.value
                    const verified = f.verified?.value
                    const mismatch =
                      claimed !== undefined &&
                      verified !== undefined &&
                      String(claimed) !== String(verified)

                    return (
                      <tr
                        key={f.rule_id}
                        tabIndex={0}
                        onClick={() => navigate(`/evidence/${f.rule_id}`, { state: { finding: f } })}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter')
                            navigate(`/evidence/${f.rule_id}`, { state: { finding: f } })
                        }}
                        className={`group cursor-pointer border-b border-slate-100 transition-colors last:border-0 hover:bg-brand-50/50 ${
                          f.status === 'FAIL' ? 'bg-red-50/30' : ''
                        }`}
                      >
                        <td className="td">
                          <span className="font-mono text-xs font-semibold text-slate-800">
                            {f.rule_id}
                          </span>
                        </td>
                        <td className="td max-w-md">
                          <span className="line-clamp-2 text-slate-600">{f.requirement_text}</span>
                        </td>
                        <td className="td">
                          <StatusChip status={f.status} />
                        </td>
                        <td className="td">
                          <SeverityChip severity={f.severity} />
                        </td>
                        <td className="td tnum text-right">
                          {claimed !== undefined ? (
                            <span className={mismatch ? 'font-semibold text-red-700' : ''}>
                              {truncate(claimed, 22)}
                            </span>
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                        <td className="td tnum text-right">
                          {verified !== undefined ? (
                            <span className={mismatch ? 'font-semibold text-slate-900' : ''}>
                              {truncate(verified, 22)}
                            </span>
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                        <td className="td pl-0 pr-3">
                          <ChevronRightIcon className="h-4 w-4 text-slate-300 transition-colors group-hover:text-brand-600" />
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {visible.length === 0 && (
            <p className="mt-4 text-center text-sm text-slate-500">
              No findings with this status.
            </p>
          )}
        </>
      )}
    </div>
  )
}

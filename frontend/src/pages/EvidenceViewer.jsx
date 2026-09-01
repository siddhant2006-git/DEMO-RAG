import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { getCompliance } from '../api/client'
import StatusChip, { SeverityChip } from '../components/compliance/StatusChip'
import { AlertIcon, ArrowLeftIcon, BuildingIcon, FileIcon, ShieldIcon } from '../components/common/icons'
import { useSession } from '../store/SessionContext'

function ValueCard({ label, sublabel, Icon, data, highlight }) {
  const has = data && data.value !== undefined
  return (
    <div
      className={`rounded-xl border p-5 transition-colors ${
        highlight ? 'border-red-300 bg-red-50/60' : 'border-slate-200 bg-white'
      }`}
    >
      <div className="flex items-center gap-2">
        <Icon className={`h-4 w-4 ${highlight ? 'text-red-600' : 'text-slate-400'}`} />
        <p
          className={`text-xs font-semibold uppercase tracking-wide ${
            highlight ? 'text-red-700' : 'text-slate-500'
          }`}
        >
          {label}
        </p>
      </div>
      <p className="mt-0.5 text-[11px] text-slate-400">{sublabel}</p>

      {has ? (
        <>
          <p
            className={`tnum mt-3 text-3xl font-bold leading-tight ${
              highlight ? 'text-red-700' : 'text-slate-900'
            }`}
          >
            {String(data.value)}
          </p>
          {data.source?.portal && (
            <p className="mt-2 text-xs text-slate-500">
              {data.source.portal} portal
              {data.source.fetched_at && (
                <span className="text-slate-400"> · fetched {data.source.fetched_at}</span>
              )}
            </p>
          )}
          {data.source?.page && (
            <p className="mt-2 text-xs text-slate-500">Bid document, page {data.source.page}</p>
          )}
          {data.source?.snippet && (
            <blockquote className="mt-3 border-l-2 border-slate-300 pl-3 text-sm italic leading-relaxed text-slate-600">
              “{data.source.snippet}”
            </blockquote>
          )}
        </>
      ) : (
        <>
          <p className="mt-3 text-lg font-medium text-slate-400">Not available</p>
          <p className="mt-1 text-xs text-slate-400">
            No value from this source — the rule falls back to the other source, or becomes Needs
            Review.
          </p>
        </>
      )}
    </div>
  )
}

export default function EvidenceViewer() {
  const { ruleId } = useParams()
  const { state } = useLocation()
  const navigate = useNavigate()
  const session = useSession()

  const fastPath = state?.finding && (!ruleId || state.finding.rule_id === ruleId)
  const [finding, setFinding] = useState(fastPath ? state.finding : null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (state?.finding && (!ruleId || state.finding.rule_id === ruleId)) {
      setFinding(state.finding)
      return
    }
    // Deep link / refresh / back-forward: refetch by id rather than depending
    // on in-memory router state.
    if (!ruleId || !session.bidId) return
    setLoading(true)
    setError(null)
    getCompliance(session.bidId)
      .then((data) => {
        const match = data.findings?.find((f) => f.rule_id === ruleId)
        setFinding(match ?? null)
        if (!match) setError(`No finding with rule id "${ruleId}" for the current bid.`)
      })
      .catch((err) => setError(err.response?.data?.message || err.message))
      .finally(() => setLoading(false))
  }, [ruleId, session.bidId, state])

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-10">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-40 rounded bg-slate-200" />
          <div className="h-8 w-64 rounded bg-slate-200" />
          <div className="grid grid-cols-1 gap-4 pt-4 sm:grid-cols-2">
            <div className="h-48 rounded-xl bg-slate-100" />
            <div className="h-48 rounded-xl bg-slate-100" />
          </div>
        </div>
      </div>
    )
  }

  if (!finding) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-10">
        <h1 className="page-title">Evidence</h1>
        {error && (
          <p className="mt-3 flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700 ring-1 ring-inset ring-red-200">
            <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
            {error}
          </p>
        )}
        <div className="card-pad mt-6 text-center">
          <p className="text-sm text-slate-500">
            Select any finding in the compliance matrix to inspect its evidence here.
          </p>
          <button className="btn-primary mt-4" onClick={() => navigate('/compliance')}>
            Go to compliance matrix
          </button>
        </div>
      </div>
    )
  }

  const claimed = finding.claimed?.value
  const verified = finding.verified?.value
  const mismatch =
    claimed !== undefined && verified !== undefined && String(claimed) !== String(verified)

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <button className="btn-ghost -ml-3" onClick={() => navigate('/compliance')}>
        <ArrowLeftIcon className="h-4 w-4" />
        Back to compliance matrix
      </button>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <h1 className="font-mono text-2xl font-bold tracking-tight text-slate-900">
          {finding.rule_id}
        </h1>
        <StatusChip status={finding.status} size="lg" />
        <SeverityChip severity={finding.severity} />
      </div>

      <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-slate-700">
        {finding.requirement_text}
      </p>
      {finding.reason && (
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-500">{finding.reason}</p>
      )}

      {mismatch && (
        <div className="mt-6 flex items-start gap-3 rounded-xl bg-red-50 p-4 ring-1 ring-inset ring-red-200">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-700">
            <AlertIcon className="h-5 w-5" />
          </span>
          <div>
            <p className="text-sm font-semibold text-red-800">
              The vendor's claim contradicts the government record
            </p>
            <p className="mt-1 text-sm leading-relaxed text-red-700">
              The bid states <span className="font-semibold">{String(claimed)}</span>, but the
              verified record shows <span className="font-semibold">{String(verified)}</span>. The
              rule engine resolved this against the government source.
            </p>
          </div>
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <ValueCard
          label="Claimed"
          sublabel="Extracted from the vendor's bid document"
          Icon={BuildingIcon}
          data={finding.claimed}
          highlight={mismatch}
        />
        <ValueCard
          label="Government verified"
          sublabel="Retrieved from the official portal record"
          Icon={ShieldIcon}
          data={finding.verified}
        />
      </div>

      {finding.evidence && (
        <div className="card mt-4 p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <FileIcon className="h-4 w-4 text-slate-400" />
              Source document
            </p>
            <span className="tnum rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
              Page {finding.evidence.page_number}
            </span>
          </div>
          {finding.evidence.snippet && (
            <blockquote className="mt-3 border-l-2 border-brand-300 bg-brand-50/40 py-2 pl-4 text-sm italic leading-relaxed text-slate-700">
              “{finding.evidence.snippet}”
            </blockquote>
          )}
          <p className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-slate-100 pt-3 text-[11px] text-slate-400">
            <span className="font-medium uppercase tracking-wide">Document SHA-256</span>
            <code className="font-mono text-slate-500">
              {finding.evidence.document_sha256?.slice(0, 32)}…
            </code>
          </p>
        </div>
      )}

      {finding.expected && Object.keys(finding.expected).length > 0 && (
        <div className="card mt-4 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Rule definition
          </p>
          <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
            {Object.entries(finding.expected).map(([key, value]) => (
              <div key={key}>
                <dt className="text-[11px] uppercase tracking-wide text-slate-400">
                  {key.replace(/_/g, ' ')}
                </dt>
                <dd className="tnum mt-0.5 text-sm font-medium text-slate-700">
                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  )
}

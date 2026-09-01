import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTenderRequirements } from '../api/client'
import { AlertIcon, CheckIcon } from '../components/common/icons'
import { useSession } from '../store/SessionContext'

const CATEGORY_TONE = {
  turnover: 'bg-brand-50 text-brand-700 ring-brand-200',
  experience: 'bg-violet-50 text-violet-700 ring-violet-200',
  certification: 'bg-teal-50 text-teal-700 ring-teal-200',
  registration: 'bg-sky-50 text-sky-700 ring-sky-200',
  financial: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  technical: 'bg-cyan-50 text-cyan-700 ring-cyan-200',
  msme: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  debarment: 'bg-red-50 text-red-700 ring-red-200',
  manual_review: 'bg-amber-50 text-amber-700 ring-amber-200',
}

function CategoryChip({ category }) {
  const tone = CATEGORY_TONE[category] ?? 'bg-slate-100 text-slate-600 ring-slate-200'
  return (
    <span
      className={`inline-flex whitespace-nowrap rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ring-1 ring-inset ${tone}`}
    >
      {String(category ?? '—').replace(/_/g, ' ')}
    </span>
  )
}

export default function Requirements() {
  const session = useSession()
  const navigate = useNavigate()
  const [requirements, setRequirements] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!session.tenderId) return
    setLoading(true)
    getTenderRequirements(session.tenderId)
      .then(setRequirements)
      .catch((err) => setError(err.response?.data?.message || err.message))
      .finally(() => setLoading(false))
  }, [session.tenderId])

  if (!session.tenderId) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-10">
        <h1 className="page-title">Eligibility requirements</h1>
        <div className="card-pad mt-6 text-center">
          <p className="text-sm text-slate-500">Upload a tender to see its extracted requirements.</p>
          <button className="btn-primary mt-4" onClick={() => navigate('/')}>
            Go to Upload
          </button>
        </div>
      </div>
    )
  }

  const sourced = requirements.filter((r) => r.source_page != null).length

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-3xl">
          <h1 className="page-title">Eligibility requirements</h1>
          <p className="page-sub">
            Criteria extracted from the tender document. Each one carries the page it came from, so
            a vendor's verdict can always be traced back to the clause that produced it.
          </p>
        </div>
        {requirements.length > 0 && (
          <div className="flex gap-2 text-xs">
            <span className="rounded-lg bg-white px-3 py-2 ring-1 ring-inset ring-slate-200">
              <span className="tnum font-bold text-slate-900">{requirements.length}</span>
              <span className="ml-1.5 text-slate-500">total</span>
            </span>
            <span className="rounded-lg bg-white px-3 py-2 ring-1 ring-inset ring-slate-200">
              <span className="tnum font-bold text-slate-900">{sourced}</span>
              <span className="ml-1.5 text-slate-500">page-sourced</span>
            </span>
          </div>
        )}
      </div>

      {error && (
        <p className="mt-5 flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700 ring-1 ring-inset ring-red-200">
          <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </p>
      )}

      {loading && requirements.length === 0 && (
        <div className="card mt-6 animate-pulse overflow-hidden">
          <div className="h-10 border-b border-slate-200 bg-slate-50" />
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center gap-4 border-b border-slate-100 px-4 py-3.5">
              <div className="h-3 w-20 rounded bg-slate-200" />
              <div className="h-3 flex-1 rounded bg-slate-100" />
            </div>
          ))}
        </div>
      )}

      {requirements.length > 0 && (
        <div className="card mt-6 overflow-hidden">
          <div className="max-h-[36rem] overflow-auto">
            <table className="w-full border-collapse">
              <thead className="sticky top-0 z-10 bg-slate-50/95 backdrop-blur">
                <tr className="border-b border-slate-200">
                  <th className="th">Ref</th>
                  <th className="th">Requirement</th>
                  <th className="th">Category</th>
                  <th className="th">Source</th>
                  <th className="th">Reviewed</th>
                </tr>
              </thead>
              <tbody>
                {requirements.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/70">
                    <td className="td">
                      <span className="font-mono text-xs font-semibold text-slate-800">
                        {r.external_ref ?? '—'}
                      </span>
                    </td>
                    <td className="td max-w-xl leading-relaxed text-slate-600">{r.text}</td>
                    <td className="td">
                      <CategoryChip category={r.category} />
                    </td>
                    <td className="td">
                      {r.source_page != null ? (
                        <span className="tnum text-xs text-slate-600">Page {r.source_page}</span>
                      ) : (
                        <span
                          className="text-xs text-slate-400"
                          title="Synthesized from the rule pack because LLM extraction hasn't run for this tender yet"
                        >
                          Rule pack
                        </span>
                      )}
                    </td>
                    <td className="td">
                      {r.human_reviewed ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                          <CheckIcon className="h-3.5 w-3.5" />
                          Yes
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">Pending</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && requirements.length === 0 && !error && (
        <div className="card-pad mt-6 text-center">
          <p className="text-sm font-medium text-slate-700">No requirements yet</p>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
            Requirements appear once extraction runs, or are synthesized from the rule pack the
            first time compliance runs for this tender.
          </p>
        </div>
      )}
    </div>
  )
}

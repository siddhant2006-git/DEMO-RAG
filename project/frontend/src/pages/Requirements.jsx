import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { extractTenderRequirements, getTenderRequirements, updateRequirement } from '../api/client'
import { AlertIcon, CheckIcon, RefreshIcon, SpinnerIcon } from '../components/common/icons'
import { useSession } from '../store/SessionContext'
import { useToast } from '../store/ToastContext'

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

const CATEGORIES = [
  'turnover', 'experience', 'certification', 'registration',
  'financial', 'technical', 'msme', 'debarment', 'manual_review',
]

const OPERATORS = ['gte', 'lte', 'gt', 'lt', 'eq', 'in', 'regex', 'date_before', 'date_after', 'exists']

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

function EditRow({ requirement, onCancel, onSaved }) {
  const [text, setText] = useState(requirement.text)
  const [category, setCategory] = useState(requirement.category)
  const [operator, setOperator] = useState(requirement.expected?.operator ?? '')
  const [value, setValue] = useState(requirement.expected?.value ?? '')
  const [unit, setUnit] = useState(requirement.expected?.unit ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function save(markReviewed) {
    setBusy(true)
    setError(null)
    try {
      const numericValue = value !== '' && !Number.isNaN(Number(value)) ? Number(value) : value
      const patch = {
        text,
        category,
        expected: operator ? { operator, value: numericValue, unit: unit || null } : {},
      }
      if (markReviewed) patch.human_reviewed = true
      const updated = await updateRequirement(requirement.tender_id, requirement.id, patch)
      onSaved(updated)
    } catch (err) {
      setError(err.response?.data?.message || err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <tr className="border-b border-slate-100 bg-brand-50/30 align-top last:border-0">
      <td className="td font-mono text-xs font-semibold text-slate-800">{requirement.external_ref ?? '—'}</td>
      <td className="td max-w-xl" colSpan={2}>
        <textarea
          className="input min-h-[3rem] w-full text-sm"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <select className="input w-40 text-xs" value={category} onChange={(e) => setCategory(e.target.value)}>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
          <select className="input w-32 text-xs" value={operator} onChange={(e) => setOperator(e.target.value)}>
            <option value="">no threshold</option>
            {OPERATORS.map((op) => (
              <option key={op} value={op}>
                {op}
              </option>
            ))}
          </select>
          {operator && (
            <>
              <input
                className="input w-28 text-xs"
                placeholder="value"
                value={value}
                onChange={(e) => setValue(e.target.value)}
              />
              <input
                className="input w-24 text-xs"
                placeholder="unit"
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
              />
            </>
          )}
        </div>
        {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
      </td>
      <td className="td" colSpan={2}>
        <div className="flex flex-col gap-1.5">
          <button className="btn-primary py-1 text-xs" disabled={busy} onClick={() => save(true)}>
            {busy && <SpinnerIcon className="h-3.5 w-3.5" />}
            Save & confirm
          </button>
          <button className="btn-secondary py-1 text-xs" disabled={busy} onClick={() => save(false)}>
            Save
          </button>
          <button className="btn-ghost py-1 text-xs" disabled={busy} onClick={onCancel}>
            Cancel
          </button>
        </div>
      </td>
    </tr>
  )
}

export default function Requirements() {
  const session = useSession()
  const navigate = useNavigate()
  const { notify } = useToast()
  const [requirements, setRequirements] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [extractBusy, setExtractBusy] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [confirmingId, setConfirmingId] = useState(null)

  function load() {
    if (!session.tenderId) return
    setLoading(true)
    getTenderRequirements(session.tenderId)
      .then(setRequirements)
      .catch((err) => setError(err.response?.data?.message || err.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [session.tenderId])

  async function handleExtract() {
    setExtractBusy(true)
    setError(null)
    try {
      const result = await extractTenderRequirements(session.tenderId)
      if (result.status === 'queued') {
        notify('Extraction queued on the worker — refresh shortly to see results.')
      } else {
        notify(`Extraction complete — ${result.requirements_created ?? 0} requirement(s) found`)
        load()
      }
    } catch (err) {
      const message = err.response?.data?.message || err.message
      setError(message)
      notify(message, { type: 'error' })
    } finally {
      setExtractBusy(false)
    }
  }

  async function handleConfirm(requirement) {
    setConfirmingId(requirement.id)
    try {
      const updated = await updateRequirement(session.tenderId, requirement.id, { human_reviewed: true })
      setRequirements((prev) => prev.map((r) => (r.id === updated.id ? updated : r)))
    } catch (err) {
      notify(err.response?.data?.message || err.message, { type: 'error' })
    } finally {
      setConfirmingId(null)
    }
  }

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
  const reviewed = requirements.filter((r) => r.human_reviewed).length

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
        <div className="flex items-center gap-2.5">
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
              <span className="rounded-lg bg-white px-3 py-2 ring-1 ring-inset ring-slate-200">
                <span className="tnum font-bold text-slate-900">{reviewed}</span>
                <span className="ml-1.5 text-slate-500">reviewed</span>
              </span>
            </div>
          )}
          <button onClick={handleExtract} disabled={extractBusy} className="btn-primary">
            {extractBusy ? <SpinnerIcon /> : <RefreshIcon />}
            {extractBusy ? 'Extracting…' : 'Extract requirements'}
          </button>
        </div>
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
                {requirements.map((r) =>
                  editingId === r.id ? (
                    <EditRow
                      key={r.id}
                      requirement={{ ...r, tender_id: session.tenderId }}
                      onCancel={() => setEditingId(null)}
                      onSaved={(updated) => {
                        setRequirements((prev) => prev.map((x) => (x.id === updated.id ? updated : x)))
                        setEditingId(null)
                      }}
                    />
                  ) : (
                    <tr key={r.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/70">
                      <td className="td">
                        <span className="font-mono text-xs font-semibold text-slate-800">
                          {r.external_ref ?? '—'}
                        </span>
                      </td>
                      <td className="td max-w-xl leading-relaxed text-slate-600">
                        <button
                          className="text-left hover:text-brand-700 hover:underline"
                          onClick={() => setEditingId(r.id)}
                          title="Edit this requirement"
                        >
                          {r.text}
                        </button>
                      </td>
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
                          <span
                            className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700"
                            title={r.reviewed_by ? `Confirmed by ${r.reviewed_by}` : undefined}
                          >
                            <CheckIcon className="h-3.5 w-3.5" />
                            Yes
                          </span>
                        ) : (
                          <button
                            className="btn-secondary py-1 text-xs"
                            disabled={confirmingId === r.id}
                            onClick={() => handleConfirm(r)}
                          >
                            {confirmingId === r.id ? <SpinnerIcon className="h-3.5 w-3.5" /> : 'Confirm'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && requirements.length === 0 && !error && (
        <div className="card-pad mt-6 text-center">
          <p className="text-sm font-medium text-slate-700">No requirements yet</p>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
            Click "Extract requirements" to run AI extraction over the tender, or requirements will be
            synthesized from the rule pack the first time compliance runs for this tender.
          </p>
        </div>
      )}
    </div>
  )
}

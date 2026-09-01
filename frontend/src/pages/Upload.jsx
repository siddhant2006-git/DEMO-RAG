import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadBid, uploadTender } from '../api/client'
import ApiStatus from '../components/common/ApiStatus'
import FileDrop from '../components/common/FileDrop'
import { AlertIcon, CheckIcon, SpinnerIcon } from '../components/common/icons'
import { useSession } from '../store/SessionContext'
import { useToast } from '../store/ToastContext'

function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="label">
        {label}
        {hint && <span className="ml-1.5 font-normal normal-case text-slate-400">{hint}</span>}
      </span>
      {children}
    </label>
  )
}

function StepHeader({ index, title, description, done, disabled }) {
  return (
    <div className="flex items-start gap-3">
      <span
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
          done
            ? 'bg-emerald-100 text-emerald-700'
            : disabled
              ? 'bg-slate-100 text-slate-400'
              : 'bg-brand-800 text-white'
        }`}
      >
        {done ? <CheckIcon className="h-4 w-4" /> : index}
      </span>
      <div className="min-w-0">
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{description}</p>
      </div>
    </div>
  )
}

function ErrorNote({ children }) {
  return (
    <p className="flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-inset ring-red-200">
      <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{children}</span>
    </p>
  )
}

export default function Upload() {
  const navigate = useNavigate()
  const session = useSession()
  const { notify } = useToast()

  const [tenderFile, setTenderFile] = useState(null)
  const [tenderTitle, setTenderTitle] = useState('')
  const [referenceNo, setReferenceNo] = useState('')
  const [category, setCategory] = useState('goods')
  const [tenderBusy, setTenderBusy] = useState(false)
  const [tenderError, setTenderError] = useState(null)

  const [bidFile, setBidFile] = useState(null)
  const [vendorName, setVendorName] = useState('')
  const [gstin, setGstin] = useState('')
  const [pan, setPan] = useState('')
  const [claimsMsme, setClaimsMsme] = useState(false)
  const [bidBusy, setBidBusy] = useState(false)
  const [bidError, setBidError] = useState(null)

  const bidLocked = !session.tenderId

  async function handleTenderSubmit(e) {
    e.preventDefault()
    if (!tenderFile || !tenderTitle) return
    setTenderBusy(true)
    setTenderError(null)
    try {
      const result = await uploadTender({
        file: tenderFile,
        title: tenderTitle,
        referenceNo,
        category,
      })
      session.update({ tenderId: result.tender_id, tenderTitle })
      notify(`Tender "${tenderTitle}" uploaded`)
    } catch (err) {
      const message = err.response?.data?.message || err.message
      setTenderError(message)
      notify(message, { type: 'error' })
    } finally {
      setTenderBusy(false)
    }
  }

  async function handleBidSubmit(e) {
    e.preventDefault()
    if (!bidFile || !vendorName || !session.tenderId) return
    setBidBusy(true)
    setBidError(null)
    try {
      const result = await uploadBid({
        file: bidFile,
        tenderId: session.tenderId,
        vendorName,
        gstin,
        pan,
        claimsMsmeBenefit: claimsMsme,
      })
      session.update({ bidId: result.bid_id, vendorName })
      notify(`Bid for "${vendorName}" uploaded`)
      navigate('/compliance')
    } catch (err) {
      const message = err.response?.data?.message || err.message
      setBidError(message)
      notify(message, { type: 'error' })
    } finally {
      setBidBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          <h1 className="page-title">Verify a vendor bid</h1>
          <p className="page-sub">
            Upload the tender and a vendor's bid. TenderGuard extracts the eligibility criteria and
            the vendor's claims, checks them against government records, and produces a compliance
            matrix where every verdict traces back to a page and a line.
          </p>
        </div>
        <ApiStatus />
      </div>

      <div className="mt-8 grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
        {/* Step 1 — tender */}
        <form onSubmit={handleTenderSubmit} className="card-pad space-y-5">
          <StepHeader
            index={1}
            title="Tender document"
            description="The document that defines the eligibility criteria vendors must meet."
            done={Boolean(session.tenderId)}
          />

          {session.tenderId && (
            <p className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800 ring-1 ring-inset ring-emerald-200">
              <CheckIcon className="h-4 w-4 shrink-0" />
              <span className="min-w-0 truncate">
                Uploaded · <span className="font-medium">{session.tenderTitle}</span>
              </span>
            </p>
          )}

          <FileDrop id="tender-file" file={tenderFile} onFile={setTenderFile} />

          <Field label="Title">
            <input
              className="input"
              value={tenderTitle}
              onChange={(e) => setTenderTitle(e.target.value)}
              placeholder="Tender for Supply of Road Construction Equipment"
            />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Reference no." hint="optional">
              <input
                className="input"
                value={referenceNo}
                onChange={(e) => setReferenceNo(e.target.value)}
                placeholder="TND/2026/0142"
              />
            </Field>
            <Field label="Category">
              <select
                className="input"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="goods">Goods</option>
                <option value="works">Works</option>
                <option value="services">Services</option>
              </select>
            </Field>
          </div>
          <p className="-mt-2 text-xs text-slate-400">
            Category selects which rule pack the bid is checked against.
          </p>

          {tenderError && <ErrorNote>{tenderError}</ErrorNote>}

          <button
            type="submit"
            disabled={tenderBusy || !tenderFile || !tenderTitle}
            className="btn-primary w-full"
          >
            {tenderBusy && <SpinnerIcon />}
            {tenderBusy ? 'Uploading…' : session.tenderId ? 'Replace tender' : 'Upload tender'}
          </button>
        </form>

        {/* Step 2 — bid */}
        <form
          onSubmit={handleBidSubmit}
          className={`card-pad space-y-5 transition-opacity ${bidLocked ? 'opacity-60' : ''}`}
        >
          <StepHeader
            index={2}
            title="Vendor bid"
            description="The vendor's submission, with the identifiers used to look them up on government portals."
            disabled={bidLocked}
          />

          <FileDrop id="bid-file" file={bidFile} onFile={setBidFile} disabled={bidLocked} />

          <Field label="Vendor name">
            <input
              className="input"
              disabled={bidLocked}
              value={vendorName}
              onChange={(e) => setVendorName(e.target.value)}
              placeholder="Ganga Infra Projects Pvt Ltd"
            />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="GSTIN">
              <input
                className="input font-mono"
                disabled={bidLocked}
                value={gstin}
                onChange={(e) => setGstin(e.target.value.toUpperCase())}
                placeholder="27AAAPL1234C1Z5"
                maxLength={15}
              />
            </Field>
            <Field label="PAN">
              <input
                className="input font-mono"
                disabled={bidLocked}
                value={pan}
                onChange={(e) => setPan(e.target.value.toUpperCase())}
                placeholder="AAAPL1234C"
                maxLength={10}
              />
            </Field>
          </div>

          <label
            className={`flex items-start gap-2.5 rounded-lg border border-slate-200 px-3 py-2.5 transition-colors ${
              bidLocked ? '' : 'cursor-pointer hover:bg-slate-50'
            }`}
          >
            <input
              type="checkbox"
              disabled={bidLocked}
              checked={claimsMsme}
              onChange={(e) => setClaimsMsme(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 accent-brand-700"
            />
            <span className="text-sm leading-snug text-slate-700">
              Claims MSME benefit
              <span className="mt-0.5 block text-xs text-slate-400">
                Enables the Udyam registration rules for this bid.
              </span>
            </span>
          </label>

          {bidError && <ErrorNote>{bidError}</ErrorNote>}

          <button
            type="submit"
            disabled={bidBusy || !bidFile || !vendorName || bidLocked}
            className="btn-primary w-full"
          >
            {bidBusy && <SpinnerIcon />}
            {bidBusy ? 'Uploading…' : 'Upload bid & run checks'}
          </button>
        </form>
      </div>
    </div>
  )
}

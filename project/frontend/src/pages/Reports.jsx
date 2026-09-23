import { getReportUrl } from '../api/client'
import { DownloadIcon, FileIcon, ShieldIcon } from '../components/common/icons'
import { useSession } from '../store/SessionContext'

const CONTENTS = [
  { title: 'Summary', body: 'Risk score, band, and pass/fail counts for the bid.' },
  { title: 'Compliance matrix', body: 'Every rule with its verdict, severity, and both values.' },
  { title: 'Evidence appendix', body: 'Page and verbatim snippet behind each non-passing finding.' },
  { title: 'Document hashes', body: 'SHA-256 of the tender and bid, so the file set is provable.' },
]

export default function Reports() {
  const session = useSession()

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="page-title">Compliance report</h1>
      <p className="page-sub max-w-2xl">
        A self-contained PDF of the last compliance run — the artefact that goes into the
        procurement file and stands up on its own in an audit.
      </p>

      <div className="card mt-8 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 bg-gradient-to-br from-brand-50/60 to-white p-6">
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-800 text-white shadow-sm">
              <FileIcon className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <p className="font-semibold text-slate-900">
                {session.vendorName ?? 'Vendor'} — compliance report
              </p>
              <p className="mt-0.5 truncate text-sm text-slate-500">
                {session.tenderTitle ?? 'Current tender'}
              </p>
            </div>
          </div>

          {session.bidId ? (
            <a href={getReportUrl(session.bidId)} className="btn-primary shrink-0">
              <DownloadIcon />
              Download PDF
            </a>
          ) : (
            <span className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700 ring-1 ring-inset ring-amber-200">
              Upload a bid and run compliance first
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 divide-y divide-slate-100 sm:grid-cols-2 sm:divide-y-0">
          {CONTENTS.map((c, i) => (
            <div
              key={c.title}
              className={`p-5 ${i % 2 === 0 ? 'sm:border-r sm:border-slate-100' : ''} ${
                i < 2 ? 'sm:border-b sm:border-slate-100' : ''
              }`}
            >
              <p className="text-sm font-semibold text-slate-800">{c.title}</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">{c.body}</p>
            </div>
          ))}
        </div>
      </div>

      <p className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-slate-500">
        <ShieldIcon className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
        <span>
          Every download is recorded in the append-only audit trail, alongside the uploads,
          verification runs, and compliance runs that produced this report.
        </span>
      </p>
    </div>
  )
}

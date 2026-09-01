import { useRef, useState } from 'react'
import { CheckIcon, FileIcon, UploadIcon } from './icons'

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function FileDrop({ file, onFile, disabled, id }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  function take(list) {
    const picked = list?.[0]
    if (!picked) return
    // Accept only PDFs — the backend rejects anything else anyway, so failing
    // here saves a round trip and explains itself immediately.
    if (picked.type !== 'application/pdf' && !picked.name.toLowerCase().endsWith('.pdf')) return
    onFile(picked)
  }

  const state = disabled ? 'disabled' : file ? 'filled' : dragging ? 'dragging' : 'empty'
  const tone = {
    disabled: 'border-slate-200 bg-slate-50 cursor-not-allowed',
    empty: 'border-slate-300 bg-white hover:border-brand-400 hover:bg-brand-50/40 cursor-pointer',
    dragging: 'border-brand-500 bg-brand-50 ring-2 ring-brand-500/20 cursor-copy',
    filled: 'border-emerald-300 bg-emerald-50/50 hover:border-emerald-400 cursor-pointer',
  }[state]

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      aria-label={file ? `Selected ${file.name}. Choose a different PDF` : 'Choose a PDF file'}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if (disabled) return
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          inputRef.current?.click()
        }
      }}
      onDragOver={(e) => {
        if (disabled) return
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        if (disabled) return
        e.preventDefault()
        setDragging(false)
        take(e.dataTransfer.files)
      }}
      className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-7 text-center transition-all ${tone}`}
    >
      <input
        id={id}
        ref={inputRef}
        type="file"
        accept="application/pdf"
        disabled={disabled}
        className="sr-only"
        onChange={(e) => take(e.target.files)}
      />

      {file ? (
        <>
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
            <CheckIcon className="h-5 w-5" />
          </span>
          <p className="mt-2 flex items-center gap-1.5 text-sm font-semibold text-slate-800">
            <FileIcon className="h-4 w-4 text-slate-400" />
            <span className="max-w-[16rem] truncate">{file.name}</span>
          </p>
          <p className="tnum mt-0.5 text-xs text-slate-500">
            {formatSize(file.size)} · click to replace
          </p>
        </>
      ) : (
        <>
          <span
            className={`flex h-9 w-9 items-center justify-center rounded-full ${
              disabled ? 'bg-slate-100 text-slate-300' : 'bg-brand-50 text-brand-600'
            }`}
          >
            <UploadIcon className="h-5 w-5" />
          </span>
          <p
            className={`mt-2 text-sm font-medium ${disabled ? 'text-slate-400' : 'text-slate-700'}`}
          >
            {disabled ? 'Upload the tender first' : 'Drop a PDF here or click to browse'}
          </p>
          <p className="mt-0.5 text-xs text-slate-400">PDF only · up to 50 MB</p>
        </>
      )}
    </div>
  )
}

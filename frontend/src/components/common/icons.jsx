/* Single-stroke 20x20 icon set. Inline (not a sprite or an icon package) so the
   app has zero network dependencies — the demo must run with the wifi off. */

function Svg({ className = 'h-4 w-4', children, ...rest }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  )
}

export function CheckIcon(props) {
  return (
    <Svg {...props}>
      <path d="m4 10.5 4 4 8-9" />
    </Svg>
  )
}

export function WarningIcon(props) {
  return (
    <Svg {...props}>
      <path d="M10 3 2 17h16L10 3Z" />
      <path d="M10 8.5v3.5" />
      <circle cx="10" cy="14.6" r="0.7" fill="currentColor" stroke="none" />
    </Svg>
  )
}

export function AlertIcon(props) {
  return (
    <Svg {...props}>
      <circle cx="10" cy="10" r="7.5" />
      <path d="M10 6.5v4" />
      <circle cx="10" cy="13.6" r="0.7" fill="currentColor" stroke="none" />
    </Svg>
  )
}

export function LockIcon({ className = 'h-3.5 w-3.5' }) {
  return (
    <Svg className={className}>
      <rect x="4.5" y="9" width="11" height="8" rx="1.5" />
      <path d="M6.75 9V6.75a3.25 3.25 0 0 1 6.5 0V9" />
    </Svg>
  )
}

export function ShieldIcon(props) {
  return (
    <Svg {...props}>
      <path d="M10 2.5 4 4.75V9.5c0 3.6 2.4 6.6 6 8 3.6-1.4 6-4.4 6-8V4.75L10 2.5Z" />
      <path d="m7.5 10 1.8 1.8L12.75 8.4" />
    </Svg>
  )
}

export function UploadIcon(props) {
  return (
    <Svg {...props}>
      <path d="M10 13V3.5" />
      <path d="m6.5 7 3.5-3.5L13.5 7" />
      <path d="M3.5 13v2.5a1.5 1.5 0 0 0 1.5 1.5h10a1.5 1.5 0 0 0 1.5-1.5V13" />
    </Svg>
  )
}

export function FileIcon(props) {
  return (
    <Svg {...props}>
      <path d="M11.5 2.5H6a1.5 1.5 0 0 0-1.5 1.5v12A1.5 1.5 0 0 0 6 17.5h8a1.5 1.5 0 0 0 1.5-1.5V6.5l-4-4Z" />
      <path d="M11.5 2.5v4h4" />
    </Svg>
  )
}

export function DownloadIcon(props) {
  return (
    <Svg {...props}>
      <path d="M10 3.5V13" />
      <path d="m6.5 9.5 3.5 3.5 3.5-3.5" />
      <path d="M3.5 13v2.5a1.5 1.5 0 0 0 1.5 1.5h10a1.5 1.5 0 0 0 1.5-1.5V13" />
    </Svg>
  )
}

export function SearchIcon(props) {
  return (
    <Svg {...props}>
      <circle cx="9" cy="9" r="5.5" />
      <path d="m13.5 13.5 3 3" />
    </Svg>
  )
}

export function ArrowLeftIcon(props) {
  return (
    <Svg {...props}>
      <path d="M16 10H4" />
      <path d="m8.5 5.5-4.5 4.5 4.5 4.5" />
    </Svg>
  )
}

export function ChevronRightIcon(props) {
  return (
    <Svg {...props}>
      <path d="m8 5 5 5-5 5" />
    </Svg>
  )
}

export function RefreshIcon(props) {
  return (
    <Svg {...props}>
      <path d="M16.5 8.5a6.5 6.5 0 1 0 .4 3.5" />
      <path d="M16.5 3.5v5h-5" />
    </Svg>
  )
}

export function SpinnerIcon({ className = 'h-4 w-4' }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={`animate-spin ${className}`} aria-hidden="true">
      <circle cx="10" cy="10" r="7.5" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2.5" />
      <path
        d="M17.5 10A7.5 7.5 0 0 0 10 2.5"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function BuildingIcon(props) {
  return (
    <Svg {...props}>
      <path d="M3.5 17h13" />
      <path d="M5 17V5.5L10 3l5 2.5V17" />
      <path d="M8.25 8.5h3.5M8.25 11.5h3.5M8.25 14.5h3.5" />
    </Svg>
  )
}

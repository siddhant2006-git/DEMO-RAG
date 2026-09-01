# Frontend UI/UX problems

Findings from reading `frontend/src/**` (App.jsx, NavBar, Upload, Requirements, ComplianceMatrix,
EvidenceViewer, Reports, RiskGauge, StatusChip, FindingRow, ApiStatus, SessionContext). Each item
below is grounded in the actual code, not a hypothetical — file:line points at the spot to fix.

The officer's real flow is Upload → Requirements → Compliance → Evidence → Reports, so the biggest
wins are ones that make that pipeline legible: where am I, what's next, did my last action work.

## 1. Navigation doesn't reflect pipeline state

`NavBar.jsx` renders all five links as always-enabled, in a flat row, with no indication of which
steps are unlocked. A user can click "Compliance Matrix" or "Evidence" before uploading anything and
land on a page whose only content is a one-line "upload first" message (`ComplianceMatrix.jsx:71-84`,
`Requirements.jsx:22-35`). That's four near-identical dead-end states instead of the nav simply
showing the step as disabled/locked up front.

- **Fix:** derive per-link enabled state from `useSession()` (`tenderId` gates Requirements/Compliance,
  `bidId` gates Evidence/Reports) and render locked links as visibly disabled with a tooltip, or as a
  numbered stepper (1 Upload → 2 Requirements → 3 Compliance → 4 Evidence → 5 Reports) showing
  completed/current/locked instead of a plain link list.

## 2. No persistent context of *which* tender/bid you're working on

`session.tenderId`/`vendorName` only surface as a one-line aside on the Upload page
(`Upload.jsx:93-97`). Every other page — Requirements, Evidence, Reports — gives no reminder of which
tender/vendor is active. `Reports.jsx` in particular just says "Download the PDF compliance report"
with no vendor/tender name, so after working multiple bids in a session an officer can't tell which
report they're about to download.

- **Fix:** show a persistent context bar (tender title + vendor name, truncated ids) in `NavBar` or a
  sub-header, sourced from `useSession()`, visible on every route once a tender/bid exists.

## 3. No way to start a new tender/bid cycle

`SessionContext.jsx` persists `tenderId`/`bidId` to `localStorage` forever (`tenderguard.session`, no
TTL, no clear action anywhere in the UI). To review a second tender the user has to know to clear
browser storage manually — there's no "New session" / "Start over" control.

- **Fix:** add a visible reset action (e.g. in the context bar from #2) that clears session state and
  routes back to Upload.

## 4. Inline-only error/success feedback, easy to miss

Every page follows the same pattern: `{error && <p className="text-sm text-red-600">{error}</p>}`
inline in the form flow (`Upload.jsx:130,192`, `Requirements.jsx:47`, `ComplianceMatrix.jsx:113`) with
no equivalent success confirmation ("tender uploaded", "verification complete") and no toast/dismiss
mechanism. A user who submits and looks away can miss a failure entirely, and there's never positive
feedback that an action succeeded beyond a state change elsewhere on the page.

- **Fix:** a shared toast/notification component for success and error, in addition to (not instead
  of) the inline messages already shown for form-level validation.

## 5. `RiskGauge` isn't a gauge

`RiskGauge.jsx` renders the score and band as plain text (`<p className="text-3xl">{score}</p>` +
colored label) — no arc, bar, or any visual proportional to 0-100. For a component whose entire job
is to give an officer an at-a-glance risk read, defaulting to reading a number is the opposite of the
point, and the HIGH/MEDIUM/LOW band is conveyed by text color alone.

- **Fix:** render an actual proportional gauge (arc or horizontal bar) with the band thresholds marked,
  and pair the color with a non-color cue (icon or label) already partially present via the text label.

## 6. Verification results dumped as raw JSON

`ComplianceMatrix.jsx:122`: `{r.status === 'UP' && `— ${JSON.stringify(r.normalized)}`}` — the one
place portal verification data reaches the UI, it's an unformatted JSON blob next to the portal name.
An officer reading this has to parse `{"gstin_status":"Active",...}` by eye.

- **Fix:** render `normalized` as a small key/value list (or a per-portal card), same treatment
  `ValueCard` already gives claimed/verified values in `EvidenceViewer.jsx`.

## 7. Evidence is only reachable via in-memory router state — breaks on refresh/back-forward/deep-link

`EvidenceViewer.jsx` reads the finding exclusively from `useLocation().state` (`state: { finding: f }`
passed by `ComplianceMatrix.jsx:175`). Refreshing the evidence page, opening it in a new tab, or
navigating via browser back/forward loses the finding and drops the user into the generic "click a
finding in the compliance matrix" empty state — even though the same finding is one API call away by
id.

- **Fix:** route by id (`/evidence/:findingId` or `?rule=`) and fetch on mount, using router state only
  as an optional fast-path/cache.

## 8. `FindingRow` component exists but isn't used, and disagrees with the table that replaced it

`components/compliance/FindingRow.jsx` renders 4 columns (`requirement_id`, requirement_text, status,
severity) but `ComplianceMatrix.jsx:171-190` inlines its own `<tr>` with 6 columns (adds `claimed`,
`verified`, and uses `rule_id` instead of `requirement_id`). `FindingRow` is dead code from a
half-finished refactor — confusing for anyone maintaining this next, and a sign the row shape/columns
were never fully decided.

- **Fix:** delete `FindingRow.jsx` and keep the inline table row as the single source of truth, or the
  reverse (extract the current inline row back into `FindingRow` and use it) — either way, one
  definition, not two.

## 9. Loading state is a layout-shifting text swap, and busy buttons lose their label

Every async page does `{loading && <p>Loading…</p>}` above the content it's loading (`Requirements.jsx:46`,
implicitly `ComplianceMatrix.jsx`), which pops in above existing content and shifts everything down
rather than reserving space (no skeleton). Separately, `ComplianceMatrix.jsx`'s "Run verification" /
"Run compliance" buttons only go `disabled` + dim on click (`ComplianceMatrix.jsx:96-109`) — unlike
`Upload.jsx:136,198` which swap the label to "Uploading…", these two give no in-button confirmation
that anything is happening, only the disabled opacity.

- **Fix:** consistent busy-button labels across all four async actions (upload tender, upload bid,
  verify, run compliance), and skeleton placeholders (or at least a fixed-height spinner region) instead
  of a text node that shifts layout when it appears/disappears.

## 10. No confirmation before an action that replaces existing findings

Per `backend/CLAUDE.md`: running compliance "replaces (not appends) this bid's `Finding` rows." The UI
button is simply labeled "Re-run compliance" (`ComplianceMatrix.jsx:108`) with no warning that prior
findings — including any an officer may have referenced or exported — are being discarded, not
versioned.

- **Fix:** a lightweight confirm step (native `confirm()` at minimum, a proper dialog ideally) before
  re-running compliance when findings already exist.

## 11. Tables have no responsive strategy beyond `overflow-x-auto`

`Requirements.jsx:50` and `ComplianceMatrix.jsx:158` both wrap a 5-6 column table in
`overflow-x-auto` and nothing else — no column priority, no stacked/card layout below a breakpoint, no
sticky header for long result sets. On a narrow viewport the officer gets a horizontally-scrolling
table with no visual hint that there's more to the right.

- **Fix:** either a responsive card layout under a breakpoint (each finding/requirement as a card on
  mobile) or at minimum a scroll-affordance (fade/shadow at the clipped edge) and a sticky header.

## 12. Color is the only status signal in a couple of spots

`RiskGauge`'s band color (red/amber/emerald text, `RiskGauge.jsx:2-4`) is the sole way of reading
HIGH/MEDIUM/LOW severity at a glance before reading the label text next to it, and the NavBar active
link relies on a filled background rather than any additional marker. `StatusChip` already pairs color
with a text label, so it's fine — the gap is specifically the risk band and could extend to an icon
(⚠/✓) alongside the label for scanability, not just accessibility.

- **Fix:** pair the risk band with an icon in addition to color+text (already has text, so this is
  about scan speed, not a strict a11y blocker).

---

## Suggested priority order

1. **#1 nav/stepper state** and **#2 persistent context bar** — these two fix the "where am I / what's
   next" problem that touches every page.
2. **#7 evidence deep-linking** and **#8 dead FindingRow** — small, contained, prevents confusion for
   the next person editing this code.
3. **#5 real risk gauge** and **#6 formatted verification results** — the two spots officers actually
   need to read data quickly.
4. **#4 toasts**, **#9 busy-state consistency**, **#10 re-run confirmation**, **#3 session reset** —
   polish pass once the structural issues above are settled.
5. **#11 responsive tables**, **#12 icon+color** — lowest urgency, revisit if/when the app needs to
   support tablet/mobile officer use.

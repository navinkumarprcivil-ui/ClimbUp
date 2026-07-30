# Handoff — where ClimbUp stands

Updated for build `2026-07-30.2`. Read this first in a new session; the README has
the architecture, this has the state and the traps.

---

## 1. Blocked on you, not on code

Everything below is committed to `main` and verified locally. The previous
Vercel project has been **deleted and is being recreated**, so there is no live
deployment right now. Three actions, all dashboard-only — no agent can do any
of them:

1. **Import the repo at vercel.com/new** — not `vercel deploy` from the CLI.
   Importing wires the Git connection at the same time, so every push to `main`
   deploys itself; a CLI deploy is a one-shot upload that never watches GitHub,
   which is what left the last project stuck on a stale build for days.
   Settings for this repo: Framework Preset **Other**, no build command, no
   output directory, root directory `./`. There is no build step.
2. **Add the new hostname to Firebase** — console → Authentication → Settings →
   Authorized domains. A new project means a new hostname and the old entry
   does not cover it. Miss this and the app loads to a sign-in screen whose
   button fails with `auth/unauthorized-domain`; since the gate covers
   everything, it looks completely broken.
3. **Hard-refresh after deploying**, or close every tab and reopen. Cache is at
   `climbup-v28`. The worker is **network-first for the page**, so an
   ordinary reload picks a new build up; a device stuck on an older
   cache-first worker needs two reloads, or Settings → App version → Refresh.

Then record the new URL in this file and in the README.

**It has landed when:** the bottom nav reads `Dashboard · Today · Plan ·
Revise`, the dashboard opens on a month calendar with today ringed, and the
middle session is called **Busy Hours** rather than Office or Noon.

`SCHEMA` is 4 and old data goes through the `MIGRATIONS` ladder. Never bump it
without adding the next migration. An unreadable/future snapshot is held for
download instead of silently replaced.

> The sandbox these sessions run in **cannot reach `vercel.app` or `github.io`**
> (network policy answers 403 to CONNECT). No agent can verify the live site for
> you. Verification here is always against a local server.

---

## 2. How to change the app

`index.html`'s app content is **not hand-editable** — it is a ~0.86 MB
self-contained bundle with base64 islands. (The loading shell before those
islands is the one exception — see the traps table.) Use the committed
tooling:

```bash
python3 tools/bundle.py unpack     # -> build/template.html  (edit THIS)
#   ... edit build/template.html ...
python3 tools/bundle.py pack       # -> writes index.html
python3 tools/bundle.py assets     # what is in the manifest, by size
```

`pack` round-trips byte-identically, so an unpack/pack with no edits is a no-op.
`build/` is gitignored; `index.html` is the artefact that ships.

To test in a browser, the sign-in gate has to be stubbed or you see nothing:

```bash
python3 tools/bundle.py pack && python3 tools/preview.py
python3 -m http.server 8000 --directory build     # then load /preview.html
```

Chromium is at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`;
`pip install playwright` and drive it — do not trust reading the code, this
codebase has produced several bugs that only appear when something is actually
clicked.

---

## 3. Traps that have already cost real debugging

Each of these was found by measuring, not reading. They are in the README too;
they are here because they will bite again.

| Trap | What happens |
| --- | --- |
| `componentDidUpdate(prevProps)` — **no prevState** | The DC runtime passes one argument. Comparing against a second throws inside a runtime `try/catch`, so the symptom is silent: the debounced cloud save simply never fires. Track previous values yourself. |
| `window.firebase` is **not stable** | `firebase-app-compat` gets evaluated twice; the second evaluation installs a *bare* namespace with no `auth`, no `database` and an empty app list. Re-initialising does not fix it — the components are gone. Always go through `window.__firebaseApp()`, never the global. |
| Assets live in **two** islands | React and ReactDOM are named only in `ext_resources`. Prune against the template alone and the app boots blank reaching for unpkg.com. |
| `<textarea>{{ x }}</textarea>` | Renders `[object Object]`, and the broken element then swallows clicks on everything beneath it. React drives a textarea through `value`. |
| Dragging an `<img>` | Starts Chrome's native image drag, which fires `pointercancel` and kills a pointer gesture after exactly two moves. The cropper image is `pointer-events:none`. |
| Gesture handlers bound to an element | Lost after one move — every move sets state and the re-render can hand back a different DOM node. Both the drag and the cropper delegate from `document`. |
| `setState` mid-drag | Rebuilds the rows and strips the transforms the gesture is driving. The drag writes styles directly and commits only on release; `_dragging` holds the clock and recall timers still. |
| `Date.toISOString()` | Converts to UTC and lands on the wrong day outside Greenwich. Use `iso()`, which formats from local parts. |
| `"//"` keys in `vercel.json` | Vercel validates strictly; a header route takes only `source`, `headers`, `has`, `missing`. Anything else fails the deploy. |
| Firebase drops empty arrays/objects | A key the user has legitimately emptied comes back **missing**. `loadCloud` refills from `freshState()`. |
| Firebase authorized domains | Every host the app is served from must be listed, or `signInWithPopup` rejects and the whole app is a dead sign-in screen. Vercel preview URLs are not covered by the production entry. |
| `index.html`'s outer shell (everything before `<script type="__bundler/manifest">`) | Not part of `build/template.html` — `unpack`/`pack` never touch it. It is the loading screen shown while the ~0.9 MB bundle downloads and unpacks, and it is hand-edited directly in `index.html`; a `pack()` afterwards leaves it alone since `pack()` starts from the on-disk `index.html` and only replaces the `template` island. On a throttled connection it is on screen for 10+ seconds, so what it shows matters — see below. |
| Auto-split's day formula used to spread points across the *whole* span with rounding | A week task's own span (once dated by the month split) is 8 inclusive calendar days, not 7, because only the month split's non-first parts get their start pushed a day late to stay contiguous — the first part keeps the extra day. Splitting that first part into 7 days with `round(span*i/(n-1))` then skips one real calendar day in the middle (Wed, between Tue and Thu). Fixed by anchoring day parts to the end date and walking back one day at a time (`addDays(end, i-(n-1))`, clamped so it never passes the start) — gap-free by construction, identical output to the old formula whenever the span was already exact. |

---

## 4. What exists now

**Model.** One task type at three zooms — `scope` is `month | week | day`, with
a `parent` link. A day task also has a `block` (keys `morning` / `noon` / `evening`, labelled
Morning / Busy Hours / Evening), a
`date`, and a `note`. Month and week tasks carry a `targetDate`. Goals sit
alongside and are just a name, a deadline and a tag on tasks. Routines are
separate: they repeat by weekday, are ticked per date, and never carry.

A day task also carries `carried` (bool) and `carryCount` (number, the row
reads "carried" at 1 and "carried ×N" above that, with a title tooltip
spelling it out). `rollForward` — the silent midnight/reopen catch-up — bumps
`carryCount` by however many calendar days the task actually sat stale
(`daysBetween(t.date, now)`), not by a flat 1, so a device closed for a week
and reopened once still reads "carried ×7" rather than under-reporting it as
once. The evening review's "Carry to tomorrow" / "Batch onto the weekend" and
the backlog's "Move to tonight" / "Move to Saturday" are each a single
deliberate user action, so those bump it by a flat +1 instead.

**Screens.** Dashboard (month calendar, coming-up, progress at three zooms,
what-to-improve, week bars, streak, weakest recall, slip reasons) · Today
(routines + tasks per session, long-press to drag into order, backlog, review)
· Plan (Month/Week tabs, guided breakdown) · Daily routine · Revise (topic
groups, image cards with a pan-and-pinch cropper, "revise all") · Settings
(editable hours per session — capacity is the span between them — office days,
notifications, recall frequency, theme, erase everything) · Goals.

**Flow the app is built around:** add a monthly task → pick its target date →
saving opens the weekly split of that same task → saving a week opens its days →
"Save and add another" keeps the sheet on the same parent and steps the date on.
The same breakdown sheet now has a no-details automatic route: months become
four evenly dated parts, and weeks become up to seven daily parts. Nested names
retain their path (`Parent — Part 1` → `Parent — Part 1.1`).

**Offline-first.** After one online sign-in, the app restores the account and
all `PERSIST_KEYS` from IndexedDB, lets every ordinary task and split-task flow
continue offline, and moves pending work to Firebase automatically on
reconnect. Pending device data wins over an older cloud read. Card-image
adds/deletions have their own compact retry queue; the data URLs remain in
`sp.cardImages`. Signing out or changing Google accounts clears the previous
account's device record. The Dashboard status chip appears only when useful;
Settings always explains the current device/cloud state.

**Opening.** Two stages, and they now share one visual language instead of
jump-cutting between them. First, `index.html`'s outer shell (not part of the
template island — see traps) shows a small inline SVG mark — stem, leaves, a
sparkle instead of a flower "bloom" — plus a "ClimbUp" wordmark, a slow
breathing pulse, and a soft blue-violet gradient, while the ~0.9 MB bundle
downloads and unpacks; the status line under it reads "Loading ClimbUp…" then
"Almost there…" (error strings are untouched, on purpose, for anyone
debugging a real failure). This used to be a generic, unrelated abstract
flower-shaped placeholder on flat grey with a static "Unpacking…" — harmless
on localhost where it clears in under 100 ms, but on a throttled connection it
was the only thing on screen for 10+ seconds with no motion, which reads as a
crash rather than a load. Second, once the real app mounts, a 2.4-second
mark/name/glow sequence in the same gradient covers the remaining cache/auth
work, then dissolves into the app. `prefers-reduced-motion` shortens the
second stage to a near-instant 250 ms and drops the first stage's pulse.

**Verified in-browser at 320/390/412px, and via a real Playwright run against
`build/preview.html` with a `Date` override to cross simulated midnights:**
the guided chain end to end (month → 4 dated week parts → up to 7 dated day
parts per week, and a week target straight into up to 7 day parts, both with
no split-detail questions and every part named `Parent — Part N` /
`Parent — Part N.M`), descriptions surviving into nested rows, drag reorder,
routines appearing on Today and never carrying, carry-forward marking a stale
task `carried` with an accurate `carryCount` on both the Today row and the
Plan nested drilldown, a completed task staying put on its own date, split
day-parts carrying independently of their siblings, crop-and-save, hour
editing, erase, calendar highlighting today, and the loading placeholder
above. No page errors, on a fast connection or a throttled one (confirmed it
completes rather than hangs — just proportionally slower).

**Verified in the source harness at build `2026-07-29.2`:** automatic month and
week split counts, nested part naming, consecutive date windows, rollover of
ordinary tasks, split tasks and fixed-time tasks, IndexedDB restore, offline
device writes, reconnect upload and queued card-image operations. Routines
remain unchanged.

---

## 5. Known limits and likely next steps

- **Weekly/monthly progress is task-count based**, not effort-weighted. Fine
  now, will feel wrong once tasks vary a lot in size.
- **No editing of an existing task** — only add and delete. This is the most
  obvious gap for daily use.
- **Notifications cannot fire while the app is closed.** Real alarms need Web
  Push and a server; `sw.js` already handles `notificationclick`, so the client
  half is done.
- **Card images now sync.** They stay out of the debounced `PERSIST_KEYS`
  payload — megabytes of base64 have no business in a realtime sync — and are
  written one key at a time to `users/<uid>/cardImages/<cardId>`, with
  `localStorage` kept as a fast local cache. `saveCloud` must therefore stay on
  `update()`; going back to `set()` wipes that sibling on the next save and the
  image vanishes on reopen.
- **One open question for the owner:** daily targets filled in for a *future*
  week are filed on those future dates, so they do not appear on Today until
  that day arrives. That is the intended reading of "assigned on a daily basis"
  — confirm, or change it so they all land on today.
- **The backlog is now wired up** (was dead — see history below). Two paths
  file into `state.backlog`: (1) the evening review's third destination "Set
  aside for now" (`reviewToBacklog`), which files every slipped task with the
  reason chosen in step 1 — so the reason the user picks now actually reaches
  the dashboard's slip-reason chart; and (2) a "Set aside" action that appears
  on any Today row carried ≥3 times (`parkTask`), for parking a single repeat
  offender without opening the review. Parked items keep `carryCount`, so
  "Do today"/"Weekend" from the backlog card bring them back with history
  intact. The backlog card and the dashboard chart were always built and
  correct — they simply never had data before. *Historic note for context: up
  to build `2026-07-30.1` nothing populated `state.backlog` at all, so the
  card never rendered and the slip-reason chart was always empty.*
- **A chronically-carried task now has an exit ramp.** A day task carried ≥3
  times gets its `carried ×N` tag in the attention colour, a one-line nudge at
  the top of Today, and the "Set aside" action above. Below 3 it stays quiet,
  so an ordinary one-day slip is not nagged.
- **Home-screen shortcuts.** `manifest.webmanifest` declares `shortcuts` for
  Today (`./?screen=today`) and Plan (`./?screen=plan`); `applyLaunchScreen()`
  reads `?screen=` on mount and opens there. This is as close to a native
  home-screen *widget* as a PWA can get — long-press the installed icon for
  quick jumps — but it is **not** a live widget (no web API exists for one on
  iOS or Android; that needs a native wrapper). The SW already serves the
  cached page for any navigation, so the query-string URLs work offline with
  no SW change.

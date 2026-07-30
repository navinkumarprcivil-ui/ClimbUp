# ClimbUp — Task, Study, Steady growth

A daily task and study planner built around one idea: **you should be able to see yourself falling behind.**
Set a monthly target, break it into weekly, break those into daily, then open Today and drag
the day into the order you'll actually do it. Review the day, and watch the backlog build if
you don't.

Single self-contained page. No build step, no dependencies, no server.

## Deploy

Everything is static — drop this folder on any host. HTTPS is required for
install-to-home-screen and for notifications; all of these give you that.

**Vercel** — what this repo is set up for. `vercel.json` carries the cache
headers; there is no build step, so Vercel just serves the folder.

```
npm i -g vercel
vercel login
vercel link            # once, from this folder
vercel deploy --prod
```

Or connect the repo at vercel.com/new and it redeploys on every push to `main`.
A private repo is fine — Vercel does not need it public.

Those cache headers matter more than they look. `index.html` **is** the app and
its name never changes, so it is sent `max-age=0, must-revalidate`: Vercel
answers 304 from the ETag when nothing changed, which costs one round trip
instead of 0.6 MB. `sw.js` gets the same treatment, because a cached service
worker is one that never updates, and this one is cache-first — a stale copy
would keep serving an old build to installed clients indefinitely. Icons and the
manifest get a day with `stale-while-revalidate`, not `immutable`, since their
names are not content-hashed.

Do not put `"//"` comment keys in `vercel.json`. Vercel validates it strictly and
a header route accepts only `source`, `headers`, `has` and `missing` — anything
else fails the deploy with *"should NOT have additional property"*. The reasoning
lives here in the README instead.

**A CLI `vercel deploy --prod` is a one-shot upload — it does not watch GitHub.**
Pushing to `main` deploys nothing until the repository is connected under
**Project → Settings → Git**. Connecting it is a dashboard action; no property in
`vercel.json` can do it.

**Firebase Hosting** — same origin as the database, if you prefer that.
```
firebase init hosting     # public directory: .   (this folder)
firebase deploy
```

**GitHub Pages** — only for a public repo, or a private one on a paid plan;
Pages is not available for private repos on GitHub Free. There is no workflow in
this repo (it would fail on every push while the repo is private). To use Pages,
make the repo public and add `.github/workflows/pages.yml` running
`actions/configure-pages` → `upload-pages-artifact` (path `.`) →
`deploy-pages`, with `pages: write` and `id-token: write` permissions, plus an
empty `.nojekyll` at the root.

Redeploying? Bump `CACHE` in `sw.js` and `BUILD` in the template — `BUILD` is
printed in Settings, so you can tell at a glance whether the thing in your hand
is the thing you deployed.

### Why the worker is network-first for the page

The app **is** `index.html` and its name never changes, so a cache-first rule
for it is a trap: the page is served from cache forever, and the only thing
that can break the loop is a new service worker — which the stale page has no
reason to go looking for. That is how a device ends up pinned to a build from
weeks ago with no way to refresh out of it, which is exactly what happened.

So the document is **network-first**, with the cache as the offline fallback;
icons and the manifest stay cache-first with a background refresh, since they
are what make an offline open fast. The page also watches for a new worker,
sends it `SKIP_WAITING` rather than waiting for every tab to close, and
reloads once on `controllerchange`. Settings carries a **Refresh** button that
unregisters every worker, deletes every cache and reloads — the escape hatch
for a device already stuck.

Measured: from the old cache-first worker, an ordinary reload swaps the worker
and the next one serves the new page — two reloads, no devtools. On the
network-first worker a single reload is enough.

### Firebase authorized domains

Every domain the app is served from must be listed under **Firebase console →
Authentication → Settings → Authorized domains**, or `signInWithPopup` rejects
with `auth/unauthorized-domain`. Since the whole app sits behind the sign-in
gate, an unlisted domain means a deployment that loads and then does nothing.

**Add the production hostname of every deployment you create.** A new Vercel
project means a new hostname, and the old entry does not cover it — the app will
load and the sign-in button will simply fail. Vercel also mints a unique preview
URL per deployment; those are not covered by the production entry either.

### The firebase namespace is not stable

`firebase-app-compat` can be evaluated **twice** in this bundle — the loader
re-creates and re-runs every script tag after it swaps the document, and the
compat build announces it ("Firebase is already defined in the global scope").
The second evaluation replaces `window.firebase` with a *bare* namespace: no
`auth`, no `database` (those components registered against the previous one),
and an empty app list. Measured, after it happens `window.firebase.database` is
not even a function, and anything going through the global throws
**"No Firebase App '[DEFAULT]' has been created"**.

Re-initialising does not fix that, because the components are gone. So the first
complete namespace is pinned on `window.__fb`, and **every** use site goes
through `window.__firebaseApp()` — never `window.firebase` directly. If you add
a Firebase call, use the helper, or it will work until the day the double
evaluation happens and then fail in a way that looks like a config problem.

## Database rules

The client holds the Firebase config, as every Firebase web app does — the API
key is an identifier, not a secret. What actually guards the data is the
Realtime Database ruleset, which must stay deny-by-default with per-user grants:

```json
{
  "rules": {
    ".read": false,
    ".write": false,
    "users": {
      "$uid": {
        ".read":  "auth != null && auth.uid === $uid",
        ".write": "auth != null && auth.uid === $uid"
      }
    }
  }
}
```

The root denial is the floor and the `$uid` grants open exactly one subtree per
signed-in user; RTDB rules cascade permissively, so a deeper `true` overrides the
root `false` for that path and nothing else. `users` itself stays unreadable, so
no one can enumerate accounts.

## Working on it

`index.html` is **not hand-editable** — it is a self-contained bundle with
base64 islands. Unpack it, edit the template, pack it back:

```bash
python3 tools/bundle.py unpack     # -> build/template.html   (edit this)
python3 tools/bundle.py pack       # -> writes index.html
python3 tools/bundle.py assets     # manifest contents by size
python3 tools/preview.py           # -> build/preview.html, sign-in stubbed
```

`pack` round-trips byte-identically, so unpack/pack with no edits is a no-op.
`build/` is gitignored. See `HANDOFF.md` for current state and the traps this
codebase has already produced.

## Files

| File | What it is |
| --- | --- |
| `index.html` | The whole app — markup, logic, styles and fonts inlined |
| `manifest.webmanifest` | Makes it installable; name, icons, standalone display |
| `sw.js` | Service worker — caches the shell so it opens offline |
| `icon-192.png` / `icon-512.png` | App icons (the ClimbUp bamboo mark) |
| `vercel.json` | Cache and security headers for the Vercel deploy |
| `tools/bundle.py` | Unpack/pack the islands inside `index.html` |
| `tools/preview.py` | Build a sign-in-stubbed copy for testing |
| `HANDOFF.md` | Current state, outstanding actions, known traps |

## Date format

Every displayed date is **DD/MM/YYYY**, and every one of them goes through
`prettyDate` — that function is the only place to change it. It used to render
"26 Jul", with the year appearing only when it was not the current one: compact,
but two formats to read and ambiguous the moment a year rolls over.

The one thing `prettyDate` does **not** control is `<input type="date">`.
Browsers render those in the device's own locale and no CSS or script can
override it. A phone set to India or the UK already shows DD/MM/YYYY there; the
only way to force it everywhere would be to replace the native pickers with
text fields, which costs the mobile date wheel and is not worth it.

## Dates

`day` used to be a counter and there was no calendar, which made every dated
thing impossible. Everything is real dates now, local-time and keyed
`YYYY-MM-DD`. **Never use `Date.toISOString()`** for a day key — it converts to
UTC and lands on the wrong day for anyone not on Greenwich; `iso()` formats from
the local parts instead. Weeks are Monday-based to match the day strip.

At midnight — and on load, and after a cloud read, since the stored `lastRoll`
may be days old — `rollForward()` runs: every past day still holding work is
written into `history`, unfinished dated tasks move to today and are marked
`carried`, and appointments that have passed are dropped rather than dragged
along. **Routines are deliberately not carried.** A routine is a rhythm, not a
debt; yesterday's missed gym session is not owed today.

## The model

One task type at three zooms, not three separate things:

```
month task  ──breaks into──▶  week task  ──breaks into──▶  day task
                                                            └─ lands in a session
```

Every task carries a `scope` (`month` | `week` | `day`) and a `parent`. A day
task additionally has a `block` — which session of the day it sits in. So
"monthly targets broken into weekly, broken into daily" and "weekly and monthly
tasks I can organise" are the same list at a different zoom, which is why one
drag implementation orders all three and there is no second hierarchy to keep in
sync. Deleting a parent takes its whole subtree with it.

Goals sit alongside, not above: a goal is a name and a deadline, and any task at
any scope can be tagged to one. Progress is just the share of its tagged tasks
that are done.

A month and a week also carry a **target date**, picked from a real calendar
control. Saving one does not drop you back on a list — it opens the next level
down immediately, because a month is not finished when it is written down, it is
finished when it has been split. *Save and add another* keeps the sheet on the
same parent and steps the suggested date on a week (or a day) at a time, so a
whole month of weeks, or a week of days, goes in without reopening anything.
Week slots start at the end of the current week unless that has already arrived
— offering "due today" as the first weekly slot of a month-long plan is worse
than useless.

Day tasks carry a **description** as well as a name: the title is what it is, the
description is what to actually do.

## Routines

Kept apart from tasks on purpose. A routine repeats by weekday, is ticked per
date rather than once, never carries over, and is stored with a `done` map keyed
by date. They appear inside the Today sessions alongside tasks and count against
that session's capacity, because an hour of badminton occupies the evening
whether or not it is "work".

## Screens

- **Dashboard** — the home page. A real month calendar marking targets falling
  due (magenta), days with work on them (blue) and days finished clean (ring);
  what is coming up in the next fortnight; progress at all three zooms — today,
  this week, this month — each over its own real window; then what to improve,
  where the day goes session by session, the week bars, streak and freezes,
  weakest recall and slip reasons. Every line of advice is derived from data you
  actually entered; with an empty account it says so instead of inventing
  numbers.
- **Daily routine** — a **section of Settings**, not a screen. It describes
  your week rather than your day: name, description, session, minutes and which
  weekdays. Today only points at it — *Add a daily routine* while none is set,
  a quieter *Edit daily routine* once one is.
- **Today** — that day's tasks only, grouped into Morning / Busy Hours / Evening,
  **press and hold to drag into the order you want to do them**. Capacity bar
  per session, fixed appointments, backlog, review-the-day.
- **Plan** — Month and Week tabs. Same drag-to-order, plus *Break into weekly* /
  *Break into daily*, and each parent shows its children inline.
- **Revise** — **subjects** (Computer networks, Structural analysis), each
  holding image cards under a **formula or heading**.
  *Revise all* walks a whole group in one pass rather than interrupting one card
  at a time. Intervals stretch 1 → 3 → 7 → 21 → 45 days.
- **Settings** — your available hours per session (capacity is the span between
  them), office days, notifications, recall frequency, theme, erase everything.

## Reaching a particular date

Three ways in, in increasing reach:

1. **Today's day strip** — three days back, eleven forward. For "what's on
   tomorrow".
2. **The dashboard calendar** — every cell is a button carrying the **number of
   tasks** on that day, and tapping one opens Today on that date. Routines are
   **not** counted: they repeat by weekday and are a rhythm, not that day's work.
3. **The calendar's ‹ › arrows** walk months, so nothing is out of reach. The
   grid used to be pinned to the current month, which made any date outside it
   unreachable entirely. `monthOffset` browses; `pMonth` still measures the
   real month, so the progress figures do not follow the browsing. Leaving the
   dashboard resets it — coming back to find yourself in March would be a bug.

`openDay` is the whole mechanism: Today is a window on one date and `dayOffset`
is how far it has slid, so opening an arbitrary day is just `daysBetween`.

## Splitting evenly, at both levels

A month splits into **Part 1..4** (weeks); each of those splits again into
**Part 1.1, 1.2 …** (days); a week splits straight into Part 1..N. The number
carries the lineage, so a day task names its place in the whole plan without
the tree being open — `partNameFor` reads the parent's own number and extends
it, and anything not already a part starts at 1.

Split asks one question and nothing else. Dates are spread across the parent's
window, the parent's minutes are divided between the pieces, and no per-child
sheet appears. It is offered from the **Split** control on any month or week
row — including a nested Part — and disappears once a row has children, since
splitting twice would append a second overlapping set.

Rows carry their whole ancestry, not just their parent: a Today row reads
`Finish structures · Part 1` above `Part 1.2`. The walk is capped at eight
levels so a cycle in stored data cannot hang the render.

## Where tasks are added, and what Today is

Every task with a target above it is added on **Plan**, at whichever of the
three zooms is showing — the floating `+` is rendered only on that screen.

Today carries a second, smaller `+` beside its heading for the other case: you
have tapped a date on the calendar and want something on **that** day. It opens
the sheet already dated to the day you are looking at, so the date is never
picked twice, and it is the only thing Today creates. Today is a *view*: it shows one date's
work and lets you tick, focus, reorder and review it, but never creates it. A
task that appears on Today with no target above it is exactly the orphan this
app exists to prevent.

Today's window is `dayOffset`, and it is view state — not persisted, reset on
leaving the screen. `viewDate` follows it; `today` does not, because the
dashboard's rings and block stats must not move when you glance at tomorrow.
Undated legacy rows count as today's, never as whatever day you shifted to, and
*Review the day* is hidden anywhere but today.

Carrying over is `rollForward`, which runs at midnight, on load, and after a
cloud read — the stored `lastRoll` can be days old. Every unfinished dated task
moves to today marked `carried`; finished ones and passed appointments stay put
for the record. Today counts what came over and says so above the sessions.

## Notifications will not fire from `new Notification()`

Android Chrome forbids the constructor outright — *"Illegal constructor. Use
ServiceWorkerRegistration.showNotification instead"* — so the permission could
be granted, the switch on, and every alert still fail with nothing in the UI
to explain it. `notify()` goes through `navigator.serviceWorker.ready` and
`showNotification`, keeps the constructor as a desktop fallback, and returns a
promise so the test button can report what actually happened.

## The back button, and leaving

Screens are state, not URLs, so a browser back press would otherwise walk
straight out of the app. `setupBack` keeps **one sentinel history entry** in
front of the entry the app loaded on; back pops it, the handler pushes it
straight back, and the press is spent unwinding the UI instead — deepest
overlay first (cropper, recall, review, then any open sheet), then any screen
back to the **dashboard**. Only from the dashboard does it ask *Leave
ClimbUp?*, and a second back press there is read as *stay*.

The sentinel is laid down on sign-in, not on mount. Laid down earlier it
swallows the first back press on the sign-in screen, where back should just be
back — and the gate is `z-index:50`, so a dialog raised behind it would look
like a dead button. For the same reason the `beforeunload` warning, which is
what covers closing the tab outright rather than only going back, is armed on
sign-in and disarmed on the way out so *Leave* does not prompt twice.

## The install banner

It rides in at the top for eight seconds on the way in, then gets out of the
way. `offerInstall` is called when auth resolves to signed-in, **not** from
`componentDidMount`: mounting happens while the sign-in gate still covers the
app, so a banner started there spent its whole life behind the gate and was
gone by the time anyone got in. Dismissing it with the × is a **snooze**, not a burial: it sets
`sp.installSnooze` a week ahead and the banner is back after that. The old
`sp.installDismissed` flag suppressed it permanently, so a single stray tap
meant it never appeared again — that key is now deleted on sight.

## Sessions and days

The three sessions are `morning` / `noon` / `evening` as **keys**, labelled
Morning / **Busy Hours** / Evening in `BLOCKS`. Keys are what stored tasks and
hours are filed under, so a label can be reworded without touching anyone's
data — reword the label, never the key.

Office-day chips are built from `DAYS`, **not** `Object.keys(state.office)`.
Firebase hands an object's keys back in lexicographic order, so after one cloud
round trip that rendered the week as Fri Mon Sat Sun Thu Tue Wed. They carry
two-letter labels for the same reason: a row of M T W T F S S is two Ts and two
Ss you have to count positions to tell apart.

## Installing, and why a button cannot do it

No script can put an app on a home screen. Chrome hands over a
`beforeinstallprompt` event, which is captured and replayed when **Install** is
tapped; without it — Safari always, Chrome until the page qualifies — the
button opens a short **instructions sheet** keyed to the browser instead.

Naming the right menu item is the whole point of that sheet. Chrome's *Add to
Home screen* **shortcut** and an *Add to Home Screen* done from a non-Safari
browser on iPhone both drop a **bookmark that reopens in a browser tab** — the
exact thing installing is meant to avoid. The sheet says *Install app* on
Android, and sends iPhone users to Safari first.

The manifest carries `"display": "standalone"`, a stable `"id"`, and
`start_url` `"./"` so the installed icon opens the app full screen rather than
in a tab. Install also requires **HTTPS** — over plain HTTP no browser offers
it at all.

## Recall frequency

Six chips (5m → 4h) for the common intervals, plus a free minutes field taking
anything from **5 minutes to 12 hours**, a per-day cap, and a window recalls
are allowed in at all. The window may wrap past midnight — `21:00 → 07:00` is
read as the two ends of the day. Outside it the timer keeps ticking and simply
does not pop, which is one more entry in the `blocked` list in `schedule`
alongside an open overlay, a running timer, the daily cap and a fixed
appointment.

## Ordering, and why priority no longer sorts

`order` is the only thing that ranks tasks within a list, and drag is the only
thing that writes it. Priority still picks the badge a row wears (*Do first*,
*Must do*, *Skip if short*) but it does **not** re-sort — an automatic rank that
silently overrode a drag would make the gesture feel broken. Appointments stay
pinned first in clock order and finished tasks sink to the bottom regardless,
which is why neither is draggable.

The drag is delegated from the document and keyed on `data-list` / `data-id`, so
it survives re-renders without per-row refs, and it never calls `setState` until
the finger lifts — a render mid-gesture would rebuild the rows and strip the
transforms it is driving. `_dragging` holds the clock and recall timers still
while it runs.

## Images

Attaching a formula opens a cropper: pan and pinch under a fixed square frame,
and only the framed region is drawn to a canvas on save, so what is stored is
the crop you chose rather than the whole photo. Two things there are easy to
get wrong and are deliberate:

1. The `<img>` is `pointer-events:none`. Dragging an image starts Chrome's
   native image drag, which fires `pointercancel` and kills the gesture after
   two moves.
2. The gesture handlers are on the document, not the frame. Bound to the frame
   they are lost after one move — every move sets state, and the re-render can
   hand back a different DOM node.

**A data URL cannot go through an inline style string.** It carries a
semicolon — `data:image/jpeg;base64,…` — and the runtime splits a `style`
attribute on `;` before React sees it, so `background-image:url(data:image/jpeg
;base64,…)` arrived truncated at `data:image/jpeg` and resolved to nothing.
Every card image was cropped, stored, synced to the account **and never once
painted**. Card images are `<img>` elements whose `src` is assigned in
`syncCardImages` from `componentDidUpdate`, out of the style string entirely —
the same reason the cropper assigns its own `src` imperatively.

It is worth saying how this survived: the earlier fix verified state, bindings
and the account round trip, all of which were correct. Nothing checked the
painted result. `naturalWidth > 0` on the rendered `<img>` is the only
assertion that would have caught it.

Images are keyed by card id and stored twice: in `localStorage` under
`sp.cardImages`, for an instant first paint, and in Realtime Database under
`users/<uid>/cardImages/<cardId>`. They are still **stripped from the
`PERSIST_KEYS` payload** before every save — megabytes of base64 have no
business in a debounced whole-state write — but `storeImage` writes the one
image that changed to its own key, so an image survives a cleared cache and
follows the account to another device.

Because the images sit in a sibling of the synced keys, `saveCloud` uses
`update()` rather than `set()`. `set()` replaces the entire user node, which
deleted `cardImages` on the very next save and made an added image disappear
the next time the app was opened. On sign-in `loadCloudImages` merges the
account copy over the device cache and lifts anything device-only up into the
account, which migrates images added before they were synced.

## The bottom nav

The ordinary bottom bar every phone app has: a 22px stroke icon over an 11px
label, with **colour alone** saying which tab you are on — accent for the
current one, 55% text for the rest. A hairline top border because content
scrolls under it.

Borders around each tab and filled pills behind the labels were both tried and
both read as clutter. A tab bar is chrome; chrome should be quiet.

Icons are single `d` strings in `NAV_ICONS` so the whole set rides in one
template binding, drawn `fill:none, stroke:currentColor` — nothing but colour
changes between states. The spacer that clears the add button is only present
on Plan, since that is the only screen the add button is on; a permanent gap
with nothing in it is the sort of thing you notice and cannot explain.

## The nav's height, and the phone's own bar

The nav box was **84px tall with its buttons pinned to `flex-start`**, so
roughly 26px of it was dead space sitting directly above the phone's
home/back/recents bar — read as a gap, because it was one. It is **46px** with
the items centred — label to screen edge went from ~50px to 16px — and every offset coupled to it moved with it: the FAB, the
timer bar, the toasts and `.scr`'s bottom padding. Change one of those and you
must change all five, or something ends up floating.

`env(safe-area-inset-bottom)` is added on top of that height on phones, never
baked into it — the inset is the hardware's home indicator, not padding of
ours.

## Layout — phone vs desktop

The app renders **edge to edge on a phone** and inside a drawn iPhone frame on a
wide screen. Both come out of the same markup; the switch is one media query in
the `<helmet>` style block:

```
@media (max-width: 560px), (display-mode: standalone) { ... }
```

Under it the shell drops its padding, `.app` goes `100dvh` with no radius or
shadow, and `.device-chrome` — the drawn notch, clock, "5G" and battery — is
hidden, because on a real phone the device already has those. Above it, the
390×844 frame stays: it is a **presentation device** for showing the design on a
desktop, not part of the app.

Anything pinned to the bottom (`.bottom-nav`, `.fab-add`, `.timer-bar`,
`.toast`, `.review-sheet`) offsets itself by `env(safe-area-inset-bottom)`, and
`.scr` clears the notch with `env(safe-area-inset-top)`, so nothing lands under
the home indicator or the camera cutout. `viewport-fit=cover` on the viewport
meta is what makes those insets non-zero — do not drop it.

Touch targets are held at 44px on phones. Controls whose drawn size is smaller
(the 22px done-toggle, the 12px ghost buttons) keep their size and grow only the
area that answers a finger, via the transparent `.tap::after` overlay — changing
the real boxes would reflow rows tuned to the type scale. `.input` is forced to
16px there too, because iOS Safari zooms the page in on focus for anything
smaller and never zooms back out.

## Type — and why it changed

The app was **Source Serif 4 for everything**. A serif at 12–15px on a phone
reads bookish rather than professional, and every button, tag, numeral and nav
label was wearing it. **Source Sans 3** (variable, 200–900, one file per subset)
now carries all of that; the serif is kept for `h1`/`h2` display headings, where
it still earns its keep and gives the app a voice.

The display rule is declared **after** the reset's own `h1..h6` block. That
block sets `font-family` at the same specificity, so declared before it the
serif silently lost on source order and every heading came out sans.

## Old type notes

Source Serif 4, and it really is loaded now. The `@font-face` block used to sit
inside `<style media="print">` with nothing to promote it back to screen — that
technique needs `<link rel=stylesheet media=print onload="this.media='all'">`,
and an inline `<style media=print>` simply never applies. The app had been
rendering in the Georgia fallback with every heading weight faked by the
browser's synthetic bold. The faces are inline base64 in the same document, so
there was never a network fetch to keep off the critical path; the guard is gone.

The roman is a **variable** face with a 200–900 weight axis, previously served
twice pinned to static 400 and 600. The `@font-face` now declares
`font-weight: 200 900`, so real 700/800 costs no extra bytes. Headings are 700,
display figures 800 with tabular lining numerals, and display sizes are fluid
(`clamp()`) so a 320px phone and a 430px phone each get a headline in proportion
to its column. Tracking tightens as size grows.

Only **latin** and **latin-ext** subsets ship. Cyrillic, Greek and Vietnamese
were dropped (161 KB) and fall back to Georgia, which covers them. Restore those
`@font-face` blocks and their assets if the app ever needs those scripts.

## Text size

Settings → Appearance carries five steps, S to XXL. Every size in this app is
a hard px value in an inline style — there is no root font-size to turn — so
the control sets `zoom` on `.scr`, which scales the scroll area whole: text,
spacing and cards together, which is what "bigger text" means on a phone. The
fixed chrome is deliberately left out of it: the nav, toasts and sheets stay at
their designed size so the tap targets do not move under your thumb.

Five steps rather than a slider. A slider invites hunting for a value that does
not exist; each of these is legible and the jump between them is visible.

## An undefined token is not an error — it is just gone

The spacing scale ran 1, 2, 3, 4, **6**, 8. Nine call sites had been written
against `--space-5`, and every one of them resolved to nothing: `padding:
var(--space-5)` computed to `0px`, silently. That is how a dialog ends up with
its text flush against a rounded corner and looking cropped. CSS does not warn,
the style attribute still reads correctly in devtools, and only
`getComputedStyle` tells the truth — which is what caught it.

`--space-5: 25px` now exists. When adding a token-based style, check the token
is real: a quick sweep is
`getComputedStyle(document.querySelector('.app')).getPropertyValue('--name')`.

## Colour and shape

The system was a hard-edged broadsheet: radii of 1/2/4px, one accent, no fills.
It is card-based now, on a lightly tinted ground.

- **Radii** 8/14/22px plus `--radius-pill`. Cards need room to read as cards
  rather than boxes ruled on a page.
- **`--card-*` / `--ink-*`** — six pale card fills, each paired with an ink of
  the same hue driven dark, so a heading on a card never falls back to plain
  black. Both sets are redefined for the dark theme; the pale fills would blow
  out otherwise.
- **`.card-panel`** — the white panel the layout is built from.
- **`BLOCK_SKIN`** gives each session its own colour, so a glance at Today says
  which part of the day you are looking at before you have read a word.
- The Today **day strip** runs three days back and eleven forward, dot-marked
  where there is work, and is the same `dayOffset` the arrows drove.

Done on Dashboard and Today. Plan, Revise and Settings still wear the older
flat treatment inside the new tokens — they inherit the radii, type and ground,
but not the cards.

## Motion

`.scr` scrolls smoothly, and section blocks tagged `.reveal` fade up as they
enter the viewport. The reveal runs on a CSS **scroll timeline**
(`animation-timeline: view()`), wrapped in `@supports` — where the engine lacks
it the animation never applies and content is simply visible, so it decorates
and never gates. Everything stands down under `prefers-reduced-motion: reduce`.

## Weight

`index.html` is one blocking document, so every byte is on the critical path.

| | before | after |
| --- | --- | --- |
| `index.html` | 2.20 MB | 0.58 MB |
| gzipped | 1642 KB | 386 KB |
| DOMContentLoaded, Fast 3G | 11.8 s | 3.2 s |

Most of it was the logo: a 1024×1024, 1.15 MB PNG shown at 96px, carrying an
opaque white background that read as a white tile on the paper ground and a
bright box in dark mode. It is now 256px with the backdrop knocked out by an
edge flood-fill — flood-fill, not a white key, because the book, the checklist
and the star highlights are white too and have to survive.

Assets are referenced from **two** islands: `__bundler/template` and
`__bundler/ext_resources`. React and ReactDOM appear only in the latter — prune
by the template alone and the app boots blank trying to reach unpkg.com.

## Schema migrations — never bump without one

`loadCloud` used to discard anything not on the current `SCHEMA` and drop the
user into `freshState()`. That is a **silent wipe of a real account** every
time the state shape changes, and it is the single most dangerous thing this
codebase has done. There is a `MIGRATIONS` ladder now: one function per
version, run in order, so an account three versions behind arrives intact.
**Add a step whenever you bump `SCHEMA`.**

What cannot be migrated — a version from the future, or a blob with no version
at all — is no longer thrown away either. It is held on `this._orphan`, the
dashboard says so in a card that cannot be missed, and the user can download
it as JSON before anything writes over the top.

One trap, found by measuring: `const data = snap.val()` cannot be reassigned,
so `data = migrate(data)` threw a `TypeError` that the promise's own `.catch`
swallowed — the account loaded as empty with no error anywhere. It is `let`.

## The streak measures days, not paperwork

It used to advance only through *Review the day*. Finish a full week and
forget to tap it once and the counter read zero — a streak that punishes you
for not filing paperwork measures nothing. `rollForward` settles every day it
closes on that day's own evidence: work finished holds it, a day with nothing
planned is a rest day and holds it too, a day with work left untouched breaks
it. `streakSettled` marks the last day ruled on, so a day Review already
judged is not counted a second time.

## Known limits — read before building on this

1. **State syncs to Firebase, and only while signed in.** Google sign-in gates the app; the
   keys in `PERSIST_KEYS` are debounced to Realtime Database under `users/<uid>` and read back
   on load. Signed out there is no persistence at all.
   `SCHEMA` guards the shape: `loadCloud` **discards** anything stored under a different
   version rather than migrating it. Bump it when the state shape changes — that is also what
   cleared the old demo seed out of accounts that had already saved it. Note Firebase stores no
   empty arrays or objects at all (it deletes the key), so anything the user has legitimately
   emptied comes back missing and is refilled from `freshState()` on load.
   *(Note: `componentDidUpdate` is called by the DC runtime with `prevProps` only — there is no
   `prevState` argument. Comparing against one throws inside a runtime `try/catch`, which
   silently disables the save. Track previous values yourself; see the comment on that method.)*
2. **Notifications cannot fire when the browser is closed.** The page's timers only run while it
   is alive. An installed PWA can notify while backgrounded on Android; iOS is stricter. Real
   scheduled alarms need a server pushing to a native app or Web Push with a subscription —
   `sw.js` already handles `notificationclick`, so the client half is ready.
3. **There is no seed data.** A new account starts genuinely empty and every screen has an
   empty state. Nothing in the render path may assume a non-empty array — that was the whole
   class of crash when the demo data came out.
4. **Dates are simulated.** `day` is a counter and `examDays` is a constant; there is no real
   calendar. Wire to actual dates before trusting the pace maths.
5. **The exam pace figure** assumes goal progress is measured in hours. Adjust if you track
   topics or chapters instead.

## If you're picking this up in Claude Code

The prototype is the spec — behaviour, copy and visual language are all decided. What it needs:

- A persistence layer (tasks, goals, cards, day history, streak state) and accounts.
- Real dates: a scheduler that rolls unfinished work forward at local midnight instead of on a
  button, and computes pace from actual elapsed days.
- Web Push with a backend so reminders and recalls arrive when the app is closed.
- The auto-split that turns "600 hours before 11 Feb" into weekly and daily targets — the UI
  shows the result, the arithmetic is stubbed.

**Visual system:** Broadsheet — Source Serif 4 throughout, paper `#f3f2f2`, ink `#201e1d`,
cyan `#0088b0` for anything interactive, magenta `#d6006c` reserved for pressure (over capacity,
backlog, weak subjects, free days). No boxes or cards; hierarchy comes from the serif scale,
whitespace and rules. Radii are 1/2/4px. Small accent text uses the 700 ramp step, not base
accent — base is only 3.65:1 on paper. Keep it that way and it stays coherent.

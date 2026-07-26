# Handoff — where ClimbUp stands

Written at commit `043e323`. Read this first in a new session; the README has
the architecture, this has the state and the traps.

---

## 1. Blocked on you, not on code

**The live site is serving an old build.** Everything below is committed to
`main` and verified locally, but `climbup-planner.vercel.app` has not had a
deploy since the rebuild. Two actions, both dashboard-only — no agent can do
either:

1. **Deploy.** `git pull && vercel deploy --prod` from the repo folder.
   Then hard-refresh, or close every tab of the app and reopen: the service
   worker is cache-first and will otherwise hand back the stale copy.
   Cache is at `climbup-v7`.
2. **Connect the repo**, so this stops recurring — vercel.com → project →
   Settings → Git → Connect Git Repository → `navinkumarprcivil-ui/ClimbUp`,
   production branch `main`. A CLI `vercel deploy` is a one-shot upload; it
   does not watch GitHub. This is an OAuth handshake between the two accounts
   and needs a signed-in human.

**It has landed when:** the bottom nav reads `Dashboard · Today · Plan ·
Revise`, the dashboard opens on a month calendar with today ringed, and the
middle session is called **Noon** rather than Office.

**Expect the old data to vanish.** `SCHEMA` is 4; `loadCloud` discards anything
stored under a different version. What is in Firebase now is the old demo seed,
so nothing real is lost — but bump `SCHEMA` again any time the state shape
changes, and know that it wipes.

> The sandbox these sessions run in **cannot reach `vercel.app` or `github.io`**
> (network policy answers 403 to CONNECT). No agent can verify the live site for
> you. Verification here is always against a local server.

---

## 2. How to change the app

`index.html` is **not hand-editable** — it is a 0.65 MB self-contained bundle
with base64 islands. Use the committed tooling:

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

---

## 4. What exists now

**Model.** One task type at three zooms — `scope` is `month | week | day`, with
a `parent` link. A day task also has a `block` (Morning / Noon / Evening), a
`date`, and a `note`. Month and week tasks carry a `targetDate`. Goals sit
alongside and are just a name, a deadline and a tag on tasks. Routines are
separate: they repeat by weekday, are ticked per date, and never carry.

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

**Verified in-browser at 320/390/412px:** the guided chain end to end,
descriptions surviving into nested rows, drag reorder, routines appearing on
Today, carry-forward marking a stale task `carried`, crop-and-save, hour
editing, erase, calendar highlighting today. No page errors.

---

## 5. Known limits and likely next steps

- **Weekly/monthly progress is task-count based**, not effort-weighted. Fine
  now, will feel wrong once tasks vary a lot in size.
- **Streak and freezes** still only advance through "Review the day"; the
  automatic midnight rollover does not touch them. Worth unifying.
- **No editing of an existing task** — only add and delete. This is the most
  obvious gap for daily use.
- **Notifications cannot fire while the app is closed.** Real alarms need Web
  Push and a server; `sw.js` already handles `notificationclick`, so the client
  half is done.
- **Card images are device-local** (`localStorage`, stripped from the Firebase
  payload deliberately — megabytes of base64 have no business in a realtime
  sync). They do not follow you to another phone.
- **One open question for the owner:** daily targets filled in for a *future*
  week are filed on those future dates, so they do not appear on Today until
  that day arrives. That is the intended reading of "assigned on a daily basis"
  — confirm, or change it so they all land on today.

# ClimbUp — Task, Study, Steady growth

**Live:** https://climbup-planner.vercel.app

A daily task and study planner built around one idea: **you should be able to see yourself falling behind.**
Open it in the morning, see today split into Morning / Office / Evening, work down the ranked
list, review the day, and watch the backlog pile build if you don't.

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
instead of 0.58 MB. `sw.js` gets the same treatment, because a cached
service worker is one that never updates, and this one is cache-first — a stale
copy would keep serving an old build to installed clients indefinitely.

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

Redeploying? Bump `CACHE` in `sw.js` or clients keep serving the old build.

### Firebase authorized domains

Every domain the app is served from must be listed under **Firebase console →
Authentication → Settings → Authorized domains**, or `signInWithPopup` rejects
with `auth/unauthorized-domain`. Since the whole app sits behind the sign-in
gate, an unlisted domain means a deployment that loads and then does nothing.

Currently needed: `climbup-planner.vercel.app`. Vercel also mints a unique
preview URL per deployment — those are *not* covered by the production entry, so
sign-in will not work on a preview link unless you add that host too.

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

## Files

| File | What it is |
| --- | --- |
| `index.html` | The whole app — markup, logic, styles and fonts inlined |
| `manifest.webmanifest` | Makes it installable; name, icons, standalone display |
| `sw.js` | Service worker — caches the shell so it opens offline |
| `icon-192.png` / `icon-512.png` | App icons (the ClimbUp bamboo mark) |
| `vercel.json` | Cache and security headers for the Vercel deploy |

## What works

- **Today** — tasks grouped by time block, ranked inside each block. The top undone item is
  badged *Do first*, high-priority *Must do*, low *Skip if short*. Carried-over work floats up.
- **Capacity** — each block has a minute budget. Overshoot it and the app says so before you start.
- **Fixed appointments** — a task with a clock time anchors its block and never rolls over.
- **Backlog** — every carried item can go to today, batch onto the weekend, or be dropped.
  Shows what clearing it actually costs in evenings.
- **Pace** — hours needed per day against your real average, projected against the exam date.
- **Review the day** — tag what slipped and why, then choose tomorrow or the weekend.
  Reasons feed the Week screen.
- **Week** — completion, hours, streak, planned-vs-done bars, subject balance, slip reasons.
- **Streak + freeze** — two freeze days a month so one bad day doesn't erase the run.
- **Revision** — concept cards with your own formula images, spaced 1 → 3 → 7 → 21 → 45 days.
  An active-recall popup interrupts you on a set frequency: *recall it*, then reveal the image.
  Suppressed during appointments and focus sessions, capped daily.
- **Focus timer** — records actual time against your estimate.
- **Settings** — office days, block capacities, reminder time, notifications, dark theme.

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

## Type

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

## Known limits — read before building on this

1. **State syncs to Firebase, and only while signed in.** Google sign-in gates the app; the
   keys in `PERSIST_KEYS` are debounced to Realtime Database under `users/<uid>` and read back
   on load. Signed out there is no persistence at all, and the formula images are the one thing
   that never leaves the device — they stay in `localStorage` under `sp.cardImages`, so they do
   not follow you to another phone.
   *(Note: `componentDidUpdate` is called by the DC runtime with `prevProps` only — there is no
   `prevState` argument. Comparing against one throws inside a runtime `try/catch`, which
   silently disables the save. Track previous values yourself; see the comment on that method.)*
2. **Notifications cannot fire when the browser is closed.** The page's timers only run while it
   is alive. An installed PWA can notify while backgrounded on Android; iOS is stricter. Real
   scheduled alarms need a server pushing to a native app or Web Push with a subscription —
   `sw.js` already handles `notificationclick`, so the client half is ready.
3. **Seed data is hard-coded** in the component's constructor (`tasks`, `backlog`, `cards`,
   `week`, `subjects`, `goals`) — that is the shape a real data layer needs to produce.
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

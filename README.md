# ClimbUp — Task, Study, Steady growth

A daily task and study planner built around one idea: **you should be able to see yourself falling behind.**
Open it in the morning, see today split into Morning / Office / Evening, work down the ranked
list, review the day, and watch the backlog pile build if you don't.

Single self-contained page. No build step, no dependencies, no server.

## Deploy

Everything is static — drop this folder on any host.

**Vercel**
```
npm i -g vercel
vercel deploy --prod
```

**Firebase Hosting**
```
firebase init hosting     # public directory: .   (this folder)
firebase deploy
```

**GitHub Pages** — push this folder, then Settings → Pages → deploy from branch.

HTTPS is required for install-to-home-screen and notifications. All three hosts give you that.

## Files

| File | What it is |
| --- | --- |
| `index.html` | The whole app — markup, logic, styles and fonts inlined |
| `manifest.webmanifest` | Makes it installable; name, icons, standalone display |
| `sw.js` | Service worker — caches the shell so it opens offline |
| `icon-192.png` / `icon-512.png` | App icons (the ClimbUp bamboo mark) |

Redeploying? Bump `CACHE` in `sw.js` or clients keep serving the old build.

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

## Known limits — read before building on this

1. **State is in memory.** Everything resets on reload except the formula images, which go to
   `localStorage` under `sp.cardImages`. There is no persistence layer and no accounts.
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

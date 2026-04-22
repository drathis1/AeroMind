# AeroMind — Operations Frontend

Next.js 14 dashboard for the AeroMind multi-agent cargo operations platform.
Talks to the FastAPI backend (`/api/demo/*`) via polling — no websockets.

> Design intent: a **human-centered AI dashboard** for cargo ops managers. Every agent
> decision shows its reasoning, escalations are impossible to miss, and confidence is
> surfaced rather than hidden.

## Stack

- Next.js 14 (app router)
- TypeScript (strict)
- Tailwind CSS 3 — dark by default (slate-950)
- Lucide icons
- Hand-rolled UI primitives (Button / Card / Modal) styled in the shadcn/ui spirit

## Pages

| Route | Purpose |
|---|---|
| `/` | Redirects to `/dashboard` |
| `/dashboard` | System pill, 4 stats cards, workflows table — polls every 5s |
| `/orders/[id]` | Order summary, escalation card, agent timeline, shared state, governance |

## Run locally

### 1. Start the backend (in the project root)

```bash
# from the repo root
pip install -e .
uvicorn aeromind.api.main:app --reload --port 8000
```

The API will serve `/api/demo/orders` and seed three sample orders on startup.

### 2. Start the frontend

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000 — it redirects to the dashboard.

### Environment

`NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`) controls the backend URL.
Copy `.env.local.example` to `.env.local` and edit if you need a non-default value.

## How requests reach the backend

`next.config.js` rewrites every `/api/*` request from the browser to the FastAPI
backend. The frontend therefore calls *relative* URLs only, which sidesteps CORS
and lets you swap backends via env var.

## Design system

| Token | Value | Used for |
|---|---|---|
| Background | `slate-950` | App shell |
| Surface | `slate-900` | Cards, modals, table |
| Border | `slate-800` | Dividers, card edges |
| Primary | `sky-400` | Active / healthy |
| Warning | `amber-400` | **Human attention needed** (dominant) |
| Danger | `rose-500` | DG lock / sanctions / blocked |
| Success | `emerald-400` | Clean close |
| Muted | `slate-400` | Secondary text |

## Human-centered details

- **No jargon codes.** `DG_LOCK_BREACH` becomes *"Dangerous-goods cargo present — awaiting human approval."*
- **Escalations are the loudest element** on the detail page — full-width amber card, big call-to-action, automatic scroll placement.
- **Confidence chips** on each agent output — high / medium / low with a human-readable note (e.g. "reliability 95%").
- **"AI decided"** label on autonomous actions so it's never ambiguous whether a human or an agent made a call.
- **Loading states narrate.** "Fetching the latest agent decisions…" rather than a bare spinner.
- **Empty state teaches.** If there are no workflows, the UI explains what triggers one and offers a primary CTA.

## File layout

```
web/
├── app/
│   ├── dashboard/page.tsx      # main list view
│   ├── orders/[id]/page.tsx    # workflow detail
│   ├── layout.tsx
│   ├── page.tsx                # → /dashboard
│   └── globals.css
├── components/
│   ├── AgentTimeline.tsx       # plain-English agent decision trail
│   ├── SharedStatePanel.tsx    # human-readable orchestrator state
│   ├── EscalationCard.tsx      # dominant AWAITING_HUMAN card
│   ├── GovernanceBadges.tsx    # DG Lock / Blast Radius / etc.
│   ├── NewOrderModal.tsx       # trigger workflow form
│   ├── StatusBadge.tsx
│   ├── AgentPill.tsx
│   ├── ConfidenceChip.tsx
│   ├── StatsCard.tsx
│   ├── SystemStatusPill.tsx
│   ├── WorkflowControls.tsx
│   └── ui/{Button,Card,Modal}.tsx
├── lib/
│   ├── api.ts                  # typed fetchers
│   ├── types.ts                # mirror of demo/models.py
│   ├── hooks.ts                # usePolling
│   ├── format.ts               # status/agent/stage label helpers
│   └── utils.ts                # cn, timeAgo, formatTime
├── next.config.js              # /api/* → backend rewrite
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

## Scripts

```bash
npm run dev         # dev server on :3000
npm run build       # production build
npm run start       # serve the built app
npm run lint        # eslint
npm run typecheck   # tsc --noEmit
```

## Non-goals (by design)

- No auth
- No websockets — 5s polling is sufficient for ops-manager latency tolerance
- No charts / analytics pages
- No tabs inside the order page — one readable surface per workflow

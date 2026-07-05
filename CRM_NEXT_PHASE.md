# CRM Next Phase — Make the Product Work

## What's Done
- People unification (Person as canonical record with contact/investor linking)
- Dispatch/Project/Opportunity linking (resolved names in tables)
- Founder dashboard with venture-goal relationship ranking
- Active venture goal (set project as active, dashboard respects it)
- Warm path finder (backend + /warm-path page)
- Dispatch→intro path linking (auto-mark in_flight, show label)
- Action queue (backend + dashboard suggested actions)

## Phase 1 — Fix the Existing Pages

### 1.1 Pipeline deals — show `person_name`
- Backend already resolves person_name — frontend just doesn't display it
- Add person_name column to the pipeline table + person_id selector in the form

### 1.2 Relationship graph — respect active project goal
- Filter graph nodes by goal context
- Show only people/edges relevant to the active project goal

### 1.3 People page — add warm path and dispatch links per person
- Add a "Find warm path" button per person row
- Add a "Create dispatch" quick-action per person
- Show if person has active intro paths

### 1.4 People API — restore full field set for frontend
- PersonRecord schema on list_people endpoint uses `label`/`primary_role` instead of `name`/`role`
- Frontend PersonRecord expects `name`, `email`, `role`, `company`, `last_contact_at`, `next_follow_up_at`
- Align the backend schema and frontend types

## Phase 2 — Venture Workflow (Guided UX)

### 2.1 Dashboard — add "Next best action" card with link to warm paths
- From suggested_actions, link to warm path page with person pre-selected
- Add "Create dispatch" button on suggested action rows

### 2.2 Navigation — wire goal→warm paths→dispatch flow
- Add context-aware navigation between pages
- After setting active project, show "Find warm paths" prompt
- After creating dispatch from warm path, show dispatch in queue

### 2.3 Onboarding / seed data
- Auto-create a "Sample Raise" project on workspace creation
- Pre-populate 2-3 sample people with relationship edges
- First-visit modal or banner explaining the venture workflow

## Phase 3 — Polish & Hardening

### 3.1 Loading/empty/error states across all pages
### 3.2 Consistent use of SectionCard + EmptyState patterns
### 3.3 Form validation and user feedback (toast/snackbar)
### 3.4 Mobile-responsive layout
### 3.5 Session/error boundary hardening

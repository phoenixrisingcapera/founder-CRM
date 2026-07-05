# Frontend User Journey Map

Source scan: SvelteKit routes in `src/routes`, shared navigation in `src/lib/components/Sidebar.svelte`, `TopBar.svelte`, and marketing header/footer components.

Legend:

```text
[PAGE]        user can see this screen
{DECISION}    page redirects depending on state
(ACTION)      click, form submit, upload, or button
-->           navigation / redirect
--x           route is referenced but not built in this frontend tree
```

## 1. Whole Site Map

```mermaid
flowchart LR
  Visitor[Visitor lands on public site] --> Marketing[/Marketing pages/]
  Marketing --> Interest[Show Interest form]
  Marketing --> Auth[Sign in / Sign up]
  Marketing --> Pricing[Pricing]
  Marketing --> Contact[Contact]
  Marketing --> Legal[Privacy / Terms / Billing]

  Auth --> Session{Session exists?}
  Session -- no --> SignIn[/auth/sign-in/]
  Session -- yes --> App[/Authenticated app shell/]

  App --> Welcome{Deck count}
  Welcome -- 0 decks --> FirstWelcome[/welcome/]
  Welcome -- has decks --> WelcomeBack[/welcome_back/]

  FirstWelcome --> Upload[/decks/new/]
  WelcomeBack --> SmartDeck[/decks/:deckId/smart-deck/]
  App --> Dashboard[/dashboard/]
  App --> Decks[/decks/]
  App --> Templates[/templates/]
  App --> SmartDeckRoot[/smart-deck/]
  App --> SmartEditRoot[/smart-edit/]
  App --> Datasets[/datasets/]
  App --> ExportsRoot[/exports/]
  App --> Settings[/settings/]

  Upload --> BrandReview[Brand review modal]
  BrandReview --> SmartDeck
  Decks --> SmartDeck
  Dashboard --> SmartDeck

  SmartDeck --> SmartEdit[/decks/:deckId/smart-edit/]
  SmartDeck --> DueDiligence[/decks/:deckId/due-diligence/]
  SmartDeck --> Export[/decks/:deckId/export/]
  SmartDeck --> Batches[/decks/:deckId/batches/]

  SmartEdit --> Batches
  SmartEdit --> Export
  DueDiligence --> SmartEdit
  DueDiligence --> Export
  Batches --> BatchDetail[/decks/:deckId/batches/:batchId/]
  BatchDetail --> Compile[/decks/:deckId/batches/:batchId/compile/]
  Compile --> Compiled[/decks/:deckId/compiled/:compiledDeckId/]
  Compiled --> Export
```

## 2. Global Navigation

### Public marketing shell

User sees this on `/`, `/pricing`, `/vcs`, `/about`, `/contact`, `/billing`, `/privacy`, `/terms`.

```mermaid
flowchart TD
  PublicHeader[Marketing header] --> Home[/ Product: /]
  PublicHeader --> VCs[/ For VCs: /vcs/]
  PublicHeader --> Pricing[/ Pricing: /pricing/]
  PublicHeader --> About[/ About: /about/]
  PublicHeader --> Contact[/ Contact: /contact/]
  PublicHeader --> SignIn[/ Sign in: /auth/sign-in/]
  PublicHeader --> Interest[/ Show interest: /#show-interest/]

  PublicFooter[Marketing footer] --> FooterPricing[/pricing/]
  PublicFooter --> FooterBilling[/billing/]
  PublicFooter --> FooterVCs[/vcs/]
  PublicFooter --> FooterAbout[/about/]
  PublicFooter --> FooterContact[/contact/]
  PublicFooter --> FooterPrivacy[/privacy/]
  PublicFooter --> FooterTerms[/terms/]
  PublicFooter --> FooterSignIn[/auth/sign-in/]
  PublicFooter --> FooterSignUp[/auth/sign-up/]
```

Built in:

- Header: `src/lib/components/marketing/MarketingHeader.svelte`
- Footer: `src/lib/components/marketing/MarketingFooter.svelte`
- Utility bar: `src/lib/components/marketing/MarketingUtilitiesBar.svelte`
- Shell is hidden on `/auth/*` and `/sign_in_landing`.

### Authenticated app shell

Every `(app)` page is guarded. If there is no session, the user is redirected to `/auth/sign-in?next=<current-page>`.

```mermaid
flowchart TD
  AnyAppRoute[Any app route] --> Guard{Logged in?}
  Guard -- no --> Login[/auth/sign-in?next=.../]
  Guard -- yes --> AppShell[App shell]

  AppShell --> Sidebar[Left sidebar]
  AppShell --> TopBar[Top bar]

  Sidebar --> NewDeck[/decks/new/]
  Sidebar --> Welcome[/welcome/]
  Sidebar --> Dashboard[/dashboard/]
  Sidebar --> Decks[/decks/]
  Sidebar --> Templates[/templates/]
  Sidebar --> SmartDeckRoot[/smart-deck/]
  Sidebar --> SmartEditRoot[/smart-edit/]
  Sidebar --> Datasets[/datasets/]
  Sidebar --> ExportsRoot[/exports/]
  Sidebar --> DueDiligenceCurrent[/decks/:deckId/due-diligence or /decks/]
  Sidebar --> BillingApp[/app/billing/]
  Sidebar --> Settings[/settings/]

  TopBar --> MarketingBilling[/billing/]
  TopBar --> ThemeToggle[Theme toggle]
  TopBar --> Search[Search panel only, no redirect]
```

Built in:

- Auth guard: `src/routes/(app)/+layout.server.ts`
- App shell: `src/lib/components/AppShell.svelte`
- Sidebar: `src/lib/components/Sidebar.svelte`
- Top bar: `src/lib/components/TopBar.svelte`

## 3. Public Journey Pages

### `/` Home

```mermaid
flowchart TD
  Home[/Home page/] --> Hero[Hero: product promise]
  Home --> HowItWorks[How it works]
  Home --> UseCases[Use case tabs]
  Home --> Comparison[Comparison]
  Home --> ForVCs[For VCs preview]
  Home --> ProductPreview[Product preview]
  Home --> InterestForm[Show Interest form]
  Home --> CTA[Final CTA]

  Hero --> InterestAnchor[/#show-interest/]
  Hero --> SignIn[/auth/sign-in/]
  UseCases --> InterestAnchor
  ForVCs --> VCs[/vcs/]
  CTA --> InterestAnchor
  CTA --> SignIn
  InterestForm --> PublicInterestAPI[/api/public/interest/]
```

User sees:

| Moment | Options available |
| --- | --- |
| Product landing | `Talk to Deck AIStack` -> `/#show-interest`; `Sign in` -> `/auth/sign-in` |
| Use case strip | switch tabs in-place; `Talk to Deck AIStack` -> `/#show-interest` |
| Show Interest form | submit lead to `/api/public/interest`; stays on page with success/error |
| Footer/header | pricing, billing, VC page, about, contact, privacy, terms, auth |

### `/pricing`

```mermaid
flowchart TD
  Pricing[/Pricing/] --> Contact[/contact/]
  Pricing --> Interest[/#show-interest/]
```

User sees premium transformation pricing. Main redirects:

- `Contact us` -> `/contact`
- `Book a consultation` / `Discuss your deck` -> `/#show-interest`

### `/vcs`, `/about`, `/contact`, `/billing`, `/privacy`, `/terms`

```mermaid
flowchart LR
  PublicInfo[Public info pages] --> HeaderLinks[Marketing header links]
  PublicInfo --> FooterLinks[Marketing footer links]
  Contact --> InterestHint[Points user back to Show Interest on home]
```

These pages mainly use shared header/footer redirects. `/contact` tells the user the fastest path is the home page Show Interest form.

## 4. Auth Journey

### `/auth/sign-in`

```mermaid
flowchart TD
  SignIn[/auth/sign-in/] --> Form[Email + password form]
  Form --> LoginAPI[/api/auth/sign-in/]
  LoginAPI --> NextUrl{response.nextUrl}
  NextUrl --> AppTarget[Go to requested app page or default]
```

User sees:

- Email field
- Password field
- Submit button
- Alternate link is provided by the public auth shell if configured

### `/auth/sign-up`

```mermaid
flowchart TD
  SignUp[/auth/sign-up/] --> Form[Name, email, password, company, role, terms]
  Form --> SignUpAPI[/api/auth/sign-up/]
  SignUpAPI --> NextUrl{response.nextUrl}
  NextUrl --> AppTarget[Go to next page]
```

### `/auth/callback` and `/auth/success`

```mermaid
flowchart TD
  Callback[/auth/callback/] --> CallbackAPI[/api/auth/callback/]
  CallbackAPI --> ResponseNext[response.nextUrl]
  Callback --> SignInFallback[/auth/sign-in/]

  Success[/auth/success/] --> Validate[/api/auth/session/validate/]
  Validate --> NextUrl[next query param or /welcome]
  Success --> Welcome[/welcome/]
  Success --> SignIn[/auth/sign-in/]
```

### Legacy auth aliases

| Route user enters | Redirect |
| --- | --- |
| `/sign-in` | `/auth/sign-in` |
| `/sign-up` | `/auth/sign-up` |

## 5. First-Time App Journey

### `/welcome`

State rule:

```mermaid
flowchart TD
  WelcomeLoad[/welcome load/] --> DeckCount{workspace.deckCount > 0?}
  DeckCount -- yes --> WelcomeBack[/welcome_back/]
  DeckCount -- no --> WelcomePage[/welcome page/]
```

User sees:

| Moment | Options available |
| --- | --- |
| Welcome hero | `Design your first deck` -> `/decks/new` |
| Setup tiles | Microsoft setup, LinkedIn setup, brand defaults |
| Action cards | `Upload a deck` -> `/decks/new`; `Guided deck intake`; `Load your API key` |

Important route gap:

```text
/settings/account/connected-accounts?provider=microsoft...  exists
/settings/account/connected-accounts?provider=linkedin...   exists
/settings/brand-defaults                                    referenced, not found
/decks/new?mode=guided                                      page exists as query state on /decks/new
```

### First-time dashboard empty state

When `/dashboard` has `uploadedDecks === 0`, user sees `FirstTimeDashboard`.

```mermaid
flowchart TD
  DashboardEmpty[/dashboard with 0 decks/] --> ProviderModal[Connect AI provider modal]
  DashboardEmpty --> UploadAnchor[#first-deck-upload]
  UploadAnchor --> UploadCard[Upload first deck card]
  UploadCard --> SmartDeck[/decks/:deckId/smart-deck/]
  DashboardEmpty --> Templates[/templates/]
```

## 6. Upload and Brand Journey

### `/decks/new`

This is the most important conversion path inside the app.

```mermaid
flowchart TD
  UploadPage[/decks/new/] --> Step1[1. Upload deck file]
  Step1 --> UploadAPI[/api/products/deck-aistack-codes/decks/upload/]
  UploadAPI --> Saved{Deck saved?}
  Saved -- no --> UploadError[Show upload error]
  Saved -- yes --> BrandModal[Open brand modal]

  BrandModal --> BrandInputs[Website, logo, brand guidelines]
  BrandInputs --> ExtractBrand[Extract brand]
  ExtractBrand --> BrandReady{Brand profile ready?}
  BrandReady -- no --> Waiting[Waiting / failed state]
  BrandReady -- yes --> ReviewBrand[Review brand]
  ReviewBrand --> SaveBrand[Save brand selection]
  ReviewBrand --> Continue[Continue]
  Continue --> SmartDeck[/decks/:deckId/smart-deck/]

  UploadPage --> ExistingDeck[Existing uploaded deck selected]
  ExistingDeck --> SmartDeck
```

User sees:

| Step | Visible options | Redirect |
| --- | --- | --- |
| Upload deck | choose `.pdf`, `.ppt`, `.pptx`; upload progress; error/success banner | none until saved |
| Load brand | company website input, logo upload, brand guidelines upload | none |
| Extract brand | `Extract brand` button | none |
| Review brand modal | edit/approve/save brand; continue | `/decks/:deckId/smart-deck` |
| Existing deck list | select a previously uploaded deck | `/decks/:deckId/smart-deck` |

## 7. Dashboard and Library

### `/dashboard`

```mermaid
flowchart TD
  Dashboard[/dashboard/] --> HasDecks{uploadedDecks > 0?}
  HasDecks -- no --> FirstTime[First-time dashboard]
  HasDecks -- yes --> Returning[Returning user dashboard]

  FirstTime --> Welcome[/welcome/]
  FirstTime --> Upload[/decks/new/]

  Returning --> ContinueLatest[/decks/:deckId/smart-deck/]
  Returning --> ReviewIterations[/decks/:deckId/batches/]
  Returning --> UploadNew[/decks/new/]
  Returning --> RecentSlide[/decks/:deckId/smart-deck?slide=:slideId/]
  Returning --> Decks[/decks/]
  Returning --> Batch[/decks/:deckId/batches/:batchId/]
```

Top action:

- If no decks: `Upload first deck` -> `/welcome`
- If decks exist: `New deck` -> `/decks/new`

### `/decks`

```mermaid
flowchart TD
  DeckLibrary[/decks/] --> DeckCount{deckCount}
  DeckCount -- 0 --> EmptyDecks[Empty state + upload card + templates]
  DeckCount -- 1_plus --> UploadedList[Uploaded deck list]

  EmptyDecks --> Welcome[/welcome/]
  EmptyDecks --> UploadCard[Upload first deck card]
  UploadCard --> SmartDeck[/decks/:deckId/smart-deck/]
  EmptyDecks --> Templates[/templates/]

  UploadedList --> UploadNew[/decks/new/]
  UploadedList --> ActiveDeck[/decks/:activeDeckId/smart-deck/]
  UploadedList --> SelectedDeck[/decks/:deckId/smart-deck/]
  UploadedList --> LatestFinal[/decks/:deckId/compiled/:compiledDeckId/]
  UploadedList --> LatestBatch[/decks/:deckId/batches/:batchId/]
```

User sees:

- Library metrics
- Upload new deck
- Open active deck
- Uploaded deck rows
- Recent deck rail
- Status filter buttons: All decks, Under review, Ready, Failed. These are visible buttons; no redirect found.

## 8. Deck Workspace Journey

### Deck route index redirect

```mermaid
flowchart LR
  DeckIndex[/decks/:deckId/] --> SmartDeck[/decks/:deckId/smart-deck/]
```

### `/decks/:deckId/smart-deck`

```mermaid
flowchart TD
  SmartDeck[/Smart Deck/] --> SlideRail[Slide rail]
  SmartDeck --> Canvas[Deck canvas]
  SmartDeck --> Inspector[Right inspector]
  SmartDeck --> AiPanel[AI panel / commands]

  SmartDeck --> SlideQuery[/same page ?slide=:slideId/]
  SmartDeck --> SmartEdit[/decks/:deckId/smart-edit?slide=:slideId/]
  SmartDeck --> DueDiligence[/decks/:deckId/due-diligence/]
  SmartDeck --> Export[/decks/:deckId/export/]
  SmartDeck --> Batches[/decks/:deckId/batches/]
```

User sees:

| Moment | Options available |
| --- | --- |
| Top actions | Smart Edit, Due Diligence, Export |
| Slide rail / canvas | choose slide -> same route with `?slide=` |
| AI workspace actions | create version -> `/decks/:deckId/batches` after run |
| Sidebar deck workflow | Smart Deck, Smart Edit, Due Diligence, Iterations, Exports |

### `/smart-deck`

Root chooser when the user is not already inside a deck.

```mermaid
flowchart TD
  SmartDeckRoot[/smart-deck/] --> Active{activeDeckId?}
  Active -- yes --> OpenActive[/decks/:activeDeckId/smart-deck/]
  Active -- no --> Decks[/decks/]
  SmartDeckRoot --> AnyDeck[/decks/:deckId/smart-deck/]
```

## 9. Smart Edit Journey

### `/smart-edit`

```mermaid
flowchart TD
  SmartEditRoot[/smart-edit/] --> DeckChoice[Choose deck]
  DeckChoice --> DeckSmartEdit[/decks/:deckId/smart-edit/]
```

### `/decks/:deckId/smart-edit`

```mermaid
flowchart TD
  SmartEdit[/Deck Smart Edit/] --> SlideList[Select slide]
  SlideList --> SlideQuery[/same page ?slide=:slideId/]
  SlideQuery --> BlockList[Select block]
  BlockList --> BlockQuery[/same page ?slide=:slideId&block=:blockId/]

  SmartEdit --> Workspace[/decks/:deckId/smart-deck/]
  SmartEdit --> DueDiligence[/decks/:deckId/due-diligence/]
  SmartEdit --> Export[/decks/:deckId/export/]

  SmartEdit --> Reject[Reject button: visible, no backend redirect found]
  SmartEdit --> Edit[Edit button: visible, no backend redirect found]
  SmartEdit --> Accept[Accept button: visible, no backend redirect found]
```

User sees:

- Slide count and slide list
- Main selected slide preview
- Block list
- Smart edit panel
- Prompt box and suggestion actions
- Breadcrumbs: `/decks` -> `/decks/:deckId/smart-deck`

## 10. Due Diligence Journey

### `/decks/:deckId/due-diligence`

```mermaid
flowchart TD
  DueDiligence[/Due diligence/] --> SmartEdit[/decks/:deckId/smart-edit/]
  DueDiligence --> Export[/decks/:deckId/export/]
  DueDiligence --> BlockToEdit[/decks/:deckId/smart-edit?slide=:id&block=:id/]
  DueDiligence --> BlockToWorkspace[/decks/:deckId/smart-deck?slide=:id&block=:id/]
```

User sees:

- Diligence page header
- Placeholder card area
- Header actions to Smart Edit and Export
- Internal event handlers can jump to Smart Edit or Smart Deck with selected slide/block query params

Legacy redirects into this page:

| Old route | Redirect |
| --- | --- |
| `/decks/:deckId/changes` | `/decks/:deckId/due-diligence` |
| `/decks/:deckId/audience` | `/decks/:deckId/due-diligence` |
| `/decks/:deckId/diligence` | `/decks/:deckId/due-diligence` |

## 11. Iterations, Batch Review, Compile, Final Deck

### `/decks/:deckId/batches`

```mermaid
flowchart TD
  Batches[/Batch history/] --> Latest{latest batch exists?}
  Latest -- yes --> CompileLatest[/decks/:deckId/batches/:batchId/compile/]
  Latest -- no --> Disabled[Prepare Full Deck disabled]
  Batches --> BatchCard[/decks/:deckId/batches/:batchId/]
```

User sees:

- Complete adaptation history
- Latest batch CTA: Prepare Full Deck
- Batch cards for each iteration

### `/decks/:deckId/batches/:batchId`

```mermaid
flowchart TD
  BatchDetail[/Iteration detail/] --> CandidateDecision[Choose generated candidate or keep original]
  CandidateDecision --> Stay[Stay on batch detail]
  BatchDetail --> Prepare[Prepare Full Deck]
  Prepare --> Compile[/decks/:deckId/batches/:batchId/compile/]
```

User sees:

- Iteration name, scope, status
- Candidate actions:
  - choose generated version
  - keep original
- Prepare Full Deck button, disabled unless batch is completed/reviewed

### `/decks/:deckId/batches/:batchId/compile`

```mermaid
flowchart TD
  Compile[/Prepare full deck/] --> ReviewIteration[/decks/:deckId/batches/:batchId/]
  Compile --> DeckLibrary[/decks/]
  Compile --> CompileAction[Compile full deck]
  CompileAction --> CompiledReady{compiledDeck exists?}
  CompiledReady -- yes --> OpenCompiled[/decks/:deckId/compiled/:compiledDeckId/]
```

User sees:

- Batch decisions
- Ready to compile / compiled deck ready card
- `Compile full deck`
- `Open compiled deck` after compile

### `/decks/:deckId/compiled/:compiledDeckId`

```mermaid
flowchart TD
  Compiled[/Compiled deck/] --> Export[/decks/:deckId/export/]
  Compiled --> ReviewBatch[/decks/:deckId/batches/:batchId/]
  Compiled --> DeckLibrary[/decks/]
```

User sees rendered final deck slides and actions:

- Export deck
- Review batch
- Deck library

## 12. Export Pages

### `/decks/:deckId/export`

```mermaid
flowchart TD
  DeckExport[/Deck export/] --> ExportPanel[Export panel]
  ExportPanel --> DownloadExisting[Download existing export]
  ExportPanel --> DownloadAPI[/api/decks/:deckId/exports/:exportId/download/]
```

### `/exports`

```mermaid
flowchart TD
  ExportsRoot[/Exports root/] --> EmptyOrList[No exports yet / exports tied to deck workflows]
  ExportsRoot --> SidebarDeckExport[/decks/:deckId/export from sidebar if current deck exists/]
```

## 13. Utility App Pages

```mermaid
flowchart TD
  Templates[/templates/] --> Sidebar[Sidebar/global nav]
  Datasets[/datasets/] --> Sidebar
  Insights[/insights/] --> Sidebar
  Team[/team/] --> Sidebar
  AppBilling[/app/billing/] --> PlanButtons[Plan buttons visible, no redirect found]
```

Page notes:

| Page | What user sees | Redirect options |
| --- | --- | --- |
| `/templates` | template placeholder / starting points | sidebar/header only |
| `/datasets` | datasets placeholder after parsing | sidebar/header only |
| `/insights` | insights placeholder after AI analysis | sidebar/header only |
| `/team` | optional team access placeholder | sidebar/header only |
| `/app/billing` | plan selection and current plan | plan buttons are visible, no route change found |

## 14. Settings Journey

### `/settings`

```mermaid
flowchart TD
  Settings[/settings/] --> AccountSettings[/settings/account/settings/]
  Settings --> ConnectedAccounts[/settings/account/connected-accounts/]
  Settings --> PreviewRoutes[Preview debugging direct route pills]
```

### `/settings/account/settings`

```mermaid
flowchart TD
  AccountSettings[/Profile and preferences/] --> SaveChanges[Save changes button, no redirect]
  AccountSettings --> ConnectedAccounts[/settings/account/connected-accounts/]
  AccountSettings --> LinkedIn[Connect LinkedIn popup/action]
  AccountSettings --> Microsoft[Connect Microsoft popup/action]
  AccountSettings --> MaybeLater[Close reminder]
```

### `/settings/account/connected-accounts`

```mermaid
flowchart TD
  ConnectedAccounts[/Connected accounts/] --> ProviderButtons[Connect/disconnect provider buttons]
  ConnectedAccounts --> SamePage[State changes on same page]
```

Typo alias:

| Route user enters | Redirect |
| --- | --- |
| `/settings/account/conected-accounts` | `/settings/account/connected-accounts` |

## 15. Error Pages

```mermaid
flowchart TD
  NotFound[/error/404/] --> Dashboard[/dashboard/]
  NotFound --> Intake[/sign_in_landing/]
  RouteList[/error/200/] --> ListedRoute[Click listed route]
```

## 16. Redirect-Only and Guarded Routes

| Route | What happens |
| --- | --- |
| Any `(app)` route while logged out | `/auth/sign-in?next=<current>` |
| `/welcome` with existing decks | `/welcome_back` |
| `/welcome_back` with no decks | `/welcome` |
| `/decks/:deckId` | `/decks/:deckId/smart-deck` |
| `/decks/:deckId/changes` | `/decks/:deckId/due-diligence` |
| `/decks/:deckId/audience` | `/decks/:deckId/due-diligence` |
| `/decks/:deckId/diligence` | `/decks/:deckId/due-diligence` |
| `/decks/:deckId/processing` | admin-only, then `/admin/processing/:deckId` |
| `/decks/:deckId/slides` | admin-only, then `/admin/slides/:deckId` |
| `/sign-in` | `/auth/sign-in` |
| `/sign-up` | `/auth/sign-up` |
| `/settings/account/conected-accounts` | `/settings/account/connected-accounts` |

## 17. Referenced Routes That Look Missing

These links or redirects are present in frontend code, but I did not find matching `src/routes` pages in this tree.

| Referenced path | Where it appears | Notes |
| --- | --- | --- |
| `/admin/elements` | app sidebar/utilities | admin route not found in current frontend tree |
| `/admin/processing/:deckId` | admin processing redirect | target route not found |
| `/admin/slides/:deckId` | admin slides redirect | target route not found |
| `/settings/brand-defaults` | welcome setup tile | route not found |

## 18. Fast Mental Model

```text
PUBLIC SITE
  / -> show interest or sign in
  /pricing /vcs /about /contact /billing /privacy /terms

AUTH
  /auth/sign-in -> API login -> nextUrl
  /auth/sign-up -> API signup -> nextUrl

APP ENTRY
  logged out -> /auth/sign-in?next=...
  no decks   -> /welcome -> /decks/new
  has decks  -> /welcome_back -> /decks/:id/smart-deck

MAIN PRODUCT LOOP
  /decks/new
    -> upload deck
    -> load/review brand
    -> /decks/:id/smart-deck

  /decks/:id/smart-deck
    -> Smart Edit
    -> Due Diligence
    -> Iterations
    -> Export

  /decks/:id/batches
    -> batch detail
    -> compile
    -> compiled deck
    -> export

ACCOUNT / ADMIN
  /settings
  /settings/account/settings
  /settings/account/connected-accounts
  /app/billing
```

## 19. Source Files Used

Key files scanned:

- `src/routes/(marketing)/+layout.svelte`
- `src/lib/components/marketing/MarketingHeader.svelte`
- `src/lib/components/marketing/MarketingFooter.svelte`
- `src/routes/(marketing)/+page.svelte`
- `src/lib/components/marketing/HeroSection.svelte`
- `src/lib/components/marketing/ShowInterestForm.svelte`
- `src/routes/(marketing)/auth/sign-in/+page.svelte`
- `src/routes/(marketing)/auth/sign-up/+page.svelte`
- `src/routes/(app)/+layout.server.ts`
- `src/lib/components/AppShell.svelte`
- `src/lib/components/Sidebar.svelte`
- `src/lib/components/TopBar.svelte`
- `src/routes/(app)/welcome/+page.svelte`
- `src/routes/(app)/welcome_back/+page.svelte`
- `src/routes/(app)/dashboard/+page.svelte`
- `src/routes/(app)/decks/+page.svelte`
- `src/routes/(app)/decks/new/+page.svelte`
- `src/routes/(app)/decks/[deckId]/smart-deck/+page.svelte`
- `src/routes/(app)/decks/[deckId]/smart-edit/+page.svelte`
- `src/routes/(app)/decks/[deckId]/due-diligence/+page.svelte`
- `src/routes/(app)/decks/[deckId]/batches/+page.svelte`
- `src/routes/(app)/decks/[deckId]/batches/[batchId]/+page.svelte`
- `src/routes/(app)/decks/[deckId]/batches/[batchId]/compile/+page.svelte`
- `src/routes/(app)/decks/[deckId]/compiled/[compiledDeckId]/+page.svelte`
- `src/routes/(app)/settings/+page.svelte`

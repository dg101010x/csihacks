# **Relief Plan Two**

## **Platform, Engine, Front End, and Infrastructure Development Plan**

## **1\. Mission**

This workstream builds everything required to transform Relief from a model into a usable financial infrastructure product.

It owns:

1. Consumer interface  
2. Bank operator interface  
3. Design system  
4. Financial event ingestion  
5. Immutable financial ledger  
6. Obligation detection  
7. Deterministic cash flow engine  
8. Financial Resilience Score  
9. Obligation Elasticity Engine  
10. Intervention generation  
11. Intervention optimization  
12. Consumer approval  
13. Provider approval  
14. LangChain explanations  
15. LangGraph workflows  
16. Plaid Sandbox integration  
17. Wells Fargo reference adapters  
18. Audit and replay  
19. Security  
20. Testing  
21. Deployment  
22. Integration with ReliefFM

This workstream does not train ReliefFM or define its internal architecture.

The model workstream will eventually provide financial trajectory forecasts and model generated risk estimates through a versioned inference interface.

## **2\. Core architectural rule**

The platform must work before ReliefFM is connected.

The application will support three forecast providers:

1. Mock Forecast Provider

Used during front end development.

2. Deterministic Forecast Provider

Used as the reliable fallback and initial functioning engine.

3. ReliefFM Forecast Provider

Connected when the model workstream passes its integration requirements.

The selected provider will be controlled through configuration:

FORECAST\_PROVIDER=mock  
FORECAST\_PROVIDER=deterministic  
FORECAST\_PROVIDER=relieffm

No page, database table, optimizer, or workflow should know which forecast provider produced the result.

All providers must return the same `ForecastResponseV1` structure.

## **3\. Relationship with Plan One**

Plan One will own:

1. ReliefFM training  
2. Financial sequence tokenization  
3. Model architecture  
4. Training datasets  
5. Synthetic model training data  
6. Pretraining objectives  
7. Model evaluation  
8. Calibration  
9. Model inference optimization  
10. Model registry  
11. Model cards  
12. Model monitoring metrics  
13. Model inference service

Plan Two will own:

1. Canonical financial product behavior  
2. Product interfaces  
3. Account and obligation records  
4. Deterministic financial calculations  
5. Provider capability rules  
6. Consumer policy rules  
7. Candidate intervention generation  
8. Workflow state  
9. Action approvals  
10. Explanation presentation  
11. Integration and execution

The model predicts what may happen.

The platform decides what may legally, contractually, and operationally be proposed.

The model must never directly execute a financial action.

## **4\. Shared integration contract**

The most important connection between the two plans is a versioned contract package.

Create:

packages/  
  relief\_contracts/

This package contains:

1. JSON schemas  
2. TypeScript types  
3. Python Pydantic models  
4. OpenAPI definitions  
5. Example request fixtures  
6. Example response fixtures  
7. Contract validation tests  
8. Contract version history

The package should not contain application logic or model code.

## **5\. Repository architecture**

Use one monorepo from the beginning so the two workstreams remain structurally connected.

relief/  
  apps/  
    web/  
    api/  
    workflow\_worker/

  services/  
    model\_gateway/  
    model\_inference/

  packages/  
    relief\_contracts/  
    design\_system/  
    financial\_math/  
    configuration/  
    test\_fixtures/  
    eslint\_config/  
    typescript\_config/

  modules/  
    authentication/  
    ledger/  
    accounts/  
    obligations/  
    recurring\_detection/  
    deterministic\_forecast/  
    resilience/  
    elasticity/  
    interventions/  
    provider\_policies/  
    consumer\_constitution/  
    explanations/  
    audit/  
    integrations/

  ml/  
    relieffm/  
    training/  
    evaluation/  
    datasets/

  infrastructure/  
    database/  
    containers/  
    deployment/  
    monitoring/

  docs/  
    architecture/  
    product/  
    compliance/  
    model\_contracts/  
    demo/

Plan Two initially owns everything except:

ml/  
services/model\_inference/

The model team owns those directories.

Both teams jointly approve changes to:

packages/relief\_contracts/

## **6\. Technology stack**

### **6.1 Front end**

Use:

1. Next.js App Router  
2. React  
3. TypeScript  
4. Tailwind CSS  
5. shadcn components where appropriate  
6. TanStack Query  
7. Zod  
8. React Hook Form  
9. Recharts or Apache ECharts  
10. Storybook  
11. Playwright  
12. Vitest

The current Next.js App Router supports layouts, server and client components, streaming, route handlers, loading states, and structured error handling, making it appropriate for the application shell and data intensive dashboard.

### **6.2 Application backend**

Use:

1. Python  
2. FastAPI  
3. Pydantic  
4. SQLAlchemy  
5. Alembic  
6. PostgreSQL  
7. Redis  
8. Structured background workers  
9. OpenTelemetry  
10. Sentry

### **6.3 Artificial intelligence workflow**

Use:

1. LangChain for model interfaces, retrieval, tools, and structured responses  
2. LangGraph for durable workflow state, approval interruptions, resumption, and failure recovery  
3. LangSmith for prompt traces and explanation evaluation

LangGraph supports persistent workflow checkpoints and interruptions that pause execution until external approval is supplied. This directly supports Relief’s consumer and provider approval stages.

### **6.4 Financial integrations**

Use:

1. Synthetic Wells Fargo reference data as the default demonstration source  
2. Plaid Sandbox for realistic connection and webhook behavior  
3. Wells Fargo Gateway adapters only for capabilities confirmed by official access

Plaid Sandbox supports configurable test scenarios and simulated webhooks, while transaction webhooks notify applications when transaction data are available or updated.

Wells Fargo provides a developer portal containing APIs, SDKs, and webhooks for areas including payments and data services. Relief must not assume that a particular consumer modification capability exists unless the exact provider documentation confirms it.

## **7\. Development strategy**

Implementation will proceed in this order:

1. Shared contracts  
2. Front end design system  
3. Front end demonstration experience  
4. Front end application state  
5. Mock backend  
6. Core backend  
7. Immutable ledger  
8. Deterministic forecasting  
9. Obligation detection  
10. Resilience calculation  
11. Elasticity calculation  
12. Intervention optimizer  
13. LangChain explanation layer  
14. LangGraph approval workflow  
15. Plaid integration  
16. Wells Fargo reference adapter  
17. Audit and replay  
18. Security hardening  
19. ReliefFM integration  
20. Deployment and demonstration hardening

Front end implementation begins before production backend work.

This forces the team to define exactly what data the user must see and prevents the backend from producing unused abstractions.

# **Part One**

# **Shared Contracts Before Implementation**

## **8\. Contract ownership rules**

Every shared schema must have:

1. A clear owner  
2. A version number  
3. A written purpose  
4. Required fields  
5. Optional fields  
6. Validation rules  
7. Example fixtures  
8. Compatibility tests  
9. Migration notes

Use semantic versions:

1.0.0  
1.1.0  
2.0.0

Rules:

1. Adding an optional field is a minor version change.  
2. Removing a field is a major version change.  
3. Changing the meaning of a field is a major version change.  
4. Renaming a field is a major version change.  
5. Adding stricter validation may require a major version change.  
6. Every API request must include `contract_version`.  
7. Every persisted model result must store its original contract version.

## **9\. Core financial event schema**

{  
  "contract\_version": "1.0.0",  
  "event\_id": "evt\_01",  
  "household\_id": "hh\_01",  
  "account\_id": "acct\_01",  
  "source": "synthetic\_wells\_fargo",  
  "source\_event\_id": "source\_981",  
  "event\_type": "scheduled\_payment",  
  "event\_status": "scheduled",  
  "occurred\_at": "2026-07-27T09:00:00Z",  
  "effective\_at": "2026-07-27T09:00:00Z",  
  "amount\_cents": 24000,  
  "currency": "USD",  
  "direction": "outflow",  
  "merchant\_name": "Auto Lender",  
  "merchant\_category": "loan\_payment",  
  "obligation\_id": "obl\_car\_01",  
  "is\_recurring": true,  
  "is\_pending": false,  
  "metadata": {}  
}

Money must be represented as integer cents in the TypeScript contract.

The Python domain layer may convert integer cents into `Decimal`, but it must never use floating point arithmetic for monetary calculations.

## **10\. Household snapshot schema**

{  
  "contract\_version": "1.0.0",  
  "snapshot\_id": "snap\_01",  
  "household\_id": "hh\_01",  
  "generated\_at": "2026-07-25T16:00:00Z",  
  "timezone": "America/Los\_Angeles",  
  "currency": "USD",  
  "accounts": \[\],  
  "obligations": \[\],  
  "recent\_events": \[\],  
  "known\_future\_events": \[\],  
  "consumer\_constitution": {},  
  "provider\_capabilities": \[\]  
}

The snapshot is the complete input to every forecast provider.

The model team must not query Plan Two’s production database directly.

Plan Two constructs and validates the snapshot.

## **11\. Forecast request schema**

{  
  "contract\_version": "1.0.0",  
  "request\_id": "forecast\_req\_01",  
  "snapshot": {},  
  "horizon\_days": 30,  
  "scenario\_count": 64,  
  "requested\_outputs": \[  
    "daily\_balance\_trajectories",  
    "distress\_probabilities",  
    "income\_distribution",  
    "variable\_spending\_distribution"  
  \]  
}

## **12\. Forecast response schema**

{  
  "contract\_version": "1.0.0",  
  "request\_id": "forecast\_req\_01",  
  "forecast\_id": "forecast\_01",  
  "provider": "deterministic",  
  "provider\_version": "1.0.0",  
  "generated\_at": "2026-07-25T16:00:01Z",  
  "valid\_until": "2026-07-25T17:00:01Z",  
  "confidence": 0.82,  
  "is\_stale": false,  
  "warnings": \[\],  
  "daily\_summary": \[\],  
  "trajectories": \[\],  
  "distress\_probabilities": {  
    "negative\_balance": 0.43,  
    "essential\_reserve\_violation": 0.72,  
    "missed\_obligation": 0.31  
  },  
  "reason\_factors": \[\],  
  "model\_metadata": null  
}

ReliefFM responses will include `model_metadata`.

The deterministic provider will set it to `null`.

## **13\. Intervention simulation request**

{  
  "contract\_version": "1.0.0",  
  "simulation\_id": "sim\_01",  
  "base\_forecast\_id": "forecast\_01",  
  "household\_snapshot\_id": "snap\_01",  
  "interventions": \[  
    {  
      "action\_type": "split\_payment",  
      "obligation\_id": "obl\_car\_01",  
      "parameters": {  
        "first\_payment\_cents": 12000,  
        "second\_payment\_cents": 12000,  
        "second\_payment\_date": "2026-08-07"  
      }  
    }  
  \]  
}

## **14\. Model integration endpoints**

Plan One must eventually expose:

POST /model/v1/forecast  
POST /model/v1/simulate\_intervention  
GET /model/v1/health  
GET /model/v1/metadata

Plan Two will call these endpoints only through:

services/model\_gateway/

No other module may call the model service directly.

# **Part Two**

# **Front End First Implementation**

## **15\. Front end product objective**

The front end must communicate five facts within ten seconds:

1. What changed  
2. When the financial problem occurs  
3. Why the problem occurs  
4. Which interventions are available  
5. What happens after each intervention

The interface must not begin with a generic spending dashboard.

The financial timeline is the main product surface.

## **16\. Primary user journeys**

### **16.1 Consumer journey**

1. Sarah opens Relief.  
2. She sees her current Financial Resilience Score.  
3. Relief displays an income change alert.  
4. The timeline recalculates.  
5. A liquidity shortfall appears on Thursday or Friday.  
6. Relief shows the obligations causing the collision.  
7. Sarah opens the proposed intervention.  
8. She compares the original outcome with three alternatives.  
9. She sees added costs and required approvals.  
10. She approves or rejects each action.  
11. Relief drafts any provider request.  
12. The workflow enters provider review.  
13. The audit page records the complete process.

### **16.2 Bank operator journey**

1. The bank operator opens the provider dashboard.  
2. The operator sees customers with upcoming recoverable distress.  
3. The operator opens Sarah’s intervention request.  
4. The system displays consumer impact and provider impact.  
5. The operator sees the provider rule supporting the modification.  
6. The operator approves, rejects, or requests more information.  
7. Relief updates the workflow.  
8. The action is simulated or executed through an authorized adapter.

### **16.3 Demonstration journey**

1. The presenter opens the shock simulator.  
2. The baseline state is visible.  
3. The presenter reduces Sarah’s paycheck by $380.  
4. The timeline updates.  
5. The risk region appears.  
6. Relief identifies the obligation collision.  
7. The intervention optimizer returns alternatives.  
8. The presenter approves the recommended package.  
9. The revised trajectory appears.  
10. The provider impact view confirms reduced simulated loss.

## **17\. Route architecture**

/  
  landing page

/demo  
  guided shock demonstration

/onboarding  
  data source and consent flow

/dashboard  
  household financial state

/timeline  
  detailed financial timeline

/interventions  
  all current interventions

/interventions/\[intervention\_id\]  
  intervention comparison and approval

/constitution  
  consumer rules

/provider  
  provider portfolio dashboard

/provider/cases/\[case\_id\]  
  individual provider review

/audit/\[decision\_id\]  
  immutable decision replay

/settings  
  account, consent, integrations

/settings/integrations  
  Plaid and provider connections

## **18\. Front end design system**

Create a dedicated package:

packages/design\_system/

It should contain:

1. Color tokens  
2. Typography tokens  
3. Spacing tokens  
4. Border tokens  
5. Elevation tokens  
6. Motion tokens  
7. Chart tokens  
8. Component primitives  
9. Accessibility helpers  
10. Storybook documentation

## **19\. Color system**

Use:

Deep Ink  
\#0B1220

Porcelain  
\#F7F8F5

Trust Blue  
\#315EFB

Relief Mint  
\#24B99A

Signal Amber  
\#E9A93B

Risk Coral  
\#D95C5C

Slate  
\#667085

Rules:

1. Deep Ink is used for navigation, primary text, and enterprise surfaces.  
2. Porcelain is used for the primary background.  
3. Trust Blue is used for selected controls and primary actions.  
4. Relief Mint is used for confirmed improvement.  
5. Signal Amber is used for upcoming uncertainty.  
6. Risk Coral is used only for verified or strongly projected risk.  
7. No outcome may rely on color alone.  
8. Every status requires text and an icon.  
9. Risk Coral must not dominate entire screens.  
10. The design must not imitate Wells Fargo’s red and gold identity.

## **20\. Typography**

Use:

1. Geist Sans for interface text  
2. Geist Mono for money, dates, event identifiers, model versions, and audit information

Typography hierarchy:

1. Display title  
2. Page title  
3. Section title  
4. Card title  
5. Body  
6. Supporting label  
7. Numerical metric  
8. Audit metadata

Numbers must use tabular figures where supported so values do not visually shift during timeline updates.

## **21\. Core components**

### **21.1 Application shell**

Components:

AppShell  
PrimaryNavigation  
ContextHeader  
DataSourceStatus  
UserMenu  
EnvironmentBadge

The `EnvironmentBadge` must display:

1. Simulated  
2. Sandbox  
3. Test  
4. Production

The demonstration must always display `Simulated`.

### **21.2 Financial state components**

BalanceSummary  
ResilienceScoreCard  
IncomeForecastCard  
UpcomingObligationsCard  
RiskSummaryCard  
DataFreshnessCard

### **21.3 Timeline components**

CashFlowTimeline  
TimelineEvent  
BalanceTrajectory  
UncertaintyBand  
RiskRegion  
CurrentTimeMarker  
PaycheckMarker  
ObligationMarker  
InterventionMarker

The timeline must support:

1. Seven day view  
2. Fourteen day view  
3. Thirty day view  
4. Baseline forecast  
5. Modified forecast  
6. Scenario uncertainty  
7. Event inspection  
8. Keyboard navigation  
9. Reduced motion mode

### **21.4 Obligation components**

ObligationCard  
ObligationDetails  
EssentialityIndicator  
ElasticityBreakdown  
ProviderCapabilityBadge  
ApprovalProbabilityStatus  
ModificationHistory

Do not show an approval probability when evidence is unavailable.

Use:

Approval likelihood unavailable

instead of inventing a percentage.

### **21.5 Intervention components**

InterventionPackageCard  
InterventionActionRow  
OutcomeComparison  
CostDisclosure  
ApprovalRequirement  
ConsumerApprovalPanel  
ProviderApprovalPanel  
AlternativeSelector

### **21.6 Explanation components**

ExplanationPanel  
ReasonFactorList  
UncertaintyDisclosure  
PolicySourceList  
ModelSourceBadge  
StructuredFactTable

### **21.7 Audit components**

AuditTimeline  
InputSnapshotViewer  
ForecastMetadata  
CandidateActionViewer  
RejectedActionViewer  
ApprovalHistory  
ReplayControls

## **22\. Financial Resilience Score interface**

Display:

1. Overall score  
2. Confidence  
3. Score trend  
4. Component contributions  
5. Primary weakness  
6. Primary stabilizing factor  
7. Data freshness

The score must include a disclosure:

> The Financial Resilience Score estimates short term liquidity capacity. It is not a credit score and does not determine eligibility for financial products.

Components:

1. Seven day liquidity coverage  
2. Fourteen day essential coverage  
3. Obligation collision risk  
4. Income stability  
5. Emergency reserve coverage

The user must be able to open the score and inspect every component.

## **23\. Timeline interaction design**

The timeline is the main demonstration surface.

### **23.1 Baseline state**

Display:

1. Current balance  
2. Scheduled income  
3. Scheduled obligations  
4. Expected variable spending  
5. Essential reserve line  
6. Forecast balance

### **23.2 Shock state**

When a paycheck changes:

1. Animate the paycheck amount changing.  
2. Recalculate the balance curve.  
3. Reveal the first reserve violation.  
4. Highlight the obligation collision.  
5. Open a concise explanation.  
6. Do not automatically jump to an intervention.

### **23.3 Intervention state**

When an intervention is selected:

1. Keep the original trajectory visible.  
2. Add the modified trajectory.  
3. Move affected obligations.  
4. Display added cost.  
5. Display new minimum balance.  
6. Display remaining risk.  
7. Display required approvals.

The interface should show causality rather than decoration.

## **24\. Front end data strategy**

Front end development must not wait for backend implementation.

Create typed fixtures:

packages/test\_fixtures/  
  sarah\_baseline.json  
  sarah\_income\_shock.json  
  sarah\_intervention\_options.json  
  sarah\_provider\_approval.json  
  sarah\_completed\_case.json

Each fixture must validate against `relief_contracts`.

Create Mock Service Worker handlers for:

1. Accounts  
2. Transactions  
3. Forecasts  
4. Interventions  
5. Approvals  
6. Audit data  
7. Provider policies  
8. Integration status

The mock application must support the complete demonstration before the real API exists.

## **25\. Front end state architecture**

Separate state into three categories.

### **25.1 Server state**

Use TanStack Query for:

1. Account data  
2. Forecast results  
3. Intervention cases  
4. Provider policies  
5. Audit records  
6. Integration status

### **25.2 Local interface state**

Use component state or a minimal state store for:

1. Selected timeline range  
2. Selected intervention  
3. Open panel state  
4. Comparison mode  
5. Demonstration step

### **25.3 Workflow state**

Workflow state must come from the backend.

The front end must never infer that an action is approved merely because a button was clicked.

The backend response must confirm the new state.

## **26\. Front end loading states**

Every data surface must support:

1. Initial loading  
2. Background refresh  
3. Stale data  
4. Partial data  
5. Failed request  
6. Empty state  
7. Permission denied  
8. Provider unavailable  
9. Model unavailable  
10. Forecast invalidated

The application must not show a blank dashboard when one subsystem fails.

## **27\. Front end accessibility**

Acceptance requirements:

1. Keyboard operable navigation  
2. Visible focus indicators  
3. Semantic headings  
4. Form labels  
5. Accessible error messages  
6. Chart summaries in text  
7. Reduced motion support  
8. Sufficient text contrast  
9. Status indicators with text  
10. Screen reader descriptions for financial trajectory changes

The timeline must have an alternate table representation.

## **28\. Front end phase deliverables**

### **Phase A**

Design foundation

Deliver:

1. Design tokens  
2. Typography  
3. Button system  
4. Form controls  
5. Card system  
6. Status indicators  
7. Empty states  
8. Loading states  
9. Storybook

Definition of done:

1. All components support light background use.  
2. All interactive components support keyboard input.  
3. Every status is represented by text and icon.  
4. No Wells Fargo proprietary visual assets are used.

### **Phase B**

Demo shell

Deliver:

1. Application shell  
2. Demo route  
3. Baseline household view  
4. Timeline  
5. Shock controls  
6. Resilience Score  
7. Obligation list

Definition of done:

The complete baseline scenario renders from static fixtures.

### **Phase C**

Intervention experience

Deliver:

1. Intervention list  
2. Comparison interface  
3. Cost disclosure  
4. Consumer approval  
5. Provider approval status  
6. Explanation panel

Definition of done:

The demonstration can progress from shock detection through consumer approval using fixtures.

### **Phase D**

Provider experience

Deliver:

1. Provider portfolio view  
2. Individual case view  
3. Policy evidence  
4. Provider approval  
5. Provider impact comparison

Definition of done:

A second browser session can review and approve the consumer’s case.

### **Phase E**

Audit experience

Deliver:

1. Audit timeline  
2. Input snapshot  
3. Forecast metadata  
4. Candidate actions  
5. Rejected actions  
6. Approval history  
7. Replay mode

Definition of done:

A completed demonstration decision can be reconstructed from stored data.

# **Part Three**

# **Application Backend**

## **29\. Backend architecture**

Start as a modular monolith.

Do not begin with independent microservices.

The API application contains isolated modules with strict interfaces.

apps/api/  
  main.py  
  dependencies.py  
  middleware/  
  routes/

modules/  
  accounts/  
  ledger/  
  obligations/  
  forecasts/  
  resilience/  
  elasticity/  
  interventions/  
  workflows/  
  provider\_policies/  
  consumer\_constitution/  
  explanations/  
  audit/  
  integrations/

Reasons:

1. Easier local development  
2. Simpler database transactions  
3. Faster demonstration deployment  
4. Lower integration overhead  
5. Clear future extraction boundaries

## **30\. API response envelope**

All responses should use:

{  
  "request\_id": "req\_01",  
  "data": {},  
  "errors": \[\],  
  "warnings": \[\],  
  "metadata": {  
    "contract\_version": "1.0.0",  
    "generated\_at": "2026-07-25T16:00:00Z"  
  }  
}

Every request must receive a unique request identifier.

The request identifier must be propagated into:

1. Logs  
2. Forecast calls  
3. LangGraph runs  
4. Model calls  
5. Audit events  
6. Integration calls

## **31\. Primary API routes**

### **31.1 Household**

GET /v1/households/current  
GET /v1/households/current/snapshot

### **31.2 Accounts**

GET /v1/accounts  
GET /v1/accounts/{account\_id}  
GET /v1/accounts/{account\_id}/events

### **31.3 Obligations**

GET /v1/obligations  
GET /v1/obligations/{obligation\_id}  
POST /v1/obligations/{obligation\_id}/confirm  
POST /v1/obligations/{obligation\_id}/correct

### **31.4 Forecasts**

POST /v1/forecasts  
GET /v1/forecasts/{forecast\_id}  
GET /v1/forecasts/{forecast\_id}/trajectories  
POST /v1/forecasts/{forecast\_id}/invalidate

### **31.5 Resilience**

GET /v1/resilience/current  
GET /v1/resilience/history

### **31.6 Interventions**

POST /v1/interventions/generate  
GET /v1/interventions  
GET /v1/interventions/{intervention\_id}  
POST /v1/interventions/{intervention\_id}/simulate  
POST /v1/interventions/{intervention\_id}/approve  
POST /v1/interventions/{intervention\_id}/reject

### **31.7 Provider cases**

GET /v1/provider/cases  
GET /v1/provider/cases/{case\_id}  
POST /v1/provider/cases/{case\_id}/approve  
POST /v1/provider/cases/{case\_id}/reject  
POST /v1/provider/cases/{case\_id}/request\_information

### **31.8 Consumer constitution**

GET /v1/constitution  
PUT /v1/constitution  
POST /v1/constitution/parse  
POST /v1/constitution/validate

### **31.9 Audit**

GET /v1/audit/{decision\_id}  
POST /v1/audit/{decision\_id}/replay

### **31.10 Integrations**

POST /v1/integrations/plaid/link\_token  
POST /v1/integrations/plaid/exchange  
POST /v1/integrations/plaid/webhook  
GET /v1/integrations/status

# **Part Four**

# **Data and Ledger**

## **32\. Database entities**

Create the following core tables.

### **32.1 Tenants**

tenants  
  id  
  name  
  environment  
  created\_at

### **32.2 Users**

users  
  id  
  tenant\_id  
  external\_auth\_id  
  role  
  status  
  created\_at

### **32.3 Households**

households  
  id  
  tenant\_id  
  primary\_user\_id  
  timezone  
  currency  
  created\_at

### **32.4 Accounts**

accounts  
  id  
  household\_id  
  provider  
  provider\_account\_token  
  account\_type  
  account\_subtype  
  display\_name  
  current\_balance\_cents  
  available\_balance\_cents  
  balance\_updated\_at  
  data\_status  
  created\_at

### **32.5 Financial events**

financial\_events  
  id  
  household\_id  
  account\_id  
  source  
  source\_event\_id  
  event\_type  
  event\_status  
  occurred\_at  
  effective\_at  
  amount\_cents  
  currency  
  direction  
  merchant\_name  
  merchant\_category  
  obligation\_id  
  is\_recurring  
  is\_pending  
  metadata  
  ingestion\_run\_id  
  created\_at

Create a uniqueness constraint across:

source  
source\_event\_id  
account\_id

This prevents duplicate ingestion.

### **32.6 Obligations**

obligations  
  id  
  household\_id  
  provider\_id  
  obligation\_type  
  display\_name  
  principal\_balance\_cents  
  scheduled\_amount\_cents  
  next\_due\_at  
  recurrence\_rule  
  essentiality\_score  
  status  
  source\_confidence  
  consumer\_confirmed  
  created\_at  
  updated\_at

### **32.7 Provider capabilities**

provider\_capabilities  
  id  
  provider\_id  
  product\_type  
  action\_type  
  eligibility\_rule  
  cost\_rule  
  timing\_rule  
  evidence\_source  
  effective\_from  
  effective\_until  
  is\_simulated  
  created\_at

### **32.8 Forecast runs**

forecast\_runs  
  id  
  household\_id  
  snapshot\_id  
  provider  
  provider\_version  
  contract\_version  
  status  
  horizon\_days  
  scenario\_count  
  confidence  
  valid\_until  
  warnings  
  input\_hash  
  created\_at

### **32.9 Forecast trajectories**

forecast\_trajectories  
  id  
  forecast\_run\_id  
  scenario\_index  
  event\_date  
  starting\_balance\_cents  
  inflow\_cents  
  outflow\_cents  
  ending\_balance\_cents  
  essential\_reserve\_cents

### **32.10 Intervention cases**

intervention\_cases  
  id  
  household\_id  
  base\_forecast\_id  
  status  
  selected\_package\_id  
  workflow\_thread\_id  
  created\_at  
  updated\_at

### **32.11 Intervention actions**

intervention\_actions  
  id  
  case\_id  
  obligation\_id  
  action\_type  
  parameters  
  provider\_capability\_id  
  consumer\_status  
  provider\_status  
  estimated\_cost\_cents  
  created\_at

### **32.12 Audit events**

audit\_events  
  id  
  decision\_id  
  event\_type  
  actor\_type  
  actor\_id  
  request\_id  
  event\_payload  
  payload\_hash  
  occurred\_at

Audit events must be append only.

## **33\. Ledger requirements**

The ledger must satisfy:

1. Events are immutable.  
2. Corrections create new correcting events.  
3. Pending and posted transactions remain distinct.  
4. Transfers are linked where possible.  
5. Balance snapshots are reconciled against event totals.  
6. Source lineage is retained.  
7. Every ingestion run is recorded.  
8. Duplicate events are rejected safely.  
9. Monetary arithmetic uses integer cents or Decimal.  
10. All times are stored in UTC.  
11. Household timezone is retained for display and due date interpretation.

## **34\. Transaction normalization pipeline**

Pipeline:

Raw transaction  
    ↓  
Schema validation  
    ↓  
Source deduplication  
    ↓  
Merchant normalization  
    ↓  
Category normalization  
    ↓  
Transfer detection  
    ↓  
Recurring candidate detection  
    ↓  
Obligation linkage  
    ↓  
Ledger persistence  
    ↓  
Forecast invalidation event

Each stage should produce:

1. Status  
2. Confidence  
3. Warnings  
4. Processing version  
5. Input reference  
6. Output reference

## **35\. Data quality checks**

Run:

1. Duplicate event check  
2. Unsupported currency check  
3. Impossible date check  
4. Missing account check  
5. Balance consistency check  
6. Amount outlier check  
7. Pending event aging check  
8. Transfer duplication check  
9. Merchant normalization confidence check  
10. Recurring pattern confidence check

Low confidence data must be shown to the user for confirmation rather than silently accepted.

# **Part Five**

# **Obligation Detection**

## **36\. Obligation model**

An obligation is a future financial commitment with:

1. Amount or amount range  
2. Due date or recurrence  
3. Provider  
4. Product type  
5. Essentiality  
6. Contractual consequences  
7. Modification capabilities  
8. Consumer confirmation status

Examples:

1. Rent  
2. Car payment  
3. Credit card minimum payment  
4. Personal loan payment  
5. Insurance premium  
6. Buy now pay later payment  
7. Utility bill  
8. Subscription

## **37\. Recurring detection algorithm**

Initial deterministic detector:

1. Group normalized transactions by merchant and category.  
2. Calculate time intervals between transactions.  
3. Identify dominant interval clusters.  
4. Calculate amount variance.  
5. Identify monthly, weekly, biweekly, quarterly, and annual patterns.  
6. Exclude likely transfers.  
7. Assign recurrence confidence.  
8. Generate an obligation candidate.

Example confidence components:

1. Interval regularity  
2. Merchant consistency  
3. Amount consistency  
4. Category compatibility  
5. Number of historical observations

Do not automatically convert uncertain recurring candidates into confirmed obligations.

## **38\. Consumer confirmation**

The front end should ask:

> Relief detected a recurring $90 payment to a buy now pay later provider around the fourth Thursday of each month. Should this be treated as an obligation?

Available responses:

1. Confirm  
2. Correct details  
3. Ignore once  
4. Never treat as recurring

Confirmed corrections become feedback data for future detection improvements.

# **Part Six**

# **Deterministic Cash Flow Engine**

## **39\. Purpose**

The deterministic engine calculates the consequences of known financial events without requiring a trained model.

It remains the fallback after ReliefFM is connected.

## **40\. Inputs**

1. Starting account balances  
2. Known income events  
3. Scheduled obligations  
4. Confirmed recurring expenses  
5. Essential reserve  
6. Pending transactions  
7. User entered events  
8. Intervention actions  
9. Forecast horizon  
10. Event ordering rules

## **41\. Outputs**

1. Daily starting balance  
2. Daily inflows  
3. Daily outflows  
4. Daily ending balance  
5. Minimum projected balance  
6. First negative balance date  
7. First reserve violation date  
8. Obligation coverage status  
9. Collision groups  
10. Data warnings

## **42\. Event ordering**

For events with the same date:

1. Respect exact timestamps where known.  
2. Use provider supplied posting order where available.  
3. Otherwise process guaranteed income before flexible spending only when the income is known to arrive earlier.  
4. Never assume a paycheck arrives before rent without timestamp evidence.  
5. Mark ambiguous ordering as uncertainty.

## **43\. Deterministic forecast algorithm**

Load household snapshot

Validate starting balances

Generate calendar buckets

Insert known future income

Insert scheduled obligations

Insert confirmed recurring events

Insert pending transactions

Order events

Calculate balances

Detect reserve violations

Detect negative balances

Detect uncovered obligations

Create collision groups

Return ForecastResponseV1

## **44\. Deterministic uncertainty**

The deterministic engine can support bounded uncertainty without pretending to be ReliefFM.

For variable expenses:

1. Use recent median daily essential spending.  
2. Calculate a conservative upper range.  
3. Calculate a lower range.  
4. Produce three paths:  
   1. Lower spending path  
   2. Expected spending path  
   3. Higher spending path

These paths must be labeled rule based, not model generated.

## **45\. Reconciliation with ReliefFM**

Known events remain authoritative.

When ReliefFM produces trajectories:

1. The platform validates starting balances.  
2. The platform confirms scheduled obligations are present.  
3. The platform checks currency.  
4. The platform verifies accounting consistency.  
5. The platform rejects malformed trajectories.  
6. The platform overlays known contractual events if necessary.  
7. The platform records reconciliation warnings.

ReliefFM must not erase a known payment because the model considers it unlikely.

# **Part Seven**

# **Financial Resilience Score**

## **46\. Score purpose**

The Financial Resilience Score summarizes short term liquidity capacity.

It is not:

1. A credit score  
2. An underwriting score  
3. A provider approval score  
4. A moral judgment  
5. A guarantee

## **47\. Score components**

### **47.1 Seven day liquidity coverage**

Measures whether liquid funds can cover projected obligations and essential expenses over seven days.

Weight:

30 percent

### **47.2 Fourteen day essential coverage**

Measures coverage of essential obligations over fourteen days.

Weight:

25 percent

### **47.3 Obligation collision risk**

Measures the concentration of large obligations before available income.

Weight:

20 percent

### **47.4 Income stability**

Measures the consistency of expected income amount and timing.

Weight:

15 percent

### **47.5 Emergency reserve coverage**

Measures available reserve relative to essential expenses.

Weight:

10 percent

## **48\. Score calculation requirements**

1. Every component must return zero through one hundred.  
2. Every component must include a confidence value.  
3. Missing data must reduce confidence.  
4. Missing data must not automatically produce a low score.  
5. The score calculation must be versioned.  
6. The score must be recalculated after material events.  
7. The explanation must expose component contributions.  
8. Historical scores must retain their original calculation version.

## **49\. Score triggers**

Recalculate when:

1. Income changes  
2. Balance changes materially  
3. A new obligation appears  
4. An obligation is paid  
5. A transaction posts  
6. A provider policy changes  
7. The consumer constitution changes  
8. An intervention is simulated  
9. A forecast expires

# **Part Eight**

# **Obligation Elasticity Engine**

## **50\. Purpose**

The Elasticity Engine estimates how safely and realistically an obligation may be modified.

Elasticity is not the same as importance.

A highly important obligation may have low flexibility.

A low importance obligation may have high flexibility.

## **51\. Elasticity profile**

Each obligation receives separate values for:

1. Essentiality  
2. Contractual flexibility  
3. Provider capability  
4. Timing slack  
5. Reversibility  
6. Added cost  
7. Consumer harm  
8. Evidence confidence

## **52\. Evidence hierarchy**

Use this order:

1. Provider supplied structured policy  
2. Provider published policy document  
3. Confirmed product contract  
4. Consumer supplied contract information  
5. Simulated demonstration policy  
6. Unknown

The system must not infer provider flexibility solely from the obligation category.

## **53\. Composite score**

Initial calculation:

1. Contractual flexibility contributes 25 percent.  
2. Provider capability contributes 20 percent.  
3. Reversibility contributes 15 percent.  
4. Timing slack contributes 15 percent.  
5. Low consumer harm contributes 15 percent.  
6. Low added cost contributes 10 percent.

Store the component values separately.

The optimizer should use components, not only the composite score.

## **54\. Unknown values**

When provider capability is unknown:

1. Do not substitute zero.  
2. Do not substitute fifty.  
3. Store `unknown`.  
4. Reduce total confidence.  
5. Exclude provider dependent actions unless the action is clearly labeled as a draft request.

## **55\. Versioning**

Create:

elasticity\_method\_version

Every recommendation stores the exact version used.

The weights must be configurable through policy files rather than hardcoded throughout the application.

# **Part Nine**

# **Intervention Engine**

## **56\. Candidate actions**

The initial action library contains:

1. Pause a cancellable subscription  
2. Defer a discretionary planned purchase  
3. Move a due date  
4. Split a payment  
5. Request temporary partial payment  
6. Request a hardship plan  
7. Waive a simulated fee  
8. Reorder optional transfers  
9. Prevent a new buy now pay later purchase  
10. Apply a temporary provider buffer

## **57\. Action categories**

### **57.1 Consumer controlled actions**

Examples:

1. Pause subscription  
2. Defer planned purchase  
3. Change an internal savings transfer

These may be approved by the consumer.

### **57.2 Provider approval actions**

Examples:

1. Move loan due date  
2. Split required payment  
3. Change minimum payment  
4. Waive fee

These require provider approval.

### **57.3 Draft only actions**

Examples:

1. Hardship request  
2. Customer service message  
3. Modification inquiry

Relief may draft these actions but cannot treat them as approved.

## **58\. Candidate generation**

For each obligation:

1. Load elasticity profile.  
2. Load provider capabilities.  
3. Load consumer constitution.  
4. Generate permitted action templates.  
5. Fill valid parameter ranges.  
6. Reject unsupported combinations.  
7. Estimate added cost.  
8. Mark required approvals.  
9. Submit candidates for simulation.

## **59\. Hard constraints**

An intervention is invalid when:

1. It violates the consumer constitution.  
2. It exceeds provider capabilities.  
3. It modifies an essential obligation prohibited by policy.  
4. It adds cost above the consumer limit.  
5. It requires unsupported execution.  
6. It leaves a required payment unresolved.  
7. It creates a larger projected liquidity problem.  
8. It relies on an expired provider policy.  
9. It requires fabricated approval probability.  
10. It contains incomplete financial terms.

Invalid interventions must remain available in the audit record with rejection reasons.

## **60\. Optimization objectives**

Rank valid interventions using:

1. Negative balance reduction  
2. Essential reserve protection  
3. Missed payment reduction  
4. Fee reduction  
5. Added interest  
6. Repayment extension  
7. Consumer preference alignment  
8. Provider recovery  
9. Number of required approvals  
10. Intervention complexity

Do not compress all outputs into a single hidden score.

Return a Pareto frontier where possible.

The interface should present:

1. Recommended balance  
2. Lowest added cost  
3. Lowest provider modification

## **61\. Simulation**

For every candidate package:

1. Clone the household snapshot.  
2. Apply the proposed actions.  
3. Request a new forecast.  
4. Calculate resulting distress.  
5. Calculate new Resilience Score.  
6. Calculate consumer outcome changes.  
7. Calculate provider outcome changes.  
8. Record warnings.  
9. Record forecast provider.  
10. Store the simulation.

## **62\. Deterministic fallback simulation**

Before ReliefFM is available, intervention simulations use the deterministic engine.

After ReliefFM becomes available:

1. Run deterministic validation first.  
2. Run ReliefFM intervention conditioned forecasting.  
3. Compare outputs.  
4. Flag material disagreement.  
5. Preserve both results.

The application should not silently average conflicting forecasts.

# **Part Ten**

# **LangChain and LangGraph**

## **63\. LangChain responsibilities**

LangChain handles:

1. Structured explanation generation  
2. Provider policy retrieval  
3. Hardship request drafting  
4. Constitution parsing  
5. Information request drafting  
6. Provider case summarization

It does not handle:

1. Monetary arithmetic  
2. Resilience calculation  
3. Elasticity calculation  
4. Intervention ranking  
5. Provider approval  
6. Consumer approval  
7. Financial execution

## **64\. LangGraph workflow**

Create a workflow named:

financial\_intervention\_workflow

States:

case\_created  
snapshot\_validated  
forecast\_completed  
distress\_detected  
candidates\_generated  
provider\_rules\_validated  
consumer\_rules\_validated  
simulations\_completed  
actions\_ranked  
explanation\_generated  
awaiting\_consumer\_approval  
awaiting\_provider\_approval  
approved  
rejected  
executed  
simulation\_completed  
failed

## **65\. Workflow graph**

Create case

Validate household snapshot

Run forecast

Detect distress

Generate candidates

Validate provider policies

Validate consumer constitution

Simulate candidates

Rank valid packages

Generate structured explanation

Pause for consumer approval

Pause for provider approval when required

Execute authorized simulation or adapter action

Write immutable audit record

Complete case

LangGraph interruptions should be used for consumer and provider review. The workflow checkpoint must persist before presenting the approval interface so the process can resume without repeating earlier external calls.

## **66\. LangGraph state**

class InterventionWorkflowState(TypedDict):  
    case\_id: str  
    request\_id: str  
    household\_snapshot\_id: str  
    forecast\_id: str | None  
    distress\_result: dict | None  
    candidate\_action\_ids: list\[str\]  
    valid\_package\_ids: list\[str\]  
    selected\_package\_id: str | None  
    explanation\_id: str | None  
    consumer\_approval: dict | None  
    provider\_approval: dict | None  
    current\_status: str  
    warnings: list\[str\]  
    errors: list\[str\]

## **67\. Explanation chain**

Input must contain only structured facts:

1. Forecast result  
2. Distress events  
3. Selected intervention  
4. Cost information  
5. Consumer rules  
6. Provider policy references  
7. Required approvals

Output schema:

class ReliefExplanation(BaseModel):  
    situation\_summary: str  
    primary\_factors: list\[str\]  
    proposed\_actions: list\[str\]  
    expected\_consumer\_effect: str  
    expected\_provider\_effect: str  
    added\_cost\_disclosure: str  
    uncertainty\_disclosure: str  
    required\_approvals: list\[str\]  
    policy\_sources: list\[str\]

## **68\. Explanation validation**

After generation:

1. Extract every number from the explanation.  
2. Confirm each number exists in structured input.  
3. Confirm every action exists in the selected package.  
4. Confirm cost language matches calculated cost.  
5. Confirm approval language matches workflow requirements.  
6. Confirm no guarantee language appears.  
7. Confirm provider policies are cited.  
8. Reject and regenerate invalid output.

## **69\. Prohibited explanation claims**

Block phrases equivalent to:

1. Guaranteed approval  
2. Guaranteed prevention  
3. The bank will accept  
4. No financial risk  
5. Your credit will not be affected  
6. This is the best financial decision  
7. Relief has changed your contract  
8. The provider has agreed

Unless a verified provider response supports the statement.

## **70\. Provider policy retrieval**

Store documents with metadata:

1. Provider  
2. Product  
3. Jurisdiction  
4. Effective date  
5. Expiration date  
6. Document version  
7. Source location  
8. Simulation status  
9. Review status

Retrieval output must include:

1. Relevant passage identifier  
2. Document identifier  
3. Effective date  
4. Confidence  
5. Whether the policy is simulated

If no supporting document is retrieved, the workflow must not present the action as provider supported.

## **71\. Consumer constitution parser**

Free text input example:

> Protect housing, groceries, medicine, and transportation. Never extend a loan if it adds interest. Ask me before pausing any subscription.

The parser produces a draft:

{  
  "protected\_categories": \[  
    "housing",  
    "groceries",  
    "medicine",  
    "transportation"  
  \],  
  "allow\_term\_extension": true,  
  "maximum\_added\_interest\_cents": 0,  
  "require\_confirmation\_for\_subscriptions": true  
}

The user must confirm the structured interpretation.

The parsed result does not become active automatically.

# **Part Eleven**

# **Integrations**

## **72\. Bank adapter interface**

class BankAdapter:  
    async def get\_accounts(self, customer\_id: str): ...  
    async def get\_balances(self, customer\_id: str): ...  
    async def get\_transactions(self, customer\_id: str, cursor: str | None): ...  
    async def get\_scheduled\_obligations(self, customer\_id: str): ...  
    async def get\_provider\_capabilities(self, customer\_id: str): ...  
    async def submit\_action\_request(self, request: dict): ...  
    async def get\_action\_status(self, external\_request\_id: str): ...

Implement:

1. `SyntheticWellsFargoAdapter`  
2. `PlaidSandboxAdapter`  
3. `WellsFargoGatewayAdapter`

The Wells Fargo Gateway adapter may initially expose only documented and authorized capabilities.

## **73\. Synthetic Wells Fargo adapter**

This is the default demonstration adapter.

It provides:

1. Synthetic checking account  
2. Synthetic balances  
3. Synthetic transactions  
4. Synthetic recurring obligations  
5. Synthetic loan terms  
6. Simulated provider policies  
7. Simulated approval responses

Every API response should include:

{  
  "is\_simulated": true,  
  "institution\_reference": "Wells Fargo",  
  "affiliation": false  
}

Visible disclosure:

> Demonstration data is simulated. Relief is not affiliated with or endorsed by Wells Fargo.

## **74\. Plaid Sandbox flow**

1. Front end requests a Link token.  
2. Backend creates the token.  
3. Front end opens Plaid Link.  
4. Backend exchanges the returned public token.  
5. Access token is encrypted and stored.  
6. Initial transaction synchronization begins.  
7. Transactions are normalized.  
8. Ledger events are created.  
9. Webhooks trigger later synchronization.  
10. Forecasts are invalidated when financial data change.

## **75\. Plaid webhook processing**

Webhook endpoint:

POST /v1/integrations/plaid/webhook

Processing:

1. Validate webhook.  
2. Extract item identifier.  
3. Create idempotency key.  
4. Store webhook receipt.  
5. Return successful acknowledgement quickly.  
6. Queue synchronization.  
7. Retrieve transaction changes.  
8. Normalize changes.  
9. Apply additions, modifications, and removals.  
10. Invalidate household forecast.  
11. Create audit event.

Plaid’s Sandbox allows test webhook triggering, which should be included in automated integration tests.

## **76\. Integration failure behavior**

When a provider is unavailable:

1. Keep the last verified ledger state.  
2. Mark data as stale.  
3. Reduce forecast confidence.  
4. Disable financial execution.  
5. Continue showing cached forecasts.  
6. Display the last successful synchronization time.  
7. Retry using controlled backoff.  
8. Preserve every failed attempt in operational logs.  
9. Do not create duplicate events after recovery.

# **Part Twelve**

# **Event Architecture**

## **77\. Domain events**

Create internal events:

account\_connected  
account\_sync\_started  
account\_sync\_completed  
transaction\_added  
transaction\_modified  
transaction\_removed  
balance\_updated  
obligation\_detected  
obligation\_confirmed  
income\_forecast\_changed  
forecast\_invalidated  
forecast\_completed  
distress\_detected  
intervention\_generated  
consumer\_approved  
consumer\_rejected  
provider\_approved  
provider\_rejected  
action\_completed  
workflow\_failed

## **78\. Transactional outbox**

Use an outbox table:

event\_outbox  
  id  
  aggregate\_type  
  aggregate\_id  
  event\_type  
  payload  
  status  
  attempt\_count  
  created\_at  
  processed\_at

Database state and outbox event must be committed in the same transaction.

This prevents a database change from succeeding while its downstream event is lost.

## **79\. Idempotency**

All external mutations require:

Idempotency Key

Examples:

1. Plaid webhook processing  
2. Consumer approval  
3. Provider approval  
4. Forecast request  
5. Intervention simulation  
6. Action submission

Repeated requests with the same key must return the original result.

# **Part Thirteen**

# **Security and Compliance Boundaries**

## **80\. Authentication**

Support:

1. Consumer role  
2. Provider reviewer role  
3. Provider administrator role  
4. Internal operator role  
5. Read only auditor role

Every API route must declare permitted roles.

## **81\. Tenant isolation**

Every household record must include a tenant identifier.

Database queries must scope by tenant.

Tests must verify that users from one tenant cannot retrieve another tenant’s:

1. Accounts  
2. Transactions  
3. Forecasts  
4. Interventions  
5. Provider policies  
6. Audit records

## **82\. Sensitive data handling**

1. Do not store raw account credentials.  
2. Encrypt provider access tokens.  
3. Tokenize account identifiers.  
4. Redact sensitive fields from logs.  
5. Do not send raw transaction descriptions to an unrestricted language model.  
6. Use minimum necessary context in explanation prompts.  
7. Record consent version.  
8. Permit integration revocation.  
9. Support data deletion workflows.  
10. Separate model telemetry from personally identifiable data.

## **83\. Artificial intelligence boundaries**

The language model may:

1. Explain  
2. Summarize  
3. Retrieve policy passages  
4. Draft requests  
5. Parse user preferences

The language model may not:

1. Change account balances  
2. Change payment schedules  
3. Calculate monetary totals  
4. Approve interventions  
5. Execute transactions  
6. Create provider capabilities  
7. Invent approval status  
8. Override deterministic constraints

## **84\. Execution modes**

Every action must have an execution mode:

recommendation\_only  
draft\_only  
simulated  
consumer\_executable  
provider\_executable

The hackathon should default to:

simulated

Production execution requires a separately authorized adapter.

# **Part Fourteen**

# **Audit and Replay**

## **85\. Audit requirements**

Every decision records:

1. Household snapshot identifier  
2. Financial event versions  
3. Forecast provider  
4. Forecast provider version  
5. Model version where applicable  
6. Contract version  
7. Consumer constitution version  
8. Provider policy version  
9. Elasticity method version  
10. Resilience method version  
11. Candidate actions  
12. Rejected actions  
13. Selected package  
14. Explanation prompt version  
15. Explanation output  
16. Consumer approval  
17. Provider approval  
18. Execution result  
19. Warning state  
20. Request identifiers

## **86\. Replay**

Replay mode must support:

1. Loading the original snapshot  
2. Running the original forecast provider version where available  
3. Recalculating deterministic results  
4. Regenerating candidate actions  
5. Comparing original and replayed outputs  
6. Reporting divergence

Replay must not modify the original case.

# **Part Fifteen**

# **Testing Strategy**

## **87\. Front end tests**

### **Unit tests**

Test:

1. Currency formatting  
2. Score rendering  
3. Status rendering  
4. Form validation  
5. Timeline event positioning  
6. Intervention selection  
7. Cost disclosure  
8. Approval state

### **Component tests**

Test:

1. Baseline timeline  
2. Shock timeline  
3. Modified timeline  
4. Stale data banner  
5. Missing provider capability  
6. Model unavailable state  
7. Partial intervention failure

### **End to end tests**

Test:

1. Complete consumer demonstration  
2. Consumer rejection  
3. Provider approval  
4. Provider rejection  
5. Model fallback  
6. Plaid synchronization failure  
7. Audit replay

## **88\. Contract tests**

Every fixture must validate against:

1. TypeScript Zod schema  
2. Python Pydantic schema  
3. JSON schema

The same fixture must pass all three validators.

## **89\. Ledger tests**

Test:

1. Duplicate transaction ingestion  
2. Pending to posted transition  
3. Transaction removal  
4. Correcting entry  
5. Transfer linking  
6. Multi account balances  
7. Date boundary behavior  
8. Timezone conversion  
9. Currency mismatch  
10. Reconciliation failure

## **90\. Property tests**

Required properties:

1. A prohibited action is never recommended.  
2. A rejected provider capability is never executed.  
3. An intervention cannot reduce an obligation amount without an explicit rule.  
4. Monetary totals remain exact.  
5. Replay does not mutate original records.  
6. Duplicate webhooks do not create duplicate financial events.  
7. A language model output cannot change calculated values.  
8. A stale forecast cannot be executed without revalidation.  
9. A consumer rejection prevents provider submission.  
10. Missing policy evidence prevents a provider supported claim.

## **91\. Optimizer tests**

Test scenarios:

1. One flexible subscription  
2. One inflexible rent payment  
3. Several flexible obligations  
4. Conflicting consumer rules  
5. Added interest prohibited  
6. Provider policy expired  
7. No valid intervention  
8. Several equally strong interventions  
9. Intervention creates later distress  
10. Model and deterministic forecasts disagree

## **92\. LangGraph tests**

Test:

1. Workflow pauses for consumer approval.  
2. Workflow resumes after approval.  
3. Workflow rejects invalid approval tokens.  
4. Workflow pauses for provider approval.  
5. External calls are not repeated after resumption.  
6. Failed nodes retry safely.  
7. Permanent errors terminate clearly.  
8. Checkpoints restore complete state.  
9. Rejected cases cannot continue to execution.  
10. Audit events are written at each transition.

## **93\. Explanation tests**

Create a fixed evaluation set covering:

1. Normal liquidity warning  
2. Missing data  
3. Provider uncertainty  
4. Added cost  
5. No valid intervention  
6. High model uncertainty  
7. Consumer rule conflict  
8. Provider rejection  
9. Model fallback  
10. Simulation only disclosure

Evaluate:

1. Numerical faithfulness  
2. Action faithfulness  
3. Policy citation correctness  
4. Uncertainty disclosure  
5. Prohibited claim rate

# **Part Sixteen**

# **Observability**

## **94\. Operational metrics**

Track:

1. API latency  
2. API error rate  
3. Forecast latency  
4. Forecast failure rate  
5. Model fallback rate  
6. Webhook processing latency  
7. Duplicate webhook rate  
8. Ledger reconciliation failures  
9. Workflow completion rate  
10. Approval abandonment rate  
11. Explanation validation failure rate  
12. Provider policy retrieval failure rate

## **95\. Business and product metrics**

Track:

1. Distress cases detected  
2. Valid intervention rate  
3. Cases with no available intervention  
4. Consumer approval rate  
5. Provider approval rate  
6. Simulated fee reduction  
7. Simulated missed payment reduction  
8. Resilience Score improvement  
9. Average added cost  
10. Average workflow duration

All hackathon metrics must be labeled simulated.

## **96\. Model integration metrics**

After ReliefFM connection, track:

1. Model response latency  
2. Model availability  
3. Invalid contract responses  
4. Accounting consistency failures  
5. Deterministic disagreement rate  
6. Stale model version rate  
7. Model confidence distribution  
8. Intervention forecast divergence  
9. Model fallback frequency  
10. Model warning frequency

# **Part Seventeen**

# **Deployment**

## **97\. Environments**

Create:

1. Local  
2. Automated test  
3. Demonstration  
4. Staging  
5. Production

The hackathon deployment uses `Demonstration`.

## **98\. Deployment structure**

### **Front end**

Deploy Next.js through Vercel.

### **API**

Deploy FastAPI as a persistent container.

### **Workflow worker**

Deploy as a separate worker process using the same application image.

### **Database**

Use managed PostgreSQL.

### **Redis**

Use managed Redis for workflow coordination, caching, and task dispatch.

### **Model service**

Initially deploy the mock model service.

Replace it with ReliefFM inference after Plan One reaches the integration gate.

## **99\. Feature flags**

Create flags for:

enable\_plaid  
enable\_relief\_fm  
enable\_provider\_dashboard  
enable\_hardship\_drafts  
enable\_provider\_execution  
enable\_audit\_replay  
enable\_shock\_simulator

All financial execution flags must default to disabled.

## **100\. Performance targets**

Demonstration targets:

1. Initial dashboard becomes useful within 2.5 seconds on a normal broadband connection.  
2. Cached forecasts load within 300 milliseconds.  
3. Deterministic forecast completes within 500 milliseconds for a normal household.  
4. Complete intervention generation finishes within 2 seconds.  
5. Shock demonstration recalculates within 2 seconds.  
6. Approval actions respond within 500 milliseconds before any external provider delay.

These are engineering targets rather than guarantees.

# **Part Eighteen**

# **ReliefFM Merge Process**

## **101\. Integration Gate One**

Contract conformance

Plan One must:

1. Accept `ForecastRequestV1`.  
2. Return `ForecastResponseV1`.  
3. Pass shared contract tests.  
4. Return model metadata.  
5. Return warnings.  
6. Reject malformed snapshots clearly.

## **102\. Integration Gate Two**

Accounting validation

Model trajectories must:

1. Begin at the provided starting balance.  
2. Use the requested currency.  
3. Preserve known obligations.  
4. Pass balance reconciliation tolerance.  
5. Contain the requested horizon.  
6. Contain the requested scenario count or explain reduction.

## **103\. Integration Gate Three**

Shadow mode

ReliefFM runs beside the deterministic provider.

The user still sees deterministic results.

Store:

1. Deterministic forecast  
2. ReliefFM forecast  
3. Differences  
4. Validation warnings  
5. Timing  
6. Confidence

Do not switch user visible forecasts until shadow mode is stable.

## **104\. Integration Gate Four**

Limited display

Display ReliefFM uncertainty bands while retaining deterministic known events.

Label:

> Probabilistic projections are generated by ReliefFM. Scheduled obligations and current balances are validated by Relief’s deterministic ledger.

## **105\. Integration Gate Five**

Intervention conditioned simulation

Connect:

POST /model/v1/simulate\_intervention

Compare ReliefFM outcomes against deterministic outcomes.

Flag material disagreements rather than hiding them.

## **106\. Integration Gate Six**

Default model activation

ReliefFM becomes the default forecast provider only after:

1. Contract tests pass.  
2. Accounting validation passes.  
3. Availability target is met.  
4. Latency target is met.  
5. Calibration requirements are met.  
6. Failure fallback is tested.  
7. Audit records contain model metadata.  
8. Deterministic disagreement is understood.

# **Part Nineteen**

# **Implementation Milestones**

## **107\. Milestone One**

Front end complete with fixtures

Deliver:

1. Design system  
2. Consumer dashboard  
3. Financial timeline  
4. Shock simulator  
5. Intervention comparison  
6. Consumer approval  
7. Provider dashboard  
8. Audit page

Exit condition:

The complete demonstration works without a backend.

## **108\. Milestone Two**

Mock API connected

Deliver:

1. FastAPI application  
2. Contract validation  
3. Fixture backed endpoints  
4. Front end query integration  
5. Error states

Exit condition:

The front end no longer imports fixture files directly.

## **109\. Milestone Three**

Ledger operational

Deliver:

1. Database schema  
2. Event ingestion  
3. Deduplication  
4. Account balances  
5. Obligation records  
6. Audit events

Exit condition:

The Sarah demonstration is generated from persisted ledger events.

## **110\. Milestone Four**

Deterministic engine operational

Deliver:

1. Cash flow forecast  
2. Reserve violations  
3. Negative balance detection  
4. Obligation collisions  
5. Forecast invalidation

Exit condition:

Changing Sarah’s paycheck produces a new forecast without manually authored results.

## **111\. Milestone Five**

Intervention engine operational

Deliver:

1. Elasticity profiles  
2. Provider capabilities  
3. Candidate generation  
4. Hard constraints  
5. Simulation  
6. Ranking

Exit condition:

The recommended intervention is generated by system logic rather than a fixture.

## **112\. Milestone Six**

LangChain and LangGraph operational

Deliver:

1. Structured explanation  
2. Policy retrieval  
3. Consumer approval interruption  
4. Provider approval interruption  
5. Workflow persistence  
6. Hardship request draft

Exit condition:

The case can pause, resume, and complete across two users.

## **113\. Milestone Seven**

Plaid Sandbox operational

Deliver:

1. Plaid Link  
2. Token exchange  
3. Transaction synchronization  
4. Webhooks  
5. Ledger import  
6. Failure handling

Exit condition:

A sandbox connection can populate the application and trigger forecast invalidation.

## **114\. Milestone Eight**

ReliefFM ready integration

Deliver:

1. Model gateway  
2. Shared contract tests  
3. Shadow mode  
4. Model metadata display  
5. Deterministic fallback

Exit condition:

ReliefFM can be enabled through one configuration change.

## **115\. Milestone Nine**

Demonstration hardened

Deliver:

1. Seeded demonstration data  
2. Reliable reset command  
3. Backup recorded demonstration  
4. Health checks  
5. Loading states  
6. Error recovery  
7. Compliance disclosures  
8. Audit replay

Exit condition:

The demonstration can be restarted and completed reliably from a fresh deployment.

# **Part Twenty**

# **Twenty Pass Architecture Review**

## **Pass One**

### **Question**

Does the plan preserve the infrastructure framing?

### **Finding**

A consumer dashboard alone could make Relief appear to be another budgeting application.

### **Upgrade**

The provider dashboard, bank adapter layer, provider policy model, approval workflow, and audit infrastructure are treated as first class components.

### **Validation**

The product can be demonstrated from both the consumer and bank perspectives.

## **Pass Two**

### **Question**

Does front end development genuinely happen first?

### **Finding**

Backend schema work could delay visual product progress.

### **Upgrade**

The front end is built completely against validated fixtures and Mock Service Worker before production endpoints.

### **Validation**

The entire demonstration works before database implementation.

## **Pass Three**

### **Question**

Can both workstreams merge without importing each other’s internals?

### **Finding**

Direct model imports would create strong coupling.

### **Upgrade**

All model communication passes through `model_gateway` and shared contracts.

### **Validation**

The mock, deterministic, and ReliefFM providers can be exchanged using configuration.

## **Pass Four**

### **Question**

Does the platform remain useful when ReliefFM fails?

### **Finding**

A model dependent architecture could make the product unavailable.

### **Upgrade**

The deterministic engine is permanent rather than temporary.

### **Validation**

Disconnecting the model service still produces a usable forecast and intervention workflow.

## **Pass Five**

### **Question**

Can language model output alter financial calculations?

### **Finding**

Generated explanations could introduce incorrect numbers.

### **Upgrade**

All arithmetic occurs before LangChain. Explanation outputs are validated against structured facts.

### **Validation**

An explanation containing an unsupported amount is rejected.

## **Pass Six**

### **Question**

Can a model directly trigger a consequential financial action?

### **Finding**

An agentic workflow could accidentally blur prediction and execution.

### **Upgrade**

The model has no execution tools. LangGraph pauses for consumer and provider approval.

### **Validation**

No action reaches execution without valid approval records.

## **Pass Seven**

### **Question**

Is the Elasticity Score sufficiently auditable?

### **Finding**

One unexplained percentage would conceal important differences.

### **Upgrade**

Elasticity is stored as a profile containing flexibility, capability, slack, reversibility, harm, cost, and confidence.

### **Validation**

Every displayed score can be reconstructed from stored components and versioned weights.

## **Pass Eight**

### **Question**

What happens when provider capability is unknown?

### **Finding**

Assigning a default probability would fabricate certainty.

### **Upgrade**

Unknown capability remains explicitly unknown. Only draft requests may proceed.

### **Validation**

No provider supported claim appears without evidence.

## **Pass Nine**

### **Question**

Can duplicate bank events corrupt the ledger?

### **Finding**

Webhook retries are normal and could create duplicate transactions.

### **Upgrade**

Source event uniqueness, idempotency keys, and webhook receipt records are required.

### **Validation**

Processing the same webhook repeatedly produces one ledger result.

## **Pass Ten**

### **Question**

Can the financial timeline produce impossible balances?

### **Finding**

Independent event transformations could break accounting consistency.

### **Upgrade**

Every forecast passes deterministic reconciliation.

### **Validation**

Starting balance plus net event flow equals ending balance within the permitted tolerance.

## **Pass Eleven**

### **Question**

Does the user retain meaningful control?

### **Finding**

A single package approval could hide individual actions.

### **Upgrade**

The user sees every action, cost, approval requirement, and affected obligation.

### **Validation**

The user can approve or reject actions individually where the workflow permits.

## **Pass Twelve**

### **Question**

Can Relief claim to execute unsupported Wells Fargo actions?

### **Finding**

A developer portal does not prove that every desired modification is available.

### **Upgrade**

Wells Fargo is a reference institution, while modification capabilities remain simulated unless exact authorized documentation exists.

### **Validation**

Every provider capability includes evidence and a simulation flag.

## **Pass Thirteen**

### **Question**

Does stale data create dangerous confidence?

### **Finding**

A cached forecast could appear current after an integration failure.

### **Upgrade**

Every forecast contains freshness data, validity limits, warnings, and source status.

### **Validation**

Stale data displays a visible warning and disables execution.

## **Pass Fourteen**

### **Question**

Can the optimizer produce a locally helpful but later harmful intervention?

### **Finding**

Moving a payment could merely shift distress into the following week.

### **Upgrade**

Every intervention is simulated over the full forecast horizon.

### **Validation**

Actions that create greater later distress are rejected or explicitly disclosed.

## **Pass Fifteen**

### **Question**

Can the team reproduce a recommendation?

### **Finding**

Changing policies, prompts, or models could make prior decisions impossible to explain.

### **Upgrade**

Store every version, input, candidate action, rejection reason, and approval.

### **Validation**

Audit replay reconstructs the original decision context.

## **Pass Sixteen**

### **Question**

Is the product accessible without relying on charts?

### **Finding**

A visual timeline alone is inaccessible to some users.

### **Upgrade**

Every chart receives a text summary and table alternative.

### **Validation**

The complete workflow can be navigated with a keyboard and screen reader.

## **Pass Seventeen**

### **Question**

Can one subsystem failure break the entire demonstration?

### **Finding**

Plaid, the language model, or ReliefFM may become unavailable.

### **Upgrade**

Use cached ledger state, deterministic forecasting, templated explanations, and disabled execution.

### **Validation**

The demonstration remains understandable after each dependency is individually disabled.

## **Pass Eighteen**

### **Question**

Can separate developers work without constant merge conflicts?

### **Finding**

Shared files could become a bottleneck.

### **Upgrade**

Use domain directories, strict ownership, generated contracts, and isolated application packages.

### **Validation**

Front end, engine, workflow, integration, and model changes occur in separate directories.

## **Pass Nineteen**

### **Question**

Does the architecture support production growth?

### **Finding**

A hackathon monolith could become difficult to separate later.

### **Upgrade**

Use a modular monolith with explicit module APIs, an outbox, a model gateway, and a separate workflow worker.

### **Validation**

Forecasting, workflows, or integrations can later be extracted without changing public API contracts.

## **Pass Twenty**

### **Question**

Does the final system still tell one clear story?

### **Finding**

The number of technical components could obscure the product value.

### **Upgrade**

All systems support one central event sequence:

Income changes

Forecast changes

Risk appears

Valid interventions are generated

The consumer approves

The provider approves

The safer trajectory is shown

The decision is auditable

### **Validation**

The complete demonstration can be explained and completed in less than three minutes.

# **Final Definition of Done**

Plan Two is complete when:

1. The front end demonstration works from validated fixtures.  
2. The production front end works through backend APIs.  
3. The ledger is immutable and deduplicated.  
4. The deterministic forecast produces reproducible results.  
5. The Financial Resilience Score is inspectable.  
6. Every obligation has a structured elasticity profile.  
7. The optimizer produces valid alternatives.  
8. Every action displays cost and required approvals.  
9. LangChain explanations contain only verified facts.  
10. LangGraph pauses and resumes approval workflows.  
11. Plaid Sandbox can populate the ledger.  
12. Wells Fargo references are visibly simulated where appropriate.  
13. Every recommendation has an audit record.  
14. All consequential actions default to simulation.  
15. The platform functions when ReliefFM is unavailable.  
16. ReliefFM can connect through `model_gateway`.  
17. Contract tests pass across TypeScript, Python, and JSON schema.  
18. Model and deterministic disagreement is preserved rather than hidden.  
19. A fresh deployment can run the complete demonstration.  
20. The architecture can merge with Plan One without structural rework.


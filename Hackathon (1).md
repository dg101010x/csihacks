You are acting as a principal product designer, staff front end engineer, financial systems architect, and interaction design reviewer.

Your task is to completely rebuild the Relief interface so that it expresses the actual product vision from Plan 1\.

Do not merely restyle the existing pages.

The current interface looks like an early administrative dashboard. It contains oversized empty cards, nearly empty screens, generic charts, placeholder route descriptions, internal specification references, weak information hierarchy, and no coherent user journey. The finished product must feel like a polished financial infrastructure platform that could win a major fintech hackathon and plausibly become a real bank integrated product.

Complete the redesign, implementation, testing, and quality assurance. Do not stop after producing a plan.

1\. Product thesis

Relief is not a budgeting application.

Relief is a financial safety infrastructure layer positioned between a consumer's income, accounts, obligations, providers, and personal rules.

Relief continuously performs six functions.

1\. It converts financial activity into a structured event stream.

2\. ReliefFM forecasts future liquidity as a probability distribution rather than a single deterministic balance.

3\. It detects upcoming financial collisions such as insufficient funds, reserve violations, missed obligations, payment timing conflicts, and income disruptions.

4\. It simulates shocks before they occur.

5\. It evaluates intervention packages and estimates the outcome of each intervention.

6\. It allows the consumer to define a financial constitution governing which actions may be proposed, automatically approved, or prohibited.

The interface must make this thesis understandable within thirty seconds.

A judge should immediately understand that Relief does not describe past spending. It protects the user's financial future.

2\. Required first step

Before modifying code, inspect the entire repository.

Review:

1\. Existing routes

2\. Current component hierarchy

3\. State management

4\. API clients

5\. Plan 1 model interfaces

6\. Existing mock data

7\. Current chart implementation

8\. Styling configuration

9\. Test setup

10\. Loading and error states

Create these documents before implementation:

docs/ui\_audit.md

docs/ui\_architecture.md

docs/implementation\_sequence.md

The audit must identify every empty page, dead interaction, inconsistent component, misleading label, duplicated data source, hardcoded value, weak mobile behavior, and accessibility issue.

After creating the documents, immediately implement the redesign.

3\. Nonnegotiable product principles

1\. Future first

The main object in Relief is the user's forecasted financial future, not the current account balance.

2\. Action oriented

Every risk must lead naturally to an explanation, scenario, or intervention.

3\. Uncertainty must be visible

Do not present model estimates as guaranteed facts. Show forecast ranges, confidence, freshness, assumptions, and model provenance.

4\. Calm severity

The interface should communicate urgency without panic. Use clear language, controlled color, and explicit next actions.

5\. User authority

Relief may recommend and prepare actions, but it must clearly distinguish recommendation, approval, provider submission, provider acceptance, and completed execution.

6\. Explainability

Every score, risk, and recommendation must answer:

What changed?

Why does it matter?

What evidence supports it?

What could improve it?

How confident is Relief?

7\. No decorative data

Every chart, metric, label, and status must support a decision.

8\. No empty routes

Every navigation destination must have a complete and useful state.

9\. No internal specification language

Remove text such as route names, phase names, section numbers, implementation comments, and developer facing component names from the visible interface.

10\. No fake integration ambiguity

Synthetic data must remain clearly labeled. It should still behave like a coherent end to end product demonstration.

4\. Information architecture

Replace the current navigation with this structure:

1\. Command Center

The primary financial safety view.

2\. Timeline

The complete forecasted event stream and liquidity trajectory.

3\. Scenario Lab

Shock simulation and comparison.

4\. Interventions

Ranked protection strategies and approval workflow.

5\. Constitution

Consumer rules, permissions, and constraints.

6\. Audit

Decision history, model history, approvals, and execution records.

7\. Providers

Connected financial institutions, capabilities, and provider responses.

8\. Data

Source freshness, lineage, quality, and model inputs.

The application name remains Relief.

The demo user remains Sarah.

The current synthetic institution remains Wells Fargo.

5\. Global application shell

Create a premium application shell with:

1\. A compact left navigation rail

2\. A clear active route state

3\. A persistent environment indicator showing Synthetic Wells Fargo

4\. A persistent system status showing current, delayed, or degraded

5\. A global forecast timestamp

6\. A global scenario state when a shock is active

7\. A command palette for navigation and actions

8\. A notification center for risks, approvals, and provider updates

9\. A user menu with demo reset

10\. Responsive behavior for desktop, tablet, and mobile

The shell should feel dense enough to communicate serious infrastructure, but never cramped.

Do not use huge empty regions.

Do not place every piece of information inside a floating card.

Use page sections, tables, grouped panels, side drawers, and charts intentionally.

6\. Command Center

The Command Center must replace the current generic dashboard.

The first viewport should answer four questions:

1\. Is Sarah financially safe?

2\. What is the next meaningful risk?

3\. When could it happen?

4\. What should Sarah do?

Create the following hierarchy.

6.1 Safety summary

Use a clear summary such as:

Sarah is protected through August 3

or:

Reserve risk begins in 2 days

Show:

Current available balance

Essential reserve

Safe liquidity runway

Next income

Next major obligation

Forecast confidence

Do not make the Financial Resilience Score the only dominant metric.

The score should support the forecast, not replace it.

6.2 Primary forecast

Create a high quality thirty day liquidity forecast.

It must contain:

Median projected balance

Lower forecast boundary

Upper forecast boundary

Essential reserve threshold

Zero balance threshold

Income events

Obligation events

Detected risk windows

Intervention effects when active

Hover details

Accessible table view

The existing three point line chart is unacceptable.

Use daily forecast points and display uncertainty as a visible range.

6.3 Next financial collision

Add a prominent incident panel describing the next predicted issue.

Example:

Rent and auto loan reduce available liquidity below Sarah's essential reserve on July 27\.

Show:

Time until collision

Affected obligations

Projected lowest balance

Probability of reserve violation

Primary causal factors

Confidence

Link to detailed timeline

Link to simulate a shock

Link to view interventions

6.4 Active protections

Show actions already protecting the user, such as:

Reserve floor enabled

Rent modification requires approval

Flexible subscriptions may be paused automatically

Provider negotiation permitted up to a defined limit

6.5 Upcoming events

Show the next five meaningful financial events in chronological order.

Each event must include:

Date

Event type

Provider

Expected amount

Confidence

Classification

Effect on available balance

7\. Timeline

Rebuild Timeline as an interactive financial event graph.

Do not show only a generic line chart.

The timeline must combine:

1\. Forecasted balance

2\. Income events

3\. Obligations

4\. Recurring charges

5\. Reserve thresholds

6\. Risk windows

7\. Interventions

8\. Provider responses

9\. Confidence ranges

Allow seven day, fourteen day, and thirty day views.

Each event should be selectable.

Selecting an event opens a detail panel containing:

Event source

Expected amount

Expected date range

Confidence

Classification

Related account

Model reasoning

Effect on liquidity

Alternative scenarios

Available interventions

Use visual clustering when events occur close together.

Highlight collisions where multiple individually manageable obligations become dangerous because of timing.

8\. Scenario Lab

Rename Shock Simulator to Scenario Lab.

The current single button experience is insufficient.

Create a controlled simulation workspace with:

1\. Baseline scenario

2\. Active scenario

3\. Editable shock inputs

4\. Immediate comparison

5\. Saved scenarios

6\. Recommended intervention packages

Include scenario presets:

Paycheck reduction

Paycheck delay

Unexpected medical expense

Vehicle repair

Rent increase

Duplicate charge

Subscription increase

Temporary income loss

Custom event

For the main demo, preserve this scenario:

Sarah's expected paycheck changes from $2,100.00 to $1,720.00.

The scenario must update:

Forecast trajectory

Liquidity runway

Risk probabilities

Financial Resilience Score

Upcoming collisions

Recommended interventions

The user must see baseline and simulated values together.

Show metric deltas such as:

Lowest projected balance

Days below reserve

Probability of missed obligation

Probability of negative balance

Added intervention cost

Time to recovery

Do not modify the real baseline until the user explicitly applies the scenario.

9\. Interventions

The Interventions page is currently empty and must become one of the strongest parts of the product.

An intervention is not a generic recommendation.

It is a structured package with modeled consequences.

Create ranked intervention cards containing:

1\. Intervention name

2\. Plain language description

3\. Obligations affected

4\. Projected outcome

5\. Residual risk after intervention

6\. Added monetary cost

7\. User effort

8\. Provider modification required

9\. Expected provider acceptance

10\. Model confidence

11\. Reversibility

12\. Constitution compatibility

13\. Reason for ranking

Example intervention packages may include:

Move the auto loan payment date

Split the auto loan payment

Pause StreamCo Plus

Transfer from an eligible reserve account

Request a rent grace period

Create a temporary reserve buffer

Combine multiple actions into one package

Provide comparison mode for the top three packages.

The comparison should answer:

Which package creates the safest result?

Which package costs the least?

Which package requires the least provider modification?

Which package best follows Sarah's constitution?

Show forecast overlays for each package.

Create a staged action process:

Review

Confirm permissions

Submit to provider

Await provider response

Accepted or rejected

Executed

Never label a recommendation as completed before execution is confirmed.

10\. Constitution

The Constitution page must become a real consumer policy interface.

Allow Sarah to write a rule in natural language.

Example:

Never delay rent without asking me first. You may pause subscriptions under $25.00 when my essential reserve is at risk.

Relief must display a structured interpretation before activation.

The structured preview should show:

Trigger

Scope

Permitted actions

Prohibited actions

Approval requirement

Maximum monetary impact

Expiration

Priority

Exceptions

Confidence of interpretation

Show conflicts with existing rules.

Show which current interventions would be allowed or blocked.

Include a simulation tool that tests the rule against the active forecast.

Require explicit confirmation before activation.

Provide recommended starter rules, but do not activate them automatically.

11\. Audit

Create a complete audit ledger.

The ledger must record:

Forecast generation

Model version

Data refresh

Scenario creation

Risk detection

Intervention generation

Rule interpretation

Rule activation

User approval

Provider submission

Provider response

Execution result

Manual override

Each record should contain:

Timestamp

Actor

Action

Reason

Evidence

Before state

After state

Related model version

Related data sources

Related constitution rule

Allow filtering by event type, status, provider, model version, and date.

Selecting a record should open a detailed evidence panel.

12\. Providers

Create a provider operations page for the synthetic Wells Fargo integration.

Show:

Connection status

Accounts available

Last successful synchronization

Supported actions

Unsupported actions

Provider response history

Approval requirements

Expected response times

Current pending requests

Synthetic environment status

Do not use Wells Fargo branding in a way that implies official partnership.

Use clear language stating that the demo uses synthetic Wells Fargo formatted data.

13\. Data and model trust

Create a Data page that exposes system trust information without overwhelming the consumer.

Show:

Data sources

Last refresh time

Coverage period

Missing data

Stale data

Duplicate detection

Event classification confidence

Forecast version

ReliefFM version

Calibration summary

Known limitations

The user should be able to trace a forecasted event back to its source.

14\. ReliefFM integration contract

The front end must remain cleanly connected to Plan 1\.

Do not place forecast logic directly inside React components.

Create a typed adapter layer that supports both live Plan 1 services and coherent synthetic data.

Use domain types similar to:

ForecastEnvelope

ForecastPoint

FinancialEvent

RiskWindow

ScenarioDefinition

ScenarioResult

InterventionPackage

ConstitutionRule

ProviderAction

AuditRecord

ModelEvidence

Every model generated object must include:

Identifier

Generation timestamp

Model version

Confidence

Relevant source references

Freshness

Status

Create one central Relief data client.

When Plan 1 endpoints are unavailable, route requests through a synthetic adapter implementing the same interface.

Do not create separate page specific mock objects.

All pages must derive from the same underlying scenario and event state.

Changing Sarah's paycheck in Scenario Lab must update every dependent screen consistently.

15\. Demo narrative

Build a guided demo mode that tells a coherent story.

Initial state:

Sarah has $2,480.00 in Everyday Checking.

Sarah expects a $2,100.00 payroll deposit on July 31\.

Rent of $1,450.00 is due July 27\.

An auto loan payment of $240.00 is due July 27\.

StreamCo Plus of $15.99 is due July 28\.

A card minimum payment of $75.00 is due August 3\.

Sarah's essential reserve threshold is visible.

Demo sequence:

1\. Start on Command Center and show that Sarah is currently stable.

2\. Open Scenario Lab.

3\. Reduce the next paycheck by $380.00.

4\. Show the forecast distribution changing.

5\. Highlight the newly detected risk window.

6\. Explain which obligations create the collision.

7\. Open Interventions.

8\. Compare the three best packages.

9\. Select the recommended package.

10\. Show the constitution check.

11\. Approve the package.

12\. Show the provider request entering a pending state.

13\. Display the new protected forecast.

14\. Record every step in Audit.

The entire sequence should take less than two minutes and should require no hidden setup.

16\. Visual direction

The visual identity must communicate safety, intelligence, precision, and institutional trust.

It must not resemble:

A generic personal finance template

A cryptocurrency dashboard

A trading terminal

A basic bank account portal

A collection of default component library cards

Use this visual system:

Primary background: soft neutral white, approximately \#F7F8FA

Primary text: deep ink, approximately \#101827

Navigation: dark navy, approximately \#0B1424

Primary action: confident cobalt, approximately \#3165F5

Healthy state: restrained teal, approximately \#24A88B

Warning state: warm amber, approximately \#C98A22

Critical state: controlled coral, approximately \#D95763

Borders: low contrast neutral gray

Typography:

Use a clean interface typeface such as Inter.

Use a restrained monospaced face for amounts, dates, model identifiers, and audit values.

Create a clear scale for:

Page title

Section title

Primary metric

Secondary metric

Body text

Metadata

Do not overuse bold text.

Do not overuse shadows.

Do not make every panel equally prominent.

Use restrained corner radii, strong alignment, consistent spacing, and precise table layouts.

The primary forecast and primary risk should receive the greatest visual weight.

17\. Interaction quality

Implement:

Smooth chart transitions

Clear hover states

Keyboard navigation

Focus indicators

Loading skeletons

Empty states with meaningful next actions

Error recovery

Undo where appropriate

Confirmation for consequential actions

Reduced motion support

Responsive side panels

Accessible chart alternatives

All buttons must work.

All toggles must affect visible state.

All links must lead to complete screens.

18\. Responsive behavior

Test at:

1440 pixel desktop

1280 pixel laptop

1024 pixel tablet landscape

768 pixel tablet

390 pixel mobile

On smaller screens:

Convert navigation into a drawer.

Prioritize the safety summary and next collision.

Allow charts to scroll when necessary.

Convert wide tables into structured event lists.

Keep intervention approval usable.

Do not simply shrink desktop components.

19\. Engineering requirements

Preserve the existing framework unless there is a strong technical reason to change it.

Use the repository's existing conventions.

Create reusable primitives for:

Status badge

Metric display

Evidence indicator

Confidence display

Event row

Risk panel

Forecast chart

Scenario comparison

Intervention card

Rule preview

Audit record

Provider status

Avoid unnecessary dependencies.

Keep financial values precise.

Use explicit currency formatting for en US.

Use deterministic dates in the demo.

Use typed state and typed API boundaries.

Keep model, view, and scenario state separate.

Do not hardcode visual chart coordinates.

Do not duplicate business logic across components.

20\. Testing requirements

Add tests covering:

Scenario state propagation

Forecast rendering

Risk state rendering

Intervention ranking display

Constitution conflict display

Approval workflow

Provider pending state

Audit record creation

Currency formatting

Date formatting

Loading states

Error states

Keyboard interactions

Responsive navigation

Run:

Lint

Type checking

Unit tests

Integration tests

Production build

Fix every error and warning that affects quality.

21\. Quality review process

Perform ten explicit review passes after implementation.

Pass 1: Product thesis

Verify that Relief looks like financial safety infrastructure rather than a budgeting application.

Pass 2: Information hierarchy

Verify that users can identify safety status, next risk, timing, and action immediately.

Pass 3: Visual quality

Remove generic component library appearance, excess whitespace, weak alignment, and inconsistent spacing.

Pass 4: Interaction quality

Test every control and route.

Pass 5: Model trust

Verify confidence, freshness, source, assumptions, and model version visibility.

Pass 6: Scenario coherence

Verify that one scenario updates the entire application consistently.

Pass 7: Intervention workflow

Verify that recommendations, approval, submission, acceptance, and execution remain distinct.

Pass 8: Constitution safety

Verify that rules are parsed, previewed, tested, and explicitly confirmed.

Pass 9: Accessibility and responsiveness

Test keyboard behavior, contrast, screen sizes, focus order, and table alternatives.

Pass 10: Hackathon demonstration

Run the complete Sarah demonstration and remove every source of confusion or delay.

Do not claim a pass is complete without inspecting the actual rendered interface.

22\. Final deliverables

Complete the code changes.

Then provide:

1\. A summary of the previous product problems

2\. A summary of the new architecture

3\. A route by route implementation summary

4\. A list of components created or replaced

5\. A list of tests added

6\. Results from lint, type checking, tests, and build

7\. Screenshots of every major route at desktop width

8\. A complete two minute demo script

9\. Any remaining Plan 1 integration dependencies

10\. The exact files where the synthetic adapter can later be replaced by live ReliefFM services

The work is complete only when every page is functional, the application presents one coherent financial story, and the interface visibly demonstrates prediction, simulation, intervention, consumer control, provider coordination, and auditability.  

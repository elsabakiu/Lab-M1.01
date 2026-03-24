# Cost Analysis

## Objective

This estimate presents a realistic upfront cost view for a medium-sized outpatient clinic that wants to pilot the solution shown in this project. The goal is not to price a full enterprise rollout, but to show what an SME-scale implementation could cost and which cost drivers matter most.

## Scope Assumed

The estimate covers:

- Python preprocessing and KPI generation
- Plotly/Streamlit dashboard deployment for internal stakeholder use
- AI insight generation over operational KPI tables
- n8n workflow setup for reminders and follow-ups
- LangSmith monitoring and evaluation setup
- documentation, testing, and handoff

It does not include:

- a full EMR or EHR integration
- production-grade security review or legal review
- HIPAA compliance implementation
- large-scale cloud infrastructure
- custom patient-facing applications

## Assumptions

- Buyer profile: medium-sized outpatient clinic or ambulatory care provider
- Team size for implementation: one consultant / builder with stakeholder support
- Pilot duration: 4 to 6 weeks for a first usable version
- Users: operations manager, front-desk lead, and clinic leadership
- Data source: one public dataset for prototype plus client operational data later
- Hosting: low-cost internal deployment or simple cloud deployment
- Currency: USD

## Upfront Implementation Estimate

### 1. Discovery, scoping, and requirements alignment

- Estimated effort: 8 to 12 hours
- Estimated cost at $75 to $100/hour: $600 to $1,200

Includes:

- stakeholder alignment
- KPI selection
- workflow scope definition
- source-system review

### 2. Data preparation and KPI modeling

- Estimated effort: 12 to 20 hours
- Estimated cost: $900 to $2,000

Includes:

- raw data inspection
- preprocessing logic
- derived KPI table generation
- validation of synthetic operational fields

### 3. Dashboard development

- Estimated effort: 14 to 24 hours
- Estimated cost: $1,050 to $2,400

Includes:

- Streamlit interface build
- Plotly chart design
- layout refinement
- stakeholder-ready narrative views

### 4. AI insight layer

- Estimated effort: 10 to 16 hours
- Estimated cost: $750 to $1,600

Includes:

- deterministic insight logic
- optional OpenAI enhancement wiring
- response validation
- risk-report generation

### 5. n8n workflow implementation

- Estimated effort: 8 to 14 hours
- Estimated cost: $600 to $1,400

Includes:

- workflow assembly
- Airtable and messaging integration
- routing logic
- testing and demo setup

### 6. LangSmith monitoring and evaluation

- Estimated effort: 6 to 10 hours
- Estimated cost: $450 to $1,000

Includes:

- dataset creation
- evaluation-case setup
- trace review
- monitoring documentation

### 7. Documentation, testing, and handoff

- Estimated effort: 6 to 10 hours
- Estimated cost: $450 to $1,000

Includes:

- setup instructions
- cost and timeline documentation
- demo rehearsal
- stakeholder handoff notes

## Estimated Total Upfront Cost

Using the assumptions above, a realistic pilot estimate is:

- Low end: $4,800
- Likely range: $6,000 to $8,500
- High end: $10,600

For a bootcamp-style MVP using mostly free tools and local execution, the out-of-pocket software spend can stay low. The main cost driver is implementation time rather than infrastructure.

## Budget Scenarios

### Option 1: Portfolio-style MVP

- Best for: coursework, internal demo, or early concept validation
- Delivery style: mostly local execution with lightweight documentation
- Estimated upfront cost: $2,500 to $4,500
- Expected software spend in month 1: $0 to $75

What is usually included:

- core preprocessing
- a working Streamlit dashboard
- deterministic insight generation
- a simplified workflow mock or partially configured n8n flow

What is usually limited:

- production readiness
- integration depth
- monitoring breadth
- stakeholder training and change management

### Option 2: SME pilot

- Best for: a medium-sized clinic evaluating real operational value
- Delivery style: stakeholder-ready proof of value with documentation and monitoring
- Estimated upfront cost: $6,000 to $8,500
- Expected software spend in month 1: $60 to $340

What is usually included:

- full KPI pipeline
- refined dashboard experience
- deterministic AI insight layer with optional LLM enhancement
- working n8n pilot workflow
- basic LangSmith evaluation and trace review
- handoff materials and demo support

### Option 3: Expanded pilot with production hardening

- Best for: a clinic preparing for broader operational rollout
- Delivery style: stronger controls, more support, and additional implementation depth
- Estimated upfront cost: $9,000 to $15,000+
- Expected software spend in month 1: $200 to $700+

Typical added scope:

- live source-system integration
- access control and audit expectations
- more robust deployment and alerting
- additional workflows, channels, or departments
- extra testing and stakeholder enablement

## Tooling And Platform Costs

### Low-cost prototype / demo setup

- Streamlit: $0 if run locally
- Plotly: $0
- Python libraries: $0
- n8n: $0 to low monthly cost on self-hosted or starter plan
- LangSmith: free tier or low pilot usage, depending on evaluation volume
- OpenAI API: low variable cost for optional wording enhancement only
- Airtable: free or starter-tier cost, depending on records and collaborators

Estimated software cost for a prototype month:

- approximately $0 to $150

### SME pilot in limited production

Estimated monthly operating software cost:

- hosting: $20 to $80
- n8n cloud or equivalent workflow hosting: $20 to $60
- Airtable or equivalent ops database: $20 to $100
- LangSmith and API usage: $20 to $100 depending on activity

Estimated monthly operating range:

- approximately $60 to $340

## First-Year Cost View

For a buyer evaluating whether the pilot is financially reasonable, it helps to separate one-time implementation from recurring operating cost.

### Example first-year total cost of ownership

- Portfolio-style MVP: about $2,500 to $5,400
- SME pilot: about $6,720 to $12,580
- Expanded pilot: about $11,400 to $23,400+

These ranges combine:

- upfront implementation effort
- 12 months of low-to-moderate tooling and API usage
- light ongoing maintenance

This keeps the project in a range that is materially lower than a traditional enterprise analytics rollout, which is one reason the pilot is attractive for an SME buyer.

## API Cost Considerations

This project is intentionally designed so the core logic still works without paid LLM calls.

That means:

- preprocessing runs locally
- KPI summaries are deterministic
- the agent can generate deterministic insights without API usage
- the dashboard does not depend on external inference to load

Optional LLM spend is therefore controllable. For an SME pilot, this is important because it limits financial risk while still demonstrating AI value.

## Maintenance Estimate

Expected ongoing support needs:

- data schema adjustments
- dashboard tweaks
- workflow credential maintenance
- monitoring review
- periodic prompt or insight tuning

Estimated maintenance effort:

- 3 to 6 hours per month

Estimated maintenance cost:

- $225 to $600 per month at the same rate assumption

## ROI Framing For Stakeholders

The strongest financial case for this type of pilot is usually operational rather than technical.

Potential value levers include:

- fewer missed appointments through better reminder targeting
- better provider slot utilization
- faster daily decision-making for front-desk and operations leads
- reduced manual effort in compiling summaries and follow-up lists

Illustrative example:

- if a clinic prevents only a small number of no-shows per week
- and each recovered appointment slot has meaningful operational value
- the pilot can begin to justify itself within a few months

This is not a claim of guaranteed ROI. It is a practical way to explain why a modest pilot can be worth testing before a larger rollout.

## Cost Risks

The main cost escalation risks are:

- connecting to real clinical systems instead of CSV-based or Airtable-based demo data
- adding compliance, access control, and audit requirements
- moving from proof of concept to patient-facing automation
- increasing workflow volume or channel complexity
- requiring stronger monitoring, alerting, and support coverage

## Conclusion

For a medium-sized clinic, this is a credible low-risk AI pilot because:

- the initial implementation cost is modest compared with enterprise health-tech projects
- the running costs can remain small
- the solution demonstrates measurable operational value before larger investments are needed
- the deterministic fallback design reduces exposure to uncontrolled API spend

Recommended commercial framing:

- position this as a pilot or proof-of-value engagement
- keep phase 1 tightly scoped around appointment operations
- measure no-show reduction, reminder coverage, and operational visibility improvements before expanding scope

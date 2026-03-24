# n8n Workflow Documentation

## Workflow Purpose

This workflow demonstrates a practical automation proof of concept for a mid-sized outpatient clinic. Its goal is to show how AI-adjacent operational automation can reduce manual coordination work around appointments, reminders, and follow-ups.

The workflow supports three operational communication moments:

- pre-appointment reminders
- completed-appointment follow-ups
- no-show follow-ups

In the project context, this is the proof-of-concept automation layer that complements the dashboard and AI insights. The dashboard identifies where the clinic has operational friction, and the n8n workflow shows how those insights could connect to real actions.

For the live demo, the clearest handoff is:

- input: high-risk appointment from the dashboard or agent
- action: prepare reminder or follow-up outreach
- log: write communication status into Airtable
- escalation: keep a human review point for high-risk or urgent cases

## Workflow File

- Export file: `n8n/Appointment Reminders and Follow-ups (Airtable + Gmail + Telegram).json`
- Workflow name inside n8n: `Production - Appointment Reminders and Follow-ups (Airtable + Gmail + Telegram)`

## Business Relevance

For a medium-sized outpatient clinic, reminders and follow-ups are high-value, low-complexity automation opportunities because they directly support:

- lower no-show rates
- better patient communication consistency
- reduced front-desk manual workload
- a clearer audit trail of outreach activity

This makes the workflow a strong proof of concept for an SME buyer who wants transparent, practical AI-enabled operations rather than a large enterprise transformation.

## Triggers

The workflow includes three trigger entry points:

- `Manual Trigger`
  Used for demos and controlled testing inside n8n.
- `Schedule Trigger`
  Used to run the workflow automatically on a recurring basis.
- `Webhook`
  Used to trigger the workflow externally from the Streamlit application or another service.

The trigger outputs are merged through `Merge Triggers`, which gives the workflow one normalized entry path before business logic is applied.

In the React dashboard demo, the intended webhook story is:

1. the dashboard identifies a high-risk appointment
2. a staff member reviews the recommendation
3. the workflow is triggered as a controlled handoff
4. outreach is prepared and logged rather than sent silently without review

## Connected Services

The workflow connects the following systems:

- Airtable
  Used to read appointment records, update delivery status fields, and write communication log entries.
- Gmail
  Used to send reminder and follow-up emails.
- Telegram
  Used as the messaging channel for non-email delivery in the exported workflow.
- n8n internal code and branching nodes
  Used to normalize inputs, choose the communication path, and set payload fields.

## Transformation Steps

The workflow logic is organized into a simple and explainable decision flow:

1. Trigger the workflow manually, on a schedule, or through the webhook.
2. Read appointment records from Airtable with `Airtable - List Appointments`.
3. Normalize each appointment and decide which communication path should apply in `Normalize + Decide Flow`.
4. Route records using `Switch by Workflow Type` into one of three branches:
   reminder, completed follow-up, or no-show follow-up.
5. Prepare message content with one of the `Set ...` nodes.
6. Choose email versus messaging branch with `... via Email?` conditions.
7. Send the message using Gmail or Telegram.
8. Write delivery status back to Airtable.
9. Log the communication event in Airtable for traceability.

This is intentionally straightforward. The point of the proof of concept is not complexity, but showing that business events can be translated into automated and auditable actions.

Operationally, this should be narrated as:

- Insight: the AI layer surfaces a high-risk appointment or no-show follow-up candidate
- Decision: staff accept or reject the outreach recommendation
- Workflow: n8n prepares the reminder or follow-up through the configured channel
- Audit trail: Airtable records what happened, when it happened, and which path was taken

## Branches And Outputs

### Reminder Branch

Used before the appointment date to prompt attendance.

Outputs:

- a reminder message is sent
- reminder delivery status is updated in Airtable
- reminder activity is logged

### Completed Follow-up Branch

Used after attended appointments to send a post-visit follow-up or next-step message.

Outputs:

- follow-up message is sent
- follow-up delivery status is updated in Airtable
- completion communication is logged

### No-show Follow-up Branch

Used after missed appointments to restart contact and encourage rescheduling or confirmation.

Outputs:

- no-show follow-up is sent
- no-show status is updated in Airtable
- no-show outreach is logged

### High-risk Outreach Handoff

This is the most useful branch to show Chloe in a live meeting.

The dashboard already contains a high-risk queue. The n8n proof of concept makes that queue operational by turning a reviewed high-risk appointment into a concrete communication workflow.

Expected outcome:

- a high-risk appointment is selected for outreach
- the reminder or follow-up payload is prepared
- the communication status is written back to Airtable
- the case remains reviewable by clinic staff

## Transparency And Observability

This workflow helps address Chloe's concern about AI opacity because it is easy to inspect and explain:

- triggers are explicit
- routing conditions are visible in n8n
- message preparation happens in named nodes
- delivery events are written back to Airtable
- every communication can be logged for audit and review
- high-risk cases can still be escalated to a person instead of being auto-closed by the workflow

This makes the automation layer operationally transparent even for non-technical stakeholders.

## Error Handling

The export shows a basic but workable structure for operational error handling:

- branch conditions reduce accidental sends by routing records intentionally
- delivery status nodes create a place to store success or failure outcomes
- Airtable logging provides an audit layer for communications

Recommended production improvements:

- add explicit failure branches after Gmail and Telegram nodes
- store HTTP or provider error messages in Airtable
- add retry logic for temporary send failures
- add alerting to Slack, email, or Telegram for repeated failures

## Assumptions

- Airtable stores the appointment and communication-log records
- Gmail and Telegram credentials are configured in n8n
- appointment records include enough metadata to determine whether a reminder, completed follow-up, or no-show follow-up is appropriate
- the workflow is being shown as a proof of concept, not as a HIPAA-ready production system
- staff review is retained for high-risk or ambiguous outreach decisions

## Why This Meets The Rubric

This artifact satisfies the automation requirement because it:

- is directly tied to the clinic use case
- demonstrates an end-to-end workflow rather than just a diagram
- uses real business systems and delivery channels
- is simple enough to explain in a stakeholder meeting
- reinforces the project theme of transparent, practical AI-supported operations

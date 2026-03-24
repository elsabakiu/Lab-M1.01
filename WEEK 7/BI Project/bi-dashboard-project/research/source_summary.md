# Research And Source Summary

## Purpose

This file provides a Git-friendly summary of the research basis for the project. The repository already contains exported PDF research notes, but this markdown version makes the logic, sources, and assumptions easier to review directly in GitHub.

## Chosen Scenario

- Sector: Healthcare
- Company size: Medium SME
- Business context: outpatient clinic or ambulatory care provider
- Business focus: appointment operations, no-shows, provider utilization, wait times, and reminder effectiveness

## Core Business Question

How can a medium-sized clinic use transparent, operational AI tools to reduce no-shows, improve staff utilization, and make daily operations easier to manage?

## Primary Data Source

- File: `data/raw/KaggleV2-May-2016.csv`
- Dataset: Medical Appointment No Shows / Kaggle source file used in this project
- Rows: 110,527
- Columns:
  - `PatientId`
  - `AppointmentID`
  - `Gender`
  - `ScheduledDay`
  - `AppointmentDay`
  - `Age`
  - `Neighbourhood`
  - `Scholarship`
  - `Hipertension`
  - `Diabetes`
  - `Alcoholism`
  - `Handcap`
  - `SMS_received`
  - `No-show`

## Why This Dataset Was Chosen

This dataset is relevant because it already contains the core signals needed to build a no-show and appointment-operations prototype:

- scheduled date versus appointment date
- attendance outcome
- reminder signal through `SMS_received`
- patient segmentation fields such as age and neighborhood
- enough volume to create meaningful operational patterns

It is a good fit for a healthcare SME demo because it supports the project’s main use cases without requiring a complex clinical data integration.

## Observed Versus Synthesized Fields

The raw dataset does not contain a full operational clinic schema. To build a usable BI and AI demo, some fields were derived deterministically in preprocessing.

### Directly observed in source data

- patient identifier
- appointment identifier
- scheduling timestamp
- appointment date
- gender
- age
- neighborhood
- scholarship flag
- hypertension flag
- diabetes flag
- alcoholism flag
- handicap flag
- reminder received flag
- no-show label

### Deterministically derived for prototype use

- `weekday`
- `hour`
- `lead_time_days`
- `attended`
- `specialty`
- `provider`
- `visit_duration_min`
- `wait_time_min`
- provider capacity fields
- utilization support fields

## Why Synthetic Fields Were Necessary

The public dataset is useful, but it is not a full clinic operations dataset. It does not include:

- provider names
- operational specialty assignments
- wait time values
- visit duration values
- provider capacity values

These fields were synthesized to create a plausible non-clinical operations scenario. They should be treated as prototype assumptions, not as real operational facts from a clinic.

## Research Themes Used In The Project

The research work behind the project focused on five operational themes:

- appointment demand and scheduling pressure
- no-show patterns by weekday, hour, and specialty
- provider utilization imbalance
- reminder effectiveness and communication timing
- AI transparency through deterministic logic, evaluation, and workflow traceability

## Opportunity Summary

The main opportunities identified for a medium-sized clinic were:

- no-show analysis and targeted reminder strategy
- provider utilization balancing
- daily operational insight generation
- workflow automation for reminders and follow-ups
- transparent monitoring of AI-generated operational recommendations

## Risk Summary

The main risks identified were:

- public data does not perfectly represent a real clinic
- synthetic fields may overstate realism if not clearly labeled
- reminder effects can be confounded by targeting bias
- stakeholders may distrust AI if recommendations are not grounded in visible evidence
- operational automation needs auditability and human review

## Use Cases Selected

The project centers on three core use cases:

1. No-show pattern analysis
2. Provider utilization optimization
3. Daily operations insight generation

These use cases were chosen because they fit the data available, are meaningful for a medium-sized clinic, and are easy to explain to a skeptical business stakeholder.

## Supporting Research Artifacts In This Folder

The following exported research documents also support the project:

- `research/sector_research.docx.pdf`
- `research/opportunities_risks.docx.pdf`
- `research/use_cases.docx.pdf`

This markdown file is the concise source-of-truth summary for reviewers who want the core reasoning without opening the PDFs.

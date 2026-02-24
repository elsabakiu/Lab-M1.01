# n8n Workflow Lab Report

## Feature Brief → Linear Epic & Stories Generator

------------------------------------------------------------------------

# 1. Context

For this lab, I analyzed and documented a production-style n8n workflow
that I built:

**"Feature Brief to Linear Epic and Stories Generator."**

The purpose of this workflow is to automate the transformation of a raw
feature brief into:

-   A structured feature intent
-   Strategic positioning metadata
-   A fully generated epic
-   5--8 well-structured user stories
-   Validated acceptance criteria and NFRs
-   Automatically created Epic and Issues in Linear

The workflow combines:

-   LLM chains
-   Structured output parsers
-   Custom validation logic
-   Multi-source contextual enrichment
-   Conditional routing
-   External system integration (Linear)

Architecturally, it represents an AI-orchestrated product operations
pipeline rather than a simple automation.

------------------------------------------------------------------------

# 2. Workflow Overview

## High-Level Flow

    Webhook
      ↓
    Intent Extraction (AI)
      ↓
    Context Enrichment (Slack Docs + Market Snapshot)
      ↓
    Strategic Classification (AI)
      ↓
    Story Generation (AI)
      ↓
    Structured Parsing
      ↓
    Custom Validation Layer
      ↓
    Conditional Routing
      ↓
    Linear Epic + Stories Creation

------------------------------------------------------------------------

# 3. n8n Node Reference Table

  -------------------------------------------------------------------------------------------------------------------------
  Node          Role           Parameters         What It Does      JSON Input      JSON Output            Key
                                                                                                           Transformation
  ------------- -------------- ------------------ ----------------- --------------- ---------------------- ----------------
  Webhook       Trigger        POST               Receives feature  HTTP body       n8n item               HTTP → JSON
  Trigger                      /story-generator   brief                                                    

  Feature       AI Chain       Prompt + Model     Extracts          feature_brief   problem_statement,     Text →
  Intent                                          structured intent                 users, etc.            structured
  Extractor                                                                                                object

  Intent Output Structured     JSON schema        Enforces schema   LLM output      Validated object       LLM → validated
  Parser        Parser                            compliance                                               JSON

  Slack Doc     Code           Custom JS          Matches feature   feature_brief   internal_context       Keyword scoring
  Loader                                          to Slack docs                                            

  Market        Code           Static data        Returns           ---             competitor_features,   Static
  Snapshot Node                                   competitor &                      themes                 enrichment
                                                  review data                                              

  Merge         Orchestrator   3 inputs           Combines intent + Multiple        Unified object         Multi-stream
  (Combine                                        context           streams                                merge
  Contexts)                                                                                                

  Strategic     AI Chain       Prompt + model     Classifies        Combined        positioning JSON       Context →
  Framing Chain                                   strategic         context                                strategy
                                                  metadata                                                 

  Parse         Code           JSON extraction    Sanitizes LLM     LLM response    Clean JSON             String →
  Strategic                                       strategy output                                          structured
  Output                                                                                                   

  Prepare Story Set            Field assignments  Aggregates full   Multiple        Single context object  Object
  Context                                         context           objects                                composition

  Story         AI Chain       Strict             Generates epic +  Full context    Structured JSON        Context →
  Generator                    instructions       stories                                                  backlog
  Chain                                                                                                    

  Story Output  Structured     Story schema       Enforces          LLM output      Validated stories      Schema
  Parser        Parser                            epic/story                                               validation
                                                  structure                                                

  Parse Story   Code           JSON cleanup       Removes markdown, Raw LLM output  Clean story object     Sanitization
  JSON                                            parses JSON                                              

  Validator     Code           Custom JS rules    Validates format, Stories object  valid + errors         QA enforcement
                                                  NFRs,                                                    
                                                  hallucinations                                           

  IF (Check     Router         Boolean condition  Routes            Validation      Routed output          Conditional
  Validation)                                     success/failure   result                                 branching

  Create Epic   Integration    Title +            Creates Epic in   Epic JSON       Linear Epic            n8n → Linear
  (Linear)                     description        Linear                                                   

  Prepare Split Set            Epic metadata      Prepares story    Epic + stories  Enhanced object        Adds epic_id
  Data                                            splitting                                                

  Split Stories SplitOut       field=stories      Splits stories    Stories array   One item per story     Array → items
                                                  into items                                               

  Create        Integration    Title +            Creates issues in Story JSON      Linear issue           n8n → Linear
  Stories                      description        Linear                                                   
  (Linear)                                                                                                 

  Success       Set            Response fields    Formats success   Linear output   API response           Final formatting
  Response                                        payload                                                  

  Format        Set            Error formatting   Formats           Errors          Error response         Error handling
  Validation                                      validation                                               
  Errors                                          failure                                                  
  -------------------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

# 4. JSON Data Flow Analysis

## Stage 1 --- Feature Brief → Intent

Input:

    { "feature_brief": "..." }

Output:

    {
      problem_statement,
      users,
      business_goal,
      unknowns[]
    }

Transformation:\
Unstructured text → structured product intent.

------------------------------------------------------------------------

## Stage 2 --- Context Enrichment

Two enrichment sources:

1.  Internal Slack documentation (keyword-scored)
2.  Market analysis (competitor features + review themes)

Transformation: Intent + Internal Context + Market Context → Combined
Context Object

------------------------------------------------------------------------

## Stage 3 --- Strategic Framing

The LLM classifies the feature into:

-   competitive_positioning
-   impact_type
-   mvp_critical
-   strategic_priority

This adds decision-layer metadata before story generation.

------------------------------------------------------------------------

## Stage 4 --- Epic & Story Generation

The LLM generates:

-   Epic
-   5--8 user stories
-   Acceptance criteria (testable)
-   Technical notes
-   Dependencies
-   NFRs (specific metrics)
-   Risks

Output is strictly structured via Output Parser.

------------------------------------------------------------------------

## Stage 5 --- Custom Validation Layer

The Validator checks:

-   Story count (4--8)
-   Proper user story format
-   Testable acceptance criteria
-   Measurable NFRs
-   No hallucinated systems
-   Required fields completeness

This creates a QA guardrail before writing to Linear.

------------------------------------------------------------------------

## Stage 6 --- Linear Integration

If valid: - Create Epic - Split stories - Create Issues - Return success
metadata

If invalid: - Return structured error response

------------------------------------------------------------------------

# 5. Most Commonly Used Node Types

-   AI Chain (LLM orchestration)
-   Code (custom transformation & validation)
-   Set (data shaping)
-   Merge (context aggregation)
-   IF (conditional routing)
-   Output Parser (schema enforcement)
-   Linear (external integration)
-   SplitOut (array handling)

------------------------------------------------------------------------

# 6. Common Patterns Observed

## AI Guardrail Pattern

LLM → Structured Parser → Custom Validator → IF

## Context-Enriched Prompt Pattern

Raw input → Internal docs → Market data → Strategy → Generation

## Safe External Write Pattern

Validate before API write.

------------------------------------------------------------------------

# 7. Node Selection Guidelines

  Scenario                        Node Choice
  ------------------------------- ------------------
  Enforce JSON schema             Output Parser
  Clean malformed LLM output      Code
  Custom QA logic                 Code
  Combine multiple data sources   Merge
  Split array into items          SplitOut
  Conditional execution           IF
  External system write           Integration node



# 8. Debugging Observations

Common debugging checkpoints:

-   Ensure correct JSON path references (`{{ $json.field }}`)
-   Validate array access before `.join()`
-   Inspect execution data at each node
-   Verify structured parser schema matches expected output
-   Check validation errors before integration

------------------------------------------------------------------------ 

# 9. Conclusion

This workflow demonstrates how structured prompting, contextual
enrichment, validation logic, and conditional routing can be combined
into a reliable, production-ready AI automation system.

It represents AI-native product operations automation rather than simple
task automation.

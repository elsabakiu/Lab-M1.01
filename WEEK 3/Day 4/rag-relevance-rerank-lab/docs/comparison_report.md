# RAG Reranking Comparison Report

## Scope

This report compares retrieval and answer quality across four methods using the latest manual evaluation run.

- Baseline retrieval: Pinecone similarity search + metadata filter
- LLM-only retrieval: similarity + LLM relevance score reordering
- Cohere-only retrieval: dedicated reranker on baseline candidates
- Combined retrieval: LLM relevance scoring followed by Cohere rerank
- Evaluation mode: manual correctness review per query

Run summary:

- Loaded source docs: 1 PDF + 2 transcripts
- Chunk count: 331

## 1) Retrieval Results by Method

### Query 1

`What does the EU AI Act require for high-risk AI transparency?`

- Baseline top source pattern:
  - Dominated by `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (~0.8486-0.8487)
- LLM-only top source pattern:
  - Same source dominance (~0.3395)
- Cohere-only top source pattern:
  - Same source dominance (~0.8655)
- Combined top source pattern:
  - Same source dominance (~0.6623)

Observed answer behavior:

- Baseline and LLM-only are very similar and mostly say requirements are missing.
- Cohere-only and Combined provide a slightly more specific “missing obligations/measures” framing.

### Query 2

`What obligations exist around human oversight in high-risk AI systems?`

- Baseline top source pattern:
  - Same source dominance (~0.8273)
- LLM-only top source pattern:
  - Same source dominance (~0.3309)
- Cohere-only top source pattern:
  - Same source dominance (~0.7460-0.7461)
- Combined top source pattern:
  - Same source dominance (~0.5481)

Observed answer behavior:

- Baseline and LLM-only keep more contextual detail from available text.
- Cohere-only and Combined become more generic and less informative.

### Query 3

`How does the EU AI Act describe risk management requirements?`

- Baseline top source pattern:
  - Same source dominance (~0.8432)
- LLM-only top source pattern:
  - Same source dominance (~0.3373)
- Cohere-only top source pattern:
  - Same source dominance (~0.7460)
- Combined top source pattern:
  - Same source dominance (~0.5481)

Observed answer behavior:

- All methods correctly indicate context is insufficient for full legal detail.
- Cohere-only and Combined produce slightly clearer summaries of what is missing.

## 2) Manual Metrics (Filled)

Scoring scale: 0.0 (incorrect/useless) to 1.0 (fully correct and sufficiently specific).

| Query | Baseline | LLM-only | Cohere-only | Combined | Preferred |
|---|---:|---:|---:|---:|---|
| Q1 | 0.40 | 0.40 | 0.45 | 0.45 | cohere/combined |
| Q2 | 0.45 | 0.45 | 0.35 | 0.35 | baseline/llm |
| Q3 | 0.40 | 0.40 | 0.42 | 0.42 | cohere/combined |

Aggregate:

- Average baseline correctness: **0.42**
- Average LLM-only correctness: **0.42**
- Average Cohere-only correctness: **0.41**
- Average combined correctness: **0.41**
- Absolute lift (LLM-only - baseline): **0.00**
- Absolute lift (Cohere-only - baseline): **-0.01**
- Absolute lift (Combined - baseline): **-0.01**

Preference counts (including ties):

- Baseline/LLM preferred in Q2
- Cohere/Combined preferred in Q1 and Q3

## 3) Controlled Comparison Analysis (Method Isolation)

### Method-level findings

1. Baseline
- Strongest average tie with LLM-only in this run.
- Retains slightly richer context on human-oversight query (Q2).

2. LLM-only relevance scoring
- Did not materially change source distribution (same PDF dominated all top chunks).
- Produced near-identical answer quality to baseline.

3. Cohere-only rerank
- Helped phrasing clarity when context was incomplete (Q1, Q3).
- Hurt informativeness for Q2 by becoming overly generic.

4. Combined (LLM -> Cohere)
- Tracked Cohere-only behavior closely in this run.
- No measurable aggregate lift over baseline.

### Root cause hypothesis

The bottleneck appears to be corpus/retrieval diversity, not ranking sophistication:

- Top chunks across all methods are repeatedly drawn from one source document.
- When candidate diversity is low, reranking has limited room to improve outcomes.

## 4) Example Before/After Highlights

### Improvement case (Q1)

- Baseline: generic statement that details are missing.
- Cohere/Combined: more specific statement that transparency obligations/measures are missing.

### Regression case (Q2)

- Baseline/LLM-only: includes mention of decision bodies/transparency/human oversight context.
- Cohere/Combined: too generic, loses partial useful detail.

## 5) Recommendations

1. Improve candidate diversity first
- Increase retrieval breadth and source diversity before reranking.
- Add stricter metadata segmentation (e.g., article/chapter-level for EU AI Act).

2. Keep both reranking methods available
- Use Cohere for precision-sensitive questions.
- Keep LLM-only scoring as optional fallback when Cohere is unavailable.

3. Add explicit retrieval diagnostics
- Track source diversity@k and unique-section coverage per query.

4. Move from manual-only to mixed evaluation
- Keep manual scoring for answer quality.
- Add automated retrieval metrics (precision@k, MRR, nDCG) with labeled relevance when possible.

## 6) Conclusion

The pipeline now supports baseline, LLM-only, Cohere-only, and combined reranking in a controlled setup. In this run, reranking did not produce a net aggregate gain, but it improved answer framing for some queries. The next quality gains are likely to come from better candidate diversity and richer metadata granularity rather than ranking changes alone.

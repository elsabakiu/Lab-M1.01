# RAG Reranking Comparison Report

## Scope

This report compares retrieval and answer quality before and after reranking in the Week 3 / Day 4 RAG pipeline using the latest manual evaluation run.

- Baseline retrieval: Pinecone similarity search + metadata filter
- Reranked retrieval: Cohere rerank (dedicated reranker)
- Evaluation mode: manual correctness review per query

## 1) Retrieval Results Before/After Reranking

All results below are copied from the run output.

### Query 1

`What does the EU AI Act require for high-risk AI transparency?`

- Baseline top sources:
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8487)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8486)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8486)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8486)
- Reranked top sources:
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8655)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8655)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8655)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8655)
- Change summary:
  - No source diversity change; same source dominates baseline and reranked sets.
  - Reranker increased combined scores but did not materially change retrieval composition.

### Query 2

`What obligations exist around human oversight in high-risk AI systems?`

- Baseline top sources:
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8273)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8273)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8273)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8273)
- Reranked top sources:
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.7461)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.7460)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.7460)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.7460)
- Change summary:
  - No meaningful ranking diversity changes.
  - Reranked answer became more conservative, but not more specific.

### Query 3

`How does the EU AI Act describe risk management requirements?`

- Baseline top sources:
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8432)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8432)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8432)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.8432)
- Reranked top sources:
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.7460)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.7460)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.7460)
  - `Living_Repository_AI_Literacy_Practices_Update_16042025_UqmogIt2HpLVokdcuzJL4mDvHk8_112203.pdf` (0.7460)
- Change summary:
  - Retrieval remained concentrated on one source.
  - Reranked answer included slightly more contextual detail but still lacked direct legal requirement text.

## 2) Performance Metrics

The current pipeline uses manual scoring (no labeled relevance dataset yet).

### Manual metrics table

| Query | Baseline correctness (0-1) | Reranked correctness (0-1) | Preferred |
|---|---:|---:|---|
| Q1 | 0.40 | 0.45 | reranked |
| Q2 | 0.45 | 0.35 | baseline |
| Q3 | 0.40 | 0.42 | reranked |

### Optional aggregate metrics

- Average baseline correctness: 0.42
- Average reranked correctness: 0.41
- Absolute lift (reranked - baseline): -0.01
- Preference rate for reranked answers: 66.7% (2/3 queries)

## 3) Analysis: When Reranking Helps Most

Reranking tends to help most when:

- top similarity results are semantically close but not directly answering the query
- legal language is dense and requires selecting the most specific chunk
- multiple chunks mention related policy terms but only one contains the actual requirement detail

Reranking tends to help less when:

- baseline retrieval is already highly precise
- query is very narrow and metadata filtering already isolates the right section

Observed in this lab run:

- Reranking helped when it made answers more explicit about missing context (Q1, Q3).
- Reranking hurt when it became too generic and removed partial useful detail (Q2).
- The biggest bottleneck was not ranking quality but corpus coverage:
  - retrieval repeatedly returned chunks from the same `Living_Repository...pdf`
  - answers often stated that key legal details were missing from context.

## 4) Example Queries and Answers Showing Improvement

### Example A

- Query: `What does the EU AI Act require for high-risk AI transparency?`
- Baseline answer: `...context does not specify the exact requirements...`
- Reranked answer: `...does not detail transparency obligations or specific measures...`
- Why reranked is better:
  - Slightly clearer about what is missing (obligations/measures), not just that details are absent.

### Example B

- Query: `What obligations exist around human oversight in high-risk AI systems?`
- Baseline answer: `...decision bodies... ensure transparency, human oversight, and AI literacy...`
- Reranked answer: `...context does not specify the obligations...`
- Why reranked is better:
  - In this case, reranked was not better; baseline retained more concrete context references.

## 5) Recommendations: When to Use Reranking

Use reranking when:

- precision matters (legal/compliance/regulated domains)
- retrieved chunks are long and semantically similar
- you can afford extra latency and token/API cost

Skip or limit reranking when:

- latency/cost constraints are strict
- baseline retrieval quality is already consistently high
- query set is simple and narrow with strong metadata filters

Practical recommendation for this project:

1. Keep metadata filtering always on (`category`, `doc_type`, `section` when possible).
2. Retrieve a broader candidate set (already implemented) and rerank top candidates.
3. Improve corpus coverage for EU AI Act requirements (current evidence is dominated by one source file).
4. Keep manual correctness checks for development and small test sets.
5. Move to automated evaluation (precision@k, recall@k, MRR) once labeled relevance data is available.

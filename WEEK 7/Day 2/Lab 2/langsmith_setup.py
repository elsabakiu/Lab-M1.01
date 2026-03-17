"""
Week 7 Day 2 Lab 2 — LangSmith Setup
Project: Databricks - Dolly Dataset

Steps:
  1. Environment setup & client initialisation
  2. Traced OpenAI call
  3. Load dataset, extract & structure examples, data quality checks
  4. Create LangSmith dataset and upload examples
  5. Implement and smoke-test target function
  6. Set up evaluators (correctness + faithfulness, LLM-as-judge)
  7. Execute evaluation experiment and collect results
  9. Analyse results — aggregate metrics, error analysis, insights
"""

import json
import os
from pathlib import Path
from statistics import mean, median, stdev

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LangSmith configuration — must be set before any client initialises
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://eu.api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "Databricks - Dolly Dataset"

from langsmith import Client, traceable
from langsmith.evaluation import evaluate
from langsmith.wrappers import wrap_openai
from openai import OpenAI
from datasets import load_dataset


# ---------------------------------------------------------------------------
# Step 1 — Client initialisation
# ---------------------------------------------------------------------------

LANGSMITH_ENDPOINT = "https://eu.api.smith.langchain.com"

langsmith_client = Client(api_url=LANGSMITH_ENDPOINT)
openai_client = wrap_openai(OpenAI())

print(f"LangSmith client connected. Project: {os.environ['LANGSMITH_PROJECT']}")
print(f"Endpoint: {LANGSMITH_ENDPOINT}")


# ---------------------------------------------------------------------------
# Step 2 — Traced OpenAI call
# ---------------------------------------------------------------------------

@traceable(name="weather-assistant")
def ask_weather(question: str) -> str:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a friendly travel assistant who helps with weather information."},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Step 3 — Extract and structure examples from the dataset
# ---------------------------------------------------------------------------

def load_qa_examples(n: int = 20) -> list[dict]:
    """
    Load the Databricks Dolly 15k dataset, filter for closed_qa examples,
    and return the first `n` structured records.

    Each record has:
      inputs:
        question  — the question to put to the model
        context   — the source passage the answer must come from
      outputs:
        answer    — the ground-truth answer
      metadata:
        category  — always "closed_qa" for this slice
        source    — original dataset name
        has_context — whether a non-empty context was provided
    """
    print("\nLoading dataset …")
    ds = load_dataset("databricks/databricks-dolly-15k", split="train")
    qa_examples = [x for x in ds if x["category"] == "closed_qa"][:n]

    structured = []
    for raw in qa_examples:
        structured.append({
            "inputs": {
                "question": raw["instruction"].strip(),
                "context":  raw["context"].strip(),
            },
            "outputs": {
                "answer": raw["response"].strip(),
            },
            "metadata": {
                "category":    raw["category"],
                "source":      "databricks/databricks-dolly-15k",
                "has_context": bool(raw["context"].strip()),
            },
        })

    return structured


def quality_check(examples: list[dict]) -> list[dict]:
    """
    Remove examples that fail any quality gate:
      - question must be non-empty
      - answer must be non-empty
      - context must be present (closed_qa requires a passage)
    Prints a summary and returns the cleaned list.
    """
    before = len(examples)
    clean = [
        ex for ex in examples
        if ex["inputs"]["question"]
        and ex["outputs"]["answer"]
        and ex["metadata"]["has_context"]
    ]
    removed = before - len(clean)
    print(f"\nData quality check:")
    print(f"  Total loaded  : {before}")
    print(f"  Removed       : {removed}  (empty question / answer / context)")
    print(f"  Remaining     : {len(clean)}")
    assert len(clean) >= 10, "Need at least 10 valid examples for evaluation."
    return clean


def save_examples(examples: list[dict], path: Path) -> None:
    """Persist examples to JSON so later steps can load them without re-downloading."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(examples, indent=2, ensure_ascii=False))
    print(f"\nExamples saved → {path}  ({len(examples)} records)")


def load_examples(path: Path) -> list[dict]:
    """Load previously saved examples from JSON."""
    examples = json.loads(path.read_text())
    print(f"Examples loaded ← {path}  ({len(examples)} records)")
    return examples


def summarise(examples: list[dict]) -> None:
    """Print a short preview of the structured examples."""
    print(f"\nDataset structure ({len(examples)} examples):")
    print("  Fields — inputs: question, context")
    print("         — outputs: answer")
    print("         — metadata: category, source, has_context\n")
    for i, ex in enumerate(examples[:3], 1):
        q = ex["inputs"]["question"]
        a = ex["outputs"]["answer"]
        print(f"  [{i}] Q: {q[:80]}{'…' if len(q) > 80 else ''}")
        print(f"       A: {a[:80]}{'…' if len(a) > 80 else ''}")
    if len(examples) > 3:
        print(f"  … and {len(examples) - 3} more examples.")


# ---------------------------------------------------------------------------
# Step 4 — Create LangSmith dataset and upload examples
# ---------------------------------------------------------------------------

DATASET_NAME        = "Dolly Databricks - Closed QA Evaluation Set"
DATASET_DESCRIPTION = (
    "20 closed-QA examples drawn from the Databricks Dolly 15k dataset. "
    "Each example contains a question, a context passage, and a ground-truth "
    "answer. Intended for evaluating extractive QA models."
)


def get_or_create_dataset(client: Client, name: str, description: str):
    """
    Return an existing LangSmith dataset by name, or create a new one.
    Avoids duplicate datasets on repeated runs.
    """
    existing = [ds for ds in client.list_datasets() if ds.name == name]
    if existing:
        dataset = existing[0]
        print(f"\nDataset already exists — reusing: '{dataset.name}'  (id: {dataset.id})")
    else:
        dataset = client.create_dataset(
            dataset_name=name,
            description=description,
        )
        print(f"\nDataset created: '{dataset.name}'  (id: {dataset.id})")
    return dataset


def upload_examples(client: Client, dataset, examples: list[dict]) -> None:
    """
    Upload examples to a LangSmith dataset.
    Skips upload if the dataset already contains the same number of examples.
    """
    existing_count = client.read_dataset(dataset_id=dataset.id).example_count or 0
    if existing_count >= len(examples):
        print(f"Dataset already contains {existing_count} examples — skipping upload.")
        return

    client.create_examples(
        dataset_id=dataset.id,
        inputs   =[ex["inputs"]  for ex in examples],
        outputs  =[ex["outputs"] for ex in examples],
        metadata =[ex["metadata"] for ex in examples],
    )
    print(f"Uploaded {len(examples)} examples to '{dataset.name}'.")


def verify_dataset(client: Client, dataset) -> None:
    """Print a confirmation summary after upload."""
    refreshed = client.read_dataset(dataset_id=dataset.id)
    count = refreshed.example_count or 0
    print(f"\nVerification:")
    print(f"  Dataset name  : {refreshed.name}")
    print(f"  Description   : {refreshed.description}")
    print(f"  Example count : {count}")
    print(f"  LangSmith URL : https://eu.smith.langchain.com/datasets/{refreshed.id}")


# ---------------------------------------------------------------------------
# Step 5 — Target function
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a precise question-answering assistant.
Answer the question using ONLY the information provided in the context.
If the answer cannot be found in the context, reply with "I don't know."
Keep your answer concise and accurate — one or two sentences at most."""


@traceable(name="closed-qa-target")
def answer_question(inputs: dict) -> dict:
    """
    Target function for closed-QA evaluation.

    Parameters
    ----------
    inputs : dict
        Must contain:
          - "question" (str): the question to answer
          - "context"  (str): the passage the answer must come from

    Returns
    -------
    dict
        {"answer": str}  — model response, or an error message string.
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,          # deterministic for reproducible evals
            max_tokens=256,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Context:\n{inputs['context']}\n\n"
                    f"Question: {inputs['question']}"
                )},
            ],
        )
        return {"answer": response.choices[0].message.content.strip()}
    except Exception as e:
        return {"answer": f"ERROR: {e}"}


def fetch_examples_from_langsmith(client: Client, dataset_name: str, n: int = 0) -> list[dict]:
    """
    Fetch examples directly from a LangSmith dataset.

    Parameters
    ----------
    client       : LangSmith Client
    dataset_name : name of the dataset to fetch from
    n            : number of examples to return (0 = all)

    Returns
    -------
    List of dicts with keys "inputs", "outputs", "metadata"
    """
    ls_examples = list(client.list_examples(dataset_name=dataset_name))
    if n:
        ls_examples = ls_examples[:n]

    structured = [
        {
            "inputs":   ex.inputs,
            "outputs":  ex.outputs  or {},
            "metadata": ex.metadata or {},
        }
        for ex in ls_examples
    ]
    print(f"Fetched {len(structured)} examples from LangSmith dataset '{dataset_name}'")
    return structured


def smoke_test(client: Client, dataset_name: str, n: int = 3) -> None:
    """Fetch `n` examples from LangSmith and run the target function on them."""
    examples = fetch_examples_from_langsmith(client, dataset_name, n=n)
    print(f"\n--- Step 5 smoke test ({len(examples)} examples from LangSmith) ---")
    for i, ex in enumerate(examples, 1):
        inputs          = ex["inputs"]
        expected_answer = ex["outputs"].get("answer", "")
        result          = answer_question(inputs)

        print(f"\n[{i}] Q : {inputs['question'][:100]}")
        print(f"     Expected : {expected_answer[:100]}")
        print(f"     Got      : {result['answer'][:100]}")


# ---------------------------------------------------------------------------
# Step 6 — Evaluators (LLM-as-judge)
# ---------------------------------------------------------------------------
#
# Evaluator contract expected by langsmith.evaluation.evaluate():
#   def evaluator(
#       inputs:            dict,  # dataset example inputs
#       outputs:           dict,  # target function outputs
#       reference_outputs: dict,  # dataset example expected outputs
#   ) -> dict:
#       # must return at least {"key": str, "score": float}
#       # optionally:         {"key": ..., "score": ..., "comment": str}
#
# Two evaluators are defined:
#   1. correctness  — does the answer match the reference?  (0.0 / 0.5 / 1.0)
#   2. faithfulness — is the answer grounded in the context? (0.0 / 1.0)
# ---------------------------------------------------------------------------

CORRECTNESS_JUDGE_PROMPT = """\
You are a strict grader for a closed-book QA system.

Question         : {question}
Reference answer : {reference_answer}
Model answer     : {model_answer}

Score the model answer for CORRECTNESS compared to the reference:
  1.0 — fully correct; captures all key information from the reference
  0.5 — partially correct; captures some but not all key information
  0.0 — incorrect, missing, or contradicts the reference

Respond with valid JSON only, no extra text:
{{"score": <0.0|0.5|1.0>, "reasoning": "<one concise sentence>"}}"""

FAITHFULNESS_JUDGE_PROMPT = """\
You are auditing a closed-book QA system for hallucination.

Context      : {context}
Model answer : {model_answer}

Score the model answer for FAITHFULNESS to the context:
  1.0 — every claim in the answer is supported by the context
  0.0 — the answer contains at least one claim not supported by the context

Respond with valid JSON only, no extra text:
{{"score": <0.0|1.0>, "reasoning": "<one concise sentence>"}}"""


def _call_judge(prompt: str) -> dict:
    """Call gpt-4o-mini with a judge prompt and parse the JSON response."""
    raw = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=128,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(raw.choices[0].message.content)


@traceable(name="eval-correctness")
def correctness_evaluator(
    inputs: dict,
    outputs: dict,
    reference_outputs: dict,
) -> dict:
    """
    LLM-as-judge: is the model answer correct relative to the reference?

    Returns
    -------
    {"key": "correctness", "score": 0.0|0.5|1.0, "comment": str}
    """
    result = _call_judge(CORRECTNESS_JUDGE_PROMPT.format(
        question         = inputs.get("question", ""),
        reference_answer = reference_outputs.get("answer", ""),
        model_answer     = outputs.get("answer", ""),
    ))
    return {
        "key":     "correctness",
        "score":   float(result.get("score", 0.0)),
        "comment": result.get("reasoning", ""),
    }


@traceable(name="eval-faithfulness")
def faithfulness_evaluator(
    inputs: dict,
    outputs: dict,
    reference_outputs: dict,  # noqa: ARG001 — required by interface
) -> dict:
    """
    LLM-as-judge: is the model answer grounded in the provided context?

    Returns
    -------
    {"key": "faithfulness", "score": 0.0|1.0, "comment": str}
    """
    result = _call_judge(FAITHFULNESS_JUDGE_PROMPT.format(
        context      = inputs.get("context", ""),
        model_answer = outputs.get("answer", ""),
    ))
    return {
        "key":     "faithfulness",
        "score":   float(result.get("score", 0.0)),
        "comment": result.get("reasoning", ""),
    }


def demo_evaluators(client: Client, dataset_name: str, n: int = 2) -> None:
    """Fetch `n` examples from LangSmith and run both evaluators on them."""
    examples = fetch_examples_from_langsmith(client, dataset_name, n=n)
    print(f"\n--- Step 6 evaluator demo ({len(examples)} examples from LangSmith) ---")
    for i, ex in enumerate(examples, 1):
        model_output = answer_question(ex["inputs"])
        c = correctness_evaluator(ex["inputs"], model_output, ex["outputs"])
        f = faithfulness_evaluator(ex["inputs"], model_output, ex["outputs"])
        print(f"\n[{i}] Q           : {ex['inputs']['question'][:80]}")
        print(f"     Model out   : {model_output['answer'][:80]}")
        print(f"     Correctness : {c['score']}  — {c['comment']}")
        print(f"     Faithfulness: {f['score']}  — {f['comment']}")


# ---------------------------------------------------------------------------
# Step 7 — Execute evaluation experiment and collect results
# ---------------------------------------------------------------------------

EXPERIMENT_PREFIX = "gpt-4o-mini-closed-qa"


def run_experiment(
    client: Client,
    dataset_name: str,
    experiment_prefix: str,
    max_concurrency: int = 2,
):
    """
    Run a full evaluation experiment via LangSmith's evaluate() framework.

    evaluate() pulls every example from the dataset, passes inputs to
    answer_question(), then passes (inputs, outputs, reference_outputs) to
    each evaluator.  All traces, scores, and comments are stored in LangSmith
    automatically and grouped under a single named experiment.

    Parameters
    ----------
    client            : LangSmith Client
    dataset_name      : name of the LangSmith dataset to evaluate against
    experiment_prefix : human-readable name prefix for this run
    max_concurrency   : parallel requests (keep low to respect rate limits)

    Returns
    -------
    ExperimentResults object from LangSmith
    """
    print(f"\n--- Step 7: running experiment '{experiment_prefix}' ---")
    print(f"  Dataset     : {dataset_name}")
    print(f"  Concurrency : {max_concurrency}")
    print("  (This may take a few minutes …)\n")

    results = evaluate(
        answer_question,
        data=dataset_name,
        evaluators=[correctness_evaluator, faithfulness_evaluator],
        experiment_prefix=experiment_prefix,
        client=client,
        max_concurrency=max_concurrency,
    )

    return results


def print_results(results) -> None:
    """
    Print a summary of experiment results to the terminal.

    Collects per-example scores and computes aggregate means for each metric.
    Also prints the LangSmith UI URL for the full experiment view.
    """
    scores: dict[str, list[float]] = {}

    for result in results:
        # Each result has .evaluation_results.results — a list of EvaluationResult
        for er in result.get("evaluation_results", {}).get("results", []):
            key = er.key
            if er.score is not None:
                scores.setdefault(key, []).append(er.score)

    print("\nExperiment results summary:")
    if scores:
        for key, vals in scores.items():
            avg = sum(vals) / len(vals)
            print(f"  {key:20s}  avg={avg:.2f}  n={len(vals)}")
    else:
        print("  (no scores returned — check LangSmith UI for details)")

    # The experiment URL is available on the results object
    experiment_url = getattr(results, "_experiment_url", None)
    if experiment_url:
        print(f"\n  LangSmith experiment : {experiment_url}")
    else:
        print(f"\n  View results at : https://eu.smith.langchain.com")


# ---------------------------------------------------------------------------
# Step 9 — Analyse results
# ---------------------------------------------------------------------------

def build_records(results) -> list[dict]:
    """
    Flatten the ExperimentResults object into a plain list of dicts, one per
    example, with all scores and metadata in a single row.

    Each record contains:
      question          — the input question
      reference_answer  — the ground-truth answer from the dataset
      model_answer      — what the target function returned
      correctness       — correctness score (0.0 / 0.5 / 1.0)
      faithfulness      — faithfulness score (0.0 / 1.0)
      correctness_comment  — judge reasoning for correctness
      faithfulness_comment — judge reasoning for faithfulness
      source            — metadata.source (if present)
    """
    records = []
    for row in results:
        run     = row.get("run", {})
        example = row.get("example", {})
        evals   = row.get("evaluation_results", {}).get("results", [])

        inputs  = getattr(example, "inputs",  None) or run.get("inputs",  {})
        ref_out = getattr(example, "outputs", None) or {}
        mod_out = getattr(run,     "outputs", None) or {}
        meta    = getattr(example, "metadata", None) or {}

        scores   = {er.key: er.score   for er in evals if er.score   is not None}
        comments = {er.key: er.comment for er in evals if er.comment is not None}

        records.append({
            "question":             inputs.get("question", ""),
            "reference_answer":     ref_out.get("answer", ""),
            "model_answer":         mod_out.get("answer", ""),
            "correctness":          scores.get("correctness"),
            "faithfulness":         scores.get("faithfulness"),
            "correctness_comment":  comments.get("correctness", ""),
            "faithfulness_comment": comments.get("faithfulness", ""),
            "source":               meta.get("source", ""),
        })
    return records


def _metric_stats(values: list[float]) -> dict:
    """Return basic stats for a list of float scores."""
    if not values:
        return {}
    return {
        "n":      len(values),
        "mean":   mean(values),
        "median": median(values),
        "stdev":  stdev(values) if len(values) > 1 else 0.0,
        "min":    min(values),
        "max":    max(values),
    }


def aggregate_metrics(records: list[dict]) -> None:
    """Print mean / median / stdev / min / max for each metric, plus pass rates."""
    print("\n── Aggregate metrics ──────────────────────────────────────────────")

    for metric, threshold in [("correctness", 0.5), ("faithfulness", 1.0)]:
        vals = [r[metric] for r in records if r[metric] is not None]
        if not vals:
            print(f"  {metric}: no scores found")
            continue

        s = _metric_stats(vals)
        pass_rate = sum(1 for v in vals if v >= threshold) / len(vals)

        print(f"\n  {metric.upper()}  (pass = score ≥ {threshold})")
        print(f"    n        : {s['n']}")
        print(f"    mean     : {s['mean']:.3f}")
        print(f"    median   : {s['median']:.3f}")
        print(f"    stdev    : {s['stdev']:.3f}")
        print(f"    min/max  : {s['min']:.1f} / {s['max']:.1f}")
        print(f"    pass rate: {pass_rate:.0%}  ({sum(1 for v in vals if v >= threshold)}/{len(vals)})")

        # Score distribution
        buckets = {0.0: 0, 0.5: 0, 1.0: 0}
        for v in vals:
            bucket = min(buckets.keys(), key=lambda b: abs(b - v))
            buckets[bucket] += 1
        dist = "  ".join(f"{k:.1f}→{n}" for k, n in sorted(buckets.items()))
        print(f"    dist     : {dist}")


def error_analysis(records: list[dict], n_worst: int = 5) -> None:
    """Print the lowest-scoring examples with judge reasoning."""
    print("\n── Error analysis — lowest correctness scores ──────────────────────")

    scored = [r for r in records if r["correctness"] is not None]
    worst  = sorted(scored, key=lambda r: r["correctness"])[:n_worst]

    for i, r in enumerate(worst, 1):
        print(f"\n  [{i}] Score: {r['correctness']:.1f}")
        print(f"       Q        : {r['question'][:100]}")
        print(f"       Expected : {r['reference_answer'][:100]}")
        print(f"       Got      : {r['model_answer'][:100]}")
        print(f"       Reason   : {r['correctness_comment']}")
        print(f"       Faith    : {r['faithfulness']}  — {r['faithfulness_comment']}")


def performance_insights(records: list[dict]) -> None:
    """Summarise key findings and failure patterns."""
    print("\n── Performance insights ────────────────────────────────────────────")

    # Correctness vs faithfulness comparison
    both = [r for r in records
            if r["correctness"] is not None and r["faithfulness"] is not None]

    faithful_wrong = [r for r in both
                      if r["faithfulness"] >= 1.0 and r["correctness"] < 0.5]
    unfaithful     = [r for r in both if r["faithfulness"] < 1.0]
    perfect        = [r for r in both
                      if r["correctness"] >= 1.0 and r["faithfulness"] >= 1.0]

    print(f"\n  Total examples evaluated : {len(records)}")
    print(f"  Fully correct + faithful : {len(perfect)}  ({len(perfect)/len(records):.0%})")
    print(f"  Faithful but wrong answer: {len(faithful_wrong)}"
          f"  — model stayed on-context but missed the point")
    print(f"  Hallucinated (unfaithful): {len(unfaithful)}"
          f"  — model introduced unsupported claims")

    # Common failure mode
    if len(faithful_wrong) > len(unfaithful):
        print("\n  → Primary failure mode: COMPREHENSION"
              " (model reads context but answers incorrectly)")
    elif unfaithful:
        print("\n  → Primary failure mode: HALLUCINATION"
              " (model adds claims not in context)")
    else:
        print("\n  → No dominant failure mode detected")

    # Best performers
    high = [r for r in records
            if r["correctness"] is not None and r["correctness"] >= 1.0]
    print(f"\n  Perfect correctness (1.0): {len(high)}/{len(records)} examples")


def analyse_results(results) -> list[dict]:
    """
    Run the full analysis pipeline on experiment results.

    Parameters
    ----------
    results : ExperimentResults from run_experiment()

    Returns
    -------
    List of flattened record dicts for further use.
    """
    print("\n═══════════════════════════════════════════════════════════════════")
    print("  STEP 9 — Results Analysis")
    print("═══════════════════════════════════════════════════════════════════")

    records = build_records(results)
    print(f"\n  Records extracted: {len(records)}")

    if not records:
        print("  No records to analyse — check that the experiment completed.")
        return records

    aggregate_metrics(records)
    error_analysis(records, n_worst=3)
    performance_insights(records)

    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

EXAMPLES_FILE = Path(__file__).parent / "qa_examples.json"

if __name__ == "__main__":

    """
    # Step 2 demo
    answer = ask_weather("What's the weather like in San Francisco and Tokyo?")
    print(f"\nWeather assistant: {answer}")

    """ 

    # Step 3
    examples = load_qa_examples(n=20)
    examples = quality_check(examples)
    save_examples(examples, EXAMPLES_FILE)
    summarise(examples)

    # Step 4
    dataset = get_or_create_dataset(langsmith_client, DATASET_NAME, DATASET_DESCRIPTION)
    upload_examples(langsmith_client, dataset, examples)
    verify_dataset(langsmith_client, dataset)

     
    # Step 5
    smoke_test(langsmith_client, DATASET_NAME, n=3)

    # Step 6
    demo_evaluators(langsmith_client, DATASET_NAME, n=2)

    # Step 7
    results = run_experiment(
        langsmith_client,
        DATASET_NAME,
        EXPERIMENT_PREFIX,
        max_concurrency=2,
    )
    print_results(results)

    # Step 9
    analyse_results(results)

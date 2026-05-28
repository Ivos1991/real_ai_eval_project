# REAL.dev AI Evaluation Harness

This repository is a small runnable home-assignment project for the REAL.dev AI Evaluation Engineer role. It implements Option B: a local eval harness for a Data Field extraction use case.

The selected field is `Lease Expiration Date` from commercial real estate lease text.

## Assignment Alignment

Selected option: **Option B - Build a tiny runnable eval harness**.

Selected REAL feature: **Data Field**. Option B does not repeat "choose one feature" as explicitly as Options A and C, but the assignment frames all options around REAL's listed features. This harness uses Data Field because structured extraction is a practical fit for deterministic checks plus judgment-style evaluation.

Requirement coverage:

- Loads a small fabricated dataset: 8 lease-expiration cases in `cases/lease_expiration_cases.json`.
- Runs a mock system-under-test: `MockLeaseExpirationExtractor`.
- Scores with rule-based metrics: schema, normalized value, citation, null handling, and confidence checks.
- Scores with an LLM-as-judge style metric: `MockLLMJudge`, implemented locally with a transparent rubric and no external calls.
- Outputs a CI-friendly pass/fail signal: pytest fails on critical metric failures or low total score.
- Produces reports: Allure evidence plus `reports/eval_summary.json` and `reports/eval_summary.csv`.
- Includes lightweight observability: OpenTelemetry spans, with optional trace evidence attached to Allure.
- Documents next steps: see Production Evolution below.

## Problem Framing

AI systems are not well covered by exact assertions alone. A final answer can be formatted differently, supported by weak citations, valid but uncertain, or correct only because it guessed. Useful evaluation needs measurable quality signals around correctness, grounding, schema validity, ambiguity handling, and regression detection.

## Why Data Field Extraction

Data Field extraction is structured enough to support deterministic checks, but still realistic for non-deterministic AI behavior. The harness combines normalized date matching and schema checks with a rubric-style judge that looks at grounding, reasoning quality, ambiguity handling, and hallucination risk.

## Architecture

```text
cases/lease_expiration_cases.json
        |
        v
LeaseExpirationCaseLoader
        |
        v
MockLeaseExpirationExtractor  <---- api/ExtractionApiClient boundary for future real API calls
        |
        v
RuleBasedEvaluator + MockLLMJudge
        |
        v
pytest quality gate + Allure attachments
        |
        v
reports/eval_summary.json and reports/eval_summary.csv
```

OpenTelemetry spans wrap case loading, mock extraction, the optional API client boundary, deterministic scoring, mock judge scoring, and report generation. The default exporter writes traces to the console. The harness can also attach per-case trace evidence to Allure.

## Metrics

Deterministic metrics:

- `schema_validity`: validates the extraction result against a Pydantic schema.
- `exact_or_normalized_value_match`: compares expected and actual dates after normalization.
- `citation_present`: requires citations for non-null answers and no citations for null answers.
- `citation_supports_answer`: uses RapidFuzz to check that the citation supports the expected clause.
- `expected_null_handling`: checks missing or irrelevant documents return null with low confidence.
- `confidence_range_valid`: ensures confidence is between 0 and 1.

Mock rubric metric:

- `MockLLMJudge` is a local rubric simulator, not a real LLM call.
- It scores groundedness, reasoning quality, ambiguity handling, and hallucination risk.
- In production this interface could be replaced by LangSmith, Braintrust, DeepEval, Ragas, Phoenix, or a custom LLM judge service.

## Handling Non-Determinism

The harness avoids brittle exact-only assertions by using normalized matching, a total-score threshold, citation similarity thresholds, confidence checks, and rubric scoring. Critical deterministic metrics still fail the test immediately because schema validity, null handling, and grounded correctness are release-blocking for this field.

Expected field values are normalized to ISO date format for scoring. Citation text intentionally preserves the original source wording and date format from the fabricated document, including scanned-text recognition errors where relevant.

## CI Usage

Pytest acts as the quality gate. A failing critical metric, failing mock judge, or total score below the configured threshold causes a non-zero pytest exit code.

```powershell
pip install -r requirements.txt
pytest
pytest -m eval --alluredir=reports/allure-results --clean-alluredir
allure serve reports/allure-results
```

Trace evidence mode is controlled by `EVAL_TRACE_EVIDENCE_MODE`:

- `failure_only` attaches per-case OpenTelemetry spans only for failed eval cases. This is the default and the CI setting.
- `always` attaches trace JSON for every case, useful for local review.
- `off` disables Allure trace attachments while keeping normal tracing available.

Local example:

```powershell
$env:EVAL_TRACE_EVIDENCE_MODE="always"
pytest -m eval --alluredir=reports/allure-results --clean-alluredir
allure serve reports/allure-results
```

Summary files are written to:

```text
reports/eval_summary.json
reports/eval_summary.csv
```

## Why `requests`

The current system under test is local and mocked so the project runs without API keys. The `api/ExtractionApiClient` class shows the production boundary where `requests` can call a real extraction endpoint later. In production this client should add retries, timeouts, auth, richer error handling, and possibly `httpx` if async support is required.

## Configuration

Runtime options can be set through environment variables or an `.env` file. See `.env.example` for the full list.

The total score uses a weighted blend:

- `EVAL_DETERMINISTIC_SCORE_WEIGHT`, default `0.70`
- `EVAL_JUDGE_SCORE_WEIGHT`, default `0.30`

The defaults intentionally prioritize deterministic correctness and grounding checks while still giving the mock judge influence over ambiguity and hallucination-risk signals.

## Production Evolution

- Replace `MockLeaseExpirationExtractor` with a real REAL API call.
- Replace `MockLLMJudge` with LangSmith, Braintrust, DeepEval, Ragas, Phoenix, or a custom judge.
- Build golden datasets from expert-reviewed lease cases.
- Add baseline comparisons such as this week versus last week.
- Add a human-in-the-loop feedback loop from lawyers, accountants, and architects.
- Track traces with OpenTelemetry plus Phoenix, LangSmith, or another observability backend.
- Add cost and latency monitoring per extraction and per eval run.

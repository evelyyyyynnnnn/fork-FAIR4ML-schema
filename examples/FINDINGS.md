# Applying FAIR4ML 0.1.0 to four real models — what held and what did not

Target vocabulary: **FAIR4ML 0.1.0**, https://w3id.org/fair4ml/0.1.0
(2 classes, 22 properties), read from `release/0.1.0/fair4ml.jsonld`.

## Method

Four trained models from two public repositories were described as FAIR4ML
cards, converted to JSON-LD with `tools/yaml2jsonld.py`, and checked against
the published vocabulary with `tools/validate_card.py`. Every value comes from
the originating project's machine-written `results/latest-real.json`; none was
entered by hand.

| Model | Kind | Card |
|---|---|---|
| ICU early-warning (hypotension, 4 h) | logistic regression | `cards/icu_early_warning_model_card.yaml` |
| Realised-volatility forecaster (^GSPC) | LSTM | `cards/volatility_lstm_model_card.yaml` |
| Portfolio allocation agent | DQN | `cards/portfolio_dqn_model_card.yaml` |
| Portfolio allocation agent | SAC | `cards/portfolio_sac_model_card.yaml` |

Projects were excluded where no model is trained, even where the project is
about ML: a rule-based empathy scorer, an authored (not fitted) credit policy,
a leakage-measurement library, and a Pareto-frontier triage study. Four is the
honest count, not a selected one.

## Finding 1 — 10 of 22 properties carried the load

Across four models from two different domains, 12 of the 22 properties were
never populated:

    codeSampleSnippet   ethicalSocial     evaluatedMLModel   evaluationDataset
    evaluationSoftware  extrinsicEvaluation  fineTunedFrom   hasCO2eEmissions
    hasEvaluation       intendedUse       legal              validatedOn

Some are genuinely inapplicable. Others — `fineTunedFrom`, `hasCO2eEmissions`,
`validatedOn` — were *considered and deliberately left empty*. **The published
JSON-LD cannot tell those two cases apart.** See Finding 3.

## Finding 2 — the common case is a field with a reason for being empty

Fields declared in the card but parsing to null:

| Field | Cards affected |
|---|---|
| `referencePublication` | 4/4 |
| `processorRequirements` | 4/4 |
| `GPURequirements` | 4/4 |
| `hasCO2eEmissions` | 4/4 |
| `validatedOn` | 4/4 |
| `successorOf` | 4/4 |
| `funder` | 4/4 |
| `fineTunedFromModel` | 4/4 |
| `evaluationResults` | **3/4** |
| `parameterSize` | 1/4 |

Each carries a short human reason — "no external validation cohort was
available", "trained from scratch", "unfunded". `yaml.safe_load` returns
`None` and the reason is gone.

**`evaluationResults` is null in three of four models.** Not an edge case:

* **LSTM volatility** — metrics computed, withheld: the feature scaler was
  fitted with `fit_transform` across the whole series, so the test split saw
  its own future. Validation R² (0.931) exceeded training R² (0.878).
* **DQN and SAC** — metrics computed, withheld: `config['data']['train_test_split']`
  was declared in every config and read by no code, so training and evaluation
  used the same 2010–2023 series. The figures are training-set scores.

Two independent projects, two different causes, same outcome: results that
exist, must not be reported as evaluation, and whose reason has nowhere to go.

## Finding 3 — withheld and never-computed collapse to the same document

This is the load-bearing one. For a consumer:

```python
yaml.safe_load(card)["evaluationResults"]   # -> None
```

`None` here means *"computed, withheld, because the evaluation is known to be
invalid"*. It is indistinguishable from `None` meaning *"nobody evaluated
this"* — which is the weaker claim, and the one a consumer will assume.

The difference matters: a model withheld **because its evaluation is known to
be invalid** carries a warning worth propagating. A model never evaluated
carries no warning at all. The schema currently converts the first into the
second.

Note that `evaluationResults` already has range `schema:Text, schema:PropertyValue`,
so structured results are expressible today. The gap is not structure — it is
**intentional absence with a reason**. Issue #17 asks a version of the same
question for `hasCO2eEmissions`, which suggests a general answer may serve
better than per-property ones.

## Finding 4 — three fields used in practice have no term in any namespace

`developmentLibrary` (4/4), `wasGeneratedBy` (4/4), `parameterSize` (1/4).

Not in FAIR4ML 0.1.0, schema.org or codemeta. The converter emits them under a
`local:` prefix rather than inventing official-looking terms. `parameterSize`
in particular seems like something a model description should be able to state.

## Proposals, cheapest first

1. A documented convention for "intentionally absent", carrying a reason
   string — no new class, usable on any property.
2. A small `absenceReason` / `withheldBecause` property applicable across
   fields, which would also answer #17.
3. Reuse an existing vocabulary for typed nulls rather than minting one.

## Reproducing

    python tools/yaml2jsonld.py cards/portfolio_dqn_model_card.yaml --report
    python tools/validate_card.py --vocab path/to/release/0.1.0/fair4ml.jsonld cards/*.yaml

`yaml2jsonld.py` also answers the question asked in #14 — a converter from the
circulating YAML cards to the published JSON-LD vocabulary — and reports every
key it cannot place instead of emitting it silently.

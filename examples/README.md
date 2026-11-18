# Worked examples for FAIR4ML 0.1.0

Four trained models described with the FAIR4ML vocabulary, the tooling used to
produce and check them, and a report of what the vocabulary could and could not
express. Prepared in response to issue #14 (*Example annotated model card*),
which also asked for a YAML-to-JSON-LD converter.

    cards/     four model cards, YAML, each pinned to vocabulary version 0.1.0
    jsonld/    the same four cards converted to JSON-LD
    tools/     the converter and the validator
    FINDINGS.md  what held and what did not, with counts

## The four models

| Model | Kind | Source |
|---|---|---|
| ICU early-warning (hypotension, 4 h) | logistic regression | PhysioNet MIMIC-IV open-access demo |
| Realised-volatility forecaster (^GSPC) | LSTM | S&P 500 daily closes, 2010–2023 |
| Portfolio allocation agent | DQN | 5 ETFs, daily, 2010–2023 |
| Portfolio allocation agent | SAC | 5 ETFs, daily, 2010–2023 |

Every value in a card comes from the originating project's machine-written
results file; none was entered by hand. Projects that train no model were left
out, including several that are about machine learning: a rule-based scorer, an
authored (not fitted) decision policy, a leakage-measurement library, and a
Pareto-frontier study.

## Tools

`tools/yaml2jsonld.py` converts a YAML card to JSON-LD. It maps each key onto
its FAIR4ML, schema.org or codemeta term and reports any key it cannot place,
emitting it under a `local:` prefix rather than inventing an official-looking
term. It also reports keys that are present in the source but parse to null,
together with the comment text beside them.

    python tools/yaml2jsonld.py cards/portfolio_dqn_model_card.yaml --report

`tools/validate_card.py` checks cards against the published vocabulary, read
from `release/0.1.0/fair4ml.jsonld` in this repository rather than a
hand-copied list, so it tracks whatever the group publishes.

    python tools/validate_card.py --vocab release/0.1.0/fair4ml.jsonld cards/*.yaml

Both need only PyYAML.

## Summary of findings

* 10 of the 22 properties carried the load across four models from two domains.
* Eight fields were declared but null in all four cards; `evaluationResults`
  was null in three of four.
* A field withheld for a stated reason and a field nobody filled in produce the
  same JSON-LD. The reason lives in a YAML comment, which does not survive
  parsing.
* Three fields used in practice have no term in FAIR4ML 0.1.0, schema.org or
  codemeta: `parameterSize`, `developmentLibrary`, `wasGeneratedBy`. The same
  three are missing from this repository's own example card, so the gap is in
  the vocabulary rather than in one author's style.

See `FINDINGS.md` for the detail.

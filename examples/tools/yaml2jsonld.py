#!/usr/bin/env python3
"""Convert a YAML FAIR4ML model card to JSON-LD.

Answers the question asked in RDA-FAIR4ML/FAIR4ML-schema#14: the published
vocabulary is JSON-LD, the circulating example cards are YAML, and nothing
bridges them.

Two things this does that a naive dump does not:

  1. Maps each YAML key onto its FAIR4ML / schema.org / codemeta term, and
     reports any key it cannot place, instead of silently emitting an
     un-namespaced property that no consumer will understand.

  2. Detects keys that are PRESENT IN THE SOURCE but parse to null, and
     reports the comment text sitting next to them. In a YAML card an author
     records "withheld, because X" in a comment; yaml.safe_load returns None
     and the reason is gone. That loss is invisible unless you look for it.

Usage:
    python yaml2jsonld.py CARD.yaml [-o OUT.jsonld] [--report]
"""
import argparse, json, pathlib, re, sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required:  pip install pyyaml")

FAIR4ML = {
    "task": "fair4ml:mlTask",
    "modelCategory": "fair4ml:modelCategory",
    "modelRisks": "fair4ml:modelRisksBiasLimitations",
    "intendedUse": "fair4ml:intendedUse",
    "evaluationMetrics": "fair4ml:evaluationMetrics",
    "evaluationResults": "fair4ml:evaluationResults",
    "trainedOn": "fair4ml:trainedOn",
    "testedOn": "fair4ml:testedOn",
    "evaluatedOn": "fair4ml:evaluatedOn",
    "validatedOn": "fair4ml:validatedOn",
    "fineTunedFromModel": "fair4ml:fineTunedFrom",
    "sharedBy": "fair4ml:sharedBy",
    "usageInstructions": "fair4ml:usageInstructions",
    "hasCO2eEmissions": "fair4ml:hasCO2eEmissions",
    "codeSampleSnippet": "fair4ml:codeSampleSnippet",
    "legal": "fair4ml:legal",
    "ethicalSocial": "fair4ml:ethicalSocial",
}
SCHEMA = {
    "identifier": "schema:identifier", "name": "schema:name",
    "version": "schema:version", "keywords": "schema:keywords",
    "headline": "schema:headline", "description": "schema:description",
    "license": "schema:license", "citation": "schema:citation",
    "codeRepository": "schema:codeRepository",
    "dateCreated": "schema:dateCreated", "dateModified": "schema:dateModified",
    "author": "schema:author", "funder": "schema:funder",
    "distribution": "schema:distribution", "language": "schema:inLanguage",
    "softwareRequirements": "schema:softwareRequirements",
    "storageRequirements": "schema:storageRequirements",
    "memoryRequirements": "schema:memoryRequirements",
    "operatingSystem": "schema:operatingSystem",
    "processorRequirements": "schema:processorRequirements",
    "sdPublisher": "schema:sdPublisher", "sdLicense": "schema:sdLicense",
}
CODEMETA = {
    "developmentStatus": "codemeta:developmentStatus",
    "referencePublication": "codemeta:referencePublication",
}
# Keys that appear in circulating cards but have no term in FAIR4ML 0.1.0,
# schema.org or codemeta. Emitted under a clearly local prefix, never faked
# into an official namespace.
NO_TERM = ["parameterSize", "GPURequirements", "successorOf", "wasGeneratedBy",
           "developmentLibrary", "quantizationBits", "quantizationMethod"]

TERMS = {**FAIR4ML, **SCHEMA, **CODEMETA}

CONTEXT = {
    "schema": "http://schema.org/",
    "codemeta": "https://w3id.org/codemeta/",
    "fair4ml": "https://w3id.org/fair4ml#",
    "cr": "http://mlcommons.org/croissant/",
    "local": "urn:local:unmapped#",
}


def declared_but_null(text):
    """Top-level keys written in the file whose value parses to null.

    Returns {key: comment_text}. The comment is what a human put there and a
    parser throws away.
    """
    out = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(#.*)?$", line)
        if not m:
            continue
        key, inline = m.group(1), (m.group(2) or "")
        # a block follows if the next non-blank line is indented and not a comment
        nxt = next((l for l in lines[i + 1:] if l.strip()), "")
        if nxt.startswith((" ", "\t")) and not nxt.lstrip().startswith("#"):
            continue  # it has a real nested value
        block = []
        for l in lines[i + 1:]:
            if l.lstrip().startswith("#"):
                block.append(l.lstrip().lstrip("#").strip())
            elif not l.strip():
                continue
            else:
                break
        note = " ".join(x for x in ([inline.lstrip("# ").strip()] + block) if x)
        out[key] = note.strip()
    return out


def convert(path, report=False):
    text = pathlib.Path(path).read_text()
    card = yaml.safe_load(text) or {}
    nulls = declared_but_null(text)

    doc = {"@context": CONTEXT, "@type": "fair4ml:MLModel"}
    unmapped, withheld = [], []

    for key, val in card.items():
        if key.startswith("_"):
            continue                      # card-level metadata, not model metadata
        if val is None:
            if key in nulls and nulls[key]:
                withheld.append((key, nulls[key]))
            continue
        term = TERMS.get(key)
        if term is None:
            term = f"local:{key}"
            unmapped.append(key)
        doc[term] = val

    if "_fair4mlVersion" in card:
        doc["schema:schemaVersion"] = card["_fair4mlVersion"]

    return doc, unmapped, withheld, nulls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("card")
    ap.add_argument("-o", "--out")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()

    doc, unmapped, withheld, nulls = convert(a.card)
    js = json.dumps(doc, indent=2, ensure_ascii=False, default=str)
    if a.out:
        pathlib.Path(a.out).write_text(js + "\n")
    else:
        print(js)

    if a.report:
        name = pathlib.Path(a.card).name
        print(f"\n--- {name} ---", file=sys.stderr)
        print(f"properties emitted : {len([k for k in doc if ':' in k])}", file=sys.stderr)
        if unmapped:
            print(f"NO TERM IN 0.1.0   : {', '.join(unmapped)}", file=sys.stderr)
            print("  (emitted under local: so they are not mistaken for official terms)",
                  file=sys.stderr)
        if withheld:
            print(f"DECLARED BUT NULL  : {len(withheld)}", file=sys.stderr)
            for k, note in withheld:
                short = (note[:88] + "...") if len(note) > 88 else note
                print(f"  - {k}: {short or '(no reason given)'}", file=sys.stderr)
            print("  These carry a human-readable reason that the JSON-LD cannot hold:",
                  file=sys.stderr)
            print("  there is no term for 'absent, and here is why'.", file=sys.stderr)


if __name__ == "__main__":
    main()

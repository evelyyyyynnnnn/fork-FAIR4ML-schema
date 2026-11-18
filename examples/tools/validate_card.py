#!/usr/bin/env python3
"""Validate a converted FAIR4ML card against the published vocabulary.

Reads the real release file (release/0.1.0/fair4ml.jsonld from
RDA-FAIR4ML/FAIR4ML-schema) rather than a hand-copied list, so the check
tracks whatever the group actually published.

Reports, per card:
  * fair4ml terms used that the vocabulary does not define
  * vocabulary terms the card leaves unused
  * properties with no term anywhere (emitted as local:)
  * fields declared in the source but parsing to null

Usage:
    python validate_card.py --vocab PATH/fair4ml.jsonld CARD.yaml [CARD.yaml ...]
"""
import argparse, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from yaml2jsonld import convert  # noqa: E402


def load_vocab(path):
    d = json.loads(pathlib.Path(path).read_text())
    graph = d.get("@graph", d if isinstance(d, list) else [])
    props, classes = set(), set()
    for x in graph:
        t = str(x.get("@type", ""))
        pid = x.get("@id", "")
        if not pid.startswith("fair4ml:"):
            continue
        if "Property" in t:
            props.add(pid)
        elif "Class" in t:
            classes.add(pid)
    return props, classes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocab", required=True)
    ap.add_argument("cards", nargs="+")
    a = ap.parse_args()

    props, classes = load_vocab(a.vocab)
    print(f"vocabulary: {pathlib.Path(a.vocab)}")
    print(f"  {len(classes)} classes, {len(props)} properties\n")

    used_overall, null_overall, local_overall = set(), {}, {}
    rc = 0

    for c in a.cards:
        doc, unmapped, withheld, _ = convert(c)
        name = pathlib.Path(c).name
        used = {k for k in doc if k.startswith("fair4ml:")}
        undefined = used - props
        used_overall |= used

        print(f"=== {name} ===")
        print(f"  fair4ml terms used     : {len(used)}/{len(props)}")
        if undefined:
            rc = 1
            print(f"  !! NOT IN VOCABULARY   : {', '.join(sorted(undefined))}")
        if unmapped:
            print(f"  no term anywhere       : {', '.join(unmapped)}")
            for u in unmapped:
                local_overall.setdefault(u, []).append(name)
        if withheld:
            print(f"  declared but null      : {len(withheld)}")
            for k, note in withheld:
                null_overall.setdefault(k, []).append(name)
        decl_type = doc.get("@type")
        if decl_type not in classes:
            print(f"  !! @type {decl_type} not a vocabulary class "
                  f"({', '.join(sorted(classes))})")
            rc = 1
        print()

    print("=" * 62)
    print(f"ACROSS {len(a.cards)} CARDS")
    print("=" * 62)
    unused = sorted(props - used_overall)
    print(f"\nvocabulary terms never used ({len(unused)}):")
    for u in unused:
        print(f"  - {u}")
    print(f"\nfields declared but null, by how many cards:")
    for k, v in sorted(null_overall.items(), key=lambda x: -len(x[1])):
        print(f"  {len(v)}/{len(a.cards)}  {k}")
    print(f"\nfields with no term in any namespace:")
    for k, v in sorted(local_overall.items(), key=lambda x: -len(x[1])):
        print(f"  {len(v)}/{len(a.cards)}  {k}")
    return rc


if __name__ == "__main__":
    sys.exit(main())

"""Independent synthetic demonstration of selective tool-knowledge updates."""

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile


def index_records(records, label):
    """Reject ambiguous identifiers instead of silently overwriting records."""
    if not isinstance(records, list):
        raise ValueError(f"{label} must be a list")
    indexed = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"{label} records must be objects")
        key = record.get("id")
        if not isinstance(key, str) or not key.strip() or key in indexed:
            raise ValueError(f"{label} requires unique, nonempty string ids")
        indexed[key] = record
    return indexed


def validate_tools(records):
    tools = index_records(records, "tools")
    for tool in tools.values():
        if not isinstance(tool.get("description"), str):
            raise ValueError("tool description must be a string")
        for field in ("parameters", "output_schema", "routing"):
            if not isinstance(tool.get(field), dict):
                raise ValueError(f"tool {field} must be an object")
    return tools


def patch(knowledge, catalog):
    """Return a new snapshot and audit report; never mutate either input.

    JSON shape checks here are intentionally narrower than JSON Schema
    validation. Semantic rule repair and agent execution are outside this demo.
    """
    if not isinstance(knowledge, dict) or not isinstance(catalog, dict):
        raise ValueError("knowledge and catalog must be objects")
    json.dumps([knowledge, catalog], allow_nan=False)
    old = validate_tools(knowledge.get("tools"))
    new = validate_tools(catalog.get("tools"))
    rules = index_records(knowledge.get("rules", []), "rules")
    previous_retired = knowledge.get("retired_rules", [])
    retired_ids = index_records(previous_retired, "retired_rules")
    if rules.keys() & retired_ids.keys():
        raise ValueError("active and retired rule ids must be disjoint")
    for rule in rules.values():
        refs = rule.get("tool_refs")
        if not isinstance(refs, list) or any(
            not isinstance(ref, str) or ref not in old for ref in refs
        ):
            raise ValueError("rule references must exist in the old catalog")
        if not isinstance(rule.get("text"), str):
            raise ValueError("rule text must be a string")
        if rule.get("status", "active") not in ("active", "needs_review"):
            raise ValueError("invalid rule status")

    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    shared = old.keys() & new.keys()
    changed = sorted(key for key in shared if old[key] != new[key])
    unchanged = sorted(shared - set(changed))
    changed_fields = {
        key: sorted(
            field for field in old[key].keys() | new[key].keys()
            if (field not in old[key] or field not in new[key]
                or old[key][field] != new[key][field])
        ) for key in changed
    }

    result = deepcopy(knowledge)
    # Keep existing record order, append additions in a deterministic order.
    result["tools"] = [
        deepcopy(old[key] if key in unchanged else new[key])
        for key in old if key in new
    ] + [deepcopy(new[key]) for key in added]
    result["rules"] = []
    result["retired_rules"] = deepcopy(previous_retired)
    flagged, retired = [], []
    for rule in rules.values():
        updated = deepcopy(rule)
        missing = sorted(set(rule["tool_refs"]) & set(removed))
        affected = sorted(set(rule["tool_refs"]) & set(changed))
        if missing:
            updated["status"] = "retired"
            updated["retirement_reason"] = {"removed_tools": missing}
            result["retired_rules"].append(updated)
            retired.append(rule["id"])
            continue
        if affected:
            updated["status"] = "needs_review"
            # Retain prior reasons until explicitly resolved by a reviewer.
            reasons = updated.setdefault("review_reasons", [])
            if not isinstance(reasons, list):
                raise ValueError("review_reasons must be a list")
            reason = {"changed_tools": affected, "action": "check_rule_semantics"}
            if reason not in reasons:
                reasons.append(reason)
            flagged.append(rule["id"])
        result["rules"].append(updated)

    final_tools = validate_tools(result["tools"])
    if final_tools != new:
        raise ValueError("patched catalog does not match authoritative target")
    if any(final_tools[key] != old[key] for key in unchanged):
        raise ValueError("unaffected metadata changed")
    if any(ref not in final_tools for r in result["rules"] for ref in r["tool_refs"]):
        raise ValueError("dangling rule reference after patch")
    report = {
        "added": added, "removed": removed, "changed": changed,
        "unchanged": unchanged, "changed_fields": changed_fields,
        "newly_flagged_rules": sorted(flagged), "retired_rules": sorted(retired),
        "pending_review": sorted(
            r["id"] for r in result["rules"] if r.get("status") == "needs_review"
        ),
        "model_calls": 0, "fixture_type": "synthetic",
    }
    return {"knowledge": result, "report": report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in (args.old.resolve(), args.new.resolve()):
        parser.error("output must differ from input paths")
    result = patch(json.loads(args.old.read_text()), json.loads(args.new.read_text()))
    serialized = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=args.output.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(serialized)
        os.replace(temporary, args.output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(json.dumps(result["report"], indent=2))


if __name__ == "__main__":
    main()

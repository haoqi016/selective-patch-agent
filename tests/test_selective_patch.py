"""Synthetic mechanism checks, not evidence of agent task performance."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from selective_patch import patch

ROOT = Path(__file__).resolve().parents[1]


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.old = json.loads((ROOT / "examples/old_knowledge.json").read_text())
        self.new = json.loads((ROOT / "examples/new_catalog.json").read_text())

    def test_local_update_preserves_unrelated_tool_and_rule(self):
        result = patch(self.old, self.new)
        self.assertEqual(result["knowledge"]["tools"][1], self.old["tools"][1])
        self.assertEqual(result["knowledge"]["rules"][1], self.old["rules"][1])
        self.assertEqual(result["report"]["changed"], ["document.fetch"])
        self.assertEqual(result["report"]["added"], ["citation.lookup"])
        self.assertEqual(result["report"]["unchanged"], ["notes.save"])

    def test_schema_change_flags_dependent_rule_without_inventing_repair(self):
        result = patch(self.old, self.new)
        rule = result["knowledge"]["rules"][0]
        self.assertEqual(rule["text"], self.old["rules"][0]["text"])
        self.assertEqual(rule["status"], "needs_review")
        self.assertEqual(result["report"]["pending_review"], ["fetch-then-save"])

    def test_removal_retires_dangling_rule_and_preserves_other_rule(self):
        new = {"tools": [self.old["tools"][1]]}
        result = patch(self.old, new)
        self.assertEqual(result["knowledge"]["rules"], [self.old["rules"][1]])
        retired = result["knowledge"]["retired_rules"][0]
        self.assertEqual(retired["status"], "retired")
        self.assertEqual(retired["retirement_reason"]["removed_tools"], ["document.fetch"])

    def test_reapplying_patch_does_not_clear_unresolved_review(self):
        first = patch(self.old, self.new)["knowledge"]
        second = patch(first, self.new)
        self.assertEqual(second["knowledge"], first)
        self.assertEqual(second["report"]["changed"], [])
        self.assertEqual(second["report"]["pending_review"], ["fetch-then-save"])

    def test_retirement_persists_across_subsequent_patches(self):
        new = {"tools": [self.old["tools"][1]]}
        first = patch(self.old, new)["knowledge"]
        self.assertEqual(patch(first, new)["knowledge"], first)

    def test_no_change_preserves_all_records(self):
        result = patch(self.old, {"tools": deepcopy(self.old["tools"])})
        self.assertEqual(result["knowledge"]["tools"], self.old["tools"])
        self.assertEqual(result["knowledge"]["rules"], self.old["rules"])
        self.assertEqual(result["report"]["pending_review"], [])

    def test_inputs_are_not_mutated(self):
        before = deepcopy((self.old, self.new))
        result = patch(self.old, self.new)
        result["knowledge"]["tools"][0]["description"] = "mutated output"
        self.assertEqual((self.old, self.new), before)

    def test_reject_duplicate_tool_and_rule_ids(self):
        self.new["tools"].append(deepcopy(self.new["tools"][0]))
        with self.assertRaises(ValueError):
            patch(self.old, self.new)
        self.old["rules"].append(deepcopy(self.old["rules"][0]))
        with self.assertRaises(ValueError):
            patch(self.old, {"tools": self.old["tools"]})

    def test_reject_unknown_old_rule_reference(self):
        self.old["rules"][0]["tool_refs"] = ["missing.tool"]
        with self.assertRaises(ValueError):
            patch(self.old, self.new)

    def test_reject_invalid_metadata_and_nonfinite_values(self):
        self.new["tools"][0]["parameters"] = "not an object"
        with self.assertRaises(ValueError):
            patch(self.old, self.new)
        self.new["tools"][0]["parameters"] = {"invalid": float("nan")}
        with self.assertRaises(ValueError):
            patch(self.old, self.new)

    def test_description_and_routing_changes_are_detected(self):
        for field, value in [("description", "New behavior"), ("routing", {"server": "v2"})]:
            with self.subTest(field=field):
                new = {"tools": deepcopy(self.old["tools"])}
                new["tools"][0][field] = value
                report = patch(self.old, new)["report"]
                self.assertEqual(report["changed_fields"]["document.fetch"], [field])
                self.assertEqual(report["pending_review"], ["fetch-then-save"])

    def test_reordering_target_does_not_change_knowledge(self):
        first = patch(self.old, self.new)
        self.new["tools"].reverse()
        self.assertEqual(patch(self.old, self.new), first)

    def test_invalid_cli_input_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output.json"
            bad = Path(tmp) / "bad.json"
            output.write_text("existing artifact")
            bad.write_text('{"tools": []}')
            # Old rules become invalid if old knowledge contains no tools.
            invalid = deepcopy(self.old)
            invalid["tools"] = []
            bad.write_text(json.dumps(invalid))
            completed = subprocess.run(
                [sys.executable, str(ROOT / "selective_patch.py"), str(bad),
                 str(ROOT / "examples/new_catalog.json"), "--output", str(output)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(output.read_text(), "existing artifact")


if __name__ == "__main__":
    unittest.main()

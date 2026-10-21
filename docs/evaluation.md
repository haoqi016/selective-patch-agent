# Evaluation design and evidence

## Current observations

The public tests exercise synthetic cases. They check mechanism properties such as preservation of unrelated records, dependency flagging, removal handling, input validation, non-mutation of inputs, and persistence of unresolved review status. They do not measure language-model behavior.

A separate private development report dated 20 October 2026 records an adaptation run on MCPEvol-Bench task139 Early-to-Late catalogs: 40 old tools, 44 new tools, 10 records replaced, 4 added, and 30 unchanged, with zero validation errors reported. This observation concerns artifact generation. The underlying catalogs and full prototype are not distributed here, so it is historical supporting context rather than a publicly reproducible benchmark result.

The deterministic adaptation path made no model calls. That does not establish a cost advantage over other methods at the agent-task level. There are no completed comparative agent results in this repository.

## Proposed controlled comparison

Compare **No Update**, **Full Rewrite**, and **Selective Patch** on matched old-to-new tool transitions. Freeze the base model and version, task inputs, available tool versions, execution budgets, observation formatting, and evaluator. Define the full-rewrite procedure and its model/prompt before running experiments. Keep execution infrastructure common across conditions and report adaptation cost separately from execution cost.

| Question | Measurement |
| --- | --- |
| Does adaptation restore affected tasks? | Paired task-success difference against No Update on affected tasks after evolution. |
| Does the method preserve unaffected capabilities? | Paired performance on unaffected control tasks, with the affected/control split fixed before inspecting outcomes. |
| Is the local scope sufficient? | Trace review of stale fields, missed dependencies, and unresolved instructions associated with task failures. |
| Does rewriting cause collateral errors? | Trace review of changed but unrelated knowledge, compared with preserved controls. |
| What does adaptation cost? | Update calls, tokens, elapsed time and records touched; report execution calls, tokens, retries, probes and any human review separately. |

An ablation that updates metadata without checking rule dependencies can test whether dependency handling contributes beyond catalog replacement. A second comparison can examine the consequences of semantic review or rewriting, with identical downstream execution budgets and explicit treatment of unresolved rules.

For stochastic agent runs, use repeated paired trials and report uncertainty as well as failures. Separate development transitions from held-out evaluation transitions. Claims of under-update or over-update require trajectory evidence, not just counts of modified records.

## Open work

Complete live end-to-end runs, validate the semantic updater, freeze the final evaluation protocol, and collect matched baseline results. Conclusions about effectiveness, generalization, or total cost will depend on those results.

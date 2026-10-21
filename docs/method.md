# Method and worked example

## Problem

An agent's external tool knowledge includes callable metadata and instructions for using tool results. An interface update can invalidate both. The research question is whether localizing these changes can recover affected capabilities without unnecessarily rewriting useful knowledge.

The current method treats the new catalog as authoritative for tool metadata. It assumes stable tool identifiers and explicit references from rules to tools. These are strong assumptions: hidden dependencies and incorrect metadata remain open failure modes.

## Update procedure

1. Compare tool identifiers and metadata fields across the old and new catalogs. Classify tools as added, removed, changed, or unchanged.
2. Find usage rules that explicitly reference changed or removed tools. The demonstration follows direct references only.
3. Replace changed metadata with its authoritative target record; add new tools and remove absent tools. Preserve unrelated records exactly as JSON values.
4. Retire rules with missing tool references. Keep other affected rules with `needs_review` status and record the reason. Do not infer a semantic rewrite from a schema change alone.
5. Check record shapes, unique identifiers, reference validity, and preservation of unchanged records. Write the result atomically through the command-line entry point.

## Example

Before the change, a rule says: “Read the text field returned by document.fetch, then save it with notes.save.” The new `document.fetch` schema returns `content.body` instead of `text`.

The patch replaces the fetch metadata and flags that rule for review. The `notes.save` record and its independent rule remain unchanged. A newly available `citation.lookup` tool is added from the target catalog. The method does not assert that replacing the words “text field” is sufficient: the intended processing or meaning of the output could also have changed.

The demonstration keeps unresolved status across subsequent updates. A flag is not a completed repair. An agent integration must decide how to withhold or resolve flagged instructions before relying on them; this repository does not execute an agent.

## Scope of this public implementation

The demonstration uses a deliberately small JSON format and standard-library shape checks. It does not provide a full JSON Schema validator, routing probes, live MCP connections, an LLM rule updater, or the team's runner and cache implementation. It conservatively flags a direct dependent rule after any metadata change, including descriptions.

The private prototype includes broader schema/routing validation and an optional gated semantic updater. No successful live run of that updater is claimed here. The public demonstration is independently written to make the method inspectable, and is not a byte-for-byte extraction of that implementation.

## Limitations to investigate

- Stable IDs are assumed. Renames appear as removal plus addition.
- Explicit one-hop references miss implicit or transitive dependencies.
- Preserving a record does not prove its task-level behavior is unaffected.
- Some metadata changes do not alter semantics; conservative flags may create unnecessary review work.
- A fully rewritten knowledge base may outperform a local patch when evolution requires a new workflow.
- Cheap metadata updates do not imply lower total cost once agent execution, probes, retries, and review are counted.

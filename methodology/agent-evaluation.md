# Agent evaluation

Agent-maintenance studies test whether representation changes how reliably machines can understand and modify software.

## Task packets

A task packet should freeze:

- user-visible request;
- allowed files/scope;
- allowed tools;
- time/attempt budget if any;
- public tests/instructions;
- hidden or verifier tests;
- success and non-regression rules.

Prefer maintenance tasks that resemble real changes rather than puzzles designed around a specific implementation.

## Fairness between arms

Use the same requested behavior and verification rule. Do not give the MNCS arm extra explanations unless the explanations are part of the artifact being evaluated (for example, machine-readable contracts checked into that arm).

Tool access, model configuration, system prompt, context window, sampling settings, and retry policy should be held constant or explicitly modeled as an experimental variable.

## Repetition

A single successful run is weak evidence. When cost permits, repeat tasks across multiple fresh runs and multiple model sizes/families. Preserve failed trajectories where licensing/privacy permits.

## Minimum run record

Record:

- study and epoch;
- task identifier;
- implementation arm;
- model/provider or local model identity;
- quantization/serving configuration when local;
- worker/machine identity class;
- tools available;
- attempt number;
- result and verifier summary;
- tokens/context/tool-call counts when available;
- elapsed time when meaningful;
- patch/content digest;
- whether human intervention occurred.

## Hidden verification

The evaluated agent should not receive hidden tests or protected verifier details that disclose the answer. The harness may use them after the attempt.

## Learning export

If trajectories are later used by RAVEL or MNEL, export both successful and failed attempts with outcome labels and provenance. Do not train on a verifier decision stripped of the task/study/epoch identity that gives it meaning.

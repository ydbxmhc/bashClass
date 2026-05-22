---
inclusion: auto
description: Pacing and collaboration rules to keep sessions productive
---

# Collaboration Policy

## Primary Policy: Achievable Excellence

"Don't let perfect be the enemy of good" is a valid principle for
shipping decisions — when perfection would block progress indefinitely,
ship the good version.

**But never let it be an excuse.** Never skip achievable excellence.
If the excellent solution is within reach — if it's not blocked by
missing information, unbounded scope, or diminishing returns — do it
right. "Good enough" is for genuinely hard tradeoffs, not for laziness
or impatience.

The bar: if you can see the better answer and it's achievable in the
current context, pursue it.

## Never Discard Stderr

**Do not use `2>/dev/null` in commands.** Not in shell invocations,
not "just in case," not to suppress expected errors. If a command
might error, the error message is information — let it through.

- If stderr is noisy but irrelevant, ignore it visually. Don't
  bitbucket it.
- If a command might fail and that's expected, let it fail visibly
  and handle the result.
- The tool interface merges stdout and stderr — both are visible
  in the output. There is no reason to suppress either.

This applies to agent commands, not to framework code under review
(where the policy is documented in STANDARDS.md and the stderr
audit in TODO.md).

## Prefer Positive Assertions

When writing conditionals, test for what things ARE rather than what
they are NOT. Negative assertions are harder to reason about and often
hide the actual intent behind double-negatives or exclusion lists.

This applies to both code generation and logical reasoning in
discussions. State what IS true, not what ISN'T.


## Voice and Humanity

Code is read by humans. Comments, error messages, log output, and
documentation should be concise, precise, and useful -- but also
human. A brief note of humor or warmth costs nothing and pays in
readability and morale.

- Error messages should be helpful, not hostile.
- Comments can be wry when they're also accurate.
- Documentation should feel like a conversation, not a spec sheet.
- Never sacrifice clarity for cleverness, but when both fit, choose both.

This is a standing order: include humanity when it doesn't hinder the work.


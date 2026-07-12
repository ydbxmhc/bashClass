---
title: Testing
---

# Testing

Test infrastructure for boop projects and general bash scripts.

## Classes

| Class | Description |
|---|---|
| [Testing.TestSuite](/docs/TestSuite) | Test runner — section grouping, assertion helpers, summary report |

## Quick start

```bash
. boop Testing::TestSuite

into=ts Testing.TestSuite name="My Tests"

$ts.section "basic math"
$ts.assert "addition" [[ $(( 2 + 2 )) -eq 4 ]]
$ts.assert "inequality" [[ 3 -lt 5 ]]

$ts.summary
```

→ [Full class reference](/docs/index)

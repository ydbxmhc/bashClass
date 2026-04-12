# Test Suite Audit — TODO & Qualification Checklist

Audit performed April 2026. All issues found during a full read of every
test file against the source it covers. Fixes applied in the same session
where noted; remaining items tracked here.

---

## Qualification Checklist

Run this checklist whenever a test file is touched, a new class is added,
or a public API changes. It is not optional.

### For every test file

- [ ] Every public method on the class under test has at least one passing
      assertion and at least one rejection/crash assertion (where applicable).
- [ ] No test captures values via `$_Out` (the global side-channel). All
      captures use `into=varname`.
- [ ] No test inspects `__boop_registry` or other internal globals directly
      unless the thing being tested IS the registry (e.g., destroy, serialize).
      Observable behavior through the public API is always preferred.
- [ ] Every section description accurately describes what is being tested.
      Descriptions like "stops on non-zero return" must be unambiguous about
      edge cases (does the stopping element count?).
- [ ] Crash/rejection tests use `bash -c` isolation. In-process crash tests
      are not allowed — they kill the test runner.
- [ ] Probabilistic tests (shuffle, random ID uniqueness) document their
      statistical assumptions and have a retry or tolerance strategy that is
      explicit, not ad-hoc.
- [ ] No `|| true` on source lines. Load failures must be loud.
- [ ] No magic numbers in assertions without a derivation comment.
- [ ] Tests that depend on ordering (section A mutates state used by section B)
      are either eliminated or explicitly documented as sequential dependencies.

### For the suite as a whole

- [ ] There is a smoke test file that answers "is the framework alive?" in
      under 2 seconds with no more than 10 assertions.
- [ ] The smoke/unit/integration taxonomy is reflected in file names or a
      manifest. Every test file is classified.
- [ ] `test_all` runs smoke first, then unit, then integration. A smoke
      failure short-circuits the rest.
- [ ] The naming convention check in `test_all` covers ALL class files and
      ALL test files, not just the ones listed at the time of writing.
- [ ] `boopExtend` has direct test coverage.
- [ ] Every class added to the hierarchy has a corresponding `_ts` test file
      or is explicitly covered in an existing file with a comment explaining why.

### For the TestSuite harness itself

- [ ] Both the passing and failing paths of every assertion type are tested
      (assert_eq pass AND fail, assert_match pass AND fail, etc.).
- [ ] The suite isolation test uses a derived bound, not a magic number.
- [ ] The stderr capture test verifies the right thing: that the command's
      stderr is captured by the harness, not that the harness's own _Debug
      output reaches a file.

---

## Issues by File — Status

### NEW: test_smoke (missing file)                                   [ ] FIXED

A smoke test file does not exist. Need a file `test_smoke` that:
- Sources boop and one class
- Creates one object, calls one method, checks the result
- Verifies the framework loaded (registry non-empty)
- Runs in under 2 seconds
- Is the first file run by test_all

### test_testsuite_ts                                                [ ] FIXED

1. **Stderr capture mechanism is wrong.** The test redirects `$t.assert_ok`'s
   stderr to a file, but assert_ok internally redirects the command's stderr
   to its own temp file. The outer redirect captures _Debug output from
   TestSuite, not the command's stderr. The test passes for the wrong reason.
   Fix: test that the harness captures stderr from the command under test by
   verifying the _Debug call receives the right content — test the harness
   contract, not the fd plumbing.

2. **Suite isolation uses magic number `< 50`.** If the suite grows past 50
   assertions, this silently becomes wrong. Fix: record the count before
   running the sub-suite, run it, verify the parent count didn't change.

3. **No negative assertion tests.** assert_eq failing, assert_match not
   matching, assert_contains not containing — only happy paths are tested.
   Fix: add a sub-suite that deliberately fails assertions and verify the
   failed count increments correctly.

4. **assert_ok/assert_fail not tested with commands that produce stdout.**
   Unknown whether stdout from the command under test leaks to the terminal
   or is suppressed. Fix: add a test with a command that writes to stdout
   and verify it doesn't corrupt the test output.

### test_box_cube_ts                                                 [ ] FIXED

1. **No crash/rejection tests.** `Cube size=abc`, `Cube` with no size,
   `Box.calc` with zero — these are in test_stress_ts instead of here.
   Unit tests for a class should be self-contained. Fix: add a "Rejection"
   section with the crash cases that belong to Box/Cube specifically.

2. **toString section is thin.** Doesn't verify internal fields are
   suppressed, doesn't test Box toString, doesn't verify field values
   appear in the output. Fix: expand toString section.

3. **_Bless is not directly tested.** The bug we just fixed (wrappers baked
   with wrong _Class after _Bless) had no test. Fix: add an explicit
   "_Bless" section that creates an object via a parent constructor, blesses
   it to the child class, and verifies isa, toString, and method dispatch
   all reflect the blessed class.

4. **Mutation section silently corrupts shared state.** `$box.set length 10`
   modifies the box used in the geometry section. Fix: use a dedicated
   mutation object, not the shared fixture.

### test_containers_ts                                               [ ] FIXED

1. **each early-exit count is ambiguous.** The description "stops on non-zero
   return" doesn't say whether the stopping element is counted. Fix: rename
   to "each: callback called for stopping element" and assert 2 explicitly
   with a comment.

2. **deepSet missing-intermediate test description is wrong.** The test uses
   index 99 (out of range), not a missing intermediate container. Fix: write
   a test that actually has a missing intermediate (e.g., a List whose
   element is a plain string, not a container) and verify it crashes.

3. **Destroy test inspects registry directly.** Fix: after destroy, attempt
   to call a method on the destroyed object and verify it crashes (or verify
   the wrapper function no longer exists). The registry check is an
   implementation detail.

4. **Map toString test only checks prefix.** Fix: verify field values appear
   in the output.

5. **Iterator snapshot isolation asserts count only.** Fix: also verify the
   values returned are the original 3, not 3 arbitrary values.

### test_math_ts                                                     [ ] FIXED

1. **Division precision not verified.** `1/3` matched with `0.333333333*`
   passes even if the result is `0.3`. Fix: assert the exact digit count
   matches the configured precision.

2. **Division by zero not tested.** Fix: add `assert_fail` for `Math.divide 5 0`.

3. **Math.DO precedence test is ambiguous.** `2 + 3 x 4 = 14` is consistent
   with both "x has higher precedence" and "left-to-right". Fix: add a test
   that distinguishes the two: `2 x 3 + 4` should be 10 if x has higher
   precedence, 20 if left-to-right.

4. **mod, pow, toScale, format, isZero not tested.** Fix: add sections for
   each. These are public methods with no coverage.

5. **Static API doesn't cover negative inputs or edge cases.** Fix: add
   `Math.neg -3.14` (double negation → positive), `Math.abs 0`, `Math.abs`
   of a negative.

### test_logging_ts                                                  [ ] FIXED

1. **"Closed stderr" test description is misleading.** "warn with closed
   stderr fails" — it's bash that fails on the write, not boop. Fix: rename
   to "writing to closed stderr propagates write failure".

2. **Fallback log file never tested.** `__boop_logFile` is set but never
   exercised. Fix: add a test that closes stderr, calls _Warn, and verifies
   the fallback file was written. (Or document that the fallback was removed
   and remove the global.)

3. **Caller context test bypasses normal dispatch.** Fix: call the method
   through the normal object wrapper (`$box.test_log`) and verify the caller
   name is still correct.

### test_stress_ts                                                   [ ] FIXED

1. **File is misnamed.** It's an adversarial/integration test, not a stress
   test. The benchmark section is opt-in and skipped by default. Fix: rename
   to `test_framework_ts` or `test_adversarial_ts`. Update test_all.

2. **Duplicate property test uses $t.info instead of assertion.** The
   behavior of duplicate constructor args is observable. Fix: assert the
   actual value (last-write-wins or first-write-wins, whichever is correct).

3. **Section 12 wrapper test logic is inverted and confusing.** The
   `assert_fail test "${__wrap_def}" != "${__wrap_def/__init/}"` pattern
   is a double-negative that tests string substitution, not the wrapper.
   Fix: use `assert_contains` / `assert_ok test -z` directly.

4. **_Super tests don't cover multi-level chaining or into=.** Fix: add a
   three-level hierarchy test and verify `into=` works with _Super.

5. **Serialization test doesn't verify property values after round-trip.**
   Fix: serialize, deserialize in a fresh shell, call `$obj.get property`,
   verify the value.

6. **`$_Out` used for object capture at top of file.** `box="$_Out"` and
   `cube="$_Out"` after `new`. Fix: use `into=box` and `into=cube`.

### test_blackjack                                                   [ ] FIXED

1. **`. blackjack </dev/null 2>/dev/null || true` swallows load errors.**
   Fix: remove `|| true`. If blackjack fails to source, the test should
   fail loudly.

2. **Shuffle test retry logic is ad-hoc.** Fix: document the statistical
   assumption (probability of a fair Fisher-Yates shuffle leaving >= 8 cards
   in place is astronomically small) and remove the retry — one shuffle is
   sufficient. Or keep the retry but make it a loop with a fixed max and a
   clear failure message.

3. **BlackjackHand.deal not tested in the unit section.** Fix: add a deal
   test in the BlackjackHand unit section (not just integration).

4. **BlackjackHand.reveal not tested directly.** Fix: assert that after
   reveal, `$h.get faceUp` equals the hand length.

5. **BlackjackHand.cardVal never tested.** Fix: add a section that calls
   cardVal directly for A, J, Q, K, and numeric ranks.

### test_all                                                         [ ] FIXED

1. **Naming convention check doesn't cover all files.** PlayingCard, Deck,
   Hand, Card, x are not in `__nc_files`. Fix: add all class files.

2. **No smoke-first ordering.** Fix: run test_smoke first; if it fails,
   print a clear message and exit before running the rest.

3. **test_stress_ts rename.** Update the loop and any references when the
   file is renamed.

---

## Methods with Zero Test Coverage

As of this audit:

| Class       | Uncovered methods                              |
|-------------|------------------------------------------------|
| Math        | mod, pow, toScale, format, isZero              |
| Math static | mod, pow, toScale, format                      |
| boop        | boopExtend (framework function, not a method)  |
| boop        | serialize/deserialize property round-trip      |
| BlackjackHand | cardVal, reveal (direct)                     |
| TestSuite   | assert_* failure paths (harness self-test)     |
| Container   | noIterators                                    |

---

## Notes

- `test_matrix` and `test_pi_growth` are benchmarks, not test suites.
  They are correctly excluded from `test_all`. No changes needed.
- The `x` file in the workspace root is unknown — not covered by any test
  or naming check. Investigate before next push.
- README.md test counts will need updating after fixes (currently says 488,
  actual is higher after recent additions).

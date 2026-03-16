# Blackjack Class Refactor Plan

## Goal
Clean up class hierarchy so generic concepts (Card, Deck, Hand) are reusable,
and blackjack-specific logic lives in the blackjack script.

## Current State (731250e)
- `Card` — has suit, rank, faceUp; FaceCard/Ace are separate classes
- `Deck` — extends List, has `fill` that creates 52 playing cards
- `Hand` — extends List, has `total`, `isBust`, `isBlackjack` (blackjack-specific)
- `blackjack` — sources Card/Deck/Hand, has game loop
- `test_blackjack` — 79 tests, all passing

## Target Structure

### Generic Classes (reusable)

**Card** — base class for any card-like object
- Properties: `faceUp`
- Methods: `new`, `flip`, `toString` (returns `[?]` when face down; subclass overrides for face-up display)

**Deck** — extends List, generic card collection
- Methods: `shuffle`, `draw`
- NO `fill` — caller populates the deck

**Hand** — extends List, displayable card collection  
- Methods: `show` (takes label arg, displays cards)
- NO scoring logic — that's game-specific

### Blackjack-Specific (in blackjack script)

**PlayingCard extends Card**
- Properties: `suit`, `rank`, `faceUp`
- Methods: `new`, `val` (returns numeric value), `toString` (rank+suit)

**FaceCard extends PlayingCard**
- Overrides: `val` → always 10

**Ace extends PlayingCard**
- Overrides: `val` → always 11

**Script functions** (not class methods):
- `fill_deck` — populates a Deck with 52 PlayingCards
- `hand_total` — computes blackjack score with ace adjustment
- `is_bust` — total > 21
- `is_blackjack` — 2 cards, total == 21

**Game loop guard**:
```bash
if [[ "${1:-}" == "--test" ]]; then
  # source TestSuite, run tests inline
elif [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  # run game loop
fi
# If neither: we're being sourced — just provide the classes
```
This gives three modes:
- `bash blackjack` — plays the game
- `bash blackjack --test` — runs its own test suite
- `. ./blackjack` — just loads the classes (for external use)

This pattern is reusable for any script that defines classes.

## Test Updates
- `test_blackjack` may become unnecessary — tests live in blackjack itself
- `bash blackjack --test` runs the suite
- Tests for PlayingCard/FaceCard/Ace stay the same
- Tests for Hand.total etc become tests for script functions
- Pattern is reusable: any class-defining script can be its own test

## Files to Modify
1. `Card` — remove suit/rank, make toString generic
2. `Deck` — remove `fill` method
3. `Hand` — remove `total`, `isBust`, `isBlackjack`
4. `blackjack` — add PlayingCard/FaceCard/Ace inline, add script functions, add guard
5. `test_blackjack` — update sourcing, update function tests

## Status
- [ ] Card refactor
- [ ] Deck refactor  
- [ ] Hand refactor
- [ ] blackjack inline classes + functions + guard
- [ ] test_blackjack updates
- [ ] All tests passing
- [ ] Commit and push

# Blackjack — boop Example Class Design

*A working single-player Blackjack game as a demonstration of boop features.*
*Replaces Box/Cube as the canonical example.*

---

## Goals

- Demonstrate boop features naturally, not contrivedly
- Dead simple rules everyone already knows
- Actually fun to run
- All classes defined inline — no file hierarchy required
- Shows inheritance doing real semantic work, not just structural work

---

## What It Demonstrates

| Feature | Where |
|---------|-------|
| Object creation | Every card is a real object |
| Properties & accessors | `$card.suit`, `$card.rank`, `$card.faceUp` |
| Inheritance chain | `FaceCard` and `Ace` extend `Card` |
| Meaningful `isa` | `$card.isa FaceCard` — a real question with a real answer |
| Method override | `FaceCard.val()`, `Ace.val()`, `Hand.toString()` |
| List (push/pop/length) | `Deck` and `Hand` extend `List` |
| Native arithmetic | Totals, bust check, ace adjustment — no Math class needed |
| Multi-class single file | All classes defined inline in one script |
| `toString` override | Cards display as `A♠`, `K♥`, `7♦` |
| Encapsulation | House logic lives in the game script, not the classes |

---

## Class Hierarchy

```
bashClass
  └── Card                     suit, rank, faceUp; flip(), val(), toString()
        ├── FaceCard            rank is J/Q/K; val() always 10
        └── Ace                 rank is A; val() returns 11 (Hand adjusts)

Container
  └── List
        ├── Deck               reset(), shuffle(), draw()
        └── Hand               total(), isBust(), isBlackjack(), toString()
```

---

## Class Descriptors

### Card

```bash
__bashClass_registry["Card"]="|class=Card|parent=bashClass\
|methods=new,flip,val,toString\
|properties=suit,rank,faceUp"
```

**Properties:**
- `suit` — ♠ ♥ ♦ ♣ (stored as string)
- `rank` — 2-10, J, Q, K, A
- `faceUp` — 0 or 1

**Methods:**
- `new` — constructor; default faceUp=0
- `flip` — toggle faceUp
- `val` — return integer card value (2-10 → face value; override in subclasses)
- `toString` — `7♦` if face up, `[?]` if face down

### FaceCard extends Card

```bash
__bashClass_registry["FaceCard"]="|class=FaceCard|parent=Card\
|methods=new,val\
|properties=suit,rank,faceUp"
```

Inherits everything from Card. Overrides:
- `val` — always returns 10

No other changes. `$card.isa Card` still true. `$card.isa FaceCard` true.
`toString` inherited — shows rank (J/Q/K) + suit correctly.

### Ace extends Card

```bash
__bashClass_registry["Ace"]="|class=Ace|parent=Card\
|methods=new,val\
|properties=suit,rank,faceUp"
```

Inherits everything from Card. Overrides:
- `val` — returns 11 (Hand.total() adjusts down to 1 if bust)

`rank` is always "A". `$card.isa Ace` lets Hand identify aces for
adjustment without any special-casing elsewhere.

### Deck extends List

```bash
__bashClass_registry["Deck"]="|class=Deck|parent=List\
|methods=new,reset,shuffle,draw\
|properties="
```

**Methods:**
- `new` — calls reset() to populate
- `reset` — clears and builds a fresh 52-card deck (creates all Card/FaceCard/Ace objects)
- `shuffle` — Fisher-Yates shuffle on the internal array
- `draw` — pop from top, return Card object ID

Inherits `push`, `pop`, `length`, `get` from List.

### Hand extends List

```bash
__bashClass_registry["Hand"]="|class=Hand|parent=List\
|methods=new,total,isBust,isBlackjack,toString\
|properties=owner"
```

**Properties:**
- `owner` — "Player" or "House" (for display)

**Methods:**
- `total` — sum card values; walk aces and adjust 11→1 while bust
- `isBust` — total > 21
- `isBlackjack` — exactly 2 cards, total == 21
- `toString` — show all face-up cards + total, e.g.:
  `Player: A♠ K♥  [21 — Blackjack!]`

---

## Ace Adjustment Logic

`Hand.total()` is the one interesting computation. The algorithm:

1. Sum all card values (Ace counts as 11 by default via `Ace.val`)
2. Count how many Aces are in the hand (using `$card.isa Ace`)
3. While total > 21 and aces > 0: subtract 10, decrement ace count

```bash
Hand.total() {
  local -I self class
  local -i __Hand_total_sum=0 __Hand_total_aces=0 __Hand_total_i __Hand_total_len
  local __Hand_total_card

  into=__Hand_total_len $self.length

  for (( __Hand_total_i=0; __Hand_total_i < __Hand_total_len; __Hand_total_i++ )); do
    into=__Hand_total_card $self.get $__Hand_total_i
    local -i __Hand_total_v
    into=__Hand_total_v $__Hand_total_card.val
    (( __Hand_total_sum += __Hand_total_v ))
    $__Hand_total_card.isa Ace && (( __Hand_total_aces++ )) || true
  done

  while (( __Hand_total_sum > 21 && __Hand_total_aces > 0 )); do
    (( __Hand_total_sum -= 10 ))
    (( __Hand_total_aces-- ))
  done

  __bashClass.return "$__Hand_total_sum" ${into:-}
}
```

Clean. No Math class. No subshells in the loop.

---

## Shuffle

Fisher-Yates in pure bash — no subshells, no external tools:

```bash
Deck.shuffle() {
  local -I self class
  local -i __Deck_shuffle_len __Deck_shuffle_i __Deck_shuffle_j
  local __Deck_shuffle_tmp __Deck_shuffle_a __Deck_shuffle_b

  into=__Deck_shuffle_len $self.length

  for (( __Deck_shuffle_i = __Deck_shuffle_len - 1;
         __Deck_shuffle_i > 0;
         __Deck_shuffle_i-- )); do
    __Deck_shuffle_j=$(( RANDOM % (__Deck_shuffle_i + 1) ))
    into=__Deck_shuffle_a $self.get $__Deck_shuffle_i
    into=__Deck_shuffle_b $self.get $__Deck_shuffle_j
    $self.set $__Deck_shuffle_i "$__Deck_shuffle_b"
    $self.set $__Deck_shuffle_j "$__Deck_shuffle_a"
  done
}
```

---

## Game Script Outline

```bash
#!/bin/bash
. boop List

# ============================================================
# Class definitions — all inline, no separate files needed
# ============================================================

# ... Card, FaceCard, Ace, Deck, Hand defined here ...

# ============================================================
# Game loop
# ============================================================

into=deck Deck
$deck.shuffle

into=player Hand owner=Player
into=house  Hand owner=House

# Initial deal — two cards each
$player.push "$( $deck.draw )" "$( $deck.draw )"
$house.push  "$( $deck.draw )" "$( $deck.draw )"

# Flip player cards and one house card up
# ... flip logic ...

# Player turn
while true; do
  into=total $player.total
  $player.toString

  $player.isBlackjack && { printf "Blackjack!\n"; break; }
  $player.isBust      && { printf "Bust!\n"; break; }

  printf "Hit or stand? [h/s] "
  read -r choice
  [[ "$choice" == "h" ]] && $player.push "$( $deck.draw )" || break
done

# House turn (hits on soft 16, stands on 17+)
# ... house logic ...

# Result
# ... compare totals, declare winner ...
```

---

## File Structure

Two options — both valid:

**Option A: Inline (preferred for example)**
Everything in one file: `blackjack`
- Demonstrates that boop doesn't require a file hierarchy
- Self-contained — copy one file, run it

**Option B: Separate class files**
- `Card`, `Deck`, `Hand` as individual files
- `blackjack` script sources them
- Demonstrates the import system

Both options should exist. Option A as the primary example,
Option B as a comment or note showing how it would split out.

---

## What to Remove

Once Blackjack is solid:

- Delete `Box`, `Cube` class files
- Delete `test_box_cube`
- Remove Box/Cube from README, PLAN, docs
- Update class hierarchy diagrams everywhere

The TestSuite rewrite of `test_box_cube` becomes moot — the
Blackjack classes get their own test file using TestSuite instead.

---

## Open Questions

- `Deck.set` (from List) lets you replace cards arbitrarily —
  should Deck override and disable it? Probably yes for correctness,
  though it won't matter for the example script. @@

- House strategy: fixed (hit ≤ 16, stand ≥ 17) is standard and
  keeps the script simple. No reason to complicate it. @@

- Betting/chips: out of scope. Keeps the example focused on
  the class system, not the game mechanics. @@

- `test_blackjack` using TestSuite — write this *after* TestSuite
  exists, as a demonstration of both classes working together. @@

# Blackjack Refactor Plan

## Problem

Card, Hand, and Deck are currently blackjack-specific but named
generically. A Card isn't necessarily a PlayingCard. A Hand of
blackjack cards (ace adjustment, bust/blackjack detection) is nothing
like a poker hand (pair detection, flush, straight). Deck hardcodes
52 playing cards with suits.

The class leakage warnings in `Hand.total()` are a symptom: Hand
iterates its cards calling `.val` and `.isa Ace`, and `_Class=Hand`
leaks into Card's baked wrappers. Hand isn't in Card's family tree,
so the dispatcher flags it as Tier 3 leakage. Fixing the warnings
without fixing the design just papers over the real issue.

## Current Structure

```
Card      → suit, rank, faceUp, flip, val, toString
FaceCard  → extends Card, val returns 10
Ace       → extends Card, val returns 11
Deck      → extends List, fill (52 cards), shuffle, draw
Hand      → extends List, total (ace adjustment), isBust, isBlackjack, show
```

Everything lives in separate class files: `Card`, `Deck`, `Hand`.

## Target Structure

### Generic base classes (keep as separate files)

```
Card      → generic card with arbitrary properties
            properties: faceUp (boolean)
            methods: flip, toString (shows [?] when face-down)
            NO suit, rank, val — those are domain-specific

Deck      → generic ordered collection you draw from
            extends List
            methods: shuffle, draw
            NO fill — filling is domain-specific

Hand      → generic scored collection
            extends List
            methods: show (delegates toString to each card)
            NO total, isBust, isBlackjack — scoring is game-specific
```

### Blackjack-specific classes (defined in `blackjack` script)

```
PlayingCard    → extends Card, adds suit + rank + val
FaceCard       → extends PlayingCard, val returns 10
Ace            → extends PlayingCard, val returns 11
PlayingDeck    → extends Deck, fill with 52 PlayingCards
BlackjackHand  → extends Hand, total (ace logic), isBust, isBlackjack
```

## The Inline Class Problem

We *want* to define PlayingCard, BlackjackHand, etc. inside the
`blackjack` script — they're game-specific, not reusable library
classes. But boop's class registration machinery (`registerMethod`,
`registerClass`, `stubAll`) expects class files to be sourceable.

What needs to work:
1. Define a class (descriptor + methods + register) inline in a script
2. The class participates fully in dispatch, inheritance, baking
3. No separate file required

What currently breaks (or is awkward):
- `__boop.import` looks for files on disk — inline classes skip this
- The load guard pattern (`[[ -n "${__boop_registry[X]+set}" ]] && return`)
  doesn't apply to inline definitions
- If another class tries to `. boop PlayingCard`, it won't find a file

This isn't a blocker — you can register inline classes today by just
writing the descriptor, methods, and calling `registerMethod` /
`registerClass` directly. The import system just won't know about
them. That's fine for script-local classes that nothing else imports.

## Refactor Steps

### 1. Slim down Card (file)

Remove `val` method — it returns 0 for non-numeric ranks, which is
meaningless outside blackjack. Keep: `flip`, `toString`, and the
`suit`/`rank`/`faceUp` properties (suit and rank are generic enough
for any card game — tarot, index cards, whatever).

Actually — reconsider whether `suit` and `rank` belong on the base.
A flash card has a "front" and "back", not a suit. An index card has
a "label". Maybe Card is just `faceUp` + `flip` + `toString`, and
PlayingCard adds `suit` + `rank`.

Decision needed: how minimal is Card?

### 2. Slim down Deck (file)

Remove `fill` — that's 52-card-specific. Keep `shuffle` and `draw`.
Constructor just creates an empty List. Subclasses provide `fill`.

### 3. Slim down Hand (file)

Remove `total`, `isBust`, `isBlackjack` — all blackjack-specific.
Keep `show` (generic: iterate cards, call toString, join).

### 4. Define blackjack classes inline in `blackjack`

```bash
# After `. boop Deck Hand`:

# --- PlayingCard (if Card becomes truly generic) ---
# Or just keep using Card with suit/rank if we decide that's fine.

# --- BlackjackHand extends Hand ---
__boop_registry["BlackjackHand"]="|class=BlackjackHand|parent=Hand|..."
BlackjackHand.new() { ... }
BlackjackHand.total() { ... }    # ace adjustment lives here
BlackjackHand.isBust() { ... }
BlackjackHand.isBlackjack() { ... }
__boop.registerMethod BlackjackHand ...
__boop.registerClass BlackjackHand

# --- PlayingDeck extends Deck ---
__boop_registry["PlayingDeck"]="|class=PlayingDeck|parent=Deck|..."
PlayingDeck.new() { ... }        # calls fill + shuffle
PlayingDeck.fill() { ... }       # 52 cards with suits
__boop.registerMethod PlayingDeck ...
__boop.registerClass PlayingDeck
```

### 5. Fix the leakage

With BlackjackHand properly extending Hand extending List, and
Card/PlayingCard in their own hierarchy, the `_Class` leakage
disappears naturally. BlackjackHand.total iterates cards and calls
`.val` — but now `_Class=BlackjackHand` is unrelated to Card, and
the baked wrapper... still warns.

Wait. The leakage warning happens whenever ANY method on object A
is called while `_Class` is set to an unrelated class B. The fix
isn't just about hierarchy — it's about not letting `_Class` leak
across object boundaries.

Two real fixes:
- **In Hand.total (or BlackjackHand.total):** clear `_Class` before
  calling card methods: `_Class= $card.val` — lets the baked wrapper
  use its own default class.
- **In the framework:** consider whether cross-object calls should
  auto-clear `_Class`. This is a bigger design question.

For now, the pragmatic fix is `_Class= $card.val` in the scoring
loop. The refactor still matters for separation of concerns, but
the warning fix is a one-liner in the method that crosses object
boundaries.

## Open Questions

1. How minimal should base Card be? Just `faceUp` + `flip` +
   `toString`? Or keep `suit`/`rank` as "common enough" properties?
2. Should `show` stay on Hand or move to blackjack? It formats
   `[total]` which is game-specific. Maybe Hand.show is just the
   card list, and BlackjackHand.show appends the score.
3. Do we want a `PlayingCard` intermediate, or is Card-with-suit-rank
   generic enough to keep as-is?
4. Framework question: should baked wrappers auto-clear `_Class` when
   the ambient class is Tier 3 (unrelated)? Currently they warn and
   proceed with the baked class. Auto-clearing would be silent and
   correct, but hides the design smell.

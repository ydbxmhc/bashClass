# Games.Deck

A shuffleable, drawable collection. Extends `Collection.List` with two extra
operations: `shuffle` (Fisher-Yates in-place) and `draw` (pop from the end).

A Deck has no opinion about what goes into it — the caller or a card class's
`newDeck` factory populates it. The elements are typically object IDs returned
by a card constructor.

## Contents

- [Dependencies](#dependencies)
- [Constructor](#constructor)
- [Deck Operations](#deck-operations)
  - [$d.shuffle](#d-shuffle)
  - [$d.draw](#d-draw)
- [Inherited from List](#inherited-from-list)
- [Example — build and deal a hand](#example--build-and-deal-a-hand)

---

## Dependencies

```bash
. boop Games::Deck    # also loads Collection::List
```

---

## Constructor

```bash
into=d Games.Deck
```

Creates an empty deck. Add cards with the inherited `push` method, then
call `shuffle` before dealing.

---

## Deck Operations

### `$d.shuffle`

Shuffle the deck in place using the Fisher-Yates algorithm. Each card ends up
in a uniformly random position.

```bash
$d.shuffle
```

Shuffling is idempotent — you can call it multiple times to re-shuffle.

### `$d.draw`

Remove and return the top card (pop from the end of the list).

```bash
into=card $d.draw
```

Returns the card's object ID. Returns empty string and exits non-zero if the
deck is empty.

```bash
while into=card $d.draw; do
  printf "drew: %s\n" "$card"
done
```

---

## Inherited from List

All `Collection.List` methods are available on a Deck. The most useful ones
when working with decks:

```bash
into=n $d.length          # cards remaining
$d.isEmpty && printf "deck is empty\n"
$d.push "$card"           # add a card
into=n $d.get 0           # peek at bottom card
```

See [List.md](List.md) for the full API including iteration, slicing, and
functional operations.

---

## Example — build and deal a hand

```bash
. boop Games::Deck

into=d Games.Deck

# Populate with string values (or use a card class)
for rank in A 2 3 4 5 6 7 8 9 10 J Q K; do
  for suit in S H D C; do
    $d.push "${rank}${suit}"
  done
done

$d.shuffle

# Deal 5 cards
for (( i=0; i<5; i++ )); do
  into=card $d.draw
  printf "  %s\n" "$card"
done

into=remaining $d.length
printf "%s cards left\n" "$remaining"
```

For a ready-made 52-card deck of proper `PlayingCard` objects, see
[`Games.PlayingCard.newDeck`](PlayingCard.md#gamesplayingcardnewdeck).

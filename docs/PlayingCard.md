# Games.PlayingCard

A standard playing card with a suit (♠ ♥ ♦ ♣) and rank (A 2–10 J Q K).
Extends `Games.Card`.

Knows how to display itself as a short string (`A♠`) or as a 7-line
ASCII art card with ANSI colour. Does not assign numeric values — point
values are game-specific logic that belongs in the game, not the card.

## Contents

- [Dependencies](#dependencies)
- [Constructor](#constructor)
- [Methods](#methods)
  - [$c.toString](#c-tostring)
  - [$c.render](#c-render)
  - [Games.PlayingCard.newDeck](#gamesplayingcardnewdeck)
- [Properties](#properties)
- [Example — render a full hand](#example--render-a-full-hand)
- [Subclassing](#subclassing)

---

## Dependencies

```bash
. boop Games::PlayingCard    # also loads Games::Card and Games::Deck
```

---

## Constructor

```bash
into=c Games.PlayingCard suit=♠ rank=A
```

Both `suit` and `rank` are free strings — the class does not validate them.
Standard values:

| Property | Values |
|----------|--------|
| `suit`   | `♠` `♥` `♦` `♣` |
| `rank`   | `A` `2` `3` `4` `5` `6` `7` `8` `9` `10` `J` `Q` `K` |

```bash
into=ace   Games.PlayingCard suit=♠ rank=A
into=ten   Games.PlayingCard suit=♥ rank=10
into=queen Games.PlayingCard suit=♦ rank=Q
```

---

## Methods

### `$c.toString`

Return the rank and suit concatenated: `rank + suit`.

```bash
into=s $ace.toString      # s="A♠"
into=s $ten.toString      # s="10♥"
```

### `$c.render`

Print a 7-line ASCII art card to stdout. Hearts and diamonds are coloured red;
spades and clubs are black. All characters have a white background so the card
reads clearly against any terminal background.

```
┌───────┐
│10     │
│       │
│   ♥   │
│       │
│     10│
└───────┘
```

```bash
$c.render
```

`render` writes directly to stdout and returns nothing.

### `Games.PlayingCard.newDeck`

Class method. Build a shuffled `Games.Deck` containing all 52 standard
playing cards (4 suits × 13 ranks) and return it.

```bash
into=deck Games.PlayingCard.newDeck
```

The cards in the deck are `Games.PlayingCard` instances. Deal with `draw`:

```bash
into=card $deck.draw
$card.render
into=s $card.toString
```

---

## Properties

| Property | Description |
|----------|-------------|
| `suit`   | Unicode suit glyph: `♠` `♥` `♦` `♣` |
| `rank`   | Rank string: `A` `2`–`10` `J` `Q` `K` |

---

## Example — render a full hand

```bash
. boop Games::PlayingCard

into=deck Games.PlayingCard.newDeck

printf "Your hand:\n"
for (( i=0; i<5; i++ )); do
  into=card $deck.draw
  $card.render
  into=label $card.toString
  printf "  %s\n\n" "$label"
done

into=remaining $deck.length
printf "%d cards remaining in deck\n" "$remaining"
```

---

## Subclassing

`newDeck` is `_Class`-aware. A subclass that inherits `newDeck` gets a deck
filled with its own type — override just what changes:

```bash
. boop Games::PlayingCard

boop.init MyCard || return 0

MyCard.new()     { local _Class=MyCard; Games.PlayingCard.new "$@"; }
MyCard.value()   { ... }     # game-specific point value

boopClass MyCard isa:Games.PlayingCard public:new,value

# Creates a shuffled deck of 52 MyCard objects, not PlayingCards:
_Class=MyCard into=deck Games.PlayingCard.newDeck
```

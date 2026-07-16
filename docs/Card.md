# Games — Card, PlayingCard, Deck

Three classes that compose into a complete card game foundation.

```
boop → Games.Card → Games.PlayingCard
boop → Collection.Container → Collection.List → Games.Deck
```

## Dependencies

```bash
. boop PlayingCard    # loads Card and Deck automatically
. boop Deck           # loads List and Container
```

( See [Container](Container) and [List](List) )

---

## Games.Card — Generic Base

`boopClass Games.Card public:new,toString`

A generic card with no assumptions about content. A property bag.
Subclasses add domain-specific properties and behavior.

### Constructor

```bash
into=c Games.Card key=value key2=value2 ...
into=c Games.Card name="red" value="10"
```

Any `key=value` arguments become properties accessible via `$c.get`.

### Methods

```bash
into=id $c.toString    # returns the object's own ID (override in subclasses)
```

`Games.Card` is the abstract base. You typically use `Games.PlayingCard`
or a custom subclass:

```bash
boopClass TarotCard isa:Games.Card has:arcana,number public:new,toString
```

---

## Games.PlayingCard — Standard Playing Card

`boopClass Games.PlayingCard isa:Games.Card has:suit,rank`

A playing card with `suit` (♠ ♥ ♦ ♣) and `rank` (A 2–10 J Q K).
Numeric values are not assigned here — that is game logic for the consumer.

### Constructor

```bash
into=c Games.PlayingCard suit="♠" rank="A"
into=c Games.PlayingCard suit="♥" rank="10"
into=c Games.PlayingCard suit="♦" rank="K"
```

### Properties

| Property | Values |
|----------|--------|
| `suit` | `♠` `♥` `♦` `♣` |
| `rank` | `A` `2` `3` ... `10` `J` `Q` `K` |

```bash
into=s $c.get suit    # s="♠"
into=r $c.get rank    # r="A"
```

### `$c.toString`

Returns rank concatenated with suit: `A♠`, `10♥`, `K♦`, `2♣`.

```bash
into=s $c.toString
printf "Card: %s\n" "$s"   # "Card: A♠"
```

### `$c.newDeck` — class method

Create a shuffled 52-card deck of this card type.

```bash
into=deck Games.PlayingCard.newDeck

# Deal two cards
into=c1 $deck.draw
into=c2 $deck.draw

into=s1 $c1.toString    # e.g. "7♣"
into=s2 $c2.toString    # e.g. "Q♥"
```

`newDeck` creates all 52 combinations (4 suits × 13 ranks), shuffles them,
and returns a `Games.Deck`. It respects `_Class` — subclasses that inherit
`newDeck` get a deck filled with their own type:

```bash
boopClass MyCard isa:Games.PlayingCard has:suit,rank,faceUp public:new,toString

into=deck MyCard.newDeck    # deck full of MyCard objects
```

---

## Games.Deck — Shuffleable, Drawable List

`boopClass Games.Deck isa:Collection.List has:type`

A [List](List) you can shuffle and draw from. No opinion about what's in it.

### Constructor

```bash
into=d Games.Deck        # empty deck; populate manually
into=d Games.PlayingCard.newDeck   # 52-card shuffled deck
```

Populate manually for custom card games:

```bash
into=d Games.Deck
for v in A 2 3 4 5 6 7 8 9 10 J Q K; do
  into=c Games.PlayingCard suit="♠" rank="$v"
  $d.push "$c"
done
```

### `$d.shuffle`

Fisher-Yates shuffle in place. Every possible permutation is equally likely.

```bash
$d.shuffle         # randomize the deck
$d.shuffle         # shuffle again (e.g. after collecting cards)
```

### `$d.draw`

Remove and return the top card (pop from end of list).
Crashes if the deck is empty.

```bash
into=card $d.draw
into=name $card.toString
printf "Dealt: %s\n" "$name"

# Draw until empty
while ! $d.isEmpty; do
  into=c $d.draw
  # ...
done
```

### Inherited from Collection.List

Because `Games.Deck` extends `Collection.List`, it inherits the full List API:

```bash
into=n $d.length     # number of cards remaining
$d.push "$c"         # add a card to the top (back)
into=c $d.pop        # remove from top
into=c $d.getAt 0    # peek at bottom card without removing
$d.isEmpty           # 0 if no cards left
```

---

## Complete Example — Simple Blackjack Hand

```bash
. boop PlayingCard

# Build and deal
into=deck Games.PlayingCard.newDeck
into=hand Collection.List

into=c $deck.draw; $hand.push "$c"
into=c $deck.draw; $hand.push "$c"

# Show hand
into=len $hand.length
for (( i=0; i<len; i++ )); do
  into=card $hand.getAt $i
  into=s $card.toString
  printf "  %s\n" "$s"
done

# Count score (consumer defines values)
score=0
for (( i=0; i<len; i++ )); do
  into=card $hand.getAt $i
  into=rank $card.get rank
  case "$rank" in
    A) (( score += 11 )) ;;
    J|Q|K) (( score += 10 )) ;;
    *) (( score += rank )) ;;
  esac
done
printf "Score: %d\n" "$score"
```

---

## Subclassing PlayingCard

Add a `faceUp` property to track card visibility:

```bash
boopClass MyCard isa:Games.PlayingCard has:suit,rank,faceUp '
  public:new,toString,flip
'

MyCard.new() {
  local _Class="${_Class:-MyCard}"
  Games.PlayingCard.new faceUp=true "$@"
}

MyCard.flip() {
  local _Self="${_Self:-${Class:-MyCard}}" _Class="${_Class:-MyCard}"
  local __MyCard_flip_cur; into=__MyCard_flip_cur __boop.get faceUp
  if [[ "$__MyCard_flip_cur" == "true" ]]; then
    __boop.set faceUp false
  else
    __boop.set faceUp true
  fi
}
```

---

## Design Notes

**No values, no game logic.** `Games.PlayingCard` knows suit and rank,
nothing else. Point values, hand totals, win conditions — all that belongs
in the game class. This keeps the card reusable across any card game.

**Deck extends List.** All List methods work on Deck. `draw` is a named alias
for `pop`. `push` adds to the top (end). The underlying array is `__boop_data_${deck}`.

**`newDeck` uses `_Class`.** The deck-filling loop calls `$_Class suit=... rank=...`
rather than `Games.PlayingCard ...`. Subclass constructors get called automatically
when `newDeck` is inherited.

---

[↑ Site map](index)

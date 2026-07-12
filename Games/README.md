---
title: Games
---

# Games

Card game foundation: Card, Deck, and PlayingCard.

## Inheritance

```
boop → Games.Card → Games.PlayingCard
boop → Collection.Container → Collection.List → Games.Deck
```

## Classes

| Class | Description |
|---|---|
| [Games.Card](/docs/Card) | Generic card base — property bag, no game logic |
| [Games.Deck](/docs/Deck) | Shuffleable, drawable List — Fisher-Yates shuffle, pop-based draw |
| [Games.PlayingCard](/docs/PlayingCard) | Standard playing card — suit, rank, ANSI render, `newDeck` factory |

See the [combined Games reference](/docs/Card) for a narrative walkthrough
of all three together, including a complete Blackjack hand example and
subclassing guide.

## Quick start

```bash
. boop Games::PlayingCard    # loads Card and Deck automatically

into=deck Games.PlayingCard.newDeck    # 52-card shuffled deck

into=card $deck.draw
into=s $card.toString    # e.g. "A♠"
$card.render             # 7-line ASCII art card
```

→ [Full class reference](/docs/index)

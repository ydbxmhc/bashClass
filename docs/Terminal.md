# Terminal (mixin)

ANSI escape sequences, raw keyboard input, terminal sizing, and a named
symbol table. Mix into any class that needs terminal output capabilities.

## Dependencies

```bash
. boop Terminal
```

## Mixing In

```bash
boopClass MyRenderer mixin:Terminal public:new,...
```

All Terminal methods become available on every instance of `MyRenderer`.

---

## Screen Control

```bash
$r.clear          # erase entire screen, move cursor to top-left
$r.home           # move cursor to top-left without clearing
$r.move 5 10      # move cursor to row 5, column 10 (1-based)
$r.hideCursor     # hide the blinking cursor (restore on exit)
$r.showCursor     # show the cursor again
```

Typical TUI loop:

```bash
trap "$r.showCursor; $r.restore" EXIT

$r.hideCursor
$r.raw              # enter raw input mode

while true; do
  $r.clear
  draw_screen       # your rendering function
  into=k $r.readKey
  [[ "$k" == "q" ]] && break
  handle_key "$k"
done
```

---

## Text Styles

Write escape sequences directly to stdout. Combine freely with `printf`.

```bash
$r.bold;       printf "This is bold\n";       $r.reset
$r.italic;     printf "This is italic\n";     $r.reset
$r.underline;  printf "This is underlined\n"; $r.reset
$r.dim;        printf "This is dim\n";        $r.reset
$r.reverse;    printf "Reversed fg/bg\n";     $r.reset

# Combine styles
$r.bold; $r.underline; printf "Bold and underlined"; $r.reset; printf "\n"
```

Always call `$r.reset` to clear active styles.

---

## Colors

Set foreground and background color by name:

```bash
$r.fg red;    printf "red text";    $r.reset; printf "\n"
$r.bg blue;   printf "blue bg";    $r.reset; printf "\n"

# Combine fg + bg + style
$r.bold; $r.fg bright_white; $r.bg red
printf " ALERT "; $r.reset; printf "\n"
```

### Available color names

| Standard | Bright variant |
|----------|---------------|
| `black` | `bright_black` (dark grey) |
| `red` | `bright_red` |
| `green` | `bright_green` |
| `yellow` | `bright_yellow` |
| `blue` | `bright_blue` |
| `magenta` | `bright_magenta` |
| `cyan` | `bright_cyan` |
| `white` | `bright_white` |

Both `fg` and `bg` accept all 16 names. Unknown names return non-zero with an error.

---

## Terminal Size

```bash
into=w $r.width     # terminal width in columns (falls back to 80)
into=h $r.height    # terminal height in rows (falls back to 24)
```

`width` uses `$COLUMNS` if set, then `tput cols`, then 80.
`height` uses `$LINES` if set, then `tput lines`, then 24.

Center a string:

```bash
into=w $r.width
text="Hello"
pad=$(( (w - ${#text}) / 2 ))
printf "%*s%s\n" "$pad" "" "$text"
```

---

## Raw Input

Raw mode disables echo and line buffering so each keypress is
delivered immediately without waiting for Enter.

```bash
$r.raw                    # enter raw mode
into=k $r.readKey         # read exactly one keypress
$r.restore                # return to normal mode
```

Always restore terminal mode on exit:

```bash
trap "$r.restore; $r.showCursor" EXIT
$r.raw
```

`readKey` returns a single character. Arrow keys and function keys
produce multi-character sequences (e.g. `$'\033[A'` for up-arrow).
Read with a timeout if you need to distinguish Escape from an escape
sequence:

```bash
$r.raw
IFS= read -rn1 k
if [[ "$k" == $'\033' ]]; then
  IFS= read -rn2 -t 0.05 rest
  k="${k}${rest}"
fi
$r.restore
```

---

## Named Characters

Access Unicode box-drawing, suits, arrows, and symbols by name.
Two lookup styles — use whichever fits the context:

### Via method (any object)

```bash
into=tl $r.char topLeft     # tl='┌'
into=sp $r.char spade       # sp='♠'
```

### Via global array (tight rendering loops)

```bash
# Direct array access — no method call overhead
printf '%s' "${__Terminal_chars[topLeft]}"
printf '%s' "${__Terminal_chars[dHoriz]}"
```

### Single-line box drawing

| Name | Char | | Name | Char |
|------|------|-|------|------|
| `topLeft` | ┌ | | `topRight` | ┐ |
| `bottomLeft` | └ | | `bottomRight` | ┘ |
| `horiz` | ─ | | `vert` | │ |
| `cross` | ┼ | | | |
| `teeDown` | ┬ | | `teeUp` | ┴ |
| `teeRight` | ├ | | `teeLeft` | ┤ |

### Double-line box drawing

| Name | Char | | Name | Char |
|------|------|-|------|------|
| `dTopLeft` | ╔ | | `dTopRight` | ╗ |
| `dBottomLeft` | ╚ | | `dBottomRight` | ╝ |
| `dHoriz` | ═ | | `dVert` | ║ |
| `dCross` | ╬ | | | |
| `dTeeDown` | ╦ | | `dTeeUp` | ╩ |
| `dTeeRight` | ╠ | | `dTeeLeft` | ╣ |

### Card suits

| Name | Char | | Name | Char |
|------|------|-|------|------|
| `spade` | ♠ | | `club` | ♣ |
| `heart` | ♥ | | `diamond` | ♦ |

### Block / shade gradient

| Name | Char |
|------|------|
| `block` | █ |
| `darkShade` | ▓ |
| `medShade` | ▒ |
| `shade` | ░ |

### Arrows

| Name | Char | | Name | Char |
|------|------|-|------|------|
| `arrowLeft` | ← | | `arrowRight` | → |
| `arrowUp` | ↑ | | `arrowDown` | ↓ |

### Misc

| Name | Char | | Name | Char |
|------|------|-|------|------|
| `bullet` | • | | `ellipsis` | … |
| `check` | ✓ | | `ballotX` | ✗ |
| `star` | ★ | | `circle` | ● |
| `square` | ■ | | | |

---

## Drawing a Box

```bash
tl="${__Terminal_chars[topLeft]}"
tr="${__Terminal_chars[topRight]}"
bl="${__Terminal_chars[bottomLeft]}"
br="${__Terminal_chars[bottomRight]}"
h="${__Terminal_chars[horiz]}"
v="${__Terminal_chars[vert]}"

printf '%s%s%s\n' "$tl" "${h}${h}${h}${h}${h}${h}" "$tr"
printf '%s %s %s\n' "$v" "Hello!" "$v"
printf '%s%s%s\n' "$bl" "${h}${h}${h}${h}${h}${h}" "$br"
```

Output:
```
┌──────┐
│ Hello! │
└──────┘
```

---

## Visual Tests

The visual test suite lets you grade each Terminal capability interactively:

```bash
./tests/visual/test_terminal_visual
```

Grade each item `y` (pass) or `n` (fail). Results feed into TestSuite
reporting. Run manually — not part of `test_all`.

---

## Design Notes

**Global arrays for direct access.** `__Terminal_chars`, `__Terminal_fg`, and
`__Terminal_bg` are populated at load time and accessible without a method call.
In a tight rendering loop that draws hundreds of box characters, direct array
access avoids per-character dispatch overhead.

**Methods write to stdout.** `fg`, `bg`, `bold`, etc. print escape sequences
directly. Use them inline with `printf`:

```bash
printf '%s%sERROR%s: %s\n' "$($r.bold)" "$($r.fg red)" "$($r.reset)" "$message"
```

Or for even tighter output, combine `printf` calls so the sequences are adjacent.

**Error on unknown names.** `char`, `fg`, and `bg` call `_Error` and return
non-zero for unknown names. This catches typos at test time rather than
silently producing broken output.

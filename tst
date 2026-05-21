. boop Stream

_LogLevel TRACE

# Stream a: from stdin, array mode; tee saves to file simultaneously
into=a Stream -a A_fields < <(
  printf $'
    This is my Poem\r
    With CRLFs\nAnd Blocks\r\n\r
    It'\'$'s not very good,\r\nBut\nIt'\'$'s all that I'\'$'ve got.' | 
  tee "Bad Poem"
)

# Stream b: from file, paragraph records, CRLF field delimiter
into=b Stream.new -P "Bad Poem" -D $'\r\n\r\n' -F $'\r\n' -a B_fields

for o in "$a" "$b"; do
  $o.buffered && $o.Read || $o.read
  into=n $o.array
  echo "Field array name: [$n]"
  declare -n _arr="$n"
  printf '<%s>' "${_arr[@]}"
  printf '\n'
#  declare +n _arr                # release nameref
done

$a.close; $b.close

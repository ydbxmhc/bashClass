# Net.Socket

Plaintext TCP connection via bash's built-in `/dev/tcp` facility. Manages the
connection lifecycle — open, write, close — and exposes the raw file descriptor
so callers can read with standard bash primitives.

No TLS. `/dev/tcp` is plaintext only.

## Contents

- [Dependencies](#dependencies)
- [Constructor](#constructor)
- [Writing](#writing)
  - [$s.write str](#s-write-str)
  - [$s.writeLine str](#s-writeline-str)
- [Reading](#reading)
- [Lifecycle](#lifecycle)
  - [$s.close](#s-close)
- [Properties](#properties)
- [Example — HTTP/1.1 GET](#example--http11-get)
- [Limitations](#limitations)

---

## Dependencies

```bash
. boop Socket
```

---

## Constructor

```bash
into=s Socket.new host=example.com port=80
into=s Socket.new host=example.com port=80 timeout=10
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `host`    | yes      | —       | Hostname or IP address |
| `port`    | yes      | —       | Port number |
| `timeout` | no       | `30`    | Connection timeout in seconds |

Returns a Socket object. Fails with a non-zero exit code and an error message
if the connection cannot be established.

---

## Writing

### `$s.write str`

Write raw bytes — no newline appended. Use this when you control the exact
bytes on the wire, for example when building HTTP headers manually.

```bash
$s.write "GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
```

### `$s.writeLine str`

Write a line terminated with `\r\n`. Convenient for line-oriented protocols
(HTTP, SMTP, FTP, IRC) where each command ends with CRLF.

```bash
$s.writeLine "EHLO example.com"
$s.writeLine "QUIT"
```

---

## Reading

Reading is left to the caller. Retrieve the fd from the object's property and
use standard bash input redirection:

```bash
fd="${__boop_static[$s.fd]}"

# Line-by-line (HTTP response headers, SMTP greetings, etc.)
IFS= read -r status_line <&"$fd"
status_line="${status_line%$'\r'}"      # strip trailing \r

# Drain all remaining output (HTTP body, multi-line responses, etc.)
body=$(cat <&"$fd")
```

---

## Lifecycle

### `$s.close`

Close the file descriptor and mark the socket as closed. Idempotent — calling
it on an already-closed socket is safe.

```bash
$s.close
```

`_destroy` is registered automatically and runs `close` when the object is
garbage-collected, so explicit close is optional but recommended for
long-lived scripts.

---

## Properties

| Property | Type   | Description |
|----------|--------|-------------|
| `host`   | string | Hostname passed to the constructor |
| `port`   | string | Port passed to the constructor |
| `fd`     | int    | Open file descriptor number |
| `timeout`| int    | Timeout in seconds |
| `closed` | `0`/`1`| Whether `close` has been called |

```bash
fd="${__boop_static[$s.fd]}"
host="${__boop_static[$s.host]}"
```

---

## Example — HTTP/1.1 GET

```bash
. boop Socket

into=s Socket.new host=example.com port=80
fd="${__boop_static[$s.fd]}"

# Send request
$s.writeLine "GET / HTTP/1.1"
$s.writeLine "Host: example.com"
$s.writeLine "Connection: close"
$s.writeLine ""

# Read status line
IFS= read -r status <&"$fd"
status="${status%$'\r'}"
printf "Status: %s\n" "$status"

# Read and discard headers
while IFS= read -r header <&"$fd"; do
  header="${header%$'\r'}"
  [[ -z "$header" ]] && break
done

# Slurp body
body=$(cat <&"$fd")
printf "%s\n" "$body"

$s.close
```

---

## Limitations

**No TLS.** Bash's `/dev/tcp` opens a raw plaintext socket. For HTTPS or any
TLS-wrapped protocol, pipe through `openssl s_client` or use `curl`/`wget`
instead.

**NUL bytes.** Bash strings cannot hold **or detect** NUL bytes. Binary
responses that contain NUL will be silently truncated at the first NUL. Use
Socket only for text protocols.

**No async I/O.** `read` on the fd blocks until data arrives. There is no
built-in select/poll; for concurrent reads, use subshells or coprocesses.

**Port range.** The port argument must be a number in the range 1–65535.
No service name resolution (`http`, `smtp`, etc.).

---

[↑ Site map](index)

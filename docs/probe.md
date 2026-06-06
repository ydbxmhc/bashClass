# probe(1)

## NAME

**probe** — minimal plaintext HTTP client

## SYNOPSIS

```
probe [-X METHOD] [-d DATA] [-j] [-H HEADER]... [-i | -s | -o FILE]
      [-t SECONDS] [--no-follow] [-v] [-q] URL...
probe (-h | --help | --examples | --about)
```

## DESCRIPTION

**probe** fetches HTTP URLs using bash's `/dev/tcp` pseudo-device — no `curl`,
no `wget`, no external dependencies.

> **NUL bytes.** Bash variables cannot hold or detect NUL bytes. Any response
> body containing a NUL will be silently truncated at the first one. See
> LIMITATIONS.

It speaks HTTP/1.1 with
`Connection: close` and is intended for quick requests against local services,
internal APIs, and health checks.

It handles **plaintext HTTP only**. An `https://` URL is rejected with a clear
message — see LIMITATIONS.

The request method defaults to `GET`, or `POST` when a body is supplied with
`-d`. Multiple URLs may be given and are fetched in order.

## OPTIONS

### Request

| Short | Long | Argument | Meaning |
|-------|------|----------|---------|
| `-X` | `--method` | METHOD | HTTP method (default: GET, or POST with `-d`) |
| `-d` | `--data` | DATA | Request body; sets Content-Length and implies POST |
| `-j` | `--json` | — | Add `Content-Type: application/json` and `Accept: application/json` |
| `-H` | `--header` | "Name: Value" | Add a request header (repeatable) |

### Response

| Short | Long | Argument | Meaning |
|-------|------|----------|---------|
| (default) | | | Write the response body to stdout |
| `-i` | `--include` | — | Print the status line and headers before the body |
| `-s` | `--status` | — | Print only the numeric HTTP status code |
| `-o` | `--output` | FILE | Write the body to FILE instead of stdout |

`-s` is mutually exclusive with `-i` and `-o` (it suppresses the body).

### Connection

| Short | Long | Argument | Meaning |
|-------|------|----------|---------|
| `-t` | `--timeout` | SECONDS | Connection + read timeout (default 30) |
| | `--no-follow` | — | Do not follow 3xx redirects |

### Verbosity

| Short | Long | Meaning |
|-------|------|---------|
| `-v` | `--verbose` | Print the request headers to stderr (`>`-prefixed) |
| `-q` | `--quiet` | Suppress informational stderr messages |

### Help

| Short | Long | Meaning |
|-------|------|---------|
| `-h` | `--help` | Synopsis |
| | `--examples` | Cookbook |
| | `--about` | About probe |

## EXAMPLES

### Basic requests

```bash
probe http://example.com               # GET, body to stdout
probe -s http://example.com            # status code only (e.g. 200)
probe -i http://example.com            # status line + headers + body
probe -o page.html http://example.com  # body to a file
```

### POST and JSON

```bash
probe -d "name=Alice&age=30" http://host/form   # form POST (method implied)
probe -j -d '{"name":"Alice"}' http://host/users # JSON POST
probe -j http://host/data                         # GET with JSON Accept header
probe -X DELETE http://host/item/3                # explicit method
```

### Headers

```bash
probe -H "Authorization: Bearer TOKEN" http://host/me
probe -H "Accept: text/plain" -H "X-Custom: foo" http://host/
```

### Inspecting redirects

```bash
probe http://host/old-path            # follows the redirect to its target
probe --no-follow -s http://host/old  # stop at the 3xx, print its status
```

A relative `Location` (e.g. `/target`) is resolved against the current
request's scheme, host, and port before the next fetch; absolute
`http://…` Locations are used as-is.

### Debugging and timeouts

```bash
probe -v http://host/                 # show the request headers sent
probe -t 5 http://slow.host/          # 5-second timeout
probe http://a.host/ http://b.host/   # several URLs, fetched in order
```

## EXIT STATUS

- **0** — every request completed (a followed redirect counts as completion).
- **non-zero** — connection failure, timeout, no response, an `https://` URL
  (rejected), or any URL in a multi-URL invocation failing.

## LIMITATIONS

- **No HTTPS/TLS.** TLS belongs in a crypto library, not pure bash, so probe
  rejects `https://` up front rather than failing obscurely. For TLS, use
  `curl` or `wget`; the bundle/installer machinery can also fetch a richer
  client (see [TODO.md](../TODO.md)).
- **Text bodies only.** The body is slurped with `cat` into a bash variable
  (`$(...)`), which strips trailing newlines; bash variables also cannot hold
  NUL bytes. Binary responses are not preserved faithfully.
- **Pragmatic, not spec-complete.** probe follows the common redirect/parse
  cases, not every corner of HTTP/1.1.

## NOTES

probe is pure bash, built on the **boop** framework's `Net.Socket` and `Args`
classes. It began as a thought experiment — what can an OOP bash standard
library do with `/dev/tcp` alone? — and it is not competitive on speed or
completeness with `curl`. Its value is reach: it runs anywhere **bash 4.3+** is
present (with `/dev/tcp` support, standard on Linux/macOS and Git Bash), making
it a "consolation prize" drop-in for stripped containers and minimal images
where curl and wget are absent but a quick HTTP GET is still needed.

`Net.Socket` owns the connection lifecycle, timeouts, and read/write
primitives; probe owns URL parsing, request construction, redirect resolution,
and output formatting. The same socket layer is the foundation for a future
`Stream::Socket` with bidirectional multi-FD I/O. For repeated use, bundle
probe with `collider` (`collider probe` → `bundle-probe`).

## SEE ALSO

`curl(1)`, `wget(1)` — the fuller-featured clients probe stands in for.
[docs/Stream.md](Stream.md) for the planned socket-stream model,
[docs/tools.md](tools.md) for the tool family.

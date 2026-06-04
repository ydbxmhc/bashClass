# probe — Minimal HTTP Client

A small HTTP client built on bash `/dev/tcp`, via the `Net.Socket` class.
Plaintext **HTTP only** — there is no TLS, by design. For quick requests
against local services, internal APIs, and health checks where bringing in
`curl` is overkill or unavailable, probe is enough.

Built on `Net.Socket` and `Args`. HTTP/1.1 with `Connection: close`.

---

## Quick Start

```bash
probe http://example.com                  # GET, body to stdout
probe -s http://example.com               # status code only (e.g. 200)
probe -i http://example.com               # status line + headers + body
probe -d "name=Alice" http://host/form    # POST (auto when -d is present)
probe -j -d '{"x":1}' http://host/api     # JSON shorthand
```

Layered help: `--examples`, `--about`.

---

## Requests

### Method

GET by default. If `-d`/`--data` is given and no method is set, the method
becomes POST. Override explicitly with `-X`/`--method`.

```bash
probe http://host/page                 # GET
probe -d "a=1" http://host/submit      # POST
probe -X DELETE http://host/item/3     # explicit method
```

### Body and JSON

| Flag | Effect |
|------|--------|
| `-d`, `--data STRING` | Send STRING as the request body (sets Content-Length) |
| `-j`, `--json` | Add `Content-Type: application/json` and `Accept: application/json` |

```bash
probe -d "name=Alice&age=30" http://host/form
probe -j -d '{"name":"Alice"}' http://host/users
probe -j http://host/data              # just the JSON Accept/Content-Type headers
```

### Headers

`-H`/`--header` adds a request header. Repeatable.

```bash
probe -H "Authorization: Bearer TOKEN" http://host/me
probe -H "Accept: text/plain" -H "X-Custom: foo" http://host/
```

---

## Responses

| Flag | Effect |
|------|--------|
| (default) | Print the response body to stdout |
| `-i`, `--include` | Print the status line and headers before the body |
| `-s`, `--status` | Print only the numeric HTTP status code |
| `-o`, `--output FILE` | Write the body to FILE instead of stdout |

`-s` is mutually exclusive with `-i` and `-o` (it suppresses the body entirely).

```bash
probe -i http://host/                  # HTTP/1.1 200 OK ... + body
probe -s http://host/                  # 200
probe -o page.html http://host/        # body to a file
```

---

## Redirects

3xx responses are followed by default. `--no-follow` stops at the redirect so
you can inspect it.

A relative `Location` header (e.g. `/target` or `next.html` — the common case
for most servers) is resolved against the **current request's** scheme, host,
and port before the next fetch. Absolute `http://…` Locations are used as-is.

```bash
probe http://host/old-path             # follows the redirect to its target
probe --no-follow -s http://host/old   # 302 (stops, shows the status)
```

---

## Connection and Verbosity

| Flag | Effect |
|------|--------|
| `-t`, `--timeout N` | Connection + read timeout in seconds (default 30) |
| `--no-follow` | Do not follow 3xx redirects |
| `-v`, `--verbose` | Print the request headers to stderr (`> ` prefixed) |
| `-q`, `--quiet` | Suppress informational stderr messages |

```bash
probe -v http://host/                  # show what was sent
probe -t 5 http://slow.host/           # 5-second timeout
```

---

## Multiple URLs

Several URLs in one call are fetched in order. The exit status is non-zero if
any fetch fails.

```bash
probe http://a.host/ http://b.host/
```

---

## Exit Status

- 0 — all requests completed (including a followed redirect).
- non-zero — connection failure, timeout, no response, an HTTPS URL (rejected),
  or any URL in a multi-URL call failing.

---

## Limitations

- **No HTTPS/TLS.** An `https://` URL is rejected with a clear message. probe
  speaks plaintext HTTP over `/dev/tcp` only. For TLS, use curl or wget — or
  see the installer's `--fetch-probe`/cascade story in
  [TODO.md](../TODO.md) for how bundles bootstrap a richer fetch.
- **Text bodies.** The body is read line-oriented; bash variables cannot hold
  NUL, so binary responses are not preserved faithfully.
- **One redirect chain, simple parsing.** probe is a pragmatic client, not a
  spec-complete user agent. It handles the everyday cases.

---

## Design Notes

### Why /dev/tcp instead of curl

The point of probe is zero external dependencies. `Net.Socket` opens a TCP
connection through bash's `/dev/tcp` pseudo-device, so probe runs anywhere bash
does — including stripped containers and minimal images where curl isn't
installed. It is the "consolation prize" drop-in: not as capable as curl, but
present when curl isn't.

### Why no TLS

TLS in pure bash is not realistic — the handshake and crypto belong in a
library. Rather than half-implement it, probe is honest about being
plaintext-only and rejects HTTPS up front instead of failing obscurely. When
real TLS is needed, the bundle/installer machinery can fetch a tool that has
it.

### Relationship to Net.Socket

probe is a thin CLI over `Net.Socket`: the socket class owns connection
lifecycle, timeouts, and the read/write primitives; probe owns URL parsing,
request construction, redirect resolution, and output formatting. The same
socket layer is the foundation for a future `Stream::Socket` with full
bidirectional, multi-FD I/O (see [Stream.md](Stream.md) and TODO).

---
title: Net
---

# Net

Network I/O classes.

## Classes

| Class | Description |
|---|---|
| [Net.Socket](/docs/Socket) | Plaintext TCP connection via bash `/dev/tcp` — no TLS |

## Quick start

```bash
. boop Net::Socket

into=s Socket.new host=example.com port=80
fd="${__boop_static[$s.fd]}"

$s.writeLine "GET / HTTP/1.1"
$s.writeLine "Host: example.com"
$s.writeLine "Connection: close"
$s.writeLine ""

IFS= read -r status <&"$fd"
$s.close
```

→ [Full class reference](/docs/index)

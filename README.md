# quoted-printable-codec

Encodes and decodes RFC 2045 quoted-printable content with soft line breaks and `=XX` hex escapes. Pure-Python, standard-library only.

## Usage

```python
from quoted_printable_codec import encode, decode, encode_bytes, decode_to_bytes

encoded = encode("Héllo=World")           # str -> str
print(encoded)                            # "H=C3=A9llo=3DWorld\r\n"

decoded = decode(encoded)                 # str -> str (UTF-8)
print(decoded)                            # "Héllo=World\n"

raw = decode_to_bytes(encoded)            # str -> bytes
b = encode_bytes(b"\xff")                 # bytes -> str
```

## Why

The standard library's `quopri` module is adequate for most work but its handling of trailing whitespace and line endings is loose; this library takes a strict, predictable position for pipelines that round-trip data and want byte-for-byte reproducibility.

## Edge cases you will hit

- The decoder accepts only **uppercase** hex escapes (`=AB`, not `=ab`). The encoder always emits uppercase, and this keeps the decoder strict and predictable.
- Bare tab (`\t`) in input is always emitted as `=09`. RFC 2045 permits bare tab but warns it may be corrupted by transports; escaping is the safe choice.
- A final line terminator (`\r\n` by default) is always appended, even for empty input, following the RFC's CRLF convention.
- Soft line breaks (`=` at end of line) consume all whitespace between the `=` and the line break; you cannot preserve trailing whitespace before a soft break in quoted-printable.

from __future__ import annotations

from typing import List, Union

# RFC 2045 Section 6.7: max line length is 76 octets, including the CRLF.
# The soft-break "=" also counts toward the 76, so we have 75 data octets per line.
_MAX_LINE = 76
_SOFT_BREAK_MAX_DATA = _MAX_LINE - 1  # 75


def _is_printable_ascii_byte(b: int) -> bool:
    """RFC 2045: printable ASCII (33-126) minus '=', plus space and tab."""
    if b in (0x3D, 0x09, 0x20):
        return True
    return 33 <= b <= 126


def _hex_escape(b: int) -> str:
    return "=" + format(b, "02X")


def _push_line(out: List[str], line: str, keep_final_newline: bool) -> None:
    """Append a decoded line. Trailing CRLF-only lines are dropped unless this is
    the very last line (keep_final_newline), to preserve the trailing-newline
    convention established by input_helper."""
    if line == "" and not keep_final_newline:
        return
    out.append(line)


def encode_bytes(data: bytes, *, line_terminator: str = "\r\n") -> str:
    """Encode bytes into RFC 2045 quoted-printable text.

    Design decisions:
      * Trailing whitespace (space/tab) is always escaped as =09/=20, because RFC
        2045 explicitly forbids bare trailing whitespace on an encoded line — it
        would be stripped or mistaken for the soft-break indicator.
      * Tab (0x09) is always escaped (``=09``). RFC 2045 allows bare tab but
        warns its handling by mail transport is unreliable; escaping is safe.
      * Soft line breaks are inserted before a line would exceed 76 octets.
      * A single trailing ``line_terminator`` is always appended at the end (the
        standard CRLF convention), even for empty input.
    """
    if not isinstance(line_terminator, str) or line_terminator == "":
        raise ValueError("line_terminator must be a non-empty string")
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes-like")
    if isinstance(data, bytearray):
        data = bytes(data)

    pieces: List[str] = []
    col = 0

    for b in data:
        if b == 0x3D:
            tok = "=3D"
        elif b == 0x09:
            tok = "=09"
        elif b == 0x20:
            tok = "=20"
        elif 33 <= b <= 126:
            tok = chr(b)
        else:
            tok = _hex_escape(b)

        if col + len(tok) > _SOFT_BREAK_MAX_DATA:
            pieces.append("=")
            pieces.append(line_terminator)
            col = 0

        pieces.append(tok)
        col += len(tok)

    pieces.append(line_terminator)
    return "".join(pieces)


def _decode_hex_escape(s: str, pos: int) -> int:
    """Decode a =XX hex escape at position ``pos`` (pointing at '=').

    Raises ValueError if the escape is malformed (not two uppercase hex digits).
    We accept uppercase only, matching what encode_bytes produces and what strict
    RFC 2045 transport guarantees; this keeps the decoder predictable."""
    if pos + 2 > len(s) or s[pos] != "=":
        raise ValueError("bad hex escape")
    hi = s[pos + 1]
    lo = s[pos + 2]
    if hi not in "0123456789ABCDEF" or lo not in "0123456789ABCDEF":
        raise ValueError("bad hex escape")
    return int(hi, 16) * 16 + int(lo, 16)


def _decode_line(line: str) -> bytes:
    """Decode a single physical line (CRLF already stripped) to bytes."""
    out = bytearray()
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c == "=":
            out.append(_decode_hex_escape(line, i))
            i += 3
        elif ord(c) > 126:
            raise ValueError("non-ASCII byte in quoted-printable input")
        else:
            out.append(ord(c))
            i += 1
    return bytes(out)


def _strip_trailing_ws_after_soft_break(line: str) -> str:
    """Strip whitespace that appears after a trailing '=' (soft break marker).
    Whitespace before the '=' is meaningful data and is preserved."""
    stripped = line.rstrip(" \t")
    if stripped.endswith("="):
        return stripped
    return line


def _input_helper(data: str) -> str:
    """Normalize input: strip trailing whitespace after soft-break markers and
    convert line endings to LF. This ensures the decoder only sees clean lines."""
    if not isinstance(data, str):
        raise TypeError("data must be a str")
    out = []
    for i, raw_line in enumerate(data.splitlines()):
        clean = _strip_trailing_ws_after_soft_break(raw_line)
        out.append(clean)
    if not out:
        return ""
    return "\n".join(out) + "\n"


def decode_to_bytes(data: str) -> bytes:
    """Decode RFC 2045 quoted-printable text to bytes.

    Accepts a ``str``. Returns the decoded bytes. Soft line breaks (a trailing
    ``=`` immediately before a line ending) are consumed and do not appear in the
    output; hard line breaks become a single 0x0A byte in the output.
    """
    normalized = _input_helper(data)
    if normalized == "":
        return b""
    lines = normalized.split("\n")
    n = len(lines)
    out = bytearray()
    pending_concat = False
    for idx, line in enumerate(lines):
        is_last = (idx == n - 1)
        if line == "" and is_last:
            break
        if pending_concat and line == "":
            continue
        if line.endswith("="):
            line = line[:-1]
            pending_concat = True
        else:
            pending_concat = False
        decoded = _decode_line(line)
        out.extend(decoded)
        if not pending_concat and not is_last:
            out.append(0x0A)
    return bytes(out)


def encode(text: Union[str, bytes], *, line_terminator: str = "\r\n") -> str:
    """Encode text or bytes into RFC 2045 quoted-printable. UTF-8 is used for str."""
    if isinstance(text, str):
        b = text.encode("utf-8")
    elif isinstance(text, (bytes, bytearray)):
        b = bytes(text)
    else:
        raise TypeError("text must be str or bytes")
    return encode_bytes(b, line_terminator=line_terminator)


def decode(data: str) -> str:
    """Decode RFC 2045 quoted-printable to a str. Bytes are interpreted as UTF-8."""
    return decode_to_bytes(data).decode("utf-8")

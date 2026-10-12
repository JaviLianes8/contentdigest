"""Bare item parsing for RFC 9651 structured fields (section 4.2.3.1 onwards)."""

from __future__ import annotations

import binascii
import string
from collections.abc import Callable
from decimal import Decimal

from ._errors import DigestError


class Token(str):
    """An sf-token, kept apart from an sf-string."""


class DisplayString(str):
    """An sf-displaystring, kept apart from an sf-string."""


class Date(int):
    """An sf-date, kept apart from an sf-integer."""


BareItem = int | Decimal | str | bytes | bool

_DIGITS = frozenset(string.digits)
_ALPHA = frozenset(string.ascii_letters)
_LCALPHA = frozenset(string.ascii_lowercase)
_KEY_FIRST = _LCALPHA | {"*"}
_KEY_REST = _KEY_FIRST | _DIGITS | frozenset("_-.")
_TCHAR = _ALPHA | _DIGITS | frozenset("!#$%&'*+-.^_`|~")
_TOKEN_REST = _TCHAR | frozenset(":/")
_BASE64 = _ALPHA | _DIGITS | frozenset("+/=")
_LOWER_HEX = frozenset("0123456789abcdef")


class Reader:
    """A cursor over an ASCII field value; every parse step consumes from it."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def peek(self) -> str:
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def done(self) -> bool:
        return self.pos >= len(self.text)

    def skip(self, chars: str) -> None:
        while self.pos < len(self.text) and self.text[self.pos] in chars:
            self.pos += 1

    def fail(self, why: str) -> DigestError:
        return DigestError(f"{why} at offset {self.pos} of {self.text!r}")

    def key(self) -> str:
        start = self.pos
        if self.peek() not in _KEY_FIRST:
            raise self.fail("expected a key")
        while not self.done() and self.text[self.pos] in _KEY_REST:
            self.pos += 1
        return self.text[start : self.pos]

    def bare_item(self) -> BareItem:
        first = self.peek()
        if first == "-" or first in _DIGITS:
            return self.number()
        parsers: dict[str, Callable[[], BareItem]] = {
            '"': self.string,
            ":": self.byte_sequence,
            "?": self.boolean,
            "@": self.date,
            "%": self.display_string,
        }
        if first in parsers:
            return parsers[first]()
        if first in _ALPHA or first == "*":
            return self.token()
        raise self.fail("unrecognised item type")

    def number(self) -> int | Decimal:
        sign = 1
        if self.peek() == "-":
            self.pos += 1
            sign = -1
        if self.peek() not in _DIGITS:
            raise self.fail("expected a digit")
        start, is_decimal = self.pos, False
        while not self.done():
            char = self.text[self.pos]
            if char == "." and not is_decimal:
                if self.pos - start > 12:
                    raise self.fail("too many integer digits in a decimal")
                is_decimal = True
            elif char not in _DIGITS:
                break
            self.pos += 1
            # A decimal cannot pass its 16 character limit once the 12 and 3 digit checks hold.
            if not is_decimal and self.pos - start > 15:
                raise self.fail("integer too long")
        digits = self.text[start : self.pos]
        if not is_decimal:
            return sign * int(digits)
        if digits.endswith(".") or len(digits.partition(".")[2]) > 3:
            raise self.fail("malformed decimal")
        return sign * Decimal(digits)

    def string(self) -> str:
        self.pos += 1
        out: list[str] = []
        while not self.done():
            char = self.text[self.pos]
            self.pos += 1
            if char == "\\":
                escaped = self.peek()
                if escaped not in ('"', "\\"):
                    raise self.fail("bad escape in string")
                out.append(escaped)
                self.pos += 1
            elif char == '"':
                return "".join(out)
            elif not " " <= char <= "~":
                raise self.fail("control character in string")
            else:
                out.append(char)
        raise self.fail("unterminated string")

    def token(self) -> Token:
        start = self.pos
        self.pos += 1
        while not self.done() and self.text[self.pos] in _TOKEN_REST:
            self.pos += 1
        return Token(self.text[start : self.pos])

    def byte_sequence(self) -> bytes:
        end = self.text.find(":", self.pos + 1)
        if end < 0:
            raise self.fail("unterminated byte sequence")
        content = self.text[self.pos + 1 : end]
        if not _BASE64.issuperset(content):
            raise self.fail("character outside the base64 alphabet")
        data = content.rstrip("=")
        # Missing padding, padding up to "==" and non-zero pad bits are accepted, as section
        # 4.2.7 asks; "=" inside the data or a length no encoder produces is not.
        if "=" in data or len(content) - len(data) > 2 or len(data) % 4 == 1:
            raise self.fail("malformed base64")
        self.pos = end + 1
        return binascii.a2b_base64(data + "=" * (-len(data) % 4))

    def boolean(self) -> bool:
        value = self.text[self.pos + 1 : self.pos + 2]
        if value not in ("0", "1"):
            raise self.fail("expected ?0 or ?1")
        self.pos += 2
        return value == "1"

    def date(self) -> Date:
        self.pos += 1
        value = self.number()
        if isinstance(value, Decimal):
            raise self.fail("a date must be an integer")
        return Date(value)

    def display_string(self) -> DisplayString:
        if self.text[self.pos : self.pos + 2] != '%"':
            raise self.fail('expected %"')
        self.pos += 2
        raw = bytearray()
        while not self.done():
            char = self.text[self.pos]
            self.pos += 1
            if not " " <= char <= "~":
                raise self.fail("control character in display string")
            if char == '"':
                try:
                    return DisplayString(raw.decode("utf-8"))
                except UnicodeDecodeError:
                    raise self.fail("display string is not UTF-8") from None
            if char == "%":
                octet = self.text[self.pos : self.pos + 2]
                if len(octet) != 2 or not _LOWER_HEX.issuperset(octet):
                    raise self.fail("bad percent escape")
                raw.append(int(octet, 16))
                self.pos += 2
            else:
                raw.append(ord(char))
        raise self.fail("unterminated display string")

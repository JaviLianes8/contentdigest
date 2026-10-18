"""Seeded generators of structured-field text, valid and broken, for the fuzz and oracle tests.

Written from the RFC 9651 grammar (section 3 and the parsing rules of section 4.2), so they
produce mostly valid fields, plus the byte-sequence padding variants of section 4.2.7, and
then random edits that break them.
"""

from __future__ import annotations

import base64
import random

LCALPHA = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
ALPHA = LCALPHA + LCALPHA.upper()
TCHAR = ALPHA + DIGITS + "!#$%&'*+-.^_`|~"
# Characters an edit inserts: the grammar's delimiters, odd whitespace, non-ASCII.
HOSTILE = ' \t,;=()":?@%*\\/+-.0123456789aZ_\x00\x7f\n\r\xe9\xff'


def key(rng: random.Random) -> str:
    rest = LCALPHA + DIGITS + "_-.*"
    return rng.choice(LCALPHA + "*") + "".join(rng.choice(rest) for _ in range(rng.randrange(8)))


def byte_sequence(rng: random.Random) -> str:
    content = base64.b64encode(rng.randbytes(rng.randrange(0, 40))).decode()
    variant = rng.randrange(8)
    if variant == 0:
        content = content.rstrip("=")  # missing padding (RFC 9651 4.2.7 leniency)
    elif variant == 1 and content:
        content += "="  # one "=" beyond the padding, as RFC 9530 prints
    elif variant == 2 and content.endswith("="):
        data = content.rstrip("=")
        bits = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        last = bits.index(data[-1])
        content = data[:-1] + bits[last | 1] + content[len(data) :]  # non-zero pad bits
    return f":{content}:"


def bare_item(rng: random.Random) -> str:
    kind = rng.randrange(9)
    if kind == 0:
        return str(rng.randrange(-(10**15) + 1, 10**15))
    if kind == 1:
        sign = "-" if rng.random() < 0.3 else ""
        fraction = str(rng.randrange(1000)).zfill(rng.randrange(1, 4))
        return f"{sign}{rng.randrange(10**12)}.{fraction}"
    if kind == 2:
        chars = [rng.choice(['\\"', "\\\\", "a", " ", "~", "x"]) for _ in range(rng.randrange(10))]
        return '"' + "".join(chars) + '"'
    if kind == 3:
        rest = TCHAR + ":/"
        return rng.choice(ALPHA + "*") + "".join(rng.choice(rest) for _ in range(rng.randrange(8)))
    if kind == 4:
        return rng.choice(["?0", "?1"])
    if kind == 5:
        # Mostly dates a datetime can hold; sometimes anywhere in the integer range.
        if rng.random() < 0.1:
            return f"@{rng.randrange(-(10**15) + 1, 10**15)}"
        return f"@{rng.randrange(0, 4 * 10**9)}"
    if kind == 6:
        text = "".join(rng.choice(["a", " ", "%c3%a9", "%e2%82%ac", "%25", "~"]) for _ in range(6))
        return f'%"{text}"'
    return byte_sequence(rng)


def parameters(rng: random.Random) -> str:
    out = ""
    for _ in range(rng.choice([0, 0, 0, 1, 2])):
        out += ";" + " " * rng.choice([0, 0, 1]) + key(rng)
        if rng.random() < 0.7:
            out += "=" + bare_item(rng)
    return out


def member(rng: random.Random) -> str:
    if rng.random() < 0.15:
        items = [bare_item(rng) + parameters(rng) for _ in range(rng.randrange(4))]
        return "(" + " " * rng.choice([0, 1]) + " ".join(items) + ")" + parameters(rng)
    return bare_item(rng) + parameters(rng)


def dictionary(rng: random.Random, size: int | None = None) -> str:
    """A dictionary field value: mostly valid, keys sometimes repeated or valueless."""
    members = []
    for _ in range(rng.randrange(1, 6) if size is None else size):
        name = key(rng)
        members.append(name + parameters(rng) if rng.random() < 0.1 else f"{name}={member(rng)}")
    separators = [",", ", ", " ,", ",\t", "\t, "]
    text = members[0]
    for item in members[1:]:
        text += rng.choice(separators) + item
    return " " * rng.choice([0, 0, 1]) + text + " " * rng.choice([0, 0, 1])


def mutate(rng: random.Random, text: str) -> str:
    """Apply one to three random edits: insert, delete, replace or duplicate a span."""
    for _ in range(rng.randrange(1, 4)):
        at = rng.randrange(len(text) + 1)
        edit = rng.randrange(4)
        if edit == 0:
            text = text[:at] + rng.choice(HOSTILE) + text[at:]
        elif edit == 1 and text:
            text = text[:at] + text[at + 1 :]
        elif edit == 2 and text:
            text = text[:at] + rng.choice(HOSTILE) + text[at + 1 :]
        else:
            text = text[:at] + text[at : at + rng.randrange(1, 6)] + text[at:]
    return text

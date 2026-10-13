"""Parse RFC 9651 structured field values: dictionaries, lists and items (section 4.2)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

from ._sf_items import BareItem, Reader

Params = dict[str, BareItem]
Item = tuple[BareItem, Params]
InnerList = tuple[list[Item], Params]
Member = Item | InnerList

#: A field value as a server or client hands it over: text, raw bytes, or several lines.
FieldValue = str | bytes | Iterable[str | bytes]

_OWS = " \t"
_T = TypeVar("_T")


def combine(field: FieldValue) -> str:
    """Join field lines with commas (RFC 9110 section 5.3) into one string."""
    if isinstance(field, (str, bytes, bytearray)):
        lines: list[str | bytes | bytearray] = [field]
    else:
        lines = list(field)
    texts: list[str] = []
    for line in lines:
        # Non-ASCII needs no check here, in str or bytes: no rule of the grammar accepts such a
        # character, so the parser rejects it. Latin-1 maps every byte to one character.
        if isinstance(line, (bytes, bytearray)):
            line = bytes(line).decode("latin-1")
        elif not isinstance(line, str):
            raise TypeError(f"a field line must be str or bytes, not {type(line).__name__}")
        texts.append(line)
    return ", ".join(texts)


def parse_dictionary(field: FieldValue) -> dict[str, Member]:
    """Parse a whole field as an sf-dictionary; an empty field is an empty dictionary."""
    return _parse(combine(field), _dictionary)


def parse_list(field: FieldValue) -> list[Member]:
    """Parse a whole field as an sf-list."""
    return _parse(combine(field), _list)


def parse_item(field: FieldValue) -> Item:
    """Parse a whole field as an sf-item."""
    return _parse(combine(field), _item)


def _parse(text: str, rule: Callable[[Reader], _T]) -> _T:
    reader = Reader(text)
    reader.skip(" ")
    result = rule(reader)
    reader.skip(" ")
    if not reader.done():
        raise reader.fail("unexpected character")
    return result


def _item(reader: Reader) -> Item:
    return reader.bare_item(), _params(reader)


def _params(reader: Reader) -> Params:
    params: Params = {}
    while reader.peek() == ";":
        reader.pos += 1
        reader.skip(" ")
        key = reader.key()
        value: BareItem = True
        if reader.peek() == "=":
            reader.pos += 1
            value = reader.bare_item()
        params[key] = value
    return params


def _member(reader: Reader) -> Member:
    if reader.peek() != "(":
        return _item(reader)
    reader.pos += 1
    items: list[Item] = []
    while not reader.done():
        reader.skip(" ")
        if reader.peek() == ")":
            reader.pos += 1
            return items, _params(reader)
        items.append(_item(reader))
        if reader.peek() not in (" ", ")"):
            raise reader.fail("expected a space or ) in an inner list")
    raise reader.fail("unterminated inner list")


def _separator(reader: Reader) -> bool:
    """Consume the comma between members; return False at the end of the input."""
    reader.skip(_OWS)
    if reader.done():
        return False
    if reader.peek() != ",":
        raise reader.fail("expected a comma")
    reader.pos += 1
    reader.skip(_OWS)
    if reader.done():
        raise reader.fail("trailing comma")
    return True


def _list(reader: Reader) -> list[Member]:
    members: list[Member] = []
    while not reader.done():
        members.append(_member(reader))
        if not _separator(reader):
            break
    return members


def _dictionary(reader: Reader) -> dict[str, Member]:
    members: dict[str, Member] = {}
    while not reader.done():
        key = reader.key()
        if reader.peek() == "=":
            reader.pos += 1
            members[key] = _member(reader)
        else:
            members[key] = (True, _params(reader))
        if not _separator(reader):
            break
    return members

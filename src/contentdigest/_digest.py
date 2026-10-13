"""Build and verify Content-Digest and Repr-Digest field values (RFC 9530 sections 2, 3)."""

from __future__ import annotations

import base64
import hmac
from collections.abc import Iterable
from typing import TYPE_CHECKING

from ._algorithms import ACTIVE_ALGORITHMS, algorithm_names, as_view, new_hasher
from ._errors import DigestError
from ._sf import FieldValue, parse_dictionary

if TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 12):
        from collections.abc import Buffer
    else:
        from typing_extensions import Buffer


class Digester:
    """Compute a digest field value over a body fed in chunks.

    ``algos`` are registry keys such as ``"sha-256"`` (any case); the value lists them in
    that order, each once.
    """

    def __init__(self, algos: Iterable[str] = ("sha-256",)) -> None:
        names = algorithm_names(algos, "algos")
        if not names:
            raise DigestError("at least one algorithm is required")
        self._hashers = {name: new_hasher(name) for name in names}

    def update(self, data: Buffer) -> None:
        """Feed the next chunk of the body."""
        view = as_view(data)
        for hasher in self._hashers.values():
            hasher.update(view)

    def digests(self) -> dict[str, bytes]:
        """The raw digest of everything fed so far, by algorithm; more chunks may follow."""
        return {name: hasher.digest() for name, hasher in self._hashers.items()}

    def value(self) -> str:
        """The field value for everything fed so far, as an RFC 9651 dictionary."""
        return ", ".join(
            f"{name}=:{base64.b64encode(digest).decode('ascii')}:"
            for name, digest in self.digests().items()
        )


class Verifier:
    """Check a body fed in chunks against a received digest field.

    The field is read first, as headers arrive before the body. Only algorithms in
    ``accept`` are checked (by default the registry's Active ones); every accepted member
    present must match. :class:`DigestError` is raised if the field is malformed or none of
    its members is accepted.
    """

    def __init__(self, field: FieldValue, *, accept: Iterable[str] = ACTIVE_ALGORITHMS) -> None:
        accepted = algorithm_names(accept, "accept")
        received = parse(field)
        self._expected = {name: digest for name, digest in received.items() if name in accepted}
        if not self._expected:
            raise DigestError(
                f"no accepted algorithm in the field (it has {sorted(received)}, "
                f"accepted are {sorted(accepted)})"
            )
        self._digester = Digester(self._expected)

    @property
    def algorithms(self) -> tuple[str, ...]:
        """The algorithms that will be checked, in field order."""
        return tuple(self._expected)

    def update(self, data: Buffer) -> None:
        """Feed the next chunk of the body."""
        self._digester.update(data)

    def verify(self) -> bool:
        """Whether everything fed so far matches every accepted digest in the field."""
        actual = self._digester.digests()
        # Every comparison runs, in constant time, so timing does not reveal which failed.
        results = [hmac.compare_digest(digest, actual[n]) for n, digest in self._expected.items()]
        return all(results)


def make_digest(body: Buffer, algos: Iterable[str] = ("sha-256",)) -> str:
    """Return a Content-Digest or Repr-Digest field value for ``body`` over ``algos``."""
    digester = Digester(algos)
    digester.update(body)
    return digester.value()


def parse(field: FieldValue) -> dict[str, bytes]:
    """Parse a digest field into raw digest bytes by algorithm key, in field order.

    ``field`` is a ``str``, ASCII ``bytes`` or an iterable of field lines, which are joined
    with commas. Every member is returned, including algorithms this library does not know.
    Parameters are ignored. An empty field gives an empty dict. A member whose value is not
    a byte sequence makes the whole field invalid (RFC 9651 section 2.2).
    """
    result: dict[str, bytes] = {}
    for key, (value, _params) in parse_dictionary(field).items():
        if type(value) is not bytes:
            raise DigestError(f"the value of {key!r} is not a byte sequence")
        result[key] = value
    return result


def verify(field: FieldValue, body: Buffer, *, accept: Iterable[str] = ACTIVE_ALGORITHMS) -> bool:
    """Return whether every accepted digest in ``field`` matches ``body``.

    See :class:`Verifier` for what is accepted and when :class:`DigestError` is raised.
    """
    verifier = Verifier(field, accept=accept)
    verifier.update(body)
    return verifier.verify()

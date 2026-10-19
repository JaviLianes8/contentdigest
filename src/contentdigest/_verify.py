"""Check a body against a received Content-Digest or Repr-Digest field (RFC 9530 section 5)."""

from __future__ import annotations

import hmac
from collections.abc import Iterable

from ._algorithms import ACTIVE_ALGORITHMS, algorithm_names
from ._digest import Digester, parse
from ._errors import DigestError, listing
from ._sf import FieldValue
from ._types import Buffer


class Verifier:
    """Check a body fed in chunks against a received digest field.

    The field is read first, as headers arrive before the body. Only algorithms in
    ``accept`` are checked (by default the registry's Active ones); every accepted member
    present must match. :class:`DigestError` is raised if the field is malformed or none of
    its members is accepted, since then there is nothing to check.

    >>> from contentdigest import Verifier, make_digest
    >>> verifier = Verifier(make_digest(b'{"hello": "world"}', algos=["md5", "sha-256"]))
    >>> verifier.algorithms  # md5 is Deprecated, so it is not checked by default
    ('sha-256',)
    >>> verifier.update(b'{"hello": ')
    >>> verifier.update(b'"world"}')
    >>> verifier.verify()
    True
    """

    def __init__(self, field: FieldValue, *, accept: Iterable[str] = ACTIVE_ALGORITHMS) -> None:
        accepted = algorithm_names(accept, "accept")
        received = parse(field)
        self._expected = {name: digest for name, digest in received.items() if name in accepted}
        if not self._expected:
            raise DigestError(
                f"no accepted algorithm in the field (it has {listing(list(received))}; "
                f"accepted are {listing(sorted(set(accepted)))})"
            )
        self._digester = Digester(self._expected)

    @property
    def algorithms(self) -> tuple[str, ...]:
        """The algorithms that will be checked, in field order.

        >>> from contentdigest import Verifier, make_digest
        >>> field = make_digest(b"", algos=["crc32c", "sha-512", "sha-256"])
        >>> Verifier(field).algorithms
        ('sha-512', 'sha-256')
        """
        return tuple(self._expected)

    def update(self, data: Buffer) -> None:
        """Feed the next chunk of the body: any bytes-like object, not ``str``.

        >>> from contentdigest import Verifier
        >>> verifier = Verifier("sha-256=:47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=:")
        >>> verifier.update(b"")
        >>> verifier.verify()
        True
        """
        self._digester.update(data)

    def verify(self) -> bool:
        """Whether everything fed so far matches every accepted digest in the field.

        More chunks may follow, so it can be called again.

        >>> from contentdigest import Verifier
        >>> verifier = Verifier("sha-256=:47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=:")
        >>> verifier.verify()
        True
        >>> verifier.update(b"x")
        >>> verifier.verify()
        False
        """
        actual = self._digester.digests()
        # Every comparison runs, in constant time, so timing does not reveal which failed.
        results = [hmac.compare_digest(digest, actual[n]) for n, digest in self._expected.items()]
        return all(results)


def verify(field: FieldValue, body: Buffer, *, accept: Iterable[str] = ACTIVE_ALGORITHMS) -> bool:
    """Return whether every accepted digest in ``field`` matches ``body``.

    See :class:`Verifier` for what is accepted and when :class:`DigestError` is raised.

    >>> from contentdigest import verify
    >>> field = "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"
    >>> verify(field, b'{"hello": "world"}'), verify(field, b"tampered")
    (True, False)
    >>> verify("md5=:Sd/dVLAcvNLSq16eXua5uQ==:", b'{"hello": "world"}', accept=["md5"])
    True
    """
    verifier = Verifier(field, accept=accept)
    verifier.update(body)
    return verifier.verify()

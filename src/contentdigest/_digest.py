"""Build and read Content-Digest and Repr-Digest field values (RFC 9530 sections 2, 3)."""

from __future__ import annotations

import base64
from collections.abc import Iterable

from ._algorithms import algorithm_names, as_view, new_hasher
from ._errors import DigestError, excerpt
from ._sf import FieldValue, parse_dictionary
from ._types import Buffer


class Digester:
    """Compute a digest field value over a body fed in chunks.

    ``algos`` are registry keys such as ``"sha-256"``, in any case; the value lists each one
    once, in the order given. :class:`DigestError` is raised for an unsupported algorithm or
    an empty collection, :class:`TypeError` for a bare string or a name that is not a string.

    >>> from contentdigest import Digester
    >>> digester = Digester(["sha-256", "crc32c"])
    >>> digester.update(b'{"hello": ')
    >>> digester.update(b'"world"}')
    >>> print(digester.value())
    sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:, crc32c=:Q3lHIA==:
    """

    def __init__(self, algos: Iterable[str] = ("sha-256",)) -> None:
        names = algorithm_names(algos, "algos")
        if not names:
            raise DigestError("at least one algorithm is required")
        self._hashers = {name: new_hasher(name) for name in names}

    def update(self, data: Buffer) -> None:
        """Feed the next chunk of the body: any bytes-like object, not ``str``.

        >>> from contentdigest import Digester, make_digest
        >>> digester = Digester()
        >>> digester.update(b"ab")
        >>> digester.update(bytearray(b"c"))
        >>> digester.value() == make_digest(b"abc")
        True
        """
        view = as_view(data)
        for hasher in self._hashers.values():
            hasher.update(view)

    def digests(self) -> dict[str, bytes]:
        """The raw digest of everything fed so far, by algorithm; more chunks may follow.

        >>> from contentdigest import Digester
        >>> digester = Digester(["sha-256", "unixsum"])
        >>> digester.update(b'{"hello": "world"}')
        >>> {name: digest.hex() for name, digest in digester.digests().items()}["unixsum"]
        '1905'
        """
        return {name: hasher.digest() for name, hasher in self._hashers.items()}

    def value(self) -> str:
        """The field value for everything fed so far, as an RFC 9651 dictionary.

        >>> from contentdigest import Digester
        >>> Digester().value()  # nothing fed yet: the digest of the empty body
        'sha-256=:47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=:'
        """
        return ", ".join(
            f"{name}=:{base64.b64encode(digest).decode('ascii')}:"
            for name, digest in self.digests().items()
        )


def make_digest(body: Buffer, algos: Iterable[str] = ("sha-256",)) -> str:
    """Return a Content-Digest or Repr-Digest field value for ``body`` over ``algos``.

    ``body`` is any bytes-like object; see :class:`Digester` for ``algos``.

    >>> from contentdigest import make_digest
    >>> make_digest(b'{"hello": "world"}')
    'sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:'
    >>> make_digest(b'{"hello": "world"}', algos=["md5", "adler"])
    'md5=:Sd/dVLAcvNLSq16eXua5uQ==:, adler=:OZkGFw==:'
    """
    digester = Digester(algos)
    digester.update(body)
    return digester.value()


def parse(field: FieldValue) -> dict[str, bytes]:
    r"""Parse a digest field into raw digest bytes by algorithm key, in field order.

    ``field`` is a ``str``, ASCII ``bytes`` or ``bytearray``, or an iterable of field lines,
    which are joined with commas. Every member is returned, including algorithms this
    library does not know. Parameters are ignored and a repeated key keeps its last value.
    An empty field gives an empty dict. A malformed field, or a member whose value is not a
    byte sequence, raises :class:`DigestError` for the whole field (RFC 9651 section 2.2).

    >>> from contentdigest import parse
    >>> digests = parse(["md5=:Sd/dVLAcvNLSq16eXua5uQ==:;x=1", b"new=:AQID:"])
    >>> list(digests), digests["new"]
    (['md5', 'new'], b'\x01\x02\x03')
    """
    result: dict[str, bytes] = {}
    for key, (value, _params) in parse_dictionary(field).items():
        if type(value) is not bytes:
            raise DigestError(f"the value of {excerpt(key)} is not a byte sequence")
        result[key] = value
    return result

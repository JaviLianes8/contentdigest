"""Build and verify RFC 9530 digest fields and their preference fields, zero dependencies.

The algorithms of the IANA "Hash Algorithms for HTTP Digest Fields" registry, by status:
``ACTIVE_ALGORITHMS`` (safe where an attacker may tamper with the content),
``DEPRECATED_ALGORITHMS`` (only against accidental corruption) and ``SUPPORTED_ALGORITHMS``
(both). Each is a ``frozenset`` of registry keys.

>>> from contentdigest import ACTIVE_ALGORITHMS, DEPRECATED_ALGORITHMS, SUPPORTED_ALGORITHMS
>>> sorted(ACTIVE_ALGORITHMS)
['sha-256', 'sha-512']
>>> sorted(DEPRECATED_ALGORITHMS)
['adler', 'crc32c', 'md5', 'sha', 'unixcksum', 'unixsum']
>>> SUPPORTED_ALGORITHMS == ACTIVE_ALGORITHMS | DEPRECATED_ALGORITHMS
True
"""

from ._algorithms import ACTIVE_ALGORITHMS, DEPRECATED_ALGORITHMS, SUPPORTED_ALGORITHMS
from ._digest import Digester, make_digest, parse
from ._errors import DigestError
from ._verify import Verifier, verify
from ._want import choose_algorithm, make_want, parse_want

__version__ = "1.0.0"

# The public classes and functions show and pickle as contentdigest.<name>, so nothing outside
# depends on the private module that defines them. Methods follow, so doctest finds them here.
for _function in (choose_algorithm, make_digest, make_want, parse, parse_want, verify):
    _function.__module__ = __name__
for _cls in (Digester, DigestError, Verifier):
    _cls.__module__ = __name__
    for _member in vars(_cls).values():
        if callable(_member) and getattr(_member, "__module__", "").startswith(__name__ + "._"):
            _member.__module__ = __name__
del _function, _cls, _member

__all__ = [
    "ACTIVE_ALGORITHMS",
    "DEPRECATED_ALGORITHMS",
    "SUPPORTED_ALGORITHMS",
    "DigestError",
    "Digester",
    "Verifier",
    "choose_algorithm",
    "make_digest",
    "make_want",
    "parse",
    "parse_want",
    "verify",
]

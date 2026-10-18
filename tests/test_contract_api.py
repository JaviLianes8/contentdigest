"""The complete public surface: signatures, type hints, examples, names and pickles."""

from __future__ import annotations

import doctest
import inspect
import pickle
import typing
from collections.abc import Callable
from typing import Any

import pytest

import contentdigest
from contentdigest import (
    ACTIVE_ALGORITHMS,
    Digester,
    DigestError,
    Verifier,
    choose_algorithm,
    make_digest,
    make_want,
    parse,
    parse_want,
    verify,
)

P = inspect.Parameter
EMPTY = P.empty
POS, KW = P.POSITIONAL_OR_KEYWORD, P.KEYWORD_ONLY
SELF = ("self", POS, EMPTY, EMPTY)

# (name, kind, default, annotation) per parameter, then the return annotation. A frozenset
# default is compared by value: its repr changes order from one run to the next.
SIGNATURES: dict[str, tuple[Callable[..., Any], list[tuple[Any, ...]], Any]] = {
    "make_digest": (
        make_digest,
        [("body", POS, EMPTY, "Buffer"), ("algos", POS, ("sha-256",), "Iterable[str]")],
        "str",
    ),
    "parse": (parse, [("field", POS, EMPTY, "FieldValue")], "dict[str, bytes]"),
    "verify": (
        verify,
        [
            ("field", POS, EMPTY, "FieldValue"),
            ("body", POS, EMPTY, "Buffer"),
            ("accept", KW, ACTIVE_ALGORITHMS, "Iterable[str]"),
        ],
        "bool",
    ),
    "parse_want": (parse_want, [("field", POS, EMPTY, "FieldValue")], "dict[str, int]"),
    "make_want": (make_want, [("preferences", POS, EMPTY, "Mapping[str, int]")], "str"),
    "choose_algorithm": (
        choose_algorithm,
        [
            ("field", POS, EMPTY, "FieldValue | None"),
            ("supported", POS, ACTIVE_ALGORITHMS, "Iterable[str]"),
        ],
        "str | None",
    ),
    "Digester": (
        Digester.__init__,
        [SELF, ("algos", POS, ("sha-256",), "Iterable[str]")],
        "None",
    ),
    "Digester.update": (Digester.update, [SELF, ("data", POS, EMPTY, "Buffer")], "None"),
    "Digester.digests": (Digester.digests, [SELF], "dict[str, bytes]"),
    "Digester.value": (Digester.value, [SELF], "str"),
    "Verifier": (
        Verifier.__init__,
        [
            SELF,
            ("field", POS, EMPTY, "FieldValue"),
            ("accept", KW, ACTIVE_ALGORITHMS, "Iterable[str]"),
        ],
        "None",
    ),
    "Verifier.update": (Verifier.update, [SELF, ("data", POS, EMPTY, "Buffer")], "None"),
    "Verifier.verify": (Verifier.verify, [SELF], "bool"),
}
METHODS = [name for name in SIGNATURES if "." in name] + ["Verifier.algorithms"]
PICKLES_FROM_0_2_0 = [
    # contentdigest 0.2.0 from PyPI: pickle.dumps(DigestError("bad field"), protocol=0 and 4).
    "63636f6e74656e746469676573742e5f6572726f72730a4469676573744572726f720a70300a2856626164"
    "206669656c640a70310a7470320a5270330a2e",
    "80049539000000000000008c15636f6e74656e746469676573742e5f6572726f7273948c0b446967657374"
    "4572726f729493948c09626164206669656c6494859452942e",
]


@pytest.mark.parametrize("name", sorted(SIGNATURES))
def test_signatures_are_pinned(name: str) -> None:
    function, parameters, returns = SIGNATURES[name]
    signature = inspect.signature(function)
    found = [(p.name, p.kind, p.default, p.annotation) for p in signature.parameters.values()]
    assert found == parameters
    assert signature.return_annotation == returns


def _member(name: str) -> Any:
    owner, _, attribute = name.partition(".")
    target = getattr(contentdigest, owner)
    return inspect.getattr_static(target, attribute) if attribute else target


@pytest.mark.parametrize("name", sorted(SIGNATURES))
def test_type_hints_resolve_at_run_time(name: str) -> None:
    hints = typing.get_type_hints(SIGNATURES[name][0])
    assert set(hints) == {p[0] for p in SIGNATURES[name][1] if p[0] != "self"} | {"return"}


def test_the_algorithms_property_is_typed() -> None:
    getter = _member("Verifier.algorithms").fget
    assert typing.get_type_hints(getter) == {"return": tuple[str, ...]}


@pytest.mark.parametrize("name", [*contentdigest.__all__, *METHODS])
def test_every_public_name_has_a_runnable_example(name: str) -> None:
    target = _member(name)
    if isinstance(target, frozenset):
        # The constants cannot carry a docstring; the package docstring shows each one.
        doc = contentdigest.__doc__ or ""
        assert f">>> sorted({name})" in doc or f"{name} ==" in doc, name
    else:
        assert ">>> " in (inspect.getdoc(target) or ""), name


def test_doctests_are_collected_once_at_the_package_top() -> None:
    found = {test.name for test in doctest.DocTestFinder().find(contentdigest) if test.examples}
    expected = {"Digester", "Digester.update", "Digester.digests", "Digester.value"}
    expected |= {"Verifier", "Verifier.algorithms", "Verifier.update", "Verifier.verify"}
    assert found == {"contentdigest"} | {
        f"contentdigest.{name}" for name in [*expected, "DigestError"]
    }


def test_all_is_exactly_the_public_attributes() -> None:
    public = sorted(name for name in dir(contentdigest) if not name.startswith("_"))
    assert sorted(contentdigest.__all__) == public
    assert not {"_cls", "_member", "annotations"} & set(vars(contentdigest))


@pytest.mark.parametrize("cls", [DigestError, Digester, Verifier])
def test_public_classes_show_as_package_names(cls: type) -> None:
    assert cls.__module__ == "contentdigest"
    assert repr(cls) == f"<class 'contentdigest.{cls.__name__}'>"


def test_digest_error_pickles_by_its_public_name() -> None:
    error = DigestError("bad field")
    data = pickle.dumps(error)
    assert b"contentdigest._errors" not in data
    again = pickle.loads(data)
    assert (type(again), again.args) == (DigestError, ("bad field",))


@pytest.mark.parametrize("hex_data", PICKLES_FROM_0_2_0)
def test_pickles_written_by_0_2_0_still_load(hex_data: str) -> None:
    again = pickle.loads(bytes.fromhex(hex_data))
    assert (type(again), again.args) == (DigestError, ("bad field",))

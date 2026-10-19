"""The PyPI release 0.2.0 as an oracle: 1.0.0 answers the same, except where documented.

Set CONTENTDIGEST_V02 to a folder holding the 0.2.0 package (for example the unpacked wheel:
`pip download contentdigest==0.2.0 --no-deps`, then unzip it); the tests skip otherwise.
Only error families are compared, since 1.0.0 shortens messages on purpose.
"""

from __future__ import annotations

import importlib.util
import os
import pickle
import random
import sys
import typing
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import generators
import pytest

import contentdigest

ALGOS = sorted(contentdigest.SUPPORTED_ALGORITHMS)


@pytest.fixture(scope="module")
def old() -> ModuleType:
    folder = os.environ.get("CONTENTDIGEST_V02")
    if not folder:
        pytest.skip("set CONTENTDIGEST_V02 to the unpacked 0.2.0 release")
    init = Path(folder) / "contentdigest" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "contentdigest_v02", init, submodule_search_locations=[str(init.parent)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["contentdigest_v02"] = module
    spec.loader.exec_module(module)
    assert module.__version__ == "0.2.0"
    return module


def _outcome(module: ModuleType, name: str, *args: Any, **kwargs: Any) -> object:
    try:
        return getattr(module, name)(*args, **kwargs)
    except Exception as error:
        kind = type(error).__name__
        return ("raised", kind if kind == "DigestError" else type(error).__mro__[0].__name__)


def _same(old: ModuleType, name: str, *args: Any, **kwargs: Any) -> None:
    assert _outcome(old, name, *args, **kwargs) == _outcome(contentdigest, name, *args, **kwargs), (
        name,
        args,
        kwargs,
    )


def test_fields_read_the_same(old: ModuleType) -> None:
    rng = random.Random(20)
    for _ in range(6000):
        text = generators.dictionary(rng)
        text = generators.mutate(rng, text) if rng.random() < 0.5 else text
        for name in ("parse", "parse_want"):
            _same(old, name, text)
        _same(old, "choose_algorithm", text, supported=ALGOS)
        _same(old, "verify", text, b"body", accept=ALGOS)


def test_values_are_built_the_same(old: ModuleType) -> None:
    rng = random.Random(21)
    for _ in range(1500):
        body = rng.randbytes(rng.randrange(0, 600))
        algos = rng.sample(ALGOS, rng.randrange(0, 4))
        _same(old, "make_digest", body, algos=algos)
        preferences = {generators.key(rng): rng.randrange(-1, 12) for _ in range(rng.randrange(3))}
        _same(old, "make_want", preferences)
        old_verifier = old.Verifier(old.make_digest(body, algos=ALGOS), accept=ALGOS)
        new_verifier = contentdigest.Verifier(old.make_digest(body, algos=ALGOS), accept=ALGOS)
        old_verifier.update(body)
        new_verifier.update(body)
        assert old_verifier.verify() is new_verifier.verify() is True


def test_the_documented_changes_and_nothing_else(old: ModuleType) -> None:
    changes: list[tuple[Callable[[ModuleType], object], str, str]] = [
        (lambda m: m.make_want([("sha-256", 1)]), "AttributeError", "TypeError"),
        (lambda m: m.make_want({"sha-256": 10**5000}), "ValueError", "DigestError"),
        (lambda m: typing.get_type_hints(m.make_digest), "NameError", "none"),
    ]
    for call, before, after in changes:
        for module, expected in ((old, before), (contentdigest, after)):
            try:
                call(module)
                outcome = "none"
            except Exception as error:
                outcome = type(error).__name__
            assert outcome == expected
    assert hasattr(old, "annotations") and not hasattr(contentdigest, "annotations")
    assert old.DigestError.__module__ == "contentdigest_v02._errors"
    assert contentdigest.DigestError.__module__ == "contentdigest"
    long_name = "q" * 100_000
    for module, longest in ((old, 100_000), (contentdigest, 100)):
        with pytest.raises(ValueError) as caught:
            module.make_digest(b"", algos=[long_name])
        assert (len(str(caught.value)) > longest) is (module is old)


def test_an_old_pickle_loads_as_the_new_class(old: ModuleType) -> None:
    data = pickle.dumps(old.DigestError("bad field"), protocol=0).replace(
        b"contentdigest_v02", b"contentdigest"
    )
    again = pickle.loads(data)
    assert type(again) is contentdigest.DigestError and again.args == ("bad field",)

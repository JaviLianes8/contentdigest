"""Pickles written by the 0.2.0 release load as the live public classes and functions."""

from __future__ import annotations

import pickle

import pytest

import contentdigest

# contentdigest 0.2.0 from PyPI (the wheel, run under CPython 3.13):
# pickle.dumps(contentdigest.<name>, protocol=0 and 4).hex(), one pair per public callable.
# 0.2.0 defined them in its private modules, so these pickles name those modules.
PICKLES_FROM_0_2_0 = {
    "DigestError": [
        "63636f6e74656e746469676573742e5f6572726f72730a4469676573744572726f720a70300a2e",
        "80049529000000000000008c15636f6e74656e746469676573742e5f6572726f7273948c0b4469676573"
        "744572726f729493942e",
    ],
    "Digester": [
        "63636f6e74656e746469676573742e5f6469676573740a44696765737465720a70300a2e",
        "80049526000000000000008c15636f6e74656e746469676573742e5f646967657374948c084469676573"
        "7465729493942e",
    ],
    "Verifier": [
        "63636f6e74656e746469676573742e5f6469676573740a56657269666965720a70300a2e",
        "80049526000000000000008c15636f6e74656e746469676573742e5f646967657374948c085665726966"
        "6965729493942e",
    ],
    "choose_algorithm": [
        "63636f6e74656e746469676573742e5f77616e740a63686f6f73655f616c676f726974686d0a70300a2e",
        "8004952c000000000000008c13636f6e74656e746469676573742e5f77616e74948c1063686f6f73655f"
        "616c676f726974686d9493942e",
    ],
    "make_digest": [
        "63636f6e74656e746469676573742e5f6469676573740a6d616b655f6469676573740a70300a2e",
        "80049529000000000000008c15636f6e74656e746469676573742e5f646967657374948c0b6d616b655f"
        "6469676573749493942e",
    ],
    "make_want": [
        "63636f6e74656e746469676573742e5f77616e740a6d616b655f77616e740a70300a2e",
        "80049525000000000000008c13636f6e74656e746469676573742e5f77616e74948c096d616b655f7761"
        "6e749493942e",
    ],
    "parse": [
        "63636f6e74656e746469676573742e5f6469676573740a70617273650a70300a2e",
        "80049523000000000000008c15636f6e74656e746469676573742e5f646967657374948c057061727365"
        "9493942e",
    ],
    "parse_want": [
        "63636f6e74656e746469676573742e5f77616e740a70617273655f77616e740a70300a2e",
        "80049526000000000000008c13636f6e74656e746469676573742e5f77616e74948c0a70617273655f77"
        "616e749493942e",
    ],
    "verify": [
        "63636f6e74656e746469676573742e5f6469676573740a7665726966790a70300a2e",
        "80049524000000000000008c15636f6e74656e746469676573742e5f646967657374948c067665726966"
        "799493942e",
    ],
}


def test_every_public_callable_has_its_0_2_0_pickles() -> None:
    callables = {name for name in contentdigest.__all__ if callable(getattr(contentdigest, name))}
    assert set(PICKLES_FROM_0_2_0) == callables


@pytest.mark.parametrize(
    ("name", "hex_data"),
    [
        pytest.param(name, data, id=f"{name}-protocol-{protocol}")
        for name, pair in sorted(PICKLES_FROM_0_2_0.items())
        for protocol, data in ((0, pair[0]), (4, pair[1]))
    ],
)
def test_a_0_2_0_pickle_of_a_public_callable_loads_as_the_live_object(
    name: str, hex_data: str
) -> None:
    assert pickle.loads(bytes.fromhex(hex_data)) is getattr(contentdigest, name)

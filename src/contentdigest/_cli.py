"""The ``contentdigest`` command: print or check a digest field value for a file."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import BinaryIO, TextIO

from ._algorithms import ACTIVE_ALGORITHMS, SUPPORTED_ALGORITHMS
from ._digest import Digester, Verifier
from ._errors import DigestError

_CHUNK = 1 << 16


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contentdigest",
        description="Print the Content-Digest / Repr-Digest value of a file, or check one.",
        epilog="Exit status: 0 printed or matched, 1 mismatch, 2 bad input.",
    )
    parser.add_argument("file", nargs="?", default="-", help="file to read, - for stdin")
    parser.add_argument(
        "-a",
        "--algorithm",
        action="append",
        metavar="NAME",
        help="algorithm, repeatable (default sha-256): " + ", ".join(sorted(SUPPORTED_ALGORITHMS)),
    )
    parser.add_argument(
        "--verify",
        metavar="VALUE",
        help="check the file against this field value instead of printing one; with -a, "
        "only those algorithms are accepted, otherwise the Active ones",
    )
    return parser


def _feed(target: Digester | Verifier, stream: BinaryIO) -> None:
    while chunk := stream.read(_CHUNK):
        target.update(chunk)


def run(
    argv: Sequence[str] | None = None,
    stdin: BinaryIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the command and return its exit status; streams are injectable for tests."""
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_:
        return 0 if exit_.code == 0 else 2
    try:
        if args.verify is not None:
            accept = args.algorithm or ACTIVE_ALGORITHMS
            target: Digester | Verifier = Verifier(args.verify, accept=accept)
        else:
            target = Digester(args.algorithm or ["sha-256"])
        if args.file == "-":
            _feed(target, stdin or sys.stdin.buffer)
        else:
            with open(args.file, "rb") as handle:
                _feed(target, handle)
    except (DigestError, OSError) as error:
        print(f"contentdigest: {error}", file=err)
        return 2
    if isinstance(target, Verifier):
        ok = target.verify()
        print("match" if ok else "mismatch", file=out)
        return 0 if ok else 1
    print(target.value(), file=out)
    return 0


def main() -> None:
    """Console entry point."""
    sys.exit(run())

"""The ``contentdigest`` command: print or check a digest field value for a file."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from collections.abc import Sequence
from typing import BinaryIO, NoReturn, TextIO

from ._algorithms import ACTIVE_ALGORITHMS, SUPPORTED_ALGORITHMS
from ._digest import Digester
from ._errors import DigestError
from ._verify import Verifier

_CHUNK = 1 << 16
# Messages can carry a file name or an argument; a terminal line is enough for either.
_MESSAGE_LIMIT = 300


def _cut(message: str) -> str:
    if len(message) <= _MESSAGE_LIMIT:
        return message
    return f"{message[:_MESSAGE_LIMIT]}... ({len(message)} characters)"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse quotes the offending argument whole; keep usage errors short.
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {_cut(message)}\n")


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="contentdigest",
        description="Print the Content-Digest / Repr-Digest value of a file, or check one.",
        epilog="Exit status: 0 printed or matched, 1 mismatch, 2 bad input or an I/O error.",
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


def _say(stream: TextIO | None, text: str) -> bool:
    """Write one line; False when the stream is missing, closed or its reader went away."""
    if stream is None:
        return False
    try:
        print(text, file=stream)
        stream.flush()
    except (OSError, ValueError):
        return False
    return True


def run(
    argv: Sequence[str] | None = None,
    stdin: BinaryIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the command and return its exit status; streams are injectable for tests."""
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    try:
        # argparse prints help and usage errors itself; send them to the chosen streams.
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            args = _parser().parse_args(argv)
    except SystemExit as exit_:
        return 0 if exit_.code == 0 else 2
    except (AttributeError, OSError, ValueError):
        # Before Python 3.12, argparse raises when it has no open stream to print to.
        return 2
    try:
        if args.verify is not None:
            accept = args.algorithm or ACTIVE_ALGORITHMS
            target: Digester | Verifier = Verifier(args.verify, accept=accept)
        else:
            target = Digester(args.algorithm or ["sha-256"])
        if args.file == "-":
            source = stdin if stdin is not None else getattr(sys.stdin, "buffer", None)
            if source is None:
                raise OSError("there is no standard input to read")
            _feed(target, source)
        else:
            with open(args.file, "rb") as handle:
                _feed(target, handle)
    except (DigestError, OSError) as error:
        _say(err, f"contentdigest: {_cut(str(error))}")
        return 2
    if isinstance(target, Verifier):
        ok = target.verify()
        if not _say(out, "match" if ok else "mismatch"):
            return 2
        return 0 if ok else 1
    return 0 if _say(out, target.value()) else 2


def main() -> None:
    """Console entry point."""
    status = run()
    try:
        sys.stdout.flush()
    except (AttributeError, OSError, ValueError):
        # The reader went away: send what is left to the null device, so the interpreter's
        # own final flush does not print a traceback and change the exit status.
        with contextlib.suppress(AttributeError, OSError, ValueError):
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    sys.exit(status)

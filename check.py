#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline CLI regressions: python check.py /absolute/path/to/cargo-pkgbuild.

Only generated test recipes are sourced. Run as an ordinary user in isolation.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


binary = str(Path(sys.argv[1]).resolve(strict=True))
if os.getuid() == 0:
    raise SystemExit("Run these checks as an ordinary user, not root")
os.environ["CARGO_NET_OFFLINE"] = "true"


def run(directory, *args, ok=True):
    result = subprocess.run(args, cwd=directory, text=True, capture_output=True,
                            timeout=30)
    if ok:
        assert result.returncode == 0, result.stderr
    return result


def project(directory, **fields):
    fields = {"name": "fixture", "version": "1.2.3", "edition": "2021",
              **fields}
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "Cargo.toml").write_text(
        "[package]\n" + "".join(f"{k} = {json.dumps(v)}\n" for k, v in fields.items()),
        encoding="utf-8")
    (directory / "src").mkdir()
    (directory / "src/main.rs").write_text("fn main() {}\n", encoding="utf-8")


def generated(directory):
    run(directory, binary, "pkgbuild")  # Cargo subcommands receive this argument.
    run(directory, "bash", "-n", "PKGBUILD")
    return (directory / "PKGBUILD").read_text(encoding="utf-8")


def value(directory, variable):
    # Variable names are fixed by this test, never taken from fixture metadata.
    return run(directory, "bash", "--noprofile", "--norc", "-c",
               f'source ./PKGBUILD; printf "%s" "${{{variable}}}"').stdout


def versions(directory):
    for index, version in enumerate(("1.2.3", "0.12.1-alpha.0", "1.2.3-rc-1+build-2")):
        case = directory / str(index)
        project(case, version=version)
        generated(case)
        assert value(case, "pkgver") == version.replace("-", "_"), version


def quoting(directory, field, variable):
    text = "Dánny's \\\"tool\\\" $HOME $(touch EXECUTED) `touch EXECUTED`\nnext line"
    project(directory, **{field: text})
    generated(directory)
    assert value(directory, variable) == text, variable
    assert not (directory / "EXECUTED").exists()


def authors(directory):
    project(directory, authors=["Alice\n: > EXECUTED\n# Bob", "Carol\rDave"])
    generated(directory)
    value(directory, "pkgname")
    assert not (directory / "EXECUTED").exists(), "author escaped its comment"


def preserve(directory, kind):
    project(directory)
    target = directory / "PKGBUILD"
    old = directory / "reviewed"
    old.write_text("# human reviewed\n", encoding="utf-8")
    if kind == "file":
        target.write_bytes(old.read_bytes())
    elif kind == "symlink":
        target.symlink_to(old.name)
    elif kind == "dangling":
        target.symlink_to("absent")
    elif kind == "hardlink":
        target.hardlink_to(old)
    elif kind == "directory":
        target.mkdir()
    elif kind == "fifo":
        os.mkfifo(target)
    result = run(directory, binary, ok=False)
    assert result.returncode != 0, f"overwrote existing {kind}"
    assert old.read_text() == "# human reviewed\n"
    if kind == "file":
        assert target.read_bytes() == old.read_bytes()
    if kind in ("symlink", "dangling"):
        assert target.is_symlink()
    assert not (directory / "absent").exists()


def offline_metadata(directory):
    project(directory)
    with (directory / "Cargo.toml").open("a") as stream:
        stream.write('\n[dependencies]\nairch-unavailable-for-offline-test = "=999.999.999"\n')
    generated(directory)
    assert not (directory / "Cargo.lock").exists(), "metadata changed the lockfile"


def workspace(directory):
    member = directory / "member"
    project(member, name="workspace-member", version="2.0.0-beta.1")
    (directory / "Cargo.toml").write_text('[workspace]\nmembers = ["member"]\nresolver = "2"\n')
    result = run(directory, binary, ok=False)
    assert result.returncode != 0 and not (directory / "PKGBUILD").exists()
    generated(member)
    assert value(member, "pkgname") == "workspace-member"
    assert value(member, "pkgver") == "2.0.0_beta.1"


def binaries(directory):
    project(directory)
    with (directory / "Cargo.toml").open("a") as stream:
        stream.write('\n[[bin]]\nname = "first-tool"\npath = "src/main.rs"\n'
                     '\n[[bin]]\nname = "second-tool"\npath = "src/main.rs"\n')
    recipe = generated(directory)
    assert "cargo install" not in recipe
    assert recipe.count("export CARGO_PROFILE_RELEASE_STRIP=none") == 2
    (directory / "target/release").mkdir(parents=True)
    for name in ("first-tool", "second-tool"):
        (directory / "target/release" / name).write_text(name)
    run(directory, "bash", "--noprofile", "--norc", "-c",
        'source ./PKGBUILD; pkgdir="$PWD/staging"; package')
    installed = sorted(p.relative_to(directory / "staging").as_posix()
                       for p in (directory / "staging").rglob("*") if p.is_file())
    assert installed == ["usr/bin/first-tool", "usr/bin/second-tool"], installed
    for name in ("first-tool", "second-tool"):
        path = directory / "staging/usr/bin" / name
        assert path.read_text() == name and path.stat().st_mode & 0o777 == 0o755


def fetch_target(directory):
    project(directory)
    generated(directory)
    tools = directory / "tools"
    tools.mkdir()
    cargo = tools / "cargo"
    cargo.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$TEST_ARGS"\n')
    cargo.chmod(0o755)
    run(directory, "bash", "--noprofile", "--norc", "-c",
        'source ./PKGBUILD; export PATH="$PWD/tools:$PATH" TEST_ARGS="$PWD/args"; '
        'CARCH=armv7h; prepare')
    host = next(line.removeprefix("host: ") for line in
                run(directory, "rustc", "-vV").stdout.splitlines() if line.startswith("host: "))
    assert (directory / "args").read_text().splitlines() == ["fetch", "--locked", "--target", host]


def invalid_input(directory, kind):
    if kind == "invalid":
        (directory / "Cargo.toml").write_text("not toml at all\n")
    elif kind == "library":
        project(directory)
        (directory / "src/main.rs").rename(directory / "src/lib.rs")
    elif kind == "NUL":
        project(directory, description="not\x00representable in a shell variable")
    result = run(directory, binary, ok=False)
    assert result.returncode != 0 and not (directory / "PKGBUILD").exists()


cases = [("versions", versions), ("author comments", authors),
         ("offline metadata", offline_metadata), ("workspace selection", workspace),
         ("binary installation", binaries), ("native target", fetch_target)]
cases += [(f"quote {field}", lambda path, field=field, variable=variable:
           quoting(path, field, variable)) for field, variable in
          (("description", "pkgdesc"), ("homepage", "url"), ("license", "license[0]"))]
cases += [(f"preserve {kind}", lambda path, kind=kind: preserve(path, kind))
          for kind in ("file", "symlink", "dangling", "hardlink", "directory", "fifo")]
cases += [(f"reject {kind}", lambda path, kind=kind: invalid_input(path, kind))
          for kind in ("missing", "invalid", "library", "NUL")]
failures = 0
for name, check in cases:
    with tempfile.TemporaryDirectory(prefix="cargo-pkgbuild-check-") as temp:
        try:
            check(Path(temp))
            print(f"PASS: {name}", flush=True)
        except (AssertionError, subprocess.TimeoutExpired) as error:
            failures += 1
            print(f"FAIL: {name}: {error}", flush=True)
print(f"{len(cases) - failures}/{len(cases)} offline CLI checks passed")
raise SystemExit(bool(failures))

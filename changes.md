# cargo-pkgbuild 0.2.0-2 — verified repair candidate

Prepared for Danny on 2026-10-31. **Three separately approved fresh clean-chroot
builds passed (3/3)**. Each passed all 19 offline CLI cases during the build and
again against its installed command. Namcap reports no errors for the recipe,
main or debug package inside those chroots; reviewed warnings remain below.
No host installation/configuration change, AUR action or package publication.

## Baseline and reproduced problems

AUR baseline: `3ca6da70d5e3b97128f449291e7e33f93c40128b` (`0.2.0-1`).
Its complete tracked contents were `PKGBUILD` and `.SRCINFO`; both were read
before execution. The fresh official metadata snapshot reports it orphaned.
That is not an adoption grant. Upstream remains pinned to
`0fc6d2767ca7fe59dd760b9d4203c78662bc1b7c`, and the downloaded archive matches
the existing AUR SHA-256. Upstream's MIT and Apache-2.0 license texts were read.

The unchanged program compiles with Arch Rust/Cargo 1.99.1. The problems are
runtime behavior and generated recipes, not a current compiler failure:

- Prerelease versions retain hyphens that Arch forbids in `pkgver`.
- Description/homepage/license text is not correctly shell-quoted. Unicode
  does not round-trip, shell expansions occur, and quotes can break syntax.
  A newline in a synthetic author field becomes an executable recipe line.
- Existing `PKGBUILD` files are truncated, including through symbolic and hard
  links. A FIFO output path hangs until the test timeout.
- Metadata collection unnecessarily resolves dependencies, fails offline with
  an uncached dependency, and cannot correctly select a virtual workspace's
  member. Renamed/multiple binaries are installed under the wrong assumption
  that the executable always has the package name.
- Native target triples are guessed from `$CARCH`, yielding invalid ARM triples.

The final 19-case regression suite was also run against a separately rebuilt,
unchanged baseline: **16 cases fail and 3 pass**. These are owned synthetic
fixtures in a network-disabled sandbox, not tests against third-party systems.

The open [`--no-track` report](https://github.com/kstep/cargo-pkgbuild/issues/13)
does **not** require another fix: upstream commit `e12c9d6` already replaced
`cargo install` with direct file installation. This package retains that design.
[`cargo-aur`](https://github.com/fosskers/cargo-aur) is an alternative for binary
release packaging; this bounded repair keeps the smaller draft-recipe workflow.

## Repair and packaging

`generator-safety.patch` changes the shared generator without adding a Rust
dependency or changing `Cargo.lock`:

- Normalize version hyphens to underscores. Shell-quote values consistently,
  reject NUL in shell fields, and keep author credits on one comment line.
- Render before opening output, then use exclusive file creation. Existing
  files, links, directories and FIFOs are refused rather than overwritten.
- Read offline metadata without a dependency graph and select the exact
  manifest path. Reject virtual workspace roots and library-only crates with
  errors; support concrete members and real binary target names.
- Obtain the native target from `rustc -vV`. Leave stripping to `makepkg` using
  `CARGO_PROFILE_RELEASE_STRIP=none`, in both the package and generated recipes.
  This prevents Cargo's implicit release stripping from discarding the debug
  information supplied through Arch's `RUSTFLAGS`.
  [Cargo's documented stripping change](https://doc.rust-lang.org/cargo/CHANGELOG.html)

Keep upstream version `0.2.0`; increment only `pkgrel` to `2`. Declare Cargo at
runtime, since the installed helper invokes it. Declare `libgcc` and `glibc`
directly: file ownership and ELF dependencies were checked; the larger
`gcc-libs` metapackage is unnecessary. Python is a check-only dependency.
Preserve prior credits and add Danny as Contributor, not AUR Maintainer.

Install both unchanged upstream license texts and `README.arch`, add source
checksums and generate `.SRCINFO`. No service, install script, automatic hook,
publishing integration or system configuration is added.

## Preliminary rootless validation

Local evidence: `verification/source-audit.SEA537/` (ignored, not for upload).
The final candidate build is under `candidate/`; earlier iterations are
diagnostics, not extra independent verification passes.

The complete recipe passes `makepkg` with source checksums and an unchanged
lockfile. The 19 checks pass in `check()` and again against the extracted
package executable: 19 distinct cases tested twice, not 38 distinct tests.
Archive paths/modes and both unchanged license texts were checked; the usage
note matches its reviewed source. `.SRCINFO` is generated from this recipe.
Bash syntax and ShellCheck pass with the usual makepkg-specific exclusions
SC2034/SC2154/SC2164 (framework variables and fail-fast function execution).

Namcap reports **no main-package errors**, with reviewed warnings for the
loader reference and the Cargo runtime dependency, which is invoked as a
subprocess rather than linked. The missing Maintainer tag is intentional while
Danny remains a contributor, not the AUR maintainer.

The separate debug archive had one standalone Namcap error: its build-ID link
targets the main package's executable, which is not installed in the checker's
package database. Both debug links resolve within the combined extracted
payload. Real `.debug_info`, `.debug_line` and `.gdb_index` sections are present;
the earlier missing-debug-information warning is gone. The later checks with
the main package installed **inside all three approved clean chroots** report
no debug-package errors; the cross-package links also resolve in each root.
This is not a claim that every standalone lint invocation was error-free.

Final rootless package SHA-256:
`01d13e01c6f920876b87a091dfa5ceaf59d875959ab07421c6d9329172f76575`

Final rootless debug package SHA-256:
`864812cf6457f7861cd412a57fbb00fdb042bc934ef05a371b32aa6e9d109ad6`

The 19 offline CLI cases cover versions, each shell-quoted field, comment
injection, offline dependency handling, workspace selection, named binaries,
the native target, six existing-output types, malformed/missing input,
library-only crates and NUL rejection. They run from `check()` and can also
test an extracted installed binary using `python check.py /path/to/binary`.
Upstream's `cargo test` currently contains zero Rust unit tests; the CLI checks
are the substantive regression coverage.

The rootless builds use the host's read-only toolchain and package inventory,
private project files, an empty home and no network during compilation/tests.
They are **not clean chroots** and do not establish complete dependency closure
or bit-identical reproducibility. A public dependency fetch happened separately;
TLS verification remained enabled. No private home, credentials or signing
workspace was exposed to the build.

## Three clean-chroot verifications

Danny reviewed the source and approved each exact privileged job separately.
The first bootstrap attempt failed before compilation: the first configured
mirror returned HTTP 200 with a zero-byte `extra.db`, causing missing base
dependencies. Its exit-255 log/root remain preserved and **do not count as a
build**. A new root used `geo.mirror.pkgbuild.com` through a build-only Pacman
configuration. The host mirror list was not changed; package signatures remained
required. A rootless dependency-resolution preview passed before the retry.

Native `mkarchroot -C` and `makechrootpkg -c -n -C -U elias` created separate
fresh base/work roots for each successful pass. Builds/tests ran as UID 1001;
package installation and Namcap ran only inside the work roots. The normal
system package cache and host kernel were shared, not earlier compiled Cargo
targets or build roots. The pinned source archive was retained and rechecked;
this does not claim three independent upstream source downloads.

Evidence base: `verification/clean-chroots.1djIf9/` (local, ignored).

| Pass / evidence directory | Build exit | CLI cases: build / installed | Namcap errors |
| --- | --- | --- | --- |
| 1 — `pass-1-retry/` | 0 | 19/19 / 19/19 | 0 |
| 2 — `pass-2/` | 0 | 19/19 / 19/19 | 0 |
| 3 — `pass-3/` | 0 | 19/19 / 19/19 | 0 |

Every installed-command retest used network-disabled rootless Bubblewrap with
only that chroot's read-only tools, the frozen checker and private temporary
data. These are 19 distinct cases repeated, not 114 different tests. Each
archive's payload/modes, installed bytes, original license texts, reviewed
README, unchanged Cargo.lock, debug links/sections and `.BUILDINFO` recipe hash
were checked. Per-pass `RESULTS.txt`, `evidence.sha256`, logs and archives retain
the detailed evidence and hashes. `checkpkg` skipped the comparison because
there is no official-repository `cargo-pkgbuild`; that skip is not a successful
comparison. Namcap's three reviewed warnings are unchanged: Contributor-only
attribution, loader heuristic and Cargo invoked as a subprocess.

Build versions include Python `3.14.9-1`, Rust `1:1.99.1-1`, glibc
`2.44+r50+g1848099f063e-1` and libgcc `16.2.1+r23+gd564253eb6c8-1`.
The installed main/debug ELF bytes match across these three builds. The package
archives have different hashes and build timestamps; this is **not** a claim of
bit-identical archive reproducibility or future-build guarantees.

Final clean-pass main package SHA-256:
`9be03d90347a8a2cca1ff12564fbdf66a7ea3cf38c79332610eba289b790e450`

Final clean-pass debug package SHA-256:
`1b3ffd4fba6cfec4e6a0d6dd059b9a6a60cf1e915509a17daef3200bdc589393`

The accepted build inputs stayed byte-identical through all three jobs. Only
this report was updated afterward. Original review/frozen-input manifests are
preserved; `verification/release-inputs.sha256` covers the current source set
and updated report. No build root, artifact, backup or unrelated work was deleted.

## Remaining limits and release gate

Generated recipes remain drafts: source URLs/checksums, source-directory
changes, runtime dependencies, features, licenses and architectures need human
review. Native x86_64 is the tested platform; inherited architecture suggestions
are not portability certification. Cargo configuration/build scripts are not
sandboxed by the helper itself. On a write/disk error, a partial NEW output file
can remain; existing files are never replaced. See `README.arch` for scope.

Next gate: Danny's final report review and separate approval for the exact
publication action. Nothing here authorizes an upload, signing or AUR adoption.

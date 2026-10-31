# Contributor: Danny (https://github.com/carrolldant-glitch) <carrolldant@gmail.com>
# Former Maintainer: Bastien "neitsab" Traverse <neitsab@archlinux.org>
# Contributor: Michael Dorst <m@mdorst.net>
# Contributor: Caleb Maclennan <caleb@alerque.com>
# Contributor: Konstantin Stepanov <me@kstep.me>

pkgname=cargo-pkgbuild
pkgver=0.2.0
# target commit hash
_sha=0fc6d2767ca7fe59dd760b9d4203c78662bc1b7c
pkgrel=2
pkgdesc='ArchLinux PKGBUILD generator from Cargo.toml manifest'
arch=(x86_64 i686 armv6h armv7h)
url='https://github.com/kstep/cargo-pkgbuild'
license=('Apache-2.0 OR MIT')
depends=(libgcc glibc cargo)
checkdepends=(python)
_archive="$pkgname-$_sha"
source=("$_archive.tar.gz::$url/archive/$_sha.tar.gz"
        'generator-safety.patch' 'check.py' 'README.arch')
sha256sums=('a295df0a83493004158a04f5a5756128d50a400a758ead5afb8df3eeed056028'
            '35644e9f55412edef0d74ada5a500c9d23af777345b1dc59f14570db82e82366'
            'd34122b262283efabb447687220bd5d439cbbd1fc437a0a5dbc5cfb245cdc0bd'
            'b890c223e77b77e9c49e1ea0217f057c7b3bd2c90c48bd01606d99fa5ddf5ed9')

prepare() {
	cd "$_archive"
	patch -Np1 -i "$srcdir/generator-safety.patch"
	export RUSTUP_TOOLCHAIN=stable
	cargo fetch --locked --target "$(rustc -vV | sed -n 's/host: //p')"
}

build() {
	cd "$_archive"
	export RUSTUP_TOOLCHAIN=stable
	export CARGO_TARGET_DIR=target
	export CARGO_PROFILE_RELEASE_STRIP=none
	cargo build --frozen --release --all-features
}

check() {
	cd "$_archive"
	export RUSTUP_TOOLCHAIN=stable
	export CARGO_TARGET_DIR=target
	export CARGO_PROFILE_RELEASE_STRIP=none
	cargo test --frozen --release --all-features
	python "$srcdir/check.py" "$srcdir/$_archive/target/release/$pkgname"
}

package() {
	cd "$_archive"
	install -Dm0755 -t "$pkgdir/usr/bin/" "target/release/$pkgname"
	install -Dm644 -t "$pkgdir/usr/share/licenses/$pkgname/" LICENSE-MIT LICENSE-APACHE
	install -Dm644 "$srcdir/README.arch" "$pkgdir/usr/share/doc/$pkgname/README.arch"
}

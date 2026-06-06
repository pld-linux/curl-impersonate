#
# curl-impersonate is patched curl + BoringSSL + an HTTP/2,3 stack that mimics
# real browser TLS/HTTP fingerprints. Only the fingerprint-critical pieces are
# bundled and statically linked: BoringSSL (pinned commit, patched), ngtcp2 and
# nghttp3 (patched), and nghttp2 pinned to 1.63 (>=1.65 drops the priority flag
# the HTTP/2 fingerprint relies on) - none have a usable PLD counterpart. The
# unpatched, fingerprint-irrelevant zlib/zstd/brotli/libidn2 come from PLD.
#
%define		boring_commit	673e61fc215b178a90c0e67858bbf162c8158993
%define		curl_tag	curl-8_15_0
%define		nghttp2_version	1.63.0
%define		ngtcp2_version	1.20.0
%define		nghttp3_version	1.15.0
Summary:	curl that impersonates real browser TLS/HTTP fingerprints
Summary(pl.UTF-8):	curl podszywający się pod odciski TLS/HTTP prawdziwych przeglądarek
Name:		curl-impersonate
Version:	1.5.6
Release:	1
License:	MIT (curl-impersonate, curl, nghttp2/3, ngtcp2), BoringSSL
Group:		Applications/Networking
URL:		https://github.com/lexiforest/curl-impersonate
Source0:	https://github.com/lexiforest/curl-impersonate/archive/v%{version}/%{name}-%{version}.tar.gz
# Source0-md5:	c220749405028695f55e224271374f3e
Source1:	https://github.com/curl/curl/archive/%{curl_tag}.tar.gz
# Source1-md5:	246e64770431f2a19c3f5c26bc83cb95
Source2:	https://github.com/google/boringssl/archive/%{boring_commit}/boringssl-%{boring_commit}.zip
# Source2-md5:	843d1d9e4b80477d21771f2a872b9edc
Source3:	https://github.com/nghttp2/nghttp2/releases/download/v%{nghttp2_version}/nghttp2-%{nghttp2_version}.tar.bz2
# Source3-md5:	c29228929c3c323ecd0eae172f1eb9d5
Source4:	https://github.com/ngtcp2/ngtcp2/releases/download/v%{ngtcp2_version}/ngtcp2-%{ngtcp2_version}.tar.bz2
# Source4-md5:	15881f426f0236956f52b3def11eb9a9
Source5:	https://github.com/ngtcp2/nghttp3/releases/download/v%{nghttp3_version}/nghttp3-%{nghttp3_version}.tar.bz2
# Source5-md5:	b1fd62a123652b878efb23fb34a8d5e0
Patch0:		%{name}-build.patch
BuildRequires:	autoconf
BuildRequires:	automake
BuildRequires:	cmake >= 3.5
BuildRequires:	libbrotli-devel
BuildRequires:	libidn2-devel
BuildRequires:	libstdc++-devel
BuildRequires:	libtool
BuildRequires:	ninja
BuildRequires:	pkgconfig
BuildRequires:	unzip
BuildRequires:	zlib-devel
BuildRequires:	zstd-devel
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
curl-impersonate is a special build of curl that can impersonate the
four major browsers: Chrome, Edge, Safari and Firefox. It performs TLS
and HTTP handshakes identical to a real browser, so it is much harder
to fingerprint and block. It ships a libcurl-impersonate shared
library and the curl-impersonate command line tool with per-browser
wrapper scripts.

%description -l pl.UTF-8
curl-impersonate to specjalna wersja curla, która potrafi podszywać
się pod cztery główne przeglądarki: Chrome, Edge, Safari i Firefox.
Wykonuje uzgodnienia TLS i HTTP identyczne jak prawdziwa przeglądarka,
dzięki czemu znacznie trudniej ją rozpoznać i zablokować. Zawiera
bibliotekę współdzieloną libcurl-impersonate oraz narzędzie wiersza
poleceń curl-impersonate ze skryptami opakowującymi dla poszczególnych
przeglądarek.

%package libs
Summary:	libcurl-impersonate shared library
Summary(pl.UTF-8):	Biblioteka współdzielona libcurl-impersonate
Group:		Libraries

%description libs
libcurl-impersonate shared library - a drop-in libcurl replacement
that performs browser-identical TLS and HTTP fingerprints.

%description libs -l pl.UTF-8
Biblioteka współdzielona libcurl-impersonate - zamiennik libcurl
wykonujący uzgodnienia TLS i HTTP identyczne jak przeglądarki.

%package devel
Summary:	Header files for libcurl-impersonate library
Summary(pl.UTF-8):	Pliki nagłówkowe biblioteki libcurl-impersonate
Group:		Development/Libraries
Requires:	%{name}-libs%{?_isa} = %{version}-%{release}

%description devel
Header files for the libcurl-impersonate library. The headers are
installed into a private %{_includedir}/curl-impersonate directory so
they do not conflict with the standard curl-devel package.

%description devel -l pl.UTF-8
Pliki nagłówkowe biblioteki libcurl-impersonate. Nagłówki instalowane
są w prywatnym katalogu %{_includedir}/curl-impersonate, aby nie
kolidowały ze standardowym pakietem curl-devel.

%prep
%setup -q
%patch -P0 -p1

# Place the pinned dependency archives where upstream's Makefile expects them,
# so the network-isolated build uses them instead of downloading.
cp -p %{SOURCE1} %{SOURCE2} %{SOURCE3} %{SOURCE4} %{SOURCE5} .

%build
%configure
export CFLAGS="%{rpmcflags} %{rpmcppflags} -fPIC"
export CXXFLAGS="%{rpmcxxflags} %{rpmcppflags} -fPIC"
export LDFLAGS="%{rpmldflags}"
# The top-level make must stay serial: several dependency rules list two
# targets sharing one recipe (e.g. libbrotli{common,dec}.a), which race under
# -j. Parallelism is delegated to each sub-build via SUBJOBS.
%{__make} -j1 build \
	SUBJOBS=%{__jobs}
%{__make} -j1 checkbuild

%install
rm -rf $RPM_BUILD_ROOT

%{__make} -C %{curl_tag} install \
	DESTDIR=$RPM_BUILD_ROOT

install -d $RPM_BUILD_ROOT%{_bindir}
install -p bin/curl_* $RPM_BUILD_ROOT%{_bindir}
# PLD requires an explicit interpreter path, not /usr/bin/env.
%{__sed} -i -e '1s,^#!.*env bash,#!/bin/bash,' $RPM_BUILD_ROOT%{_bindir}/curl_*

# libcurl.m4 is the stock curl autoconf macro and conflicts with curl-devel.
%{__rm} $RPM_BUILD_ROOT%{_datadir}/aclocal/libcurl.m4

# Move the curl headers into a private directory to avoid clashing with
# curl-devel, and point the pkg-config/config files at it.
install -d $RPM_BUILD_ROOT%{_includedir}/curl-impersonate
mv $RPM_BUILD_ROOT%{_includedir}/curl \
	$RPM_BUILD_ROOT%{_includedir}/curl-impersonate/curl
%{__sed} -i -e 's,^includedir=.*,includedir=%{_includedir}/curl-impersonate,' \
	$RPM_BUILD_ROOT%{_pkgconfigdir}/libcurl-impersonate.pc
%{__sed} -i -e 's,^includedir=.*,includedir="%{_includedir}/curl-impersonate",' \
	$RPM_BUILD_ROOT%{_bindir}/curl-impersonate-config

%{__rm} $RPM_BUILD_ROOT%{_libdir}/libcurl-impersonate.la
%{__rm} $RPM_BUILD_ROOT%{_libdir}/libcurl-impersonate.a

%clean
rm -rf $RPM_BUILD_ROOT

%post	libs -p /sbin/ldconfig
%postun	libs -p /sbin/ldconfig

%files
%defattr(644,root,root,755)
%doc README.md docs/install.rst docs/fingerprints.rst
%attr(755,root,root) %{_bindir}/curl-impersonate
%attr(755,root,root) %{_bindir}/curl_*
%attr(755,root,root) %{_bindir}/wcurl-impersonate

%files libs
%defattr(644,root,root,755)
%{_libdir}/libcurl-impersonate.so.*.*.*
%ghost %{_libdir}/libcurl-impersonate.so.4

%files devel
%defattr(644,root,root,755)
%attr(755,root,root) %{_bindir}/curl-impersonate-config
%{_libdir}/libcurl-impersonate.so
%{_includedir}/curl-impersonate
%{_pkgconfigdir}/libcurl-impersonate.pc

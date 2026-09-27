from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler


class UnsafeUrlError(ValueError):
    pass


BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".localhost", ".lan", ".home", ".corp")
BLOCKED_HOSTS = {"localhost", "localhost.localdomain", "0.0.0.0"}


@dataclass(frozen=True)
class ValidatedUrl:
    url: str
    hostname: str
    resolved_ips: tuple[str, ...]


def _canonical_ip(value: str) -> str:
    return str(ipaddress.ip_address(value))


def _ip_is_public(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_peer(sock: socket.socket, *, expected_ip: str) -> None:
    """Bind URL policy to the actual connected peer, not a prior DNS answer."""
    try:
        peer_ip = _canonical_ip(str(sock.getpeername()[0]))
        expected = _canonical_ip(expected_ip)
    except (OSError, ValueError, IndexError, TypeError) as exc:
        raise UnsafeUrlError("Koneksi tujuan tidak dapat diverifikasi dengan aman.") from exc
    if peer_ip != expected or not _ip_is_public(peer_ip):
        raise UnsafeUrlError("Koneksi berubah ke alamat yang tidak diizinkan.")


def validate_external_url(raw_url: str) -> ValidatedUrl:
    if not raw_url or len(raw_url) > 2048:
        raise UnsafeUrlError("URL tidak valid atau terlalu panjang.")

    parsed = urlparse(raw_url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("Hanya URL http/https yang dapat dianalisis.")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("URL dengan kredensial tidak diizinkan.")
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if not hostname:
        raise UnsafeUrlError("URL tidak memiliki hostname yang valid.")
    if hostname in BLOCKED_HOSTS or hostname.endswith(BLOCKED_HOST_SUFFIXES):
        raise UnsafeUrlError("Alamat jaringan lokal/internal tidak dapat diakses.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    candidates: list[str] = []
    try:
        candidates = [_canonical_ip(hostname)]
    except ValueError:
        try:
            infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise UnsafeUrlError("Hostname tidak dapat di-resolve.") from exc
        for info in infos:
            try:
                address = _canonical_ip(str(info[4][0]))
            except (ValueError, IndexError, TypeError):
                continue
            if address not in candidates:
                candidates.append(address)

    # Reject the hostname when *any* relevant DNS answer is non-public. This
    # prevents a mixed public/private answer set from being used as an SSRF
    # bypass and gives the connection layer a fixed public allow-list.
    if not candidates or any(not _ip_is_public(address) for address in candidates):
        raise UnsafeUrlError("URL mengarah ke alamat jaringan privat/internal yang diblokir.")
    return ValidatedUrl(url=raw_url.strip(), hostname=hostname, resolved_ips=tuple(candidates))


class PinnedHTTPConnection(http.client.HTTPConnection):
    """HTTP connection that never re-resolves the validated hostname."""

    def __init__(self, hostname: str, connect_ip: str, *, port: int, timeout: float):
        super().__init__(hostname, port=port, timeout=timeout)
        self._connect_ip = _canonical_ip(connect_ip)

    def connect(self) -> None:
        sock = socket.create_connection((self._connect_ip, self.port), self.timeout, self.source_address)
        try:
            _validate_peer(sock, expected_ip=self._connect_ip)
        except Exception:
            sock.close()
            raise
        self.sock = sock


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection pinned to a validated IP with normal hostname TLS."""

    def __init__(
        self,
        hostname: str,
        connect_ip: str,
        *,
        port: int,
        timeout: float,
        context: ssl.SSLContext | None = None,
    ):
        super().__init__(hostname, port=port, timeout=timeout, context=context or ssl.create_default_context())
        self._connect_ip = _canonical_ip(connect_ip)

    def connect(self) -> None:
        # Connect to the already-validated literal IP so the hostname cannot be
        # re-resolved between validation and connection (DNS rebinding/TOCTOU).
        raw_sock = socket.create_connection((self._connect_ip, self.port), self.timeout, self.source_address)
        try:
            _validate_peer(raw_sock, expected_ip=self._connect_ip)
            # Keep the *original hostname* for SNI and certificate hostname
            # verification. TLS verification is intentionally never disabled.
            self.sock = self._context.wrap_socket(raw_sock, server_hostname=self.host)
        except Exception:
            raw_sock.close()
            raise


class SafeRedirectHandler(HTTPRedirectHandler):
    """Legacy compatibility helper. New article fetches validate and pin each hop."""

    max_redirections = 4

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        target = urljoin(req.full_url, newurl)
        validate_external_url(target)
        return super().redirect_request(req, fp, code, msg, headers, target)

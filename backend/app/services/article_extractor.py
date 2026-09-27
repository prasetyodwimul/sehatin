from __future__ import annotations

import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlsplit

from app.services.url_safety import (
    PinnedHTTPConnection,
    PinnedHTTPSConnection,
    UnsafeUrlError,
    ValidatedUrl,
    validate_external_url,
)


class ArticleFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExtractedArticle:
    title: str | None
    publisher: str | None
    published_date: str | None
    author: str | None
    main_text: str
    url: str


class _ReadableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._capture_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs):  # noqa: ANN001
        attrs_dict = {str(k).lower(): str(v) for k, v in attrs if k and v is not None}
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "form", "aside"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._capture_title = True
        if tag == "meta":
            key = (attrs_dict.get("property") or attrs_dict.get("name") or "").lower()
            value = attrs_dict.get("content", "").strip()
            if key and value:
                self.meta[key] = value
        if tag in {"p", "h1", "h2", "h3", "li", "article", "section"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "form", "aside"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._capture_title = False
        if not self._skip_depth and tag in {"p", "h1", "h2", "h3", "li"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str):
        if self._skip_depth:
            return
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self._capture_title:
            self.title_parts.append(cleaned)
        self.text_parts.append(cleaned + " ")


def _clean_text(parts: list[str]) -> str:
    text = html.unescape("".join(parts))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) >= 20]
    return "\n".join(lines)


def extract_article_from_html(raw_html: str, *, final_url: str) -> ExtractedArticle:
    parser = _ReadableHTMLParser()
    parser.feed(raw_html)
    main_text = _clean_text(parser.text_parts)
    if len(main_text) < 80:
        raise ArticleFetchError("Isi artikel tidak dapat diekstrak dengan cukup jelas.")

    title = parser.meta.get("og:title") or parser.meta.get("twitter:title") or " ".join(parser.title_parts).strip() or None
    publisher = parser.meta.get("og:site_name") or parser.meta.get("application-name")
    published_date = (
        parser.meta.get("article:published_time")
        or parser.meta.get("date")
        or parser.meta.get("datepublished")
        or parser.meta.get("dc.date")
    )
    author = parser.meta.get("author") or parser.meta.get("article:author")
    return ExtractedArticle(
        title=title,
        publisher=publisher,
        published_date=published_date,
        author=author,
        main_text=main_text[:20_000],
        url=final_url,
    )


def _request_target(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query}"
    return path


def _open_validated_response(validated: ValidatedUrl, *, timeout: float):
    parsed = urlparse(validated.url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    last_error: Exception | None = None
    for connect_ip in validated.resolved_ips:
        connection = (
            PinnedHTTPSConnection(validated.hostname, connect_ip, port=port, timeout=timeout)
            if parsed.scheme == "https"
            else PinnedHTTPConnection(validated.hostname, connect_ip, port=port, timeout=timeout)
        )
        try:
            connection.request(
                "GET",
                _request_target(validated.url),
                headers={
                    "User-Agent": "SEHATIN-HealthChecker/1.0 (+evidence-verification)",
                    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
                    "Connection": "close",
                },
            )
            return connection, connection.getresponse()
        except UnsafeUrlError:
            connection.close()
            raise
        except Exception as exc:
            connection.close()
            last_error = exc
    raise ArticleFetchError("SEHATIN tidak dapat membaca isi halaman ini. Silakan paste teks artikelnya.") from last_error


def fetch_article(url: str, *, timeout: float = 6.0, max_bytes: int = 1_500_000) -> ExtractedArticle:
    current_url = url.strip()
    max_redirects = 4

    try:
        for redirect_count in range(max_redirects + 1):
            validated = validate_external_url(current_url)
            connection = None
            response = None
            try:
                connection, response = _open_validated_response(validated, timeout=timeout)
                status = int(response.status)

                if status in {301, 302, 303, 307, 308}:
                    location = response.headers.get("Location")
                    if not location:
                        raise ArticleFetchError("Redirect halaman tidak valid.")
                    if redirect_count >= max_redirects:
                        raise ArticleFetchError("Terlalu banyak redirect saat membaca halaman.")
                    # The next loop validates *all* DNS answers for the redirect
                    # and pins the next connection to that validated IP set.
                    current_url = urljoin(validated.url, location)
                    continue

                if status >= 400:
                    raise ArticleFetchError("SEHATIN tidak dapat membaca isi halaman ini. Silakan paste teks artikelnya.")

                content_type = (response.headers.get_content_type() or "").lower()
                if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
                    raise ArticleFetchError("Tipe konten URL tidak didukung. Gunakan halaman artikel HTML/text.")
                declared = response.headers.get("Content-Length")
                if declared and declared.isdigit() and int(declared) > max_bytes:
                    raise ArticleFetchError("Halaman terlalu besar untuk dianalisis dengan aman.")
                payload = response.read(max_bytes + 1)
                if len(payload) > max_bytes:
                    raise ArticleFetchError("Halaman terlalu besar untuk dianalisis dengan aman.")
                charset = response.headers.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
                if content_type == "text/plain":
                    cleaned = " ".join(text.split())
                    if len(cleaned) < 80:
                        raise ArticleFetchError("Isi halaman terlalu pendek untuk dianalisis.")
                    return ExtractedArticle(None, None, None, None, cleaned[:20_000], validated.url)
                return extract_article_from_html(text, final_url=validated.url)
            finally:
                if response is not None:
                    response.close()
                if connection is not None:
                    connection.close()
    except UnsafeUrlError:
        raise
    except ArticleFetchError:
        raise
    except Exception as exc:
        raise ArticleFetchError("SEHATIN tidak dapat membaca isi halaman ini. Silakan paste teks artikelnya.") from exc

    raise ArticleFetchError("SEHATIN tidak dapat membaca isi halaman ini. Silakan paste teks artikelnya.")

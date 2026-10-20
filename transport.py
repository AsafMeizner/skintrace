"""Bounded HTTPS transport; redirects are never followed and nothing is logged."""
import json
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from urllib.parse import urlsplit


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HTTPTransport:
    def __init__(self, *, timeout=20, max_response_bytes=1024 * 1024, opener=None):
        if not 0 < timeout <= 60 or not 0 < max_response_bytes <= 4 * 1024 * 1024:
            raise ValueError('Invalid transport limits')
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes
        self.opener = opener or build_opener(ProxyHandler(), NoRedirect())

    def request(self, method, url, headers, body):
        destination = urlsplit(url)
        if (destination.scheme != 'https' or not destination.hostname
                or destination.username or destination.password or destination.fragment
                or destination.port not in (None, 443)):
            raise ValueError('HTTPS destination required')
        if method not in ('GET', 'POST', 'PUT'):
            raise ValueError('Unsupported request method')
        request = Request(url, data=body, headers=headers, method=method)
        with self.opener.open(request, timeout=self.timeout) as response:
            if not 200 <= response.status < 300:
                raise ValueError('HTTP request failed')
            if method == 'PUT':
                return None
            raw = response.read(self.max_response_bytes + 1)
            if len(raw) > self.max_response_bytes:
                raise ValueError('API response too large')
            try:
                result = json.loads(raw)
            except (ValueError, UnicodeError):
                raise ValueError('Invalid API JSON') from None
            if not isinstance(result, dict):
                raise ValueError('API response must be an object')
            return result

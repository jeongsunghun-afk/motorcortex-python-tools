#!/usr/bin/python3

#
#   Developer: Alexey Zakharov (alexey.zakharov@vectioneer.com)
#   All rights reserved. Copyright (c) 2016-2025 VECTIONEER.
#

from pynng import ffi, lib
from pynng.exceptions import check_err


class NngUrl:
    """Python wrapper for nng_url."""

    def __init__(self, url: str):
        self._url_p = ffi.new("nng_url **")
        check_err(lib.nng_url_parse(self._url_p, url.encode()))

    def __del__(self):
        if self._url_p[0] != ffi.NULL:
            lib.nng_url_free(self._url_p[0])

    @property
    def _url(self):
        return self._url_p[0]

    @property
    def hostname(self) -> str | None:
        if self._url.u_hostname == ffi.NULL:
            return None
        return ffi.string(self._url.u_hostname).decode()

    @property
    def port(self) -> str | None:
        if self._url.u_port == ffi.NULL:
            return None
        return ffi.string(self._url.u_port).decode()

    @property
    def scheme(self) -> str | None:
        if self._url.u_scheme == ffi.NULL:
            return None
        return ffi.string(self._url.u_scheme).decode()

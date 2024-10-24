"""
raven.utils.http
~~~~~~~~~~~~~~~~

:copyright: (c) 2010-2012 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""
from __future__ import absolute_import

import socket
import ssl
import sys

from raven.conf import defaults
from raven.utils.compat import urllib2, httplib
from raven.utils.ssl_match_hostname import match_hostname


def urlopen(url, data=None, timeout=defaults.TIMEOUT, ca_certs=None,
            verify_ssl=False, assert_hostname=None):

    class ValidHTTPSConnection(httplib.HTTPConnection):
        default_port = httplib.HTTPS_PORT

        def __init__(self, *args, **kwargs):
            httplib.HTTPConnection.__init__(self, *args, **kwargs)

        def connect(self):
            sock = socket.create_connection(
                address=(self.host, self.port),
                timeout=self.timeout,
            )
            if self._tunnel_host:
                self.sock = sock
                self._tunnel()

            # Create a secure SSL context
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

            if ca_certs:
                context.load_verify_locations(cafile=ca_certs)

            # Ensure that we require certificate verification
            if verify_ssl:
                context.verify_mode = ssl.CERT_REQUIRED
            else:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

            # Wrap the socket with SSL/TLS using the context
            self.sock = context.wrap_socket(sock, server_hostname=self.host)

            # Perform hostname verification if required
            if assert_hostname is not None:
                match_hostname(self.sock.getpeercert(),
                               self.assert_hostname or self.host)

    class ValidHTTPSHandler(urllib2.HTTPSHandler):
        def https_open(self, req):
            return self.do_open(ValidHTTPSConnection, req)

    if verify_ssl:
        handlers = [ValidHTTPSHandler]
    else:
        try:
            handlers = [urllib2.HTTPSHandler(
                context=ssl._create_unverified_context())]
        except AttributeError:
            handlers = []

    opener = urllib2.build_opener(*handlers)

    if sys.version_info < (2, 6):
        default_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            return opener.open(url, data)
        finally:
            socket.setdefaulttimeout(default_timeout)
    return opener.open(url, data, timeout)

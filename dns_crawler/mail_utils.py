# Copyright © 2019 CZ.NIC, z. s. p. o.
#
# This file is part of dns-crawler.
#
# dns-crawler is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This software is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License. If not,
# see <http://www.gnu.org/licenses/>.


import smtplib
import socket
import ssl

import certifi

from .certificate import parse_cert


def parse_helo(h):
    return h[1].decode("utf-8").split("\n")


def get_mx_info(mx_records, timeout):
    socket.setdefaulttimeout(float(timeout))
    results = []
    if not mx_records:
        return None
    for mx in mx_records:
        result = {}
        if mx and mx["value"]:
            host = mx["value"].split(" ")[-1]
            if host and host != ".":
                result["host"] = host
                try:
                    s = smtplib.SMTP(host=host, port=25, timeout=timeout)
                except (OSError, socket.timeout) as e:
                    result["error"] = str(e)
                else:
                    try:
                        result["helo"] = parse_helo(s.helo())
                        result["ehlo"] = parse_helo(s.ehlo())
                    except smtplib.SMTPServerDisconnected as e:
                        result["error"] = str(e)
                    else:
                        if "STARTTLS" in result["ehlo"]:
                            should_get_cert = True
                            ctx = ssl.create_default_context()
                            ctx.options &= ~(ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1)
                            ctx.load_verify_locations(certifi.where())
                            ctx.check_hostname = False
                            ctx.verify_mode = ssl.CERT_NONE
                            try:
                                s.starttls(context=ctx)
                            except smtplib.SMTPNotSupportedError:
                                should_get_cert = False
                            except (smtplib.SMTPResponseException) as e:
                                result["tls"] = {}
                                result["tls"]["error"] = str(e)
                                should_get_cert = False
                            except ssl.SSLError as e:
                                if e.reason in ["UNSUPPORTED_PROTOCOL", "DH_KEY_TOO_SMALL"]:
                                    s.starttls(context=ctx)
                            if should_get_cert:
                                result["tls"] = {}
                                result["tls"]["tls_version"] = s.sock.version()
                                result["tls"]["tls_cipher_name"] = s.sock.cipher()[0]
                                result["tls"]["tls_cipher_bits"] = s.sock.cipher()[2]
                                cert = s.sock.getpeercert(binary_form=True)
                                result["tls"]["cert"] = parse_cert(cert, host)
                        try:
                            s.quit()
                        except smtplib.SMTPServerDisconnected:
                            pass
                results.append(result)
    return results

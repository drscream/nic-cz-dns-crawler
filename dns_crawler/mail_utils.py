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
            if host:
                result["host"] = host
                try:
                    s = smtplib.SMTP(host, 25, timeout)
                except Exception as e:
                    result["error"] = str(e)
                else:
                    result["helo"] = parse_helo(s.helo())
                    result["ehlo"] = parse_helo(s.ehlo())
                    try:
                        s.starttls()
                    except smtplib.SMTPNotSupportedError:
                        pass
                    else:
                        cert = s.sock.getpeercert(binary_form=True)
                        result["cert"] = parse_cert(cert, host)
                    s.quit()
                results.append(result)
    return results

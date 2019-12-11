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

import re
import socket
import ssl
from html.parser import HTMLParser
from urllib.parse import unquote

import certifi
import idna
import requests
import urllib3
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from .ip_utils import is_valid_ip_address

alpn_protocols = ['h3', 'h3-Q046', 'h3-Q043', 'h3-Q039', 'h3-24', 'h3-23',
                  'h2', 'spdy/3.1', 'spdy/3', 'spdy/2', 'spdy/1', 'http/1.1']
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def drop_null_values(orig_dict):
    return {k: v for k, v in orig_dict.items() if v is not None}


def create_request_headers(domain):
    return {
        "Host": idna.encode(domain).decode("ascii"),
        "Connection": "close",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "cs-CZ,cs;q=0.9,en-US;q=0.8,en;q=0.7",
    }


def parse_alt_svc(header):
    if not header:
        return None
    result = {}
    for pair in [i.split(";")[0].replace("\"", "") for i in re.findall(r'[a-zA-Z0-9-]+=[^,]+', header)]:
        list = unquote(pair).split("=")
        result[list[0]] = list[1]
    return result


def cert_datetime_to_iso(cert_date):
    return cert_date.strftime("%Y-%m-%d %H:%M:%S")


def parse_cert_name(name):
    return {k: v for k, v in [s.rfc4514_string().split("=") for s in name.rdns]}


def format_cert_serial_number(serial):
    return serial.to_bytes(((serial.bit_length() + 7) // 8), "big").hex()


def parse_cert(cert, domain):
    cert = x509.load_der_x509_certificate(cert, default_backend())
    result = {}
    result["not_before"] = cert_datetime_to_iso(cert.not_valid_before)
    result["not_after"] = cert_datetime_to_iso(cert.not_valid_after)
    result["subject"] = parse_cert_name(cert.subject)
    result["issuer"] = parse_cert_name(cert.issuer)
    result["version"] = int(str(cert.version)[-1])
    result["serial"] = format_cert_serial_number(cert.serial_number)
    result["algorithm"] = cert.signature_hash_algorithm.name
    try:
        result["alt_names"] = [str(name.value) for name in cert.extensions.get_extension_for_oid(
            x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value]
    except x509.extensions.ExtensionNotFound:
        pass
    return drop_null_values(result)


def get_tls_info(domain, ip, http_timeout, ipv6=False, port=443):
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(certifi.where())
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.set_alpn_protocols(alpn_protocols)

    if not ipv6:
        inet = socket.AF_INET
    else:
        inet = socket.AF_INET6
    sock = socket.socket(inet, socket.SOCK_STREAM)
    conn = ctx.wrap_socket(sock, server_hostname=domain)
    conn.settimeout(float(http_timeout))

    try:
        conn.connect((ip, port))
    except (OSError, socket.timeout) as e:
        result = {
            "error": str(e)
        }
    try:
        cert = conn.getpeercert(binary_form=True)
    except (OSError, AttributeError) as e:
        result = {
            "error": str(e)
        }
    else:
        result = drop_null_values({
            "alpn_protocol": conn.selected_alpn_protocol(),
            "tls_version": conn.version(),
            "tls_cipher_name": conn.cipher()[0],
            "tls_cipher_bits": conn.cipher()[2],
            "cert": parse_cert(cert, domain)
        })
    conn.close()
    return result


class HTMLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_starttag(self, tag, attrs):
        if tag in ["script", "style"]:
            return ""

    def handle_data(self, d):
        tag = self.get_starttag_text()
        if not tag:
            self.fed.append(d)
        else:
            if tag.startswith("<script") or tag.startswith("<style"):
                pass
            else:
                self.fed.append(d)

    def get_data(self):
        return " ".join(self.fed)


def strip_tags(html):
    s = HTMLStripper()
    s.feed(html)
    return s.get_data()


def strip_newlines(text):
    return re.sub(r"(\r?\n *)+", "\n", re.sub(r" {2,}", "", re.sub(r"\t+", "", text))).strip()


def get_response_headers(headers):
    return drop_null_values({
        "location": headers.get("location"),
        "server": headers.get("server"),
        "x-frame-options": headers.get("x-frame-options"),
        "content-security-policy": headers.get("content-security-policy"),
        "x-xss-protection": headers.get("x-xss-protection"),
        "strict-transport-security": headers.get("strict-transport-security"),
        "expect-ct": headers.get("expect-ct"),
        "x-content-type-options": headers.get("x-content-type-options"),
        "feature-policy": headers.get("feature-policy"),
        "access-control-allow-origin": headers.get("access-control-allow-origin"),
        "x-powered-by": headers.get("x-powered-by"),
        "alt-svc": parse_alt_svc(headers.get("alt-svc"))
    })


def get_webserver_info(domain, ips, config, ipv6=False, tls=False):
    if not ips or len(ips) < 1:
        return None
    http_timeout = int(config["http_timeout"])
    save_content = config["save_web_content"] == "True"
    strip_html = config["strip_html"] == "True"
    results = []
    for ip in ips:
        ip = ip["value"]
        if not is_valid_ip_address(ip):
            continue
        result = {
            "ip": ip
        }
        protocol = "http://"
        if tls:
            result["tls"] = get_tls_info(domain, ip, http_timeout, ipv6)
            protocol = "https://"
        host = ip
        if ipv6:
            host = f"[{ip}]"
        if save_content:
            r = requests.get
        else:
            r = requests.head
        try:
            response = r(f"{protocol}{host}/", headers=create_request_headers(domain),
                         allow_redirects=False, verify=False, timeout=http_timeout, stream=False)
            response.close()
        except Exception as e:
            result["error"] = str(e)
        else:
            result["status"] = response.status_code
            result["headers"] = get_response_headers(response.headers)
            if save_content:
                if not strip_html:
                    result["content"] = response.text
                else:
                    result["content"] = strip_newlines(strip_tags(response.text))
        results.append(result)
    return results

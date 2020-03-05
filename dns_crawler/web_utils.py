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
# import socket
# import ssl
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

import cert_human
# import certifi
import idna
import requests
import urllib3
from forcediphttpsadapter.adapters import ForcedIPHTTPSAdapter
from requests_toolbelt.adapters.source import SourceAddressAdapter
# from requests.packages.urllib3.connection import VerifiedHTTPSConnection

from .certificate import parse_cert
# from .utils import drop_null_values

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
cert_human.enable_urllib3_patch()

alpn_protocols = ['h3', 'h3-Q046', 'h3-Q043', 'h3-Q039', 'h3-24', 'h3-23',
                  'h2', 'spdy/3.1', 'spdy/3', 'spdy/2', 'spdy/1', 'http/1.1']


class CrawlerAdapter(SourceAddressAdapter, ForcedIPHTTPSAdapter):
    pass


def create_request_headers(domain, user_agent, accept_language):
    return {
        "Host": idna.encode(domain).decode("ascii"),
        "Connection": "close",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": accept_language,
    }


def parse_alt_svc(header):
    result = {}
    for pair in [i.split(";")[0].replace("\"", "") for i in re.findall(r'[a-zA-Z0-9-]+=[^,]+', header)]:
        list = unquote(pair).split("=")
        result[list[0]] = list[1]
    return result


def parse_hsts(header):
    result = {}
    items = header.split("; ")
    result["includeSubdomains"] = "includeSubdomains" in items
    result["preload"] = "preload" in items
    result["max-age"] = [int(i.split("=")[1]) for i in items if i.startswith("max-age")][0]
    return result


header_parsers = {
    "alt-svc": parse_alt_svc,
    "strict-transport-security": parse_hsts,
    "content-length": lambda header: int(header)
}


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


def get_webserver_info(domain, ips, config, source_ip, ipv6=False, tls=False):
    if not ips or len(ips) < 1:
        return None
    http_timeout = config["timeouts"]["http"]
    save_content = config["web"]["save_content"]
    max_redirects = config["web"]["max_redirects"]
    protocol = "https" if tls else "http"
    path = "/"
    results = []
    for entry in ips:
        ip = entry["value"]
        s1 = requests.session()
        s2 = requests.session()
        s1.mount(f'https://', CrawlerAdapter(dest_ip=ip, source_address=source_ip))
        s2.mount(f'https://', SourceAddressAdapter(source_address=source_ip))
        s2.mount(f'http://', SourceAddressAdapter(source_address=source_ip))
        headers = create_request_headers(domain, config["web"]["user_agent"], config["web"]["accept_language"])
        h = {}
        try:
            if protocol == "https":
                h["r"] = s1.get(f"{protocol}://{domain}{path}", allow_redirects=False,
                                verify=False, stream=True, timeout=http_timeout, headers=headers)
            else:
                if ipv6:
                    host = f"[{ip}]"
                else:
                    host = ip
                h["r"] = s2.get(f"{protocol}://{host}{path}",
                                allow_redirects=False, stream=True, timeout=http_timeout, headers=headers)
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            results.append({
                "ip": ip,
                "error": str(e)
            })
            continue
        history = [h]
        redirect_count = 0
        while history[-1]["r"].is_redirect:
            url = history[-1]["r"].headers["location"]
            h = {
                "url": url
            }
            try:
                h["r"] = s1.get(url, verify=False, allow_redirects=False, stream=True, timeout=http_timeout,
                                headers=create_request_headers(urlparse(url).hostname, config["web"]["user_agent"],
                                                               config["web"]["accept_language"]))
            except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
                h["e"] = str(e)
            history.append(h)
            redirect_count = redirect_count + 1
            if redirect_count >= max_redirects:
                break

        steps = []
        for (i, h) in enumerate(history):
            if i == 0:
                url = f"{protocol}://{domain}{path}"
            else:
                url = h["url"]
            if "e" in h:
                steps.append({
                    "url": url,
                    "error": h["e"]
                })
                continue
            step_tls = "r" in h and h["r"].url.startswith("https")
            step = {}
            if "r" in h:
                step["url"] = h["r"].url
                step["status"] = h["r"].status_code
                step["is_redirect"] = h["r"].is_redirect
            cookies = []
            for cookie in h["r"].cookies:
                cookies.append({
                    "domain": cookie.domain,
                    "name": cookie.name,
                    "value": cookie.value,
                    "secure": cookie.secure,
                    "expires": cookie.expires,
                    **cookie.__dict__['_rest']
                })
            headers = {}
            for k, v in h["r"].headers.items():
                key = k.lower()
                if key == "set-cookie":
                    headers[key] = cookies
                elif key in header_parsers:
                    headers[key] = header_parsers[key](v)
                else:
                    headers[key] = v
            step["headers"] = headers
            if i == 0:
                step["ip"] = ip
            if step_tls:
                if h["r"].raw._fp.fp:
                    step["tls"] = {
                        "version": h["r"].raw._fp.fp.raw._sock.connection.get_protocol_version_name(),
                        "cipher_bits": h["r"].raw._fp.fp.raw._sock.connection.get_cipher_bits(),
                        "cipher_name": h["r"].raw._fp.fp.raw._sock.connection.get_cipher_name()
                    }
                if config["web"]["save_cert_chain"]:
                    if h["r"].raw.peer_cert_chain:
                        cert_chain = []
                        for cert in h["r"].raw.peer_cert_chain:
                            cert_chain.append(parse_cert(cert.to_cryptography()))
                        step["cert"] = cert_chain
                else:
                    if h["r"].raw.peer_cert:
                        step["cert"] = [parse_cert(h["r"].raw.peer_cert.to_cryptography())]
            if save_content:
                if not config["web"]["strip_html"]:
                    step["content"] = h["r"].text
                else:
                    step["content"] = strip_newlines(strip_tags(h["r"].text))
            h["r"].close()
            steps.append(step)

        result = {
            "ip": ip,
            "steps": steps,
            "redirect_count": redirect_count
        }
        results.append(result)

        s1.close()
        s2.close()
    return results

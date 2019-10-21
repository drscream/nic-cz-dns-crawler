import urllib3
from hyper import HTTPConnection
from hyper.tls import init_context
from html.parser import HTMLParser
import re
import ssl
import socket
import certifi
from hyper.http20.exceptions import StreamResetError


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
        return "".join(self.fed)


def strip_tags(html):
    s = HTMLStripper()
    s.feed(html)
    return s.get_data()


def strip_newlines(text):
    return re.sub(r"\n+", "\n", re.sub(r" {2,}", "", re.sub(r"\t+", "", text))).strip()


def get_header_list(headers, name):
    return None if headers.get(name) is None else [s.decode("utf-8") for s in headers.get(name)]


def get_webserver_info(domain, ips, ipv6=False, tls=False, timeout=5, save_content=False, strip_html=False):
    headers = {
        "Host": domain,
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/74.0.3729.131 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
                  "application/signed-exchange;v=b3",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "cs-CZ,cs;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    if not ips or len(ips) < 1:
        return None
    results = []
    for ip in ips:
        result = {}
        ip = ips[0]["value"]
        result["ip"] = ip
        if tls:
            port = 443
        else:
            port = 80
        ssl_context = init_context(cert_path=certifi.where())
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        try:
            conn = HTTPConnection(host=ip, port=port, timeout=timeout, secure=tls, ssl_context=ssl_context)
            request = conn.request("GET", "/", headers={**headers, ":authority": domain})
            response = conn.get_response()
            if response.status == 400:
                conn = HTTPConnection(host=ip, port=port, timeout=timeout, secure=tls, ssl_context=ssl_context)
                request = conn.request("GET", "/", headers=headers)
                response = conn.get_response()
        except (
            ConnectionRefusedError,
            ssl.SSLError,
            socket.timeout,
            StreamResetError,
            ConnectionResetError,
            OSError,
        ) as e:
            result["error"] = str(e)
        else:
            result["status"] = response.status
            result["headers"] = {}
            if 300 < response.status < 400:
                result["headers"]["location"] = get_header_list(response.headers, "location")
            result["headers"]["server"] = get_header_list(response.headers, "server")
            result["headers"]["x-frame-options"] = get_header_list(response.headers, "x-frame-options")
            result["headers"]["content-security-policy"] = get_header_list(response.headers, "content-security-policy")
            result["headers"]["x-xss-protection"] = get_header_list(response.headers, "x-xss-protection")
            result["headers"]["strict-transport-security"] = get_header_list(
                response.headers, "strict-transport-security"
            )
            result["headers"]["expect-ct"] = get_header_list(response.headers, "expect-ct")
            result["headers"]["x-content-type-options"] = get_header_list(response.headers, "x-content-type-options")
            result["headers"]["feature-policy"] = get_header_list(response.headers, "feature-policy")
            result["headers"]["access-control-allow-origin"] = get_header_list(
                response.headers, "access-control-allow-origin"
            )
            result["headers"]["x-powered-by"] = get_header_list(response.headers, "x-powered-by")
            result["headers"] = dict(filter(lambda item: item[1] is not None, result["headers"].items()))
            if save_content:
                content = str(response.read(decode_content=True).decode())
                if strip_html:
                    result["content"] = strip_newlines(strip_tags(content))
                else:
                    result["content"] = content
            if tls and request is not None:
                result["http2"] = True
            elif tls:
                result["http2"] = False
            response.close()
        results.append(result)
    return results

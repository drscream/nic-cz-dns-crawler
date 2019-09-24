import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_webserver_vendor(domain, ips, ipv6=False, tls=False, timeout=5):
    if not ips or len(ips) < 1:
        return None
    results = []
    for ip in ips:
        result = {}
        ip = ips[0]["value"]
        result["ip"] = ip
        if tls:
            protocol = "https"
            port = 443
        else:
            protocol = "http"
            port = 80
        if not ipv6:
            host = ip
        else:
            host = f"[{ip}]"
        try:
            r_head = requests.head(
                f"{protocol}://{host}:{port}/",
                timeout=timeout,
                headers={"Host": domain},
                verify=False,
            )
        except Exception as e:
            result["value"] = None
            result["error"] = str(e)
        else:
            if "server" in r_head.headers:
                result["value"] = r_head.headers["server"]
        results.append(result)
    return results

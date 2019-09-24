import requests
from ip_utils import is_valid_ipv6_address


def ripe_ip_info(ip):
    def get_attr(json, name):
        for field in json:
            if field["name"] == name:
                return field["value"]
        return False

    def get_inetnum(json):
        inetnum = get_attr(json, "inetnum")
        if inetnum is False:
            inetnum = get_attr(json, "inet6num")
        return inetnum

    if is_valid_ipv6_address(ip):
        ripe_url = "https://rest.db.ripe.net/search?type-filter=inet6num"
    else:
        ripe_url = "https://rest.db.ripe.net/search?type-filter=inetnum"
    ripe_url = ripe_url + "&source=ripe&query-string="
    r = requests.get(ripe_url + ip, headers={"Accept": "application/json"}, timeout=5)
    try:
        ripe_json = r.json()["objects"]["object"][0]["attributes"]["attribute"]
    except KeyError:
        return None
    return {
        "netname": get_attr(ripe_json, "netname"),
        "inetnum": get_inetnum(ripe_json)
    }


def annotate_ripe(items, key="value"):
    if items:
        for item in items:
            ip = item[key]
            item["ripe"] = ripe_ip_info(ip)
    return items

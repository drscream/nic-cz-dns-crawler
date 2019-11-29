from os import path, getcwd

import yaml


def load_config(filename):
    pwd = getcwd()
    try:
        with open(path.join(pwd, filename), "r") as conf_file:
            config = yaml.load(conf_file, Loader=yaml.BaseLoader)
    except FileNotFoundError:
        config = {
            "geoip": {
                "country": "/usr/share/GeoIP/GeoIP2-Country.mmdb",
                "isp": "/usr/share/GeoIP/GeoIP2-ISP.mmdb"},
            "dns": [
                "127.0.0.1"
            ],
            "job_timeout": "80",
            "dns_timeout": "2",
            "http_timeout": "2",
            "save_web_content": "False",
            "strip_html": "True"
        }
    return config

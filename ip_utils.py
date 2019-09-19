import ipaddress


def is_valid_ipv6_address(ip):
    try:
        ipaddress.IPv6Address(ip)
    except ValueError:
        return False
    return True

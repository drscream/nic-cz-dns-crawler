import ipaddress


def is_valid_ipv6_address(ip):
    try:
        ipaddress.IPv6Address(ip)
    except ValueError:
        return False
    return True


def is_valid_ipv4_address(ip):
    try:
        ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    return True


def is_valid_ip_address(ip):
    return is_valid_ipv4_address(ip) or is_valid_ipv6_address(ip)

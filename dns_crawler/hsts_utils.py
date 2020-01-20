from hstspreload import in_hsts_preload
import idna


def get_hsts_status(domain):
    return in_hsts_preload(idna.encode(domain).decode("ascii"))

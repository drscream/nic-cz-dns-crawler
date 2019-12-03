import json
import sys

from .crawl import process_domain
from .timestamp import timestamp


def print_help():
    sys.stderr.write(f"Usage: {sys.argv[0]} <file>\n")
    sys.stderr.write(f"       file - plaintext domain list, one domain per line (separated by \\n)\n")
    sys.exit(1)


def main():
    try:
        filename = sys.argv[1]
    except IndexError:
        print_help()

    try:
        with open(filename, "r") as file:
            sys.stderr.write(f"{timestamp()} Reading domains from {filename}.\n")
            domains = [line for line in file.read().splitlines() if line.strip()]
            domain_count = len(domains)
            sys.stderr.write(f"{timestamp()} Read {domain_count} domain{('s' if domain_count > 1 else '')}.\n")
            for num, domain in enumerate(domains, start=1):
                print(json.dumps(process_domain(domain)))
                sys.stderr.write(f"{timestamp()} {num}/{domain_count}\n")
            sys.stderr.write(f"{timestamp()} Finished.\n")
    except FileNotFoundError:
        sys.stderr.write(f"File '{filename}' does not exist.\n\n")
        print_help()
    except KeyboardInterrupt:
        sys.exit(0)

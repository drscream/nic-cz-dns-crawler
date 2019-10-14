import sys


def print_help():
    sys.stderr.write(f"Usage: {sys.argv[0]} <table name> - generate the table structure\n")
    sys.stderr.write(f"                                    (-> CREATE TABLE table_name …)\n")
    sys.stderr.write(f"       main.py … | {sys.argv[0]} <table name> - insert results into the table\n")
    sys.stderr.write(f"                                                (-> INSERT INTO table_name VALUES …)\n")
    sys.exit(1)


try:
    table_name = sys.argv[1]
except IndexError:
    print_help()


if sys.stdin.isatty():
    sys.stdout.write(f"CREATE TABLE {table_name} (ID bigserial NOT NULL PRIMARY KEY, data jsonb NOT NULL);\n")
else:
    sys.stdout.write(f"INSERT INTO {table_name} (data) VALUES ")
    for line in sys.stdin:
        data = line.replace("\n", "").replace("'", "''")
        sys.stdout.write(f"('{data}'),")
    sys.stdout.write(";\n")

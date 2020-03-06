# Copyright © 2019-2020 CZ.NIC, z. s. p. o.
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of dns-crawler.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from redis import Redis
from redis.exceptions import ConnectionError


REDIS_DEFAULT_HOST = "localhost:6379:0"


def get_redis_host(argv, index):
    default = REDIS_DEFAULT_HOST.split(":")

    try:
        param = argv[index].split(":")
    except IndexError:
        redis_host = default[0]
        redis_port = int(default[1])
        redis_db = int(default[2])
    else:
        try:
            redis_host = param[0]
        except IndexError:
            redis_host = default[0]
            redis_port = int(default[1])
            redis_db = int(default[2])
        else:
            try:
                redis_port = int(param[1])
            except IndexError:
                redis_port = int(default[1])
                redis_db = int(default[2])
            else:
                try:
                    redis_db = int(param[2])
                except IndexError:
                    redis_db = int(default[2])

    try:
        redis = Redis(host=redis_host, port=redis_port, db=redis_db)
        redis.ping()
    except (ConnectionError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
        raise Exception(f"Can't connect to Redis DB #{redis_db} at {redis_host}:{redis_port}.")
    return (redis_host, redis_port, redis_db)

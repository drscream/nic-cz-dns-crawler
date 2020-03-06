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

from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="dns-crawler",
    use_scm_version=True,
    packages=["dns_crawler"],
    setup_requires=["setuptools_scm"],
    description="A crawler for getting info about DNS domains and services attached to them.",
    author="Jiri Helebrant",
    author_email="jiri.helebrant@nic.cz",
    url="https://gitlab.labs.nic.cz/adam/dns-crawler",
    entry_points={
        "console_scripts": [
            "dns-crawler-controller=dns_crawler.controller:main",
            "dns-crawler-workers=dns_crawler.workers:main",
            "dns-crawler-worker=dns_crawler.worker:main",
            "dns-crawler=dns_crawler.single:main"
        ]
    },
    install_requires=[
        "asn1crypto==1.3.0",
        "cert_human==1.0.7",
        "cryptography==2.8",
        "dnspython",
        "ecdsa==0.15",
        "forcediphttpsadapter==1.0.1",
        "geoip2==3.0.0",
        "hstspreload",
        "idna==2.9",
        "pyaml==19.12.0",
        "pycryptodome==3.9.7",
        "pyopenssl==19.1.0",
        "redis==3.4.1",
        "requests_toolbelt==0.9.1",
        "requests==2.23.0",
        "rq==1.2.2",
    ],
    keywords=["crawler", "dns", "http", "https"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent"
    ],
    python_requires='>=3.6',
    long_description=long_description,
    long_description_content_type="text/markdown"
)

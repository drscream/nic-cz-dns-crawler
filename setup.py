from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="dns-crawler",
    version="1.0.0",
    packages=["dns_crawler"],
    setup_requires=["setuptools_scm"],
    description="A crawler for getting info about DNS domains and services attached to them.",
    author="Jiri Helebrant",
    author_email="jiri.helebrant@nic.cz",
    url="https://gitlab.labs.nic.cz/adam/dns-crawler",
    entry_points={
        "console_scripts": [
            "dns-crawler=dns_crawler.controller:main",
            "dns-crawler-workers=dns_crawler.workers:main"
        ]
    },
    install_requires=[
        "rq==1.1.0",
        "redis==3.3.11",
        "geoip2==2.9.0",
        "pyaml==19.4.1",
        "pycryptodome==3.9.0",
        "ecdsa==0.13.3",
        "certifi==2019.9.11",
        "requests==2.22.0",
        "cryptography==2.8",
        "pyopenssl==19.1.0",
        "dnspython"
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

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
        "rq==1.2.2",
        "redis==3.4.1",
        "geoip2==3.0.0",
        "pyaml==19.12.0",
        "pycryptodome==3.9.7",
        "ecdsa==0.15",
        "certifi==2019.11.28",
        "requests==2.23.0",
        "cryptography==2.8",
        "pyopenssl==19.1.0",
        "idna==2.9",
        "hstspreload",
        "requests_toolbelt==0.9.1",
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

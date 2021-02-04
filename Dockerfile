FROM python:3.9-slim
RUN apt-get -yqq update
RUN apt-get -yqq upgrade
RUN apt-get -yqq install libicu-dev pkg-config build-essential ca-certificates
RUN pip install dns-crawler
RUN apt-get remove -yqq pkg-config build-essential
RUN apt-get -yqq autoremove
RUN apt-get -yqq clean
COPY config.docker.yml /config.yml
RUN mkdir /crawler
RUN mkdir /geoip
CMD bash

# Usage:
# echo -e "nic.cz\nnetmetr.cz\nroot.cz" > domain-list.txt
# docker run --rm -v /usr/share/GeoIP/:/geoip -v $(pwd):/crawler helb/dns-crawler dns-crawler /crawler/domain-list.txt > results.json
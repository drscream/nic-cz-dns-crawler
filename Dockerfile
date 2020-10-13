FROM python:3.9.0-slim
RUN apt-get -yqq update
RUN apt-get -yqq install libicu-dev pkg-config build-essential
RUN pip install dns-crawler
RUN apt-get remove -yqq pkg-config build-essential
RUN apt-get -yqq autoremove
RUN apt-get -yqq clean
CMD bash
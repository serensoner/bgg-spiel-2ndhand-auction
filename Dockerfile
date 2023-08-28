FROM python:3.11-slim
WORKDIR /var/www/html
COPY ./requirements.txt /var/www/html

# Updating and installing libs
RUN apt-get update \
    && apt-get upgrade -yq \
    && apt-get install python3-pip -yq \
    && apt-get install tzdata locales -yq \
    && apt-get install git -yq \
    && locale-gen en_US.UTF-8

ENV AUCTION_ID=319184

RUN echo $TZ > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    && pip3 install Cython==0.29.21 \
    && pip3 install -r /var/www/html/requirements.txt

COPY . /var/www/html

ENTRYPOINT ["/entrypoint.sh"]

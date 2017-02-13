FROM debian:jessie

RUN apt-get update \
    && apt-get install -y curl \
    && curl -s https://packagecloud.io/install/repositories/rolandoislas/drc-sim/script.deb.sh | bash
RUN apt-get update \
    && apt-get install -y \
    wpasupplicant-drc \
    python2.7 \
    python2.7-dev \
    python-pip \
    libffi-dev \
    zlib1g-dev \
    libjpeg62-turbo-dev \
    net-tools \
    wireless-tools \
    sysvinit-utils \
    psmisc \
    libavcodec-dev \
    libswscale-dev \
    rfkill \
    isc-dhcp-client

ADD drc*.py /root/
ADD setup.py /root/
ADD src/ /root/src/
ADD resources/ /root/resources/
ADD MANIFEST.in /root/
RUN cd /root/ && python setup.py install && rm -rf /root/*

ENV TERM xterm
ENTRYPOINT ["drc-sim-helper.py"]

FROM debian:jessie

RUN apt-get update \
    && apt-get install -y curl \
    && curl -s https://packagecloud.io/install/repositories/rolandoislas/drc-sim/script.deb.sh | bash
RUN apt-get update \
    && apt-get install -y \
    wpasupplicant-drc \
    python3 \
    python3-dev \
    python3-pip \
    libffi-dev \
    zlib1g-dev \
    libjpeg-dev \
    net-tools \
    wireless-tools \
    sysvinit-utils \
    psmisc \
    libavcodec-dev \
    libswscale-dev \
    rfkill \
    isc-dhcp-client \
    ifmetric

ADD drc*.py /root/
ADD setup.py /root/
ADD src/ /root/src/
ADD resources/ /root/resources/
ADD MANIFEST.in /root/
RUN cd /root/ && python3 setup.py install

ENV TERM xterm
ENTRYPOINT ["drc-sim-backend.py", "--cli"]
CMD ["-h"]

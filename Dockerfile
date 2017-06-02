FROM debian:jessie

ADD drc-sim-backend /root/
ADD setup.py /root/
ADD src/ /root/src/
ADD resources/ /root/resources/
ADD MANIFEST.in /root/
ADD install.sh /root/

RUN apt-get update \
    && cd /root/ \
    && ./install.sh local

ENV TERM xterm
ENTRYPOINT ["drc-sim-backend", "--cli"]
CMD ["-h"]

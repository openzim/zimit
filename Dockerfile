FROM webrecorder/browsertrix-crawler:0.1.4
LABEL org.opencontainers.image.source https://github.com/openzim/zimit

RUN mkdir -p /output

WORKDIR /app

RUN pip install 'warc2zim>=1.3.3' 'requests>=2.24.0' 'inotify==0.2.10'

ADD zimit.py /app/

RUN ln -s /app/zimit.py /usr/bin/zimit

CMD ["zimit"]


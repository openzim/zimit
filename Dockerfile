FROM webrecorder/browsertrix-crawler:0.1.1

RUN mkdir -p /output

WORKDIR /app

RUN pip install 'warc2zim>=1.3.1'

ADD zimit.py /app/

RUN ln -s /app/zimit.py /usr/bin/zimit

CMD ["zimit"]


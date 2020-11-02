FROM webrecorder/browsertrix-crawler:0.1.0

WORKDIR /app

RUN pip install 'warc2zim>=1.3.0'

ADD zimit.py /app/

RUN ln -s /app/zimit.py /usr/bin/zimit

CMD ["zimit"]


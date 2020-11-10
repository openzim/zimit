FROM webrecorder/browsertrix-crawler:0.1.1

WORKDIR /app

#RUN pip install 'warc2zim>=1.3.0'
RUN pip install git+https://github.com/openzim/warc2zim.git@favicon-fix

ADD zimit.py /app/

RUN ln -s /app/zimit.py /usr/bin/zimit

CMD ["zimit"]


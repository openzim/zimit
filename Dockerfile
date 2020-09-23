FROM oldwebtoday/chrome:84 as chrome

FROM nikolaik/python-nodejs

ENV PROXY_HOST=localhost \
    PROXY_PORT=8080 \
    PROXY_CA_URL=http://wsgiprox/download/pem \
    PROXY_CA_FILE=/tmp/proxy-ca.pem \
    NO_SOCAT=1

RUN pip install pywb uwsgi warc2zim
# force reinstall of gevent to prevent segfault on uwsgi worker
RUN pip install -U gevent

#COPY --from=chrome /opt/google/chrome/ /opt/google/chrome/
  
#COPY --from=chrome /app/ /browser/
COPY --from=chrome /usr/lib/x86_64-linux-gnu/ /usr/lib/x86_64-linux-gnu/
COPY --from=chrome /lib/x86_64-linux-gnu/libdbus* /lib/x86_64-linux-gnu/
#COPY --from=chrome /usr/bin/run_forever /usr/bin/
#COPY --from=chrome /usr/bin/wget /usr/bin/
#COPY --from=chrome /usr/bin/certutil /usr/bin/

#RUN ln -s /opt/google/chrome/google-chrome /usr/bin/google-chrome

RUN useradd zimit --shell /bin/bash --create-home \
  && usermod -a -G sudo zimit \
  && echo 'ALL ALL = (ALL) NOPASSWD: ALL' >> /etc/sudoers \
  && echo 'zimit:secret' | chpasswd

WORKDIR /app

ADD package.json /app/

RUN chown -R zimit /app

#USER zimit

RUN yarn install

ADD config.yaml /app/
ADD uwsgi.ini /app/
ADD run.sh /app/
ADD index.js /app/

ENTRYPOINT ["/app/run.sh"]


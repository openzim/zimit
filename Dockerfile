FROM webrecorder/browsertrix-crawler:0.1.4
LABEL org.opencontainers.image.source https://github.com/openzim/zimit

RUN mkdir -p /output

WORKDIR /app

RUN pip install 'warc2zim>=1.3.3' 'requests>=2.24.0' 'inotify==0.2.10'

ADD zimit.py /app/

RUN ln -s /app/zimit.py /usr/bin/zimit

# download list of bad domains to filter-out. intentionnaly ran post-install
# so it's not cached in earlier layers (url stays same but content updated)
RUN mkdir -p /tmp/ads && cd /tmp/ads && \
    curl -L -O https://hosts.anudeep.me/mirror/adservers.txt && \
    curl -L -O https://hosts.anudeep.me/mirror/CoinMiner.txt && \
    curl -L -O https://hosts.anudeep.me/mirror/facebook.txt && \
    cat ./*.txt > /etc/blocklist.txt \
    && rm ./*.txt
RUN printf '#!/bin/sh\ncat /etc/blocklist.txt >> /etc/hosts\nexec "$@"' > /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["entrypoint.sh"]
CMD ["zimit"]

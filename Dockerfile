FROM webrecorder/browsertrix-crawler:0.5.0-beta.0
LABEL org.opencontainers.image.source https://github.com/openzim/zimit

RUN mkdir -p /output

WORKDIR /app

RUN apt-get update && apt-get install -qqy libmagic1

RUN pip3.8 install 'requests>=2.24.0' 'inotify==0.2.10' 'tld>=0.12,<0.13'
RUN pip3.8 install git+https://github.com/openzim/warc2zim@video-replay-fixes#A

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

ADD zimit.py /app/

RUN ln -s /app/zimit.py /usr/bin/zimit

ENTRYPOINT ["entrypoint.sh"]
CMD ["zimit"]

FROM webrecorder/browsertrix-crawler:0.7.0-beta.1
LABEL org.opencontainers.image.source https://github.com/openzim/zimit

RUN apt-get update && apt-get install -qqy --no-install-recommends libmagic1 && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir 'requests>=2.24.0' 'inotify==0.2.10' 'tld>=0.12,<0.13' && \
    pip3 install 'git+https://github.com/openzim/warc2zim@master#egg_name=warc2zim'

RUN mkdir -p /output

WORKDIR /app

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

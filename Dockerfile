FROM webrecorder/browsertrix-crawler:0.12.3
LABEL org.opencontainers.image.source https://github.com/openzim/zimit

RUN apt-get update \
    && apt-get install -qqy --no-install-recommends \
        libmagic1 \
        python3.10-venv \
    && rm -rf /var/lib/apt/lists/* \
    # python setup (in venv not to conflict with browsertrix)
    && python3 -m venv /app/zimit \
    && /app/zimit/bin/python -m pip install --no-cache-dir 'requests==2.31.0' 'inotify==0.2.10' 'tld==0.13' \
    'git+https://github.com/openzim/warc2zim@main#egg_name=warc2zim' \
    # placeholder (default output location)
    && mkdir -p /output \
    # disable chrome upgrade
    && printf "repo_add_once=\"false\"\nrepo_reenable_on_distupgrade=\"false\"\n" > /etc/default/google-chrome \
    # download list of bad domains to filter-out. intentionnaly ran post-install \
    # so it's not cached in earlier layers (url stays same but content updated) \
    mkdir -p /tmp/ads && cd /tmp/ads && \
    curl -L -O https://hosts.anudeep.me/mirror/adservers.txt && \
    curl -L -O https://hosts.anudeep.me/mirror/CoinMiner.txt && \
    curl -L -O https://hosts.anudeep.me/mirror/facebook.txt && \
    cat ./*.txt > /etc/blocklist.txt \
    && rm ./*.txt \
    && printf '#!/bin/sh\ncat /etc/blocklist.txt >> /etc/hosts\nexec "$@"' > /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /app
ADD zimit.py /app/
# fix shebang on zimit to use in-venv python
RUN sed -i.bak "1 s/.*/#!\/app\/zimit\/bin\/python3/" /app/zimit.py \
    && ln -s /app/zimit.py /usr/bin/zimit \
    && chmod +x /usr/bin/zimit

ENTRYPOINT ["entrypoint.sh"]
CMD ["zimit"]

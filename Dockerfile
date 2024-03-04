FROM webrecorder/browsertrix-crawler:0.12.4
LABEL org.opencontainers.image.source https://github.com/openzim/zimit

# add deadsnakes ppa for Python 3.12 on Ubuntu Jammy
RUN add-apt-repository ppa:deadsnakes/ppa -y

RUN apt-get update \
 && apt-get install -qqy --no-install-recommends \
      libmagic1 \
      python3.12-venv \
 && rm -rf /var/lib/apt/lists/* \
 # python setup (in venv not to conflict with browsertrix)
 && python3.12 -m venv /app/zimit \
 # placeholder (default output location)
 && mkdir -p /output \
 # disable chrome upgrade
 && printf "repo_add_once=\"false\"\nrepo_reenable_on_distupgrade=\"false\"\n" > /etc/default/google-chrome \
 # download list of bad domains to filter-out. intentionnaly ran post-install \
 # so it's not cached in earlier layers (url stays same but content updated) \
 && mkdir -p /tmp/ads \
 && cd /tmp/ads \
 && curl -L -O https://hosts.anudeep.me/mirror/adservers.txt \
 && curl -L -O https://hosts.anudeep.me/mirror/CoinMiner.txt \
 && curl -L -O https://hosts.anudeep.me/mirror/facebook.txt \
 && cat ./*.txt > /etc/blocklist.txt \
 && rm ./*.txt \
 && printf '#!/bin/sh\ncat /etc/blocklist.txt >> /etc/hosts\nexec "$@"' > /usr/local/bin/entrypoint.sh \
 && chmod +x /usr/local/bin/entrypoint.sh

# Copy pyproject.toml and its dependencies
COPY pyproject.toml README.md /src/
COPY src/zimit/__about__.py /src/src/zimit/__about__.py

# Install Python dependencies
RUN /app/zimit/bin/python -m pip install --no-cache-dir /src

# Copy code + associated artifacts
COPY src /src/src
COPY *.md /src/

# Install + cleanup
RUN /app/zimit/bin/python -m pip install --no-cache-dir /src \
 && ln -s /app/zimit/bin/zimit /usr/bin/zimit \
 && chmod +x /usr/bin/zimit \
 && rm -rf /src

ENTRYPOINT ["entrypoint.sh"]
CMD ["zimit", "--help"]

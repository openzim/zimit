FROM webrecorder/browsertrix-crawler:1.15.4
LABEL org.opencontainers.image.source=https://github.com/openzim/zimit

# static uv binary, used below to fetch a standalone Python 3.14 build
# instead of relying on the deadsnakes PPA, whose Launchpad mirror has had
# repeated multi-hour outages
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

# update yarnpkg public key to workaround https://github.com/webrecorder/browsertrix-browser-base/issues/22
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
 && echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list

RUN apt-get update \
 && apt-get install -qqy --no-install-recommends \
      libmagic1 \
 && rm -rf /var/lib/apt/lists/* \
 # python setup (in venv not to conflict with browsertrix); --seed installs
 # pip in the venv, since the rest of this file uses "python -m pip install"
 && uv venv --seed --python 3.14 /app/zimit \
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
RUN . /app/zimit/bin/activate && python -m pip install --no-cache-dir /src

# Copy code + associated artifacts
COPY src /src/src
COPY *.md /src/

# Install + cleanup
RUN . /app/zimit/bin/activate && python -m pip install --no-cache-dir /src \
 && ln -s /app/zimit/bin/zimit /usr/bin/zimit \
 && ln -s /app/zimit/bin/warc2zim /usr/bin/warc2zim \
 && chmod +x /usr/bin/zimit \
 && rm -rf /src

ENTRYPOINT ["entrypoint.sh"]
CMD ["zimit", "--help"]

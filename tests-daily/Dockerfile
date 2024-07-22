# Let's extract kiwix-tools as usual on alpine temporary build container
FROM alpine:3.18 as kiwix-serve
LABEL org.opencontainers.image.source https://github.com/openzim/kiwix-tools

# TARGETPLATFORM is injected by docker build
ARG TARGETPLATFORM
ARG KIWIX_TOOLS_VERSION

RUN set -e && \
    # default (no KIWIX_TOOLS_VERSION set) to today's nightly
    if [ -z "$KIWIX_TOOLS_VERSION" ] ; then KIWIX_TOOLS_VERSION=$(date +"%Y-%m-%d") ; fi && \
    apk --no-cache add dumb-init curl && \
    echo "TARGETPLATFORM: $TARGETPLATFORM" && \
    if [ "$TARGETPLATFORM" = "linux/386" ]; then ARCH="i586"; \
    # linux/arm64/v8 points to linux/arm64
    elif [ "$TARGETPLATFORM" = "linux/arm64/v8" \
        -o "$TARGETPLATFORM" = "linux/arm64" ]; then ARCH="aarch64"; \
    # linux/arm translates to linux/arm/v7
    elif [ "$TARGETPLATFORM" = "linux/arm/v7" ]; then ARCH="armv8"; \
    elif [ "$TARGETPLATFORM" = "linux/arm/v6" ]; then ARCH="armv6"; \
    elif [ "$TARGETPLATFORM" = "linux/amd64/v3" \
        -o "$TARGETPLATFORM" = "linux/amd64/v2" \
        -o "$TARGETPLATFORM" = "linux/amd64" ]; then ARCH="x86_64"; \
    # we dont suppot any other arch so let it fail
    else ARCH="unknown"; fi && \
    # download requested kiwix-tools version
    url="http://mirror.download.kiwix.org/nightly/$KIWIX_TOOLS_VERSION/kiwix-tools_linux-$ARCH-$KIWIX_TOOLS_VERSION.tar.gz" && \
    echo "URL: $url" && \
    mkdir /kiwix-serve && \
    curl -k -L $url | tar -xz -C /kiwix-serve --strip-components 1

# Build real "workload" container
FROM python:3.12-slim-bookworm

# Add kiwix-serve
COPY --from=kiwix-serve /kiwix-serve /usr/local/bin

# Update apt + install dependencies + install Google Chrome dependencies + clean-up apt lists
RUN apt-get update -y && \
    apt-get install -qqy wget xvfb unzip jq && \
    apt-get install -qqy libxss1 libappindicator1 libgconf-2-4 \
    fonts-liberation libasound2 libnspr4 libnss3 libx11-xcb1 libxtst6 lsb-release xdg-utils \
    libgbm1 libnss3 libatk-bridge2.0-0 libgtk-3-0 libx11-xcb1 libxcb-dri3-0 && \
    rm -rf /var/lib/apt/lists/*

# Fetch the latest version numbers and URLs for Chrome and ChromeDriver
RUN wget -q -O /tmp/versions.json https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json

# Install chrome
RUN CHROME_URL=$(jq -r '.channels.Stable.downloads.chrome[] | select(.platform=="linux64") | .url' /tmp/versions.json) && \
    wget -q --continue -O /tmp/chrome-linux64.zip $CHROME_URL && \
    unzip /tmp/chrome-linux64.zip -d /opt/chrome

RUN chmod +x /opt/chrome/chrome-linux64/chrome

# Install chromedriver
RUN CHROMEDRIVER_URL=$(jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url' /tmp/versions.json) && \
    wget -q --continue -O /tmp/chromedriver-linux64.zip $CHROMEDRIVER_URL && \
    unzip /tmp/chromedriver-linux64.zip -d /opt/chromedriver && \
    chmod +x /opt/chromedriver/chromedriver-linux64/chromedriver

# Set up Chromedriver Environment variables
ENV CHROMEDRIVER_DIR /opt/chromedriver
ENV PATH $CHROMEDRIVER_DIR:$PATH

# Clean up
RUN rm /tmp/chrome-linux64.zip /tmp/chromedriver-linux64.zip /tmp/versions.json

# Update pip, install selenium, create work directory
RUN \
   python -m pip install --no-cache-dir -U \
     pip \
     selenium==4.23.0 \
     pytest==8.2.2 \
&& mkdir -p /work

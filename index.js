const puppeteer = require("puppeteer");
const { Cluster } = require("puppeteer-cluster");
const child_process = require("child_process");
const fetch = require("node-fetch");
const AbortController = require("abort-controller");

const HTML_TYPES = ["text/html", "application/xhtml", "application/xhtml+xml"];


async function run(params) {
  // Chrome Flags, including proxy server
  const args = [
    "--no-xshm", // needed for Chrome >80 (check if puppeteer adds automatically)
    `--proxy-server=http://${process.env.PROXY_HOST}:${process.env.PROXY_PORT}`
  ];

  // prefix for direct capture via pywb
  const capturePrefix = `http://${process.env.PROXY_HOST}:${process.env.PROXY_PORT}/capture/record/id_/`;

  // Puppeter Options
  const puppeteerOptions = {
    headless: true,
    //executablePath: "/usr/bin/google-chrome",
    ignoreHTTPSErrors: true,
    args
  };

  // Puppeteer Cluster init and options
  const cluster = await Cluster.launch({
    concurrency: Cluster.CONCURRENCY_PAGE,
    maxConcurrency: Number(params.workers) || 1,
    skipDuplicateUrls: true,
    puppeteerOptions,
    puppeteer,
    monitor: true
  });

  // Maintain own seen list
  let seenList = new Set();
  const url = params._[0];

  let { waitUntil, timeout, scope, limit } = params;

  // waitUntil condition (see: https://github.com/puppeteer/puppeteer/blob/main/docs/api.md#pagegotourl-options)
  waitUntil = waitUntil || "load";

  // Timeout per page
  timeout = Number(timeout) || 60000;

  // Scope for crawl, default to the domain of the URL
  scope = scope || new URL(url).origin + "/";

  // Limit number of pages captured
  limit = Number(limit) || 0;

  console.log("Limit: " + limit);

  // links crawled counter
  let numLinks = 0;

  // Crawl Task
  cluster.task(async ({page, data}) => {
    const {url} = data;

    if (!await htmlCheck(url, capturePrefix)) {
      return;
    }

    try {
      await page.goto(url, {waitUntil, timeout});
    } catch (e) {
      console.log(`Load timeout for ${url}`);
    }

    let results = null;

    try {
      results = await page.evaluate(() => {
        return [...document.querySelectorAll('a[href]')].map(el => ({ url: el.href}))
      });
    } catch (e) {
      console.warn("Link Extraction failed", e);
      return;
    }

    try {
      for (data of results) {
        const newUrl = shouldCrawl(scope, seenList, data.url);

        if (newUrl) {
          seenList.add(newUrl);
          if (numLinks++ >= limit && limit > 0) {
            break;
          }
          cluster.queue({url: newUrl});
        }
      }
    } catch (e) {
      console.log("Queuing Error: " + e);
    }
  });

  numLinks++;
  cluster.queue({url});

  await cluster.idle();
  await cluster.close();

  const zimName = params.name || new URL(url).hostname;
  const zimOutput = params.output || "/output";

  const warc2zim = `warc2zim --url ${url} --name ${zimName} --output ${zimOutput} ./collections/capture/archive/\*.warc.gz`;

  console.log("Running: " + warc2zim);

  //await new Promise((resolve) => {
  child_process.execSync(warc2zim, {shell: "/bin/bash", stdio: "inherit", stderr: "inherit"});
  //});
}


function shouldCrawl(scope, seenList, url) {
  try {
    url = new URL(url);
  } catch(e) {
    return false;
  }

  // remove hashtag
  url.hash = "";

  // only queue http/https URLs
  if (url.protocol != "http:" && url.protocol != "https:") {
    return false;
  }

  url = url.href;

  // skip already crawled
  if (seenList.has(url)) {
    return false;
  }

  // if scope is provided, skip urls not in scope
  if (scope && !url.startsWith(scope)) {
    return false;
  }

  return url;
}

async function htmlCheck(url, capturePrefix) {
  try {
    const resp = await fetch(url, {method: "HEAD"});

    if (resp.status >= 400) {
      console.log(`Skipping ${url}, invalid status ${resp.status}`);
      return false;
    }

    const contentType = resp.headers.get("Content-Type");

    // just load if no content-type
    if (!contentType) {
      return true;
    }

    const mime = contentType.split(";")[0];

    if (HTML_TYPES.includes(mime)) {
      return true;
    }

    // capture directly
    console.log(`Direct capture: ${capturePrefix}${url}`);
    const abort = new AbortController();
    const signal = abort.signal;
    const resp2 = await fetch(capturePrefix + url, {signal});
    abort.abort();

    return false;
  } catch(e) {
    console.log("HTML Check error", e);
    // can't confirm not html, so try in browser
    return true;
  }
}


async function main() {
  const params = require('yargs').argv;
  console.log(params);

  try {
    await run(params);
    process.exit(0);
  } catch(e) {
    console.error("Crawl failed, ZIM creation skipped");
    console.error(e);
    process.exit(1);
  }
}

main();



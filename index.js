const puppeteer = require("puppeteer");
const { Cluster } = require("puppeteer-cluster");
const child_process = require("child_process");
const fetch = require("node-fetch");
const AbortController = require("abort-controller");

const HTML_TYPES = ["text/html", "application/xhtml", "application/xhtml+xml"];
const WAIT_UNTIL_OPTS = ["load", "domcontentloaded", "networkidle0", "networkidle2"];
const CHROME_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36";

// to ignore HTTPS error for HEAD check
const HTTPS_AGENT = require("https").Agent({
  rejectUnauthorized: false,
});


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
  const seenList = new Set();

  // params
  const { url, waitUntil, timeout, scope, limit, exclude, scroll } = params;

  //console.log("Limit: " + limit);

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

    if (scroll) {
      try {
        await Promise.race([page.evaluate(autoScroll), sleep(30000)]);
      } catch (e) {
        console.warn("Behavior Failed", e);
      }
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
        const newUrl = shouldCrawl(scope, seenList, data.url, exclude);

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

  // extra wait for all resources to land into WARCs
  console.log("Waiting 30s to ensure WARCs are finished");
  await sleep(30000);
}


function shouldCrawl(scope, seenList, url, exclude) {
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

  // check exclusions
  for (const e of exclude) {
    if (e.exec(url)) {
      //console.log(`Skipping ${url} excluded by ${e}`);
      return false;
    }
  }

  return url;
}

async function htmlCheck(url, capturePrefix) {
  try {
    const headers = {"User-Agent": CHROME_USER_AGENT};

    const agent = url.startsWith("https:") ? HTTPS_AGENT : null;

    const resp = await fetch(url, {method: "HEAD", headers, agent});

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
    const resp2 = await fetch(capturePrefix + url, {signal, headers});
    abort.abort();

    return false;
  } catch(e) {
    console.log("HTML Check error", e);
    // can't confirm not html, so try in browser
    return true;
  }
}


async function autoScroll() {
  const canScrollMore = () =>
    self.scrollY + self.innerHeight <
    Math.max(
      self.document.body.scrollHeight,
      self.document.body.offsetHeight,
      self.document.documentElement.clientHeight,
      self.document.documentElement.scrollHeight,
      self.document.documentElement.offsetHeight
    );

  const scrollOpts = { top: 250, left: 0, behavior: 'auto' };

  while (canScrollMore()) {
    self.scrollBy(scrollOpts);
    await new Promise(resolve => setTimeout(resolve, 500));
  }
}

function sleep(time) {
  return new Promise(resolve => setTimeout(resolve, time));
}


async function main() {
  const params = require('yargs')
  .usage("zimit [options] [warc2zim options]")
  .options({
    "url": {
      alias: "u",
      describe: "The URL to start crawling from and main page for ZIM",
      demandOption: true,
      type: "string",
    },

    "workers": {
      alias: "w",
      describe: "The number of workers to run in parallel",
      demandOption: false,
      default: 1,
      type: "number",
    },

    "waitUntil": {
      describe: "Puppeteer page.goto() condition to wait for before continuing",
      default: "load",
    },

    "limit": {
      describe: "Limit crawl to this number of pages",
      default: 0,
      type: "number",
    },

    "timeout": {
      describe: "Timeout for each page to load (in millis)",
      default: 90000,
      type: "number",
    },

    "scope": {
      describe: "The scope of current page that should be included in the crawl (defaults to the domain of URL)",
    },

    "exclude": {
      describe: "Regex of URLs that should be excluded from the crawl."
    },

    "scroll": {
      describe: "If set, will autoscroll to bottom of the page",
      type: "boolean",
      default: false,

    }}).check((argv, option) => {
      // Scope for crawl, default to the domain of the URL
      const url = new URL(argv.url);

      if (url.protocol !== "http:" && url.protocol != "https:") {
        throw new Error("URL must start with http:// or https://");
      }

      // ensure valid url is used (adds trailing slash if missing)
      argv.url = url.href;

      if (!argv.scope) {
        argv.scope = url.href.slice(0, url.href.lastIndexOf("/") + 1);
      }

      // waitUntil condition must be: load, domcontentloaded, networkidle0, networkidle2
      // (see: https://github.com/puppeteer/puppeteer/blob/main/docs/api.md#pagegotourl-options)
      if (!WAIT_UNTIL_OPTS.includes(argv.waitUntil)) {
        throw new Error("Invalid waitUntil, must be one of: " + WAIT_UNTIL_OPTS.join(","));
      }

      if (argv.exclude) {
        if (typeof(argv.exclude) === "string") {
          argv.exclude = [new RegExp(argv.exclude)];
        } else {
          argv.exclude = argv.exclude.map(e => new RegExp(e));
        }
      } else {
        argv.exclude = [];
      }

      return true;
    })
  .argv;

  runWarc2Zim(params, true);

  try {
    await run(params);
    runWarc2Zim(params, false);
    process.exit(0);
  } catch(e) {
    console.error("Crawl failed, ZIM creation skipped");
    console.error(e);
    process.exit(1);
  }
}

function runWarc2Zim(params, checkOnly = true) {
  const OPTS = ["_", "u", "$0", "keep", "workers", "w", "waitUntil", "wait-until", "limit", "timeout", "scope", "exclude", "scroll"];

  let zimOptsStr = "";

  for (const key of Object.keys(params)) {
    if (!OPTS.includes(key)) {
      zimOptsStr += (key.length === 1 ? "-" : "--") + key + " ";

      switch (typeof(params[key])) {
        case "string":
        case "number":
          zimOptsStr += `"${params[key]}" `;
          break;

        case "object":
          zimOptsStr += params[key].map(x => `"${x}"`).join(` --${key} `) + " ";
          break;
      }
    }
  }

  const warc2zimCmd = "warc2zim " + zimOptsStr + (checkOnly ? "" : " ./collections/capture/archive/\*.warc.gz");

  console.log("Running: " + warc2zimCmd);

  const {status} = child_process.spawnSync(warc2zimCmd, {shell: "/bin/bash", stdio: "inherit", stderr: "inherit"});

  if ((!checkOnly && status) || (checkOnly && status !== 100)) {
    console.error("Invalid warc2zim params, warc2zim exited with: " + status);
    process.exit(status);
  }
}






main();



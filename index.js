const puppeteer = require("puppeteer-core");
const { Cluster } = require("puppeteer-cluster");
const child_process = require("child_process");

async function run(params) {
  // Chrome Flags, including proxy server
  const args = [
    "--no-xshm", // needed for Chrome >80 (check if puppeteer adds automatically)
    `--proxy-server=http://${process.env.PROXY_HOST}:${process.env.PROXY_PORT}`
  ];

  // Puppeter Options
  const puppeteerOptions = {
    headless: true,
    executablePath: "/usr/bin/google-chrome",
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

  let { waitUntil, timeout, scope } = params;

  // waitUntil condition (see: https://github.com/puppeteer/puppeteer/blob/main/docs/api.md#pagegotourl-options)
  waitUntil = waitUntil || "load";

  // Timeout per page
  timeout = timeout || 60000;

  // Scope for crawl, default to the domain of the URL
  scope = scope || new URL(url).origin + "/";

  // Crawl Task
  cluster.task(async ({page, data}) => {
    const {url} = data;

    try {
      await page.goto(url, {waitUntil, timeout});
    } catch (e) {
      console.log(`Load timeout for ${url}`);
    }

    try{
      const result = await page.evaluate(() => {
        return [...document.querySelectorAll('a[href]')].map(el => ({ url: el.href}))
      });

      for (data of result) {
        const newUrl = shouldCrawl(scope, seenList, data.url);
        if (newUrl) {
          seenList.add(newUrl);
          cluster.queue({url: newUrl});
        }
      }
    } catch (e) {
      console.warn("error");
      console.warn(e);
    }
  });

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


async function main() {
  const params = require('yargs').argv;
  console.log(params);

  try {
    await run(params);
    process.exit(0);
  } catch(e) {
    console.log(e);
    process.exit(1);
  }
}

main();



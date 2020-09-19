const puppeteer = require("puppeteer-core");
const { Cluster } = require("puppeteer-cluster");
const child_process = require("child_process");

async function run(params) {
  const args = [
    "--no-first-run",
    "--no-xshm",
    `--proxy-server=http://${process.env.PROXY_HOST}:${process.env.PROXY_PORT}`
  ];

  const puppeteerOptions = {
    headless: true,
    executablePath: "/usr/bin/google-chrome",
    ignoreHTTPSErrors: true,
    args
  };

  const cluster = await Cluster.launch({
    concurrency: Cluster.CONCURRENCY_PAGE,
    maxConcurrency: Number(params.workers) || 1,
    skipDuplicateUrls: true,
    puppeteerOptions,
    puppeteer,
    monitor: true
  });

  let seenList = new Set();
  const url = params._[0];

  let { waitUntil, timeout, scope } = params;
  waitUntil = waitUntil || "load";
  timeout = timeout || 60000;
  scope = scope || new URL(url).origin + "/";

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
        if (seenList.has(data.url)) {
          continue;
        }
        //console.log(`check ${data.url} in ${allowedDomain}`);
        if (scope && data.url.startsWith(scope)) {
          seenList.add(data.url);
          cluster.queue({url: data.url});
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



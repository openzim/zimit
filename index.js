const puppeteer = require("puppeteer-core");

const PAGE_TIMEOUT = 60000;

async function run() {
  const defaultViewport = null;
  const browserURL = `http://localhost:9222`;
  let browser = null;

  console.log("waiting for browser...");

  while (!browser) {
    try {
      browser = await puppeteer.connect({browserURL, defaultViewport});
    } catch (e) {
      //console.log(e);
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }

  console.log("connected!");

  const pages = await browser.pages();
    
  const page = pages.length ? pages[0] : await browser.newPage();

  console.log(process.argv);
  const url = process.argv.length > 2 ? process.argv[2] : "";

  if (!url) {
    throw "No URL specified, exiting";
  }

  await page.goto(url, {"waitUntil": "networkidle0", "timeout": PAGE_TIMEOUT});

  console.log("loaded!");
}


async function main() {
  try {
    await run();
    process.exit(0);
  } catch(e) {
    console.log(e);
    process.exit(1);
  }
}

main();



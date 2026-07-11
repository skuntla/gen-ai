const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const ROOT = __dirname;
const DEFAULT_SCENE = path.join(ROOT, "scenes/phase-01-messages.json");
const TEMPLATE = path.join(ROOT, "templates/analogy-table.html");
const DEFAULT_OUTPUT = path.join(
  ROOT,
  "../../docs/PHASE-NOTES/phase-01/visuals/messages-format.png"
);

async function exportImage(scenePath = DEFAULT_SCENE, outputPath = DEFAULT_OUTPUT) {
  const scene = JSON.parse(fs.readFileSync(scenePath, "utf8"));
  const templateUrl = `file://${TEMPLATE}`;

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });

  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 2
  });

  await page.addInitScript((sceneData) => {
    window.SCENE = sceneData;
  }, scene);

  await page.goto(templateUrl);
  await page.waitForFunction(() => typeof window.renderScene === "function");
  await page.waitForTimeout(600);

  const sceneLocator = page.locator(".scene");
  await sceneLocator.screenshot({ path: outputPath });

  await browser.close();
  console.log(`Exported ${outputPath}`);
}

const sceneArg = process.argv[2];
const outputArg = process.argv[3];

exportImage(
  sceneArg ? path.resolve(ROOT, sceneArg) : DEFAULT_SCENE,
  outputArg ? path.resolve(outputArg) : DEFAULT_OUTPUT
).catch((error) => {
  console.error(error);
  process.exit(1);
});

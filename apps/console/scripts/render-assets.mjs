// Renders the 3D scenes to WebP images for the Flutter app (apps/mobile/assets/images).
// Usage: npx vite --config vite.render.config.ts  (in one terminal), then
//        node scripts/render-assets.mjs <path-to-chrome>
// Needs puppeteer-core (not a project dependency: `npm i --no-save puppeteer-core`).
import puppeteer from 'puppeteer-core';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const out = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../mobile/assets/images');
const chrome = process.argv[2] ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const jobs = [
  { scene: 'hero', w: 1200, h: 800, transparent: false },
  { scene: 'badge', w: 800, h: 800, transparent: true },
  { scene: 'coins', w: 800, h: 800, transparent: true },
  { scene: 'shield', w: 800, h: 800, transparent: true },
];
const browser = await puppeteer.launch({ executablePath: chrome, headless: 'new',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
for (const job of jobs) {
  const page = await browser.newPage();
  await page.setViewport({ width: job.w, height: job.h, deviceScaleFactor: 1 });
  await page.goto(`http://localhost:5199/?scene=${job.scene}`, { waitUntil: 'networkidle0' });
  await page.waitForFunction('window.__ready === true', { timeout: 30000 });
  await page.screenshot({ path: `${out}/${job.scene}.webp`, type: 'webp', quality: 88, omitBackground: job.transparent });
  console.log('rendered', job.scene);
  await page.close();
}
await browser.close();

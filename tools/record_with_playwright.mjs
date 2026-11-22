import { chromium } from 'playwright';
import fs from 'node:fs';

const BASE = process.env.PASOK_CONSOLE || 'http://127.0.0.1:8090';
const DURS = JSON.parse(fs.readFileSync('/tmp/narasi_en_dur.json', 'utf8'));
const QUESTIONS = [
  'What should we order this week?',
  'Why did we order 417 units of SKU0436?',
  'What is the nearest event, and what product that spike',
  'What runs out this week?',
  'What should we transfer between warehouses?',
];

const browser = await chromium.launch({ channel: 'chrome', headless: true });
const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1.2,
  recordVideo: { dir: '/tmp/pwvid3', size: { width: 1920, height: 1200 } } });
const t0 = Date.now();
const page = await ctx.newPage();
await page.goto(BASE + '/', { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
const marks = [];
for (let i = 0; i < QUESTIONS.length; i++) {
  const start = (Date.now() - t0) / 1000;
  const box = page.locator('input[type=text], textarea').first();
  await box.click();
  await page.keyboard.press('Control+A');
  await page.keyboard.press('Backspace');
  await box.type(QUESTIONS[i], { delay: 35 });
  await page.waitForTimeout(250);
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => {
    const a = [...document.querySelectorAll('div.answer')];
    if (!a.length) return false;
    const t = a[a.length - 1].innerText;
    return t.length > 80 && !/Thinking/i.test(t);
  }, { timeout: 60000 });
  await page.waitForTimeout(1200);
  await page.evaluate(() => {
    const a = [...document.querySelectorAll('div.answer')];
    const el = a[a.length - 1];
    if (el) window.scrollBy(0, el.getBoundingClientRect().top - 140);
  });
  const want = Math.max(2.0, (DURS[String(i + 1)] || 10) - ((Date.now() - t0) / 1000 - start) + 1.2);
  await page.waitForTimeout(want * 1000);
  marks.push({ chapter: i + 1, start: +start.toFixed(2), end: +((Date.now() - t0) / 1000).toFixed(2) });
}
await ctx.close();
await browser.close();
fs.writeFileSync('/tmp/pw_marks.json', JSON.stringify({ marks }, null, 2));
console.log(JSON.stringify(marks));

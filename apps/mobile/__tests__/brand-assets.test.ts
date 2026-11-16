import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';

// pngjs is already locked through Expo's image tooling; no runtime dependency is added.
const { PNG } = createRequire(__filename)('pngjs') as { PNG: { sync: { read: (bytes: Buffer) => { width: number; height: number; data: Buffer } } } };
const root = path.join(__dirname, '..');
const approved = fs.readFileSync(path.join(root, 'assets/marina-smart-approved.png'));
const config = JSON.parse(fs.readFileSync(path.join(root, 'app.json'), 'utf8')).expo;

test('all ordinary product icon references retain the exact approved source', () => {
  expect(createHash('sha256').update(approved).digest('hex')).toBe('24678424bf13e4a983f6225fa72c3a73cabc573205832652ee39ed7b27f15356');
  for (const reference of [config.icon, config.ios.icon, config.web.favicon, config.splash.image]) {
    expect(reference).toBe('./assets/marina-smart-approved.png');
  }
  expect(config.android.adaptiveIcon.backgroundColor).toBe('#0B1F2A');
});

test('Android adaptive foreground leaves every visible pixel inside the central 72/108 safe circle', () => {
  expect(config.android.adaptiveIcon.foregroundImage).toBe('./assets/marina-smart-adaptive.png');
  const image = PNG.sync.read(fs.readFileSync(path.join(root, config.android.adaptiveIcon.foregroundImage)));
  expect(image.width).toBe(1024); expect(image.height).toBe(1024);
  const center = (image.width - 1) / 2;
  const safeRadiusSquared = Math.pow(image.width * 72 / 108 / 2, 2);
  let visible = 0;
  let outside = 0;
  for (let y = 0; y < image.height; y++) for (let x = 0; x < image.width; x++) {
    if (image.data[(y * image.width + x) * 4 + 3] === 0) continue;
    visible++;
    if (Math.pow(x - center, 2) + Math.pow(y - center, 2) > safeRadiusSquared) outside++;
  }
  expect(visible).toBeGreaterThan(250000);
  expect(outside).toBe(0);
});

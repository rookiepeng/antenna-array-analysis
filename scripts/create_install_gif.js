/**
 * Creates an animated GIF for the Squirrel Windows installer.
 *
 * This script renders the app icon SVG onto an HTML5 canvas, adds branded text
 * and an animated progress-bar, then encodes the frames into a GIF using the
 * `gif-encoder-2` package.
 *
 * Usage:
 *   node scripts/create_install_gif.js
 *
 * Output:
 *   build/install-spinner.gif
 */

const { createCanvas, loadImage } = require('@napi-rs/canvas');
const GIFEncoder = require('gif-encoder-2');
const fs = require('fs');
const path = require('path');

const WIDTH = 600;
const HEIGHT = 450;
const BG = '#1e1e2e';
const TOTAL_FRAMES = 40; // ~2 s loop at 50 ms/frame
const FRAME_DELAY = 50; // ms

async function main() {
  const outDir = path.join(__dirname, '..', 'build');
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  // Load the app icon
  const iconPath = path.join(__dirname, '..', 'res', 'aaa_icon.png');
  const icon = await loadImage(iconPath);

  const encoder = new GIFEncoder(WIDTH, HEIGHT, 'neuquant', true);
  encoder.setDelay(FRAME_DELAY);
  encoder.setRepeat(0); // infinite loop
  encoder.setQuality(10);
  encoder.start();

  for (let i = 0; i < TOTAL_FRAMES; i++) {
    const canvas = createCanvas(WIDTH, HEIGHT);
    const ctx = canvas.getContext('2d');

    // Background
    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    // Subtle polar grid rings (decorative)
    // ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    // ctx.lineWidth = 1;
    // ctx.setLineDash([4, 4]);
    // for (let r = 60; r <= 200; r += 40) {
    //   ctx.beginPath();
    //   ctx.arc(WIDTH / 2, 175, r, 0, Math.PI * 2);
    //   ctx.stroke();
    // }
    // // Radial lines
    // for (let a = 0; a < Math.PI * 2; a += Math.PI / 4) {
    //   ctx.beginPath();
    //   ctx.moveTo(WIDTH / 2, 175);
    //   ctx.lineTo(WIDTH / 2 + Math.cos(a) * 200, 175 + Math.sin(a) * 200);
    //   ctx.stroke();
    // }
    // ctx.setLineDash([]);

    // Draw icon centered
    const iconSize = 160;
    const iconX = (WIDTH - iconSize) / 2;
    const iconY = 80;
    ctx.drawImage(icon, iconX, iconY, iconSize, iconSize);

    // App name
    ctx.fillStyle = '#ffffff';
    ctx.font = '600 24px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Antenna Array Analysis', WIDTH / 2, 290);

    // Progress bar track
    const barWidth = 300;
    const barHeight = 6;
    const barX = (WIDTH - barWidth) / 2;
    const barY = 330;
    const barRadius = barHeight / 2;

    // Track background
    ctx.fillStyle = 'rgba(255,255,255,0.1)';
    roundRect(ctx, barX, barY, barWidth, barHeight, barRadius);
    ctx.fill();

    // Animated fill — sweeping highlight
    const progress = (i / TOTAL_FRAMES); // 0..1
    const fillWidth = barWidth * progress;

    if (fillWidth > 0) {
      ctx.save();
      // Clip to rounded rect
      ctx.beginPath();
      roundRectPath(ctx, barX, barY, barWidth, barHeight, barRadius);
      ctx.clip();

      // Gradient fill
      const grad = ctx.createLinearGradient(barX, 0, barX + barWidth, 0);
      grad.addColorStop(0, '#4da37a');
      grad.addColorStop(0.5, '#6ec6a0');
      grad.addColorStop(1, '#a8e6cf');
      ctx.fillStyle = grad;
      ctx.fillRect(barX, barY, fillWidth, barHeight);
      ctx.restore();
    }

    // "Installing..." text
    ctx.fillStyle = '#888888';
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Installing...', WIDTH / 2, 365);

    // Version
    // ctx.fillStyle = '#555555';
    // ctx.font = '12px sans-serif';
    // ctx.fillText('v3.0.0', WIDTH / 2, 420);

    encoder.addFrame(ctx);
  }

  encoder.finish();

  const buffer = encoder.out.getData();
  const outPath = path.join(outDir, 'install-spinner.gif');
  fs.writeFileSync(outPath, buffer);
  console.log(`Created ${outPath} (${(buffer.length / 1024).toFixed(1)} KB)`);
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  roundRectPath(ctx, x, y, w, h, r);
  ctx.closePath();
}

function roundRectPath(ctx, x, y, w, h, r) {
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});

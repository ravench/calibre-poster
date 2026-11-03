const { chromium } = require('playwright');
(async () => {
  const [,, html, png, pdf, w, h, scale] = process.argv;
  const b = await chromium.launch(); const p = await b.newPage({deviceScaleFactor: +scale});
  const mm = 96/25.4; await p.setViewportSize({width: Math.round(w*mm), height: Math.round(h*mm)});
  await p.goto('file://' + html); await p.screenshot({path: png});
  if (pdf !== '-') await p.pdf({path: pdf, width: w+'mm', height: h+'mm', printBackground: true});
  await b.close();
})();

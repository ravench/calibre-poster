const { chromium } = require('playwright');
(async () => {
  const [,, html, pdf, w, h] = process.argv;
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + html);
  await p.pdf({path: pdf, width: w+'mm', height: h+'mm', printBackground: true});
  await b.close();
})();

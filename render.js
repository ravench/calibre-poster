// Prints one poster page to PDF: node render.js poster.html poster.pdf WIDTH_MM HEIGHT_MM

// Chromium cannot print a page of exactly the sheet's size: it rounds the page to its print raster and
// fills it only to the last whole pixel, which left a white line of up to a third of a millimetre along
// the right and bottom edges. So the page is printed a millimetre larger than the sheet (paper-coloured,
// see poster.page_html) and an incremental update then gives it the sheet's own size, measured from the
// top left corner where the drawing starts.
function trim(pdf, w, h) {
  const text = pdf.toString('latin1'), count = mark => text.split(mark).length - 1;
  const page = /(\d+) 0 obj\n<<\/Type \/Page\n[\s\S]*?\/MediaBox \[0 0 ([\d.]+) ([\d.]+)\][\s\S]*?endobj\n/.exec(text);
  const trailer = /trailer\n<<([\s\S]*?)>>\nstartxref\n(\d+)\n%%EOF\s*$/.exec(text);
  if (!page || !trailer || count('<</Type /Page\n') !== 1 || count('%%EOF') !== 1)
    throw new Error('render.js: not a one-page PDF as Chromium writes it (or one that was trimmed before)');
  const [right, top] = [+page[2], +page[3]], pt = mm => mm / 25.4 * 72;
  const box = `/MediaBox [0 ${Math.max(0, top - pt(h)).toFixed(3)} ${Math.min(right, pt(w)).toFixed(3)} ${top}]`;
  const object = page[0].replace(/\/MediaBox \[[^\]]*\]/, box);
  const at = pdf.length;
  const xref = `xref\n${page[1]} 1\n${String(at).padStart(10, '0')} 00000 n \n` +
    `trailer\n<<${trailer[1]}\n/Prev ${trailer[2]}>>\nstartxref\n${at + object.length}\n%%EOF\n`;
  return Buffer.concat([pdf, Buffer.from(object + xref, 'latin1')]);
}

async function main([html, pdf, w, h]) {
  const { chromium } = require('playwright');
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + html);
  const printed = await p.pdf({width: (+w + 1) + 'mm', height: (+h + 1) + 'mm', printBackground: true});
  require('fs').writeFileSync(pdf, trim(printed, +w, +h));
  await b.close();
}

if (require.main === module) main(process.argv.slice(2));
module.exports = { trim };

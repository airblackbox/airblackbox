// Run the Asqav governance scanner (github.com/jagmarques/asqav-compliance)
// on many dirs, through its own exported functions.
//
//   node asqav_driver.js <compiled scanner.js> manifest.json out.json
//
// The scanner ships as a GitHub Action; src/scanner.ts is compiled to
// JavaScript first (see README.md). For each directory this records which
// files scanDirectory() selected (it keeps only .py files that import a known
// agent framework) and analyzeFile()'s five verdicts for each of them.
const fs = require('fs');

const [scannerPath, manifestPath, outPath] = process.argv.slice(2);
const { scanDirectory, analyzeFile } = require(scannerPath);

const dirs = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
const out = {};
for (const dir of dirs) {
  try {
    const files = scanDirectory(dir);
    out[dir] = {
      files: files.map((f) => {
        const r = analyzeFile(f.filePath, f.content);
        return {
          file: f.filePath,
          auditTrail: r.auditTrail.pass,
          policyEnforcement: r.policyEnforcement.pass,
          revocation: r.revocation.pass,
          humanOversight: r.humanOversight.pass,
          errorHandling: r.errorHandling.pass,
        };
      }),
    };
  } catch (e) {
    out[dir] = { error: String(e) };
  }
}
fs.writeFileSync(outPath, JSON.stringify(out));

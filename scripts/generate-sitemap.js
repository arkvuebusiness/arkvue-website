/**
 * generate-sitemap.js
 * Scans the repository for .html files and writes a sitemap.xml to the repo root.
 * Run with: npm run generate:sitemap
 */
const fs = require('fs');
const path = require('path');
const glob = require('glob');
const { SitemapStream, streamToPromise } = require('sitemap');

const BASE_URL = 'https://arkvue.co';
const REPO_ROOT = __dirname + '/..';

async function generateSitemap() {
  // Find all .html files in the repo (including subfolders)
  const files = glob.sync('**/*.html', { cwd: REPO_ROOT, ignore: ['node_modules/**', 'dist/**', 'build/**'] });

  const links = files.map(file => {
    // Convert file path to URL path
    let urlPath = file.replace(/\\/g, '/');          // windows -> unix
    urlPath = urlPath.replace(/index\.html$/, '');   // drop index.html
    urlPath = urlPath.replace(/\.html$/, '');        // drop .html
    if (urlPath === '') urlPath = '/';
    else if (!urlPath.startsWith('/')) urlPath = '/' + urlPath;

    return {
      url: urlPath,
      changefreq: 'weekly',
      priority: urlPath === '/' ? 1.0 : 0.8,
      lastmod: new Date().toISOString().split('T')[0],
    };
  });

  const sitemapStream = new SitemapStream({ hostname: BASE_URL });
  const xml = await streamToPromise(sitemapStream).then(data => data.toString());

  // Write each link
  links.forEach(link => sitemapStream.write(link));
  sitemapStream.end();

  const finalXml = await streamToPromise(sitemapStream).then(data => data.toString());

  const outPath = path.join(REPO_ROOT, 'sitemap.xml');
  fs.writeFileSync(outPath, finalXml);
  console.log(`✅ sitemap.xml generated at ${outPath} with ${links.length} URLs`);
}

generateSitemap().catch(err => {
  console.error(err);
  process.exit(1);
});
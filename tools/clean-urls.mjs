// 把 dist 里每个页面额外复制成 <route>/index.html，
// 让静态托管（EdgeOne Pages 等）无需重写规则即可直接访问无 .html 后缀的 URL。
import { copyFile, mkdir, readdir } from 'node:fs/promises';
import path from 'node:path';

const DIST = path.resolve(process.cwd(), 'dist');
const SKIP = new Set(['index.html', '404.html']);

async function walk(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      await walk(file);
      continue;
    }
    if (!entry.name.endsWith('.html') || SKIP.has(entry.name)) continue;
    const dest = path.join(file.slice(0, -'.html'.length), 'index.html');
    await mkdir(path.dirname(dest), { recursive: true });
    await copyFile(file, dest);
  }
}

await walk(DIST);

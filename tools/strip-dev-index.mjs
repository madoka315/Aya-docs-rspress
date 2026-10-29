// 构建后从全文搜索索引中剔除开发者专区页面，避免未解锁用户通过搜索索引直接拿到正文。
// searchHooks 只能过滤运行时结果，静态索引文件仍需在产物里处理。
import { readdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const STATIC_DIR = path.resolve(process.cwd(), 'dist/static');
const DEV_PREFIX = '/kai-fa-zhe-gong-neng';

const files = (await readdir(STATIC_DIR)).filter(
  (name) => name.startsWith('search_index') && name.endsWith('.json'),
);

for (const name of files) {
  const file = path.join(STATIC_DIR, name);
  const data = JSON.parse(await readFile(file, 'utf8'));
  if (!Array.isArray(data)) continue;
  const kept = data.filter(
    (item) => !String(item?.routePath ?? '').startsWith(DEV_PREFIX),
  );
  if (kept.length === data.length) continue;
  await writeFile(file, JSON.stringify(kept), 'utf8');
  console.log(`[strip-dev-index] ${name}: ${data.length} -> ${kept.length}`);
}

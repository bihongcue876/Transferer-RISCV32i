/**
 * 静态检查：UI 模块里 querySelector('#id') / getElementById('id') 引用的 id
 * 必须在同文件的 HTML 模板中出现，避免运行时 null 引用。
 *
 * 运行：node tools/check-dom-ids.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const uiDir = path.join(here, '..', 'src', 'ui');
const files = fs.readdirSync(uiDir).filter((f) => f.endsWith('.js'));

let problems = 0;

for (const file of files) {
  const src = fs.readFileSync(path.join(uiDir, file), 'utf8');

  const defined = new Set();
  for (const m of src.matchAll(/\bid="([^"$]+)"/g)) defined.add(m[1]);
  // 模板里带 ${} 的动态 id：记录其静态前缀
  const dynamicPrefixes = [];
  for (const m of src.matchAll(/\bid="([^"]*?)\$\{/g)) dynamicPrefixes.push(m[1]);

  const referenced = new Set();
  for (const m of src.matchAll(/\$\('#([A-Za-z0-9_-]+)'\)/g)) referenced.add(m[1]);
  for (const m of src.matchAll(/querySelector\('#([A-Za-z0-9_-]+)'\)/g)) referenced.add(m[1]);
  for (const m of src.matchAll(/getElementById\('([A-Za-z0-9_-]+)'\)/g)) referenced.add(m[1]);

  for (const id of referenced) {
    if (defined.has(id)) continue;
    if (dynamicPrefixes.some((p) => p && id.startsWith(p))) continue;
    console.error(`✖ ${file}: 引用了未定义的 id "${id}"`);
    problems += 1;
  }

  const unused = [...defined].filter((id) => !referenced.has(id));
  if (unused.length) {
    console.log(`· ${file}: 定义了但未在脚本中引用的 id → ${unused.join(', ')}`);
  }
}

if (problems) {
  console.error(`\n共 ${problems} 处 id 引用问题`);
  process.exit(1);
}
console.log('\n所有 id 引用均有对应定义');

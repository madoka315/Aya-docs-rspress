import * as path from 'node:path';
import { defineConfig } from '@rspress/core';

export default defineConfig({
  root: path.join(__dirname, 'docs'),
  outDir: 'dist',
  lang: 'zh',
  title: 'Aya 帮助文档',
  description: 'Aya QQ 机器人的功能说明与使用帮助',
  search: {
    searchHooks: path.join(__dirname, 'theme/searchHooks'),
  },
  themeConfig: {
    socialLinks: [
      {
        icon: 'github',
        mode: 'link',
        content: 'https://github.com/madoka315',
      },
    ],
  },
});

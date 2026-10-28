import type { MatchResult } from '@rspress/core/theme';
import { DEV_PREFIX, isDevUnlocked } from './DevMode';

/** 锁定开发者模式时，把开发者分区从全文搜索结果中剔除 */
export function afterSearch(_query: string, result: MatchResult): void {
  if (isDevUnlocked()) return;
  for (let i = result.length - 1; i >= 0; i--) {
    const group = result[i] as { renderType?: string; result?: { link?: string }[] };
    if (group.renderType !== 'default' || !Array.isArray(group.result)) continue;
    group.result = group.result.filter(
      (item) => !String(item.link ?? '').startsWith(DEV_PREFIX),
    );
    if (group.result.length === 0) result.splice(i, 1);
  }
}

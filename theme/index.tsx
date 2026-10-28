import './index.css';
import {
  Layout as OriginalLayout,
  Nav as OriginalNav,
  SidebarList as OriginalSidebarList,
  type NavProps,
} from '@rspress/core/theme-original';
import { usePage, useSidebarDynamic } from '@rspress/core/runtime';
import { useMemo, type ComponentProps } from 'react';
import {
  DevGatePage,
  DevModeToggle,
  DEV_PREFIX,
  isDevPath,
  useDevMode,
} from './DevMode';

export * from '@rspress/core/theme-original';

/** 导航栏最右侧注入开发者模式开关（用 afterNavMenu 槽位，避免被 NavMenu 包进 <ul>；
 *  导航栏有 backdrop-filter 会让内部 fixed 元素定位失效，故弹窗本体走 portal 挂 body） */
export function Nav(props: NavProps) {
  return (
    <OriginalNav
      {...props}
      afterNavMenu={
        <>
          {props.afterNavMenu}
          <DevModeToggle />
        </>
      }
    />
  );
}

/** 侧边栏过滤：锁定时隐藏开发者专区 */
export function Sidebar() {
  const [sidebarData, setSidebarData] = useSidebarDynamic();
  const unlocked = useDevMode();
  const filtered = useMemo(
    () =>
      unlocked
        ? sidebarData
        : sidebarData.filter(
            (item) => !String((item as { link?: string }).link ?? '').startsWith(DEV_PREFIX),
          ),
    [sidebarData, unlocked],
  );
  return (
    <OriginalSidebarList sidebarData={filtered} setSidebarData={setSidebarData} />
  );
}

/** 路由门禁：锁定时访问开发者分区渲染门禁页（SSG 阶段即生效，正文不进静态 HTML） */
export function Layout(props: ComponentProps<typeof OriginalLayout>) {
  const { page } = usePage();
  const devPath = isDevPath(page?.routePath ?? '');
  const unlocked = useDevMode();
  if (devPath && !unlocked) {
    return <DevGatePage />;
  }
  return <OriginalLayout {...props} />;
}

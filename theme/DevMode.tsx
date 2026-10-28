import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

/** 开发者模式：纯前端隐藏（方案 A），密码仅做界面级门槛，不是安全防护 */

const STORAGE_KEY = 'aya-dev-unlocked';
const DEV_EVENT = 'aya-dev-change';
export const DEV_PREFIX = '/kai-fa-zhe-gong-neng';
// SHA-256('794275021Hoshino')，避免明文出现在 bundle 里
const DEV_PASSWORD_HASH =
  '769393e54d53bbecbd54b8c690f2104e34b098f7b4fe334f8f83923db9d55661';

export function isDevPath(pathname: string): boolean {
  return pathname.startsWith(DEV_PREFIX);
}

export function isDevUnlocked(): boolean {
  if (typeof window === 'undefined') return false;
  return window.localStorage.getItem(STORAGE_KEY) === '1';
}

export function setDevUnlocked(unlocked: boolean): void {
  if (unlocked) window.localStorage.setItem(STORAGE_KEY, '1');
  else window.localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event(DEV_EVENT));
}

/** 解锁状态：SSG 与客户端首次渲染恒为 false（与静态 HTML 一致，避免 hydration 抖动），挂载后读 localStorage */
export function useDevMode(): boolean {
  const [unlocked, setUnlocked] = useState(false);
  useEffect(() => {
    const update = () => setUnlocked(isDevUnlocked());
    update();
    window.addEventListener(DEV_EVENT, update);
    window.addEventListener('storage', update);
    return () => {
      window.removeEventListener(DEV_EVENT, update);
      window.removeEventListener('storage', update);
    };
  }, []);
  return unlocked;
}

async function sha256Hex(input: string): Promise<string> {
  const digest = await window.crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(input),
  );
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

function LockIcon({ unlocked }: { unlocked: boolean }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="4" y="11" width="16" height="10" rx="2" />
      {unlocked ? (
        <path d="M8 11V7a4 4 0 0 1 7.9-.9" />
      ) : (
        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      )}
    </svg>
  );
}

/** 密码表单：导航弹窗与门禁页共用 */
function DevPasswordForm({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const submit = async () => {
    if (!password || checking) return;
    if (!window.crypto?.subtle) {
      setError('当前环境不支持密码校验，请使用 localhost 或 HTTPS 访问');
      return;
    }
    setChecking(true);
    try {
      const hex = await sha256Hex(password);
      if (hex === DEV_PASSWORD_HASH) {
        setDevUnlocked(true);
        onSuccess();
      } else {
        setError('密码错误');
        setPassword('');
        inputRef.current?.focus();
      }
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="dev-form">
      <input
        ref={inputRef}
        className="dev-form__input"
        type="password"
        placeholder="输入开发者密码"
        value={password}
        onChange={(e) => {
          setPassword(e.target.value);
          setError('');
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') submit();
        }}
      />
      {error && <div className="dev-form__error">{error}</div>}
      <button
        className="dev-form__submit"
        type="button"
        disabled={checking || !password}
        onClick={submit}
      >
        {checking ? '校验中…' : '解锁'}
      </button>
    </div>
  );
}

/** 导航栏开关按钮（锁定时点击弹密码框，解锁后点击直接关闭开发者模式） */
export function DevModeToggle() {
  const unlocked = useDevMode();
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className="dev-mode-btn"
        title={unlocked ? '关闭开发者模式' : '开发者模式'}
        aria-label={unlocked ? '关闭开发者模式' : '开发者模式'}
        onClick={() => {
          if (unlocked) setDevUnlocked(false);
          else setModalOpen(true);
        }}
      >
        <LockIcon unlocked={unlocked} />
      </button>
      {modalOpen &&
        createPortal(
          <div
            className="dev-modal__overlay"
            onClick={(e) => {
              if (e.target === e.currentTarget) setModalOpen(false);
            }}
          >
            <div className="dev-modal__card" role="dialog" aria-modal="true">
              <h3 className="dev-modal__title">开发者模式</h3>
              <p className="dev-modal__desc">输入密码以显示开发者功能文档。</p>
              <DevPasswordForm onSuccess={() => setModalOpen(false)} />
              <button
                type="button"
                className="dev-modal__cancel"
                onClick={() => setModalOpen(false)}
              >
                取消
              </button>
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}

/** 门禁页：锁定状态下访问 /kai-fa-zhe-gong-neng/* 时替代正文渲染 */
export function DevGatePage() {
  return (
    <div className="dev-gate">
      <div className="dev-gate__card">
        <div className="dev-gate__icon">
          <LockIcon unlocked={false} />
        </div>
        <h1 className="dev-gate__title">开发者模式未解锁</h1>
        <p className="dev-gate__desc">此分区仅对开发者开放，请输入密码查看。</p>
        <DevPasswordForm onSuccess={() => undefined} />
        <a className="dev-gate__back" href="/">
          返回首页
        </a>
      </div>
    </div>
  );
}

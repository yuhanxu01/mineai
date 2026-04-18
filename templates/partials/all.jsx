{% verbatim %}
const {useState, useEffect, useRef, useCallback, useMemo} = React;
const API = '/api';
const F = async (url, o = {}) => {
  const token = localStorage.getItem('mf_token');
  const headers = {'Content-Type':'application/json', ...o.headers};
  if (token) headers['Authorization'] = `Token ${token}`;
  const r = await fetch(url, {headers, ...o});
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  if (r.status === 204 || r.status === 205) return null;
  const text = await r.text();
  if (!text) return null;
  const ct = (r.headers.get('content-type') || '').toLowerCase();
  if (ct.includes('application/json')) {
    try { return JSON.parse(text); } catch (_) { throw new Error('响应 JSON 解析失败'); }
  }
  try { return JSON.parse(text); } catch (_) { return text; }
};
const P = (u, d) => F(u, {method:'POST', body:JSON.stringify(d)});
const U = (u, d) => F(u, {method:'PUT', body:JSON.stringify(d)});
const displayName = (u) => (u?.is_guest ? '访客' : (u?.email || '访客'));

const STATUS_MAP = {outline:'大纲',draft:'草稿',writing:'写作中',review:'审阅',done:'完成'};
const EVT_COLORS = {plot:'var(--gold)',character:'var(--cyan)',relation:'var(--purple)',turning:'var(--red)',foreshadow:'var(--orange)',reveal:'var(--green)',worldbuild:'var(--blue)'};

const hexToRgba = (hex, alpha) => {
  if (!hex) return null;
  const raw = hex.toString().trim().replace('#','');
  let r, g, b;
  if (raw.length === 3) {
    r = parseInt(raw[0] + raw[0], 16);
    g = parseInt(raw[1] + raw[1], 16);
    b = parseInt(raw[2] + raw[2], 16);
  } else if (raw.length === 6) {
    r = parseInt(raw.slice(0,2), 16);
    g = parseInt(raw.slice(2,4), 16);
    b = parseInt(raw.slice(4,6), 16);
  } else {
    return null;
  }
  if ([r,g,b].some(v => Number.isNaN(v))) return null;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

const Svg = ({size=16, stroke=1.8, className='', style={}, children}) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={stroke}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={`icon ${className}`}
    style={style}
    aria-hidden="true"
  >
    {children}
  </svg>
);

const ICONS = {
  home: (p) => (
    <Svg {...p}>
      <path d="M3 11l9-7 9 7" />
      <path d="M5 10v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V10" />
    </Svg>
  ),
  menu: (p) => (
    <Svg {...p}>
      <path d="M4 6h16" />
      <path d="M4 12h16" />
      <path d="M4 18h16" />
    </Svg>
  ),
  logout: (p) => (
    <Svg {...p}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="M16 17l5-5-5-5" />
      <path d="M21 12H9" />
    </Svg>
  ),
  x: (p) => (
    <Svg {...p}>
      <path d="M6 6l12 12" />
      <path d="M18 6l-12 12" />
    </Svg>
  ),
  mail: (p) => (
    <Svg {...p}>
      <rect x="3" y="6" width="18" height="12" rx="2" />
      <path d="M3 7l9 6 9-6" />
    </Svg>
  ),
  link: (p) => (
    <Svg {...p}>
      <path d="M10 13a5 5 0 0 1 0-7l2-2a5 5 0 0 1 7 7l-1 1" />
      <path d="M14 11a5 5 0 0 1 0 7l-2 2a5 5 0 0 1-7-7l1-1" />
    </Svg>
  ),
  globe: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3a14 14 0 0 1 0 18" />
      <path d="M12 3a14 14 0 0 0 0 18" />
    </Svg>
  ),
  bot: (p) => (
    <Svg {...p}>
      <rect x="5" y="7" width="14" height="10" rx="2" />
      <path d="M12 3v4" />
      <circle cx="9" cy="12" r="1" />
      <circle cx="15" cy="12" r="1" />
    </Svg>
  ),
  rocket: (p) => (
    <Svg {...p}>
      <path d="M12 2c4 1 7 4 8 8-2 1-4 2-6 2l-4-4c0-2 1-4 2-6z" />
      <path d="M8 14l-3 3" />
      <path d="M6 18l-2 4 4-2" />
    </Svg>
  ),
  terminal: (p) => (
    <Svg {...p}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M7 10l3 2-3 2" />
      <path d="M12 14h5" />
    </Svg>
  ),
  sun: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v3" />
      <path d="M12 19v3" />
      <path d="M2 12h3" />
      <path d="M19 12h3" />
      <path d="M4.5 4.5l2 2" />
      <path d="M17.5 17.5l2 2" />
      <path d="M4.5 19.5l2-2" />
      <path d="M17.5 6.5l2-2" />
    </Svg>
  ),
  settings: (p) => (
    <Svg {...p}>
      <path d="M4 6h16" />
      <circle cx="9" cy="6" r="2" />
      <path d="M4 12h16" />
      <circle cx="15" cy="12" r="2" />
      <path d="M4 18h16" />
      <circle cx="11" cy="18" r="2" />
    </Svg>
  ),
  user: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c2-4 6-6 8-6s6 2 8 6" />
    </Svg>
  ),
  chat: (p) => (
    <Svg {...p}>
      <path d="M4 6h16a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H9l-5 4v-4H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z" />
    </Svg>
  ),
  'message-square': (p) => (
    <Svg {...p}>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </Svg>
  ),
  clipboard: (p) => (
    <Svg {...p}>
      <rect x="6" y="6" width="12" height="14" rx="2" />
      <path d="M9 4h6a2 2 0 0 1 2 2v1H7V6a2 2 0 0 1 2-2z" />
    </Svg>
  ),
  book: (p) => (
    <Svg {...p}>
      <path d="M4 5h7a3 3 0 0 1 3 3v12a3 3 0 0 0-3-3H4z" />
      <path d="M20 5h-7a3 3 0 0 0-3 3v12a3 3 0 0 1 3-3h7z" />
    </Svg>
  ),
  pen: (p) => (
    <Svg {...p}>
      <path d="M3 21l4-1 11-11-3-3L4 17l-1 4z" />
      <path d="M13 6l3 3" />
    </Svg>
  ),
  layers: (p) => (
    <Svg {...p}>
      <path d="M12 3l9 5-9 5-9-5 9-5z" />
      <path d="M3 12l9 5 9-5" />
      <path d="M3 17l9 5 9-5" />
    </Svg>
  ),
  clock: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v6l4 2" />
    </Svg>
  ),
  map: (p) => (
    <Svg {...p}>
      <path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z" />
      <path d="M9 4v14" />
      <path d="M15 6v14" />
    </Svg>
  ),
  spark: (p) => (
    <Svg {...p}>
      <path d="M12 3l2.2 5.2L20 10l-5.8 1.8L12 17l-2.2-5.2L4 10l5.8-1.8z" />
    </Svg>
  ),
  star: (p) => (
    <Svg {...p}>
      <path d="M12 3l2.5 5 5.5.8-4 3.9.9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-3.9 5.5-.8z" />
    </Svg>
  ),
  bolt: (p) => (
    <Svg {...p}>
      <path d="M13 2L3 14h7l-1 8 11-14h-7l1-6z" />
    </Svg>
  ),
  refresh: (p) => (
    <Svg {...p}>
      <path d="M3 12a9 9 0 0 1 15-6l2 2" />
      <path d="M18 3v5h-5" />
      <path d="M21 12a9 9 0 0 1-15 6l-2-2" />
      <path d="M6 21v-5h5" />
    </Svg>
  ),
  search: (p) => (
    <Svg {...p}>
      <circle cx="11" cy="11" r="6" />
      <path d="M20 20l-3.5-3.5" />
    </Svg>
  ),
  note: (p) => (
    <Svg {...p}>
      <path d="M4 20h4l10-10-4-4L4 16z" />
      <path d="M13 6l4 4" />
    </Svg>
  ),
  eye: (p) => (
    <Svg {...p}>
      <path d="M2 12s4-6 10-6 10 6 10 6-4 6-10 6-10-6-10-6z" />
      <circle cx="12" cy="12" r="3" />
    </Svg>
  ),
  thought: (p) => (
    <Svg {...p}>
      <path d="M4 9a6 6 0 0 1 6-6h4a6 6 0 0 1 0 12H9l-5 4v-4H4a6 6 0 0 1 0-12z" />
      <circle cx="9" cy="11" r="1" />
      <circle cx="12" cy="11" r="1" />
      <circle cx="15" cy="11" r="1" />
    </Svg>
  ),
  target: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="7" />
      <circle cx="12" cy="12" r="3" />
    </Svg>
  ),
  key: (p) => (
    <Svg {...p}>
      <circle cx="7" cy="12" r="3" />
      <path d="M10 12h11" />
      <path d="M18 12v3" />
      <path d="M15 12v3" />
    </Svg>
  ),
  check: (p) => (
    <Svg {...p}>
      <path d="M5 13l4 4L19 7" />
    </Svg>
  ),
  alert: (p) => (
    <Svg {...p}>
      <path d="M12 3l9 16H3z" />
      <path d="M12 9v5" />
      <circle cx="12" cy="17" r="1" />
    </Svg>
  ),
  folder: (p) => (
    <Svg {...p}>
      <path d="M3 7h6l2 2h10a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z" />
    </Svg>
  ),
  file: (p) => (
    <Svg {...p}>
      <path d="M6 3h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
      <path d="M14 3v5h5" />
    </Svg>
  ),
  upload: (p) => (
    <Svg {...p}>
      <path d="M12 16V6" />
      <path d="M8 10l4-4 4 4" />
      <path d="M4 19h16" />
    </Svg>
  ),
  download: (p) => (
    <Svg {...p}>
      <path d="M12 8v8" />
      <path d="M8 12l4 4 4-4" />
      <path d="M4 20h16" />
    </Svg>
  ),
  trash: (p) => (
    <Svg {...p}>
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M6 6l1 14h10l1-14" />
    </Svg>
  ),
  share: (p) => (
    <Svg {...p}>
      <circle cx="18" cy="5" r="2" />
      <circle cx="6" cy="12" r="2" />
      <circle cx="18" cy="19" r="2" />
      <path d="M8 12l8-6" />
      <path d="M8 12l8 6" />
    </Svg>
  ),
  scan: (p) => (
    <Svg {...p}>
      <path d="M4 8V4h4" />
      <path d="M20 8V4h-4" />
      <path d="M4 16v4h4" />
      <path d="M20 16v4h-4" />
      <path d="M7 12h10" />
    </Svg>
  ),
  grid: (p) => (
    <Svg {...p}>
      <rect x="4" y="4" width="7" height="7" rx="1" />
      <rect x="13" y="4" width="7" height="7" rx="1" />
      <rect x="4" y="13" width="7" height="7" rx="1" />
      <rect x="13" y="13" width="7" height="7" rx="1" />
    </Svg>
  ),
  triangle: (p) => (
    <Svg {...p}>
      <path d="M12 5l7 12H5z" />
    </Svg>
  ),
  dots: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="5"  r="1.3" fill="currentColor" stroke="none"/>
      <circle cx="12" cy="12" r="1.3" fill="currentColor" stroke="none"/>
      <circle cx="12" cy="19" r="1.3" fill="currentColor" stroke="none"/>
    </Svg>
  ),
  pin: (p) => (
    <Svg {...p}>
      <path d="M12 2l2 6h5l-4 3 1.5 6L12 14l-4.5 3L9 11 5 8h5z"/>
    </Svg>
  ),
  palette: (p) => (
    <Svg {...p}>
      <circle cx="13.5" cy="6.5" r=".5" fill="currentColor" stroke="none"/>
      <circle cx="17.5" cy="10.5" r=".5" fill="currentColor" stroke="none"/>
      <circle cx="8.5" cy="7.5" r=".5" fill="currentColor" stroke="none"/>
      <circle cx="6.5" cy="12.5" r=".5" fill="currentColor" stroke="none"/>
      <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.9 0 1.6-.7 1.6-1.6 0-.4-.2-.8-.5-1.1-.3-.3-.5-.7-.5-1.1 0-.9.7-1.6 1.6-1.6H17c2.8 0 5-2.2 5-5 0-5.3-4.5-9.5-10-9.5z"/>
    </Svg>
  ),
  adjust: (p) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 18a6 6 0 0 0 0-12v12z" />
    </Svg>
  ),
  'chevron-up': (p) => (
    <Svg {...p}><path d="M18 15l-6-6-6 6" /></Svg>
  ),
  'chevron-down': (p) => (
    <Svg {...p}><path d="M6 9l6 6 6-6" /></Svg>
  ),
  'share-2': (p) => (
    <Svg {...p}>
      <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
      <path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4" />
    </Svg>
  ),
  'cloud-drive': (p) => (
    <Svg {...p}>
      <path d="M18 10a6 6 0 0 0-12 0 4 4 0 0 0 0 8h12a4 4 0 0 0 0-8z" />
      <path d="M12 16v-4" />
      <path d="M9 13l3-3 3 3" />
    </Svg>
  ),
  'cloud-up': (p) => (
    <Svg {...p}>
      <path d="M18 10a6 6 0 0 0-12 0 4 4 0 0 0 0 8h12a4 4 0 0 0 0-8z" />
      <path d="M12 13v5" />
      <path d="M9 16l3-3 3 3" />
    </Svg>
  ),
};

const Icon = ({name, ...props}) => {
  const Comp = ICONS[name] || ICONS.grid;
  return <Comp {...props} />;
};

const APP_ICON_ALIASES = {
  memoryforge: 'layers',
  ocr_studio: 'scan',
  novel_share: 'share',
  novel: 'book',
  memory: 'layers'
};

const APP_ICON_RULES = [
  {re:/ocr|识别|扫描/, icon:'scan'},
  {re:/分享|share/, icon:'share'},
  {re:/小说|写作|创作|章节|大纲|作者/, icon:'pen'},
  {re:/记忆|memory|档案|知识/, icon:'layers'},
  {re:/日志|监控|记录/, icon:'clipboard'},
  {re:/项目|管理|工作台/, icon:'grid'}
];

const pickAppIcon = (app = {}) => {
  const iconKey = (app.icon || '').toString().trim().toLowerCase();
  if (ICONS[iconKey]) return iconKey;
  if (APP_ICON_ALIASES[iconKey]) return APP_ICON_ALIASES[iconKey];
  const slug = (app.slug || '').toString().trim().toLowerCase();
  if (APP_ICON_ALIASES[slug]) return APP_ICON_ALIASES[slug];
  const text = `${app.name || ''} ${app.description || ''}`.toLowerCase();
  for (const rule of APP_ICON_RULES) {
    if (rule.re.test(text)) return rule.icon;
  }
  return 'grid';
};

const appIconStyle = (app = {}) => {
  const color = app.color || '#c9a86c';
  const bg = hexToRgba(color, 0.12);
  const border = hexToRgba(color, 0.35);
  return {
    color,
    background: bg || 'var(--bg3)',
    borderColor: border || 'var(--border)'
  };
};

// ── 通用对话框组件 ──
// 使用方法：
// showDialog({title:'提示',message:'确定要删除吗？',onConfirm:()=>{...}})
const showDialog = (options) => {
  const {
    title = '提示',
    message = '',
    confirmText = '确定',
    cancelText = '取消',
    showCancel = true,
    onConfirm = null,
    onCancel = null,
    type = 'info' // info | warning | danger
  } = options;

  // 创建遮罩层
  const overlay = document.createElement('div');
  overlay.className = 'modal-ov';
  overlay.style.cssText = 'display:flex;z-index:9999';

  // 创建对话框
  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.style.cssText = 'max-width:400px;padding:24px';

  // 图标颜色
  const iconColor = type === 'danger' ? 'var(--red)' : type === 'warning' ? 'var(--orange)' : 'var(--gold)';
  const iconName = type === 'danger' ? 'alert' : type === 'warning' ? 'bolt' : 'check';

  modal.innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <div style="width:40px;height:40px;border-radius:10px;background:${hexToRgba(iconColor, 0.15)};display:flex;align-items:center;justify-content:center;color:${iconColor};flex-shrink:0">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          ${type === 'danger' ? '<path d="M12 3l9 16H3z"/><path d="M12 9v5"/><circle cx="12" cy="17" r="1"/>' :
            type === 'warning' ? '<path d="M13 2L3 14h7l-1 8 11-14h-7l1-6z"/>' :
            '<path d="M5 13l4 4L19 7"/>'}
        </svg>
      </div>
      <h2 style="margin:0;font-size:18px;color:var(--fg)">${title}</h2>
    </div>
    <div style="margin-bottom:24px;line-height:1.7;color:var(--fg2);font-size:14px">${message}</div>
    <div style="display:flex;gap:10px;justify-content:flex-end">
      ${showCancel ? `<button class="btn btn-s btn-sm dialog-cancel" style="padding:8px 16px">${cancelText}</button>` : ''}
      <button class="btn btn-p btn-sm dialog-confirm" style="padding:8px 16px">${confirmText}</button>
    </div>
  `;

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  // 按钮事件
  const confirmBtn = modal.querySelector('.dialog-confirm');
  const cancelBtn = modal.querySelector('.dialog-cancel');

  const close = () => {
    document.body.removeChild(overlay);
  };

  confirmBtn.onclick = () => {
    close();
    if (onConfirm) onConfirm();
  };

  if (cancelBtn) {
    cancelBtn.onclick = () => {
      close();
      if (onCancel) onCancel();
    };
  }

  // 点击遮罩关闭
  overlay.onclick = (e) => {
    if (e.target === overlay) {
      close();
      if (onCancel) onCancel();
    }
  };
};

// 简化的 alert 和 confirm 包装器
const showAlert = (message, title = '提示') => {
  return new Promise((resolve) => {
    showDialog({title, message, showCancel: false, onConfirm: resolve});
  });
};

const showConfirm = (message, title = '确认') => {
  return new Promise((resolve) => {
    showDialog({
      title,
      message,
      confirmText: '确定',
      cancelText: '取消',
      showCancel: true,
      onConfirm: () => resolve(true),
      onCancel: () => resolve(false)
    });
  });
};

// 覆盖全局 alert 以确保所有对话框风格一致
// 注意：window.confirm 因异步特性无法完美覆盖，建议直接使用 await showConfirm()
window.alert = (message) => {
  showAlert(String(message));
};

{% endverbatim %}
{% verbatim %}
// ── User Panel App ────────────────────────────────────────────
function UserPanelApp({user, onLogout, onUpdateUser, siteConfig}) {
  const [tab, setTab] = useState('profile');
  const [apiKey, setApiKey] = useState('');
  const [keyInfo, setKeyInfo] = useState(null);
  const [keyMsg, setKeyMsg] = useState('');
  const [cloudFiles, setCloudFiles] = useState([]);
  const [cloudUsed, setCloudUsed] = useState(0);
  const [cloudQuota, setCloudQuota] = useState(50 * 1024 * 1024);
  const [cloudLoading, setCloudLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const ALLOWED_EXTS_STR = '.pdf,.txt,.md,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.csv,.jpg,.jpeg,.png,.gif,.webp,.bmp,.svg,.py,.js,.ts,.jsx,.tsx,.java,.c,.cpp,.go,.rs,.sh,.bash,.html,.css,.scss,.json,.yaml,.yml,.toml,.xml,.sql,.r,.rb,.php,.swift,.kt';
  const ALLOWED_EXTS = ALLOWED_EXTS_STR.split(',');

  useEffect(() => {
    loadApiKey();
    if (!user?.is_guest) loadCloud();
  }, []);

  const loadApiKey = async () => {
    try { const d = await F(`${API}/auth/user-api-key/`); setKeyInfo(d); } catch {}
  };

  const loadCloud = async () => {
    setCloudLoading(true);
    try {
      const d = await F(`${API}/auth/cloud/`);
      setCloudFiles(d.files || []);
      setCloudUsed(d.used_bytes || 0);
      setCloudQuota(d.quota_bytes || 50 * 1024 * 1024);
    } catch {}
    setCloudLoading(false);
  };

  const saveApiKey = async () => {
    if (!apiKey.trim()) return;
    try {
      const d = await P(`${API}/auth/user-api-key/`, {api_key: apiKey.trim()});
      setKeyInfo(d); setApiKey('');
      setKeyMsg('✓ API 密钥已保存'); setTimeout(() => setKeyMsg(''), 2500);
    } catch (e) { setKeyMsg('保存失败：' + e.message); }
  };

  const deleteApiKey = async () => {
    const confirmed = await showConfirm('确认删除 API 密钥？');
    if (!confirmed) return;
    try {
      await F(`${API}/auth/user-api-key/`, {method: 'DELETE'});
      setKeyInfo({has_key: false, preview: null});
      setKeyMsg('✓ API 密钥已删除'); setTimeout(() => setKeyMsg(''), 2500);
    } catch {}
  };

  const fmtBytes = (b) => {
    if (!b) return '0 B';
    if (b < 1024) return `${b} B`;
    if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
    return `${(b / 1024 / 1024).toFixed(2)} MB`;
  };

  const fmtType = (t) => ({'pdf':'PDF','image':'图片','doc':'文档','code':'代码','other':'其他'}[t] || t);

  const validateFile = (file) => {
    const parts = file.name.split('.');
    const ext = parts.length > 1 ? '.' + parts.pop().toLowerCase() : '';
    if (!ALLOWED_EXTS.includes(ext)) return `不支持 ${ext||'此'} 格式，仅允许 PDF、图片、文档、代码文件`;
    if (file.size > 10 * 1024 * 1024) return '单个文件不能超过 10 MB';
    return null;
  };

  const doUpload = (file) => {
    const err = validateFile(file);
    if (err) { setUploadError(err); return Promise.resolve(); }
    setUploadError(''); setUploading(true); setUploadProgress(0);
    const formData = new FormData();
    formData.append('file', file);
    const token = localStorage.getItem('mf_token');
    return new Promise((resolve) => {
      const xhr = new XMLHttpRequest();
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) setUploadProgress(Math.round(e.loaded / e.total * 100));
      };
      xhr.onload = () => {
        setUploading(false);
        if (xhr.status === 201) {
          const d = JSON.parse(xhr.responseText);
          setCloudFiles(prev => [d, ...prev]);
          setCloudUsed(d.used_bytes || 0);
          setCloudQuota(d.quota_bytes || cloudQuota);
        } else {
          try { setUploadError(JSON.parse(xhr.responseText).error || '上传失败'); } catch { setUploadError('上传失败'); }
        }
        resolve();
      };
      xhr.onerror = () => { setUploading(false); setUploadError('网络错误，上传失败'); resolve(); };
      xhr.open('POST', `${API}/auth/cloud/`);
      if (token) xhr.setRequestHeader('Authorization', `Token ${token}`);
      xhr.send(formData);
    });
  };

  const handleFileSelect = async (files) => {
    for (const f of files) { await doUpload(f); }
  };

  const handleDelete = async (id) => {
    const confirmed = await showConfirm('确认删除此文件？');
    if (!confirmed) return;
    try {
      const d = await F(`${API}/auth/cloud/${id}/`, {method: 'DELETE'});
      setCloudFiles(prev => prev.filter(f => f.id !== id));
      setCloudUsed(d.used_bytes || 0);
    } catch (e) { showAlert('删除失败：' + e.message, '删除失败'); }
  };

  const handleDownload = (id) => {
    const token = localStorage.getItem('mf_token');
    const url = `${API}/auth/cloud/${id}/download/`;
    const a = document.createElement('a');
    a.href = url; document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };

  const usedPct = cloudQuota ? Math.min(100, Math.round(cloudUsed / cloudQuota * 100)) : 0;
  const isGuest = user?.is_guest;

  return (
    <div style={{minHeight:'100vh', background:'var(--bg)', display:'flex', flexDirection:'column'}}>
      <nav style={{height:52, background:'var(--bg2)', borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', padding:'0 24px', gap:14, flexShrink:0}}>
        <button className="btn btn-s btn-sm" onClick={() => window.location.hash='#/'} style={{display:'inline-flex',alignItems:'center',gap:6}}>
          <Icon name="home" size={14} /> 返回首页
        </button>
        <div style={{fontFamily:'var(--serif)', fontSize:17, fontWeight:600, color:'var(--gold2)', marginLeft:4, display:'flex', alignItems:'center', gap:6}}>
          <Icon name="user" size={14}/> 个人中心
        </div>
        <div style={{marginLeft:'auto', display:'flex', alignItems:'center', gap:12}}>
          <span style={{fontSize:12, color:'var(--fg3)', maxWidth:200, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{user?.email}</span>
          {!isGuest && <button className="btn btn-s btn-sm" onClick={onLogout}>退出登录</button>}
        </div>
      </nav>

      <div style={{flex:1, maxWidth:860, margin:'0 auto', width:'100%', padding:'28px 24px'}}>
        {isGuest ? (
          <div className="card" style={{textAlign:'center', padding:48}}>
            <div style={{fontSize:48, marginBottom:12}}>🔒</div>
            <h3 style={{fontFamily:'var(--serif)', color:'var(--fg2)', marginBottom:8}}>请先登录</h3>
            <p style={{color:'var(--fg3)', fontSize:13, marginBottom:20}}>个人中心和云盘功能需要登录才能使用</p>
            <button className="btn btn-p" onClick={() => window.location.hash='#/login'}>立即登录</button>
          </div>
        ) : (
          <>
            <div className="tabs">
              <div className={`tab${tab==='profile'?' on':''}`} onClick={() => setTab('profile')}>
                <span style={{display:'inline-flex',alignItems:'center',gap:5}}><Icon name="user" size={13}/> 基本信息</span>
              </div>
              <div className={`tab${tab==='cloud'?' on':''}`} onClick={() => setTab('cloud')}>
                <span style={{display:'inline-flex',alignItems:'center',gap:5}}><Icon name="cloud-drive" size={13}/> 我的云盘</span>
              </div>
            </div>

            {tab === 'profile' && (
              <div>
                <div className="card" style={{marginBottom:16}}>
                  <h3 style={{fontFamily:'var(--serif)',fontSize:16,marginBottom:14,color:'var(--gold2)'}}>账号信息</h3>
                  <div className="g2">
                    <div>
                      <div style={{fontSize:11,color:'var(--fg3)',marginBottom:3}}>邮箱</div>
                      <div style={{fontSize:14}}>{user?.email}</div>
                    </div>
                    <div>
                      <div style={{fontSize:11,color:'var(--fg3)',marginBottom:3}}>注册日期</div>
                      <div style={{fontSize:14}}>{user?.joined || '—'}</div>
                    </div>
                    <div>
                      <div style={{fontSize:11,color:'var(--fg3)',marginBottom:3}}>账号类型</div>
                      <div style={{fontSize:14}}>
                        {user?.is_staff
                          ? <span style={{color:'var(--gold)'}}>管理员</span>
                          : <span style={{color:'var(--green)'}}>普通用户</span>}
                      </div>
                    </div>
                    <div>
                      <div style={{fontSize:11,color:'var(--fg3)',marginBottom:3}}>云盘空间</div>
                      <div style={{fontSize:14}}>{fmtBytes(cloudUsed)} / {fmtBytes(cloudQuota)}</div>
                    </div>
                  </div>
                </div>

                <div className="card">
                  <h3 style={{fontFamily:'var(--serif)',fontSize:16,marginBottom:4,color:'var(--gold2)'}}>自定义 API 密钥</h3>
                  <p style={{fontSize:12,color:'var(--fg3)',marginBottom:14,lineHeight:1.7}}>
                    配置后，所有 AI 功能将使用您自己的密钥，不消耗平台共享配额。
                  </p>
                  {keyInfo?.has_key ? (
                    <div style={{display:'flex',alignItems:'center',gap:10,flexWrap:'wrap'}}>
                      <div style={{background:'var(--bg3)',border:'1px solid var(--border2)',borderRadius:6,padding:'6px 12px',fontFamily:'var(--mono)',fontSize:13,color:'var(--fg2)',display:'inline-flex',alignItems:'center',gap:6}}>
                        <Icon name="key" size={13}/> {keyInfo.preview}
                      </div>
                      <button className="btn btn-d btn-sm" onClick={deleteApiKey}>删除密钥</button>
                      {keyMsg && <span style={{fontSize:12,color:'var(--green)'}}>{keyMsg}</span>}
                    </div>
                  ) : (
                    <div style={{display:'flex',gap:8,flexWrap:'wrap',alignItems:'flex-end'}}>
                      <div className="fg" style={{flex:1,minWidth:220,marginBottom:0}}>
                        <label>API 密钥</label>
                        <input type="password" placeholder="sk-..." value={apiKey}
                          onChange={e => setApiKey(e.target.value)}
                          onKeyDown={e => e.key==='Enter' && saveApiKey()} />
                      </div>
                      <button className="btn btn-p" onClick={saveApiKey} disabled={!apiKey.trim()}>保存</button>
                      {keyMsg && <span style={{fontSize:12,color:keyMsg.startsWith('✓')?'var(--green)':'var(--red)'}}>{keyMsg}</span>}
                    </div>
                  )}
                </div>
              </div>
            )}

            {tab === 'cloud' && (
              <div>
                {/* Storage bar */}
                <div className="card" style={{marginBottom:14}}>
                  <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
                    <div style={{fontSize:13,fontWeight:500,display:'flex',alignItems:'center',gap:6}}>
                      <Icon name="cloud-drive" size={16}/> 存储空间
                    </div>
                    <div style={{fontSize:12,color:'var(--fg3)',fontFamily:'var(--mono)'}}>
                      {fmtBytes(cloudUsed)} / {fmtBytes(cloudQuota)}
                    </div>
                  </div>
                  <div style={{height:6,background:'var(--bg4)',borderRadius:4,overflow:'hidden'}}>
                    <div style={{
                      height:'100%',borderRadius:4,transition:'width .4s',width:`${usedPct}%`,
                      background: usedPct>90?'var(--red)':usedPct>70?'var(--orange)':'var(--gold)',
                    }}/>
                  </div>
                  <div style={{fontSize:11,color:'var(--fg3)',marginTop:4}}>已用 {usedPct}%，共 50 MB 免费空间</div>
                </div>

                {/* Upload zone */}
                <div
                  onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={e => { e.preventDefault(); setDragOver(false); handleFileSelect(Array.from(e.dataTransfer.files)); }}
                  onClick={() => !uploading && fileInputRef.current?.click()}
                  style={{
                    border:`2px dashed ${dragOver?'var(--gold)':'var(--border2)'}`,
                    borderRadius:10, padding:'28px 20px', textAlign:'center', cursor:'pointer',
                    marginBottom:14, transition:'all .2s',
                    background: dragOver?'rgba(201,168,108,.06)':'var(--bg2)',
                  }}
                >
                  <input ref={fileInputRef} type="file" multiple style={{display:'none'}}
                    accept={ALLOWED_EXTS_STR}
                    onChange={e => { handleFileSelect(Array.from(e.target.files)); e.target.value=''; }}
                  />
                  <Icon name="cloud-up" size={32} style={{color:'var(--gold)',opacity:.7,display:'block',margin:'0 auto 10px'}}/>
                  {uploading ? (
                    <>
                      <div style={{fontSize:13,color:'var(--fg2)',marginBottom:8}}>上传中 {uploadProgress}%</div>
                      <div style={{height:4,background:'var(--bg4)',borderRadius:2,maxWidth:200,margin:'0 auto'}}>
                        <div style={{height:'100%',borderRadius:2,background:'var(--gold)',width:`${uploadProgress}%`,transition:'width .2s'}}/>
                      </div>
                    </>
                  ) : (
                    <>
                      <div style={{fontSize:13,color:'var(--fg2)',marginBottom:4}}>
                        拖拽文件到此处，或 <span style={{color:'var(--gold)'}}>点击选择文件</span>
                      </div>
                      <div style={{fontSize:11,color:'var(--fg3)'}}>
                        支持 PDF · 图片 · 文档 · 代码 · 单个文件最大 10 MB
                      </div>
                    </>
                  )}
                  {uploadError && (
                    <div style={{marginTop:10,fontSize:12,color:'var(--red)',background:'rgba(196,90,90,.08)',borderRadius:6,padding:'6px 12px'}}>
                      ⚠ {uploadError}
                    </div>
                  )}
                </div>

                {/* File list */}
                {cloudLoading ? (
                  <div className="load">加载中...</div>
                ) : cloudFiles.length === 0 ? (
                  <div className="empty"><h3>云盘为空</h3><p>上传您的第一个文件吧</p></div>
                ) : cloudFiles.map(f => (
                  <div key={f.id} style={{
                    display:'flex',alignItems:'center',gap:12,padding:'10px 14px',
                    borderRadius:8,border:'1px solid var(--border)',marginBottom:6,
                    background:'var(--bg2)',transition:'border-color .12s',
                  }}>
                    <div style={{width:36,height:36,borderRadius:8,display:'flex',alignItems:'center',justifyContent:'center',fontSize:18,background:'var(--bg3)',border:'1px solid var(--border)',flexShrink:0}}>
                      {f.file_type==='pdf'?'📄':f.file_type==='image'?'🖼️':f.file_type==='code'?'💻':'📝'}
                    </div>
                    <div style={{flex:1,minWidth:0}}>
                      <div style={{fontSize:13,fontWeight:500,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{f.name}</div>
                      <div style={{fontSize:11,color:'var(--fg3)',marginTop:2}}>
                        {fmtType(f.file_type)} · {fmtBytes(f.size)} · {f.uploaded_at}
                      </div>
                    </div>
                    <div style={{display:'flex',gap:6,flexShrink:0}}>
                      <button className="btn btn-s btn-sm" onClick={() => handleDownload(f.id)}
                        style={{display:'inline-flex',alignItems:'center',gap:4}}>
                        <Icon name="download" size={12}/> 下载
                      </button>
                      <button className="btn btn-sm" onClick={() => handleDelete(f.id)}
                        style={{background:'rgba(196,90,90,.12)',color:'var(--red)',border:'1px solid rgba(196,90,90,.2)',display:'inline-flex',alignItems:'center',gap:4}}>
                        <Icon name="trash" size={12}/> 删除
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function MemoryForgeApp({user, onLogout, onUpdateUser}) {

  const [v, setV] = useState('home');
  const [ps, setPs] = useState([]);
  const [ap, setAp] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [sbOpen, setSbOpen] = useState(false);
  const goTo = (view) => { setV(view); setSbOpen(false); };

  useEffect(() => { initApp(); }, []);

  // Auto-refresh stats every 60s
  useEffect(() => {
    const id = setInterval(refreshUser, 60000);
    return () => clearInterval(id);
  }, []);

  const initApp = () => {
    F(`${API}/core/config/`).then(setCfg).catch(() => setCfg({configured:false}));
    F(`${API}/novel/projects/`).then(setPs).catch(()=>{});
  };

  const refreshUser = () => {
    const token = localStorage.getItem('mf_token');
    F(`${API}/auth/me/`).then(me => { if (me.authenticated) onUpdateUser({...me, token}); }).catch(()=>{});
  };

  const loadPs = () => F(`${API}/novel/projects/`).then(setPs).catch(()=>{});
  const selP = async (p) => { const f = await F(`${API}/novel/project/${p.id}/`); setAp(f); setV('project'); };
  const refP = () => ap && F(`${API}/novel/project/${ap.id}/`).then(setAp);

  if (cfg && !cfg.configured) return (
    <>
      <div style={{position:'fixed',top:14,left:14,zIndex:999}}>
        <button className="btn btn-s btn-sm" onClick={() => { window.location.hash = '#/'; }}>← 返回 MineAI</button>
      </div>
      <Setup
        onDone={() => { F(`${API}/core/config/`).then(setCfg); }}
        platformConfigured={cfg.platform_configured}
        platformAllowed={cfg.platform_allowed}
      />
    </>
  );

  const u = user?.usage || {};

  return (
    <div className="app">
      <div className={`sb-ov${sbOpen?' open':''}`} onClick={()=>setSbOpen(false)}/>
      <div className={`sb${sbOpen?' open':''}`}>
        <div className="sb-back" onClick={() => { window.location.hash = '#/'; }}>← 返回 MineAI</div>
        <div className="sb-hd"><h1>记忆熔炉</h1><p>无限记忆·长篇创作</p></div>
        <div className="sb-nav">
          <div className="ns"><div className="ns-t">导航</div>
            <div className={`ni ${v==='home'?'on':''}`} onClick={()=>goTo('home')}><i><Icon name="home" size={14} /></i>工作台</div>
          </div>
          {ap && <div className="ns"><div className="ns-t">{ap.title}</div>
            <div className={`ni ${v==='project'?'on':''}`} onClick={()=>goTo('project')}><i><Icon name="book" size={14} /></i>章节管理</div>
            <div className={`ni ${v==='write'?'on':''}`} onClick={()=>goTo('write')}><i><Icon name="pen" size={14} /></i>写作工坊</div>
            <div className={`ni ${v==='pyramid'?'on':''}`} onClick={()=>goTo('pyramid')}><i><Icon name="layers" size={14} /></i>记忆金字塔</div>
            <div className={`ni ${v==='timeline'?'on':''}`} onClick={()=>goTo('timeline')}><i><Icon name="clock" size={14} /></i>时间线</div>
            <div className={`ni ${v==='chars'?'on':''}`} onClick={()=>goTo('chars')}><i><Icon name="user" size={14} /></i>角色图鉴</div>
            <div className={`ni ${v==='chat'?'on':''}`} onClick={()=>goTo('chat')}><i><Icon name="chat" size={14} /></i>剧情顾问</div>
            <div className={`ni ${v==='logs'?'on':''}`} onClick={()=>goTo('logs')}><i><Icon name="clipboard" size={14} /></i>运行日志</div>
          </div>}
          <div style={{marginTop:'auto'}}>
            <div style={{padding:'10px 8px 0',borderTop:'1px solid var(--border)'}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'0 4px',marginBottom:6}}>
                <span style={{fontSize:10,color:'var(--fg3)',letterSpacing:1}}>TOKEN 用量</span>
                <button onClick={refreshUser} style={{background:'none',color:'var(--fg3)',fontSize:9,padding:'1px 5px',border:'1px solid var(--border)',borderRadius:3,cursor:'pointer'}}>刷新</button>
              </div>
              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:4,padding:'0 4px',marginBottom:8}}>
                <div style={{background:'var(--bg3)',borderRadius:4,padding:'5px 6px',textAlign:'center'}}>
                  <div style={{fontFamily:'var(--mono)',fontSize:16,color:'var(--gold2)',fontWeight:500}}>{(u.prompt_count||0).toLocaleString()}</div>
                  <div style={{fontSize:9,color:'var(--fg3)',marginTop:1,letterSpacing:.5}}>提交次数</div>
                </div>
                <div style={{background:'var(--bg3)',borderRadius:4,padding:'5px 6px',textAlign:'center'}}>
                  <div style={{fontFamily:'var(--mono)',fontSize:16,color:'var(--cyan)',fontWeight:500}}>{((u.total_tokens||0)/1000).toFixed(1)}K</div>
                  <div style={{fontSize:9,color:'var(--fg3)',marginTop:1,letterSpacing:.5}}>总Token</div>
                </div>
                <div style={{background:'var(--bg3)',borderRadius:4,padding:'4px 6px',textAlign:'center'}}>
                  <div style={{fontFamily:'var(--mono)',fontSize:13,color:'var(--blue)',fontWeight:500}}>{((u.input_tokens||0)/1000).toFixed(1)}K</div>
                  <div style={{fontSize:9,color:'var(--fg3)',marginTop:1,letterSpacing:.5}}>输入</div>
                </div>
                <div style={{background:'var(--bg3)',borderRadius:4,padding:'4px 6px',textAlign:'center'}}>
                  <div style={{fontFamily:'var(--mono)',fontSize:13,color:'var(--green)',fontWeight:500}}>{((u.output_tokens||0)/1000).toFixed(1)}K</div>
                  <div style={{fontSize:9,color:'var(--fg3)',marginTop:1,letterSpacing:.5}}>输出</div>
                </div>
              </div>
            </div>
            <div style={{padding:'6px 12px 10px'}}>
              <div style={{fontSize:11,color:'var(--fg3)',marginBottom:6,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',padding:'0 2px',display:'flex',alignItems:'center',gap:6}} title={displayName(user)}>
                <Icon name="user" size={14} />
                <span style={{overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{displayName(user)}</span>
              </div>
              <div style={{display:'flex',gap:6}}>
                {user ? (
                  <>
                    <div className={`ni ${v==='settings'?'on':''}`} style={{flex:1,padding:'5px 8px',margin:0}} onClick={()=>goTo('settings')}><i><Icon name="settings" size={14} /></i>设置</div>
                    <button onClick={onLogout} style={{padding:'5px 11px',borderRadius:'var(--r)',background:'var(--bg4)',color:'var(--fg3)',border:'1px solid var(--border2)',fontSize:13,cursor:'pointer',display:'inline-flex',alignItems:'center',justifyContent:'center'}} title="退出登录"><Icon name="logout" size={14} /></button>
                  </>
                ) : (
                  <button onClick={() => window.location.hash = '#/login'} style={{flex:1,padding:'5px 8px',borderRadius:'var(--r)',background:'var(--bg4)',color:'var(--fg3)',border:'1px solid var(--border2)',fontSize:13,cursor:'pointer'}} title="登录/注册">前往登录 / 注册</button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="main">
        <div className="top">
          <button className="menu-btn" onClick={()=>setSbOpen(o=>!o)}><Icon name="menu" size={18} /></button>
          <span className="top-t">
            {v==='home'&&'工作台'}{v==='project'&&ap?.title}{v==='write'&&'写作工坊'}{v==='pyramid'&&'记忆金字塔'}
            {v==='timeline'&&'故事时间线'}{v==='chars'&&'角色图鉴'}{v==='chat'&&'剧情顾问'}{v==='logs'&&'运行日志'}{v==='settings'&&'系统设置'}
          </span>
          {ap && <span className="top-b">{ap.genre||'小说'}</span>}
        </div>
        <div className="ct">
          {v==='home'&&<Home ps={ps} onSel={selP} onRef={loadPs} user={user} />}
          {v==='project'&&ap&&<Proj p={ap} onRef={refP} goWrite={()=>setV('write')} user={user} />}
          {v==='write'&&ap&&<Write p={ap} onRef={refP} onUsage={refreshUser} user={user} />}
          {v==='pyramid'&&ap&&<Pyramid pid={ap.id} user={user} />}
          {v==='timeline'&&ap&&<Timeline pid={ap.id} user={user} />}
          {v==='chars'&&ap&&<Chars pid={ap.id} user={user} />}
          {v==='chat'&&ap&&<Chat pid={ap.id} onUsage={refreshUser} user={user} />}
          {v==='logs'&&<Logs pid={ap?.id} user={user} />}
          {v==='settings'&&<Settings cfg={cfg} onSave={()=>F(`${API}/core/config/`).then(setCfg)} />}
        </div>
      </div>
      <FloatingChat user={user} onUsage={refreshUser} />
    </div>
  );
}

function FloatingChat({user, onUsage}) {
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [pos, setPos] = useState(null);
  const [size, setSize] = useState({w:340, h:480});
  const [msgs, setMsgs] = useState([]);
  const [inp, setInp] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');
  const endRef = useRef(null);
  const dragRef = useRef({});

  useEffect(() => { endRef.current?.scrollIntoView({behavior:'smooth'}); }, [msgs, streamText]);

  const getDefaultPos = () => ({
    x: Math.max(0, window.innerWidth - size.w - 24),
    y: Math.max(0, window.innerHeight - size.h - 24),
  });

  const startDrag = (e) => {
    if (e.target.closest('button')) return;
    e.preventDefault();
    const cur = pos || getDefaultPos();
    dragRef.current = {startX: e.clientX - cur.x, startY: e.clientY - cur.y};
    const onMove = (e) => setPos({x: e.clientX - dragRef.current.startX, y: e.clientY - dragRef.current.startY});
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  const startResize = (e) => {
    e.preventDefault(); e.stopPropagation();
    const startX=e.clientX, startY=e.clientY, startW=size.w, startH=size.h;
    const onMove = (e) => setSize({w:Math.max(280,startW+(e.clientX-startX)), h:Math.max(320,startH+(e.clientY-startY))});
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  const send = async () => {
    if (!user) { showAlert('请先登录后使用对话功能', '提示'); return; }
    if (!inp.trim() || streaming) return;
    const m = inp.trim(); setInp('');
    const history = msgs.map(msg => ({role: msg.role, content: msg.content}));
    setMsgs(p => [...p, {role:'user', content:m}]);
    setStreaming(true); setStreamText('');
    const token = localStorage.getItem('mf_token');
    const hdrs = {'Content-Type':'application/json'};
    if(token) hdrs['Authorization'] = `Token ${token}`;
    try {
      const resp = await fetch(`${API}/core/chat-stream/`, {method:'POST', headers:hdrs, body:JSON.stringify({message:m, history})});
      if(!resp.ok) throw new Error(await resp.text());
      const reader = resp.body.getReader(); const dec = new TextDecoder();
      let buf=''; let full='';
      while(true) {
        const {done, value} = await reader.read(); if(done) break;
        buf += dec.decode(value,{stream:true});
        const lns = buf.split('\n'); buf = lns.pop();
        for(const ln of lns) {
          if(!ln.startsWith('data: ')) continue;
          let ev; try{ ev=JSON.parse(ln.slice(6)); }catch{ continue; }
          if(ev.type==='chunk'){ full+=ev.text; setStreamText(full); }
          else if(ev.type==='done'){ setMsgs(p=>[...p,{role:'assistant',content:full}]); setStreamText(''); onUsage&&onUsage(); }
          else if(ev.type==='error'){ throw new Error(ev.message); }
        }
      }
    } catch(e) {
      setMsgs(p=>[...p,{role:'assistant',content:`错误: ${e.message}`}]); setStreamText('');
    }
    setStreaming(false);
  };

  const computedPos = pos || getDefaultPos();
  const winStyle = {
    position:'fixed', left:computedPos.x, top:computedPos.y,
    width:size.w, height:minimized?44:size.h,
    zIndex:9000, background:'var(--bg2)', border:'1px solid var(--border2)',
    borderRadius:10, display:'flex', flexDirection:'column',
    overflow:'hidden', boxShadow:'0 8px 32px rgba(0,0,0,.55)',
  };

  if (!open) return (
    <button className="fc-bubble" onClick={()=>setOpen(true)} title="AI 对话">
      <Icon name="chat" size={20}/>
    </button>
  );

  return (
    <div className="fc-window" style={winStyle}>
      <div className="fc-hd" onMouseDown={startDrag}>
        <span className="fc-hd-title"><Icon name="chat" size={13}/> AI 对话</span>
        <div className="fc-hd-btns">
          <button className="fc-hd-btn" onClick={()=>setMsgs([])} title="清空对话">
            <Icon name="refresh" size={11}/>
          </button>
          <button className="fc-hd-btn" onClick={()=>setMinimized(m=>!m)} title={minimized?'展开':'最小化'}>
            {minimized ? '□' : '—'}
          </button>
          <button className="fc-hd-btn" onClick={()=>{setOpen(false);setMinimized(false);}} title="关闭">×</button>
        </div>
      </div>
      {!minimized && <>
        <div className="fc-msgs">
          {msgs.length===0 && (
            <div className="fc-empty">
              <div className="fc-empty-icon"><Icon name="chat" size={18} /></div>
              <div style={{fontWeight:500,marginBottom:4}}>AI 智能助手</div>
              <div style={{color:'var(--fg3)',lineHeight:1.6}}>随时为你解答任何问题<br/>支持多轮对话，Enter 发送</div>
            </div>
          )}
          {msgs.map((m,i)=>(
            <div key={i} className={`fc-msg ${m.role}`}>
              <div className="fc-bbl">{m.content}</div>
            </div>
          ))}
          {streamText && (
            <div className="fc-msg assistant">
              <div className="fc-bbl">{streamText}<span style={{opacity:.7,animation:'blink 1s infinite'}}>▌</span></div>
            </div>
          )}
          {streaming && !streamText && <div className="fc-thinking">思考中...</div>}
          <div ref={endRef}/>
        </div>
        <div className="fc-input-row">
          <textarea
            value={inp}
            onChange={e=>setInp(e.target.value)}
            onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}}}
            placeholder="输入消息… Enter 发送，Shift+Enter 换行"
            rows={1}
          />
          <button className="btn btn-p btn-sm" onClick={send} disabled={streaming} style={{flexShrink:0,alignSelf:'flex-end'}}>发送</button>
        </div>
        <div className="fc-resize" onMouseDown={startResize}/>
      </>}
    </div>
  );
}

function AuthScreen({onAuth, siteConfig}) {
  const [tab, setTab] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [codeSent, setCodeSent] = useState(false);
  const [error, setError] = useState('');
  const [forgotSent, setForgotSent] = useState(false);
  const timerRef = useRef(null);

  const fmtCD = (s) => `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;

  const startCountdown = (seconds) => {
    clearInterval(timerRef.current);
    setCountdown(seconds);
    timerRef.current = setInterval(() => {
      setCountdown(n => { if (n <= 1) { clearInterval(timerRef.current); return 0; } return n - 1; });
    }, 1000);
  };

  const parseErr = (e) => {
    try {
      const msg = e.message || '';
      // Remove status code prefix (e.g., "500: " or "403: ")
      const jsonStr = msg.replace(/^\d+:\s*/, '').trim();
      return JSON.parse(jsonStr);
    } catch (err) {
      console.error('Failed to parse error:', e.message, e);
      return {};
    }
  };

  const sendCode = async () => {
    if (!email) return setError('请先输入邮箱');
    setError(''); setSending(true);
    try {
      const res = await P(`${API}/auth/send-code/`, {email});
      setCodeSent(true);
      startCountdown(res.cooldown_seconds || 300);
    } catch(e) {
      const msg = parseErr(e);
      console.error('Send code error:', e, 'Parsed:', msg);
      // Show the actual error from backend, or a more descriptive fallback
      if (msg.error) {
        setError(msg.error);
      } else {
        // If we can't parse the error, show the raw message for debugging
        setError(`发送失败: ${e.message?.substring(0, 100) || '未知错误'}`);
      }
      if (msg.remaining_seconds) startCountdown(msg.remaining_seconds);
    }
    setSending(false);
  };

  const submit = async () => {
    if (!email || !password) return;
    if (tab === 'register' && !code) return setError('请输入验证码');
    setError(''); setLoading(true);
    try {
      const url = tab === 'login' ? `${API}/auth/login/` : `${API}/auth/register/`;
      const body = tab === 'login' ? {email, password} : {email, password, code};
      const res = await P(url, body);
      localStorage.setItem('mf_token', res.token);
      onAuth(res);
    } catch(e) {
      const msg = parseErr(e);
      setError(msg.error || '网络错误，请重试');
    }
    setLoading(false);
  };

  const submitForgot = async () => {
    if (!email) return setError('请输入邮箱');
    setError(''); setLoading(true);
    try {
      await P(`${API}/auth/forgot-password/`, {email});
      setForgotSent(true);
    } catch(e) {
      const msg = parseErr(e);
      setError(msg.error || '发送失败，请重试');
    }
    setLoading(false);
  };

  const switchTab = (t) => {
    setTab(t); setError(''); setCode(''); setCodeSent(false);
    setForgotSent(false); setCountdown(0); clearInterval(timerRef.current);
  };

  return (
    <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'100vh',background:'var(--bg)'}}>
      <div style={{textAlign:'center',maxWidth:400,width:'100%',padding:'0 24px'}}>
        <h1 style={{fontFamily:'var(--serif)',fontSize:34,color:'var(--gold2)',marginBottom:4,letterSpacing:2,display:'inline-flex',alignItems:'center',gap:10}}>
          <img src="/static/favicon-mineai.svg" alt="MineAI" style={{width:36,height:36,display:'inline-block'}} />
          {siteConfig?.site_title || 'MineAI'}
        </h1>
        <p style={{color:'var(--fg3)',marginBottom:28,fontSize:12,letterSpacing:2}}>{siteConfig?.site_subtitle || '多功能应用集成工作台'}</p>
        <div style={{background:'var(--bg2)',border:'1px solid var(--border)',borderRadius:12,padding:28}}>
          {tab !== 'forgot' && (
            <div className="tabs" style={{marginBottom:20}}>
              <div className={`tab ${tab==='login'?'on':''}`} onClick={()=>switchTab('login')}>登录</div>
              <div className={`tab ${tab==='register'?'on':''}`} onClick={()=>switchTab('register')}>注册</div>
            </div>
          )}

          {tab === 'forgot' ? (
            forgotSent ? (
              <div style={{textAlign:'center',padding:'12px 0'}}>
                <div style={{marginBottom:12}}><Icon name="mail" size={36} /></div>
                <div style={{color:'var(--fg)',fontSize:14,marginBottom:8}}>重置链接已发送</div>
                <div style={{color:'var(--fg3)',fontSize:12,marginBottom:20}}>请检查 <b>{email}</b> 的收件箱，链接 30 分钟内有效。</div>
                <button className="btn btn-s" onClick={()=>switchTab('login')} style={{width:'100%'}}>返回登录</button>
              </div>
            ) : (
              <>
                <div style={{textAlign:'left',marginBottom:16}}>
                  <div style={{color:'var(--fg)',fontSize:14,fontWeight:600,marginBottom:4}}>忘记密码</div>
                  <div style={{color:'var(--fg3)',fontSize:12}}>输入注册邮箱，我们将发送重置链接。</div>
                </div>
                <div className="fg" style={{textAlign:'left'}}>
                  <label>邮箱</label>
                  <input type="email" value={email} onChange={e=>setEmail(e.target.value)}
                    onKeyDown={e=>e.key==='Enter'&&submitForgot()}
                    placeholder="your@email.com" style={{width:'100%'}}/>
                </div>
                {error && <div style={{color:'var(--red)',fontSize:12,marginBottom:12,textAlign:'left',padding:'6px 10px',background:'rgba(196,90,90,.1)',borderRadius:'var(--r)'}}>{error}</div>}
                <button className="btn btn-p" onClick={submitForgot} disabled={loading||!email} style={{width:'100%',padding:'10px',fontSize:14,marginBottom:10}}>
                  {loading?'发送中...':'发送重置链接'}
                </button>
                <button className="btn btn-s" onClick={()=>switchTab('login')} style={{width:'100%',fontSize:13}}>返回登录</button>
              </>
            )
          ) : (
            <>
              <div className="fg" style={{textAlign:'left'}}>
                <label>邮箱</label>
                {tab==='register' ? (
                  <div style={{display:'flex',gap:8}}>
                    <input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="your@email.com" style={{flex:1,minWidth:0}}/>
                    <button className="btn btn-s" onClick={sendCode} disabled={sending||countdown>0||!email}
                      style={{flexShrink:0,fontSize:12,padding:'7px 10px',whiteSpace:'nowrap'}}>
                      {sending?'发送中...':countdown>0?fmtCD(countdown):codeSent?'重新发送':'获取验证码'}
                    </button>
                  </div>
                ) : (
                  <input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="your@email.com" style={{width:'100%'}}/>
                )}
              </div>

              {tab==='register' && (
                <div className="fg" style={{textAlign:'left'}}>
                  <label>验证码
                    {codeSent && (
                      <span style={{color:'var(--green)',fontSize:10,marginLeft:8,fontWeight:'normal'}}>
                        <span className="with-ic">
                          <Icon name="check" size={12} />
                          已发送至邮箱
                        </span>
                      </span>
                    )}
                  </label>
                  <input value={code} onChange={e=>setCode(e.target.value.replace(/\D/g,'').slice(0,6))}
                    placeholder="6 位数字验证码" maxLength={6}
                    style={{width:'100%',fontFamily:'var(--mono)',letterSpacing:6,fontSize:18,textAlign:'center'}}/>
                </div>
              )}

              <div className="fg" style={{textAlign:'left'}}>
                <label>密码{tab==='register'?' (至少 6 位)':''}</label>
                <div style={{position:'relative',display:'flex',alignItems:'center'}}>
                  <input type={showPwd?'text':'password'} value={password} onChange={e=>setPassword(e.target.value)}
                    onKeyDown={e=>e.key==='Enter'&&submit()} placeholder="••••••" style={{width:'100%',paddingRight:36}}/>
                  <button type="button" onClick={()=>setShowPwd(v=>!v)}
                    style={{position:'absolute',right:8,background:'none',border:'none',cursor:'pointer',padding:0,color:'var(--muted)',lineHeight:1,fontSize:16}}
                    title={showPwd?'隐藏密码':'显示密码'}>
                    {showPwd
                      ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                      : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                    }
                  </button>
                </div>
              </div>

              {error && <div style={{color:'var(--red)',fontSize:12,marginBottom:12,textAlign:'left',padding:'6px 10px',background:'rgba(196,90,90,.1)',borderRadius:'var(--r)'}}>{error}</div>}

              <button className="btn btn-p" onClick={submit}
                disabled={loading||!email||!password||(tab==='register'&&!code)}
                style={{width:'100%',padding:'10px',fontSize:14}}>
                {loading?(tab==='login'?'登录中...':'注册中...'):(tab==='login'?'登录':'注册账号')}
              </button>

              {tab==='login' && (
                <div style={{marginTop:12,textAlign:'center'}}>
                  <button onClick={()=>switchTab('forgot')}
                    style={{background:'none',border:'none',cursor:'pointer',color:'var(--fg3)',fontSize:12,padding:0}}
                    onMouseOver={e=>e.target.style.color='var(--gold)'}
                    onMouseOut={e=>e.target.style.color='var(--fg3)'}>
                    忘记密码？
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ResetPasswordScreen({siteConfig}) {
  const token = new URLSearchParams(window.location.hash.split('?')[1] || '').get('token') || '';
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  const submit = async () => {
    if (!password) return;
    if (password.length < 6) return setError('密码至少 6 位');
    setError(''); setLoading(true);
    try {
      await P(`${API}/auth/reset-password/`, {token, password});
      setDone(true);
    } catch(e) {
      try {
        const msg = JSON.parse((e.message || '').replace(/^\d+:\s*/, '').trim());
        setError(msg.error || '重置失败，请重试');
      } catch { setError('重置失败，请重试'); }
    }
    setLoading(false);
  };

  return (
    <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'100vh',background:'var(--bg)'}}>
      <div style={{textAlign:'center',maxWidth:400,width:'100%',padding:'0 24px'}}>
        <h1 style={{fontFamily:'var(--serif)',fontSize:34,color:'var(--gold2)',marginBottom:4,letterSpacing:2,display:'inline-flex',alignItems:'center',gap:10}}>
          <img src="/static/favicon-mineai.svg" alt="MineAI" style={{width:36,height:36,display:'inline-block'}} />
          {siteConfig?.site_title || 'MineAI'}
        </h1>
        <p style={{color:'var(--fg3)',marginBottom:28,fontSize:12,letterSpacing:2}}>重置密码</p>
        <div style={{background:'var(--bg2)',border:'1px solid var(--border)',borderRadius:12,padding:28}}>
          {!token ? (
            <div style={{color:'var(--red)',fontSize:13}}>链接无效，请重新申请重置密码。</div>
          ) : done ? (
            <div style={{textAlign:'center',padding:'8px 0'}}>
              <div style={{marginBottom:12}}><Icon name="check" size={36} /></div>
              <div style={{color:'var(--fg)',fontSize:14,marginBottom:8}}>密码已重置</div>
              <div style={{color:'var(--fg3)',fontSize:12,marginBottom:20}}>请使用新密码登录。</div>
              <button className="btn btn-p" onClick={()=>{window.location.hash='#/login';}} style={{width:'100%'}}>前往登录</button>
            </div>
          ) : (
            <>
              <div style={{textAlign:'left',marginBottom:16}}>
                <div style={{color:'var(--fg)',fontSize:14,fontWeight:600,marginBottom:4}}>设置新密码</div>
                <div style={{color:'var(--fg3)',fontSize:12}}>请输入您的新密码（至少 6 位）。</div>
              </div>
              <div className="fg" style={{textAlign:'left'}}>
                <label>新密码</label>
                <div style={{position:'relative',display:'flex',alignItems:'center'}}>
                  <input type={showPwd?'text':'password'} value={password} onChange={e=>setPassword(e.target.value)}
                    onKeyDown={e=>e.key==='Enter'&&submit()} placeholder="••••••" style={{width:'100%',paddingRight:36}}/>
                  <button type="button" onClick={()=>setShowPwd(v=>!v)}
                    style={{position:'absolute',right:8,background:'none',border:'none',cursor:'pointer',padding:0,color:'var(--muted)',lineHeight:1,fontSize:16}}
                    title={showPwd?'隐藏密码':'显示密码'}>
                    {showPwd
                      ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                      : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                    }
                  </button>
                </div>
              </div>
              {error && <div style={{color:'var(--red)',fontSize:12,marginBottom:12,textAlign:'left',padding:'6px 10px',background:'rgba(196,90,90,.1)',borderRadius:'var(--r)'}}>{error}</div>}
              <button className="btn btn-p" onClick={submit} disabled={loading||!password} style={{width:'100%',padding:'10px',fontSize:14}}>
                {loading?'重置中...':'确认重置'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Setup({onDone, platformConfigured, platformAllowed}) {
  const [k, setK] = useState(''); const [s, setS] = useState(false);
  const showPlatformLoginTip = platformConfigured && !platformAllowed;
  const save = async () => {
    setS(true);
    try {
      await F(`${API}/auth/user-api-key/`, {method:'POST', body:JSON.stringify({api_key:k})});
      onDone();
    } catch(e){showAlert(e.message, '错误')}
    setS(false);
  };
  return (
    <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'100vh',background:'var(--bg)'}}>
      <div style={{textAlign:'center',maxWidth:420,padding:40}}>
        <h1 style={{fontFamily:'var(--serif)',fontSize:34,color:'var(--gold2)',marginBottom:6}}>记忆熔炉</h1>
        <p style={{color:'var(--fg3)',marginBottom:30,fontSize:13}}>AI长篇小说创作引擎 · 无限层级记忆系统</p>
        <div className="card" style={{textAlign:'left',marginBottom:16,borderColor:'var(--border2)'}}>
          <p style={{fontSize:12,color:'var(--fg2)',lineHeight:1.8}}>
            {showPlatformLoginTip
              ? <>平台密钥仅对已登录用户可用。您可以先 <b style={{color:'var(--gold)'}}>登录</b> 使用平台额度，或填写自己的<b style={{color:'var(--gold)'}}>智谱AI API密钥</b>（<a href="https://open.bigmodel.cn" target="_blank" style={{color:'var(--blue)'}}>bigmodel.cn</a>）以继续使用。</>
              : <>平台尚未配置API密钥。请填写您自己的<b style={{color:'var(--gold)'}}>智谱AI API密钥</b>（<a href="https://open.bigmodel.cn" target="_blank" style={{color:'var(--blue)'}}>bigmodel.cn</a>）以继续使用。</>
            }
          </p>
        </div>
        <div className="fg" style={{textAlign:'left'}}>
          <label>您的 API 密钥</label>
          <input value={k} onChange={e=>setK(e.target.value)} placeholder="输入您的API密钥..." type="password"/>
        </div>
        <div style={{display:'flex',gap:8}}>
          <button className="btn btn-p" onClick={save} disabled={s||!k} style={{flex:1}}>{s?'保存中...':'开始创作'}</button>
          {showPlatformLoginTip && (
            <button className="btn btn-s" onClick={() => { window.location.hash = '#/login'; }} style={{flex:1}}>去登录</button>
          )}
        </div>
      </div>
    </div>
  );
}

function Home({ps, onSel, onRef, user}) {
  const lang = getLang();
  const [show, setShow] = useState(false);
  const [f, setF] = useState({title:'',genre:'',synopsis:'',style_guide:'',world_setting:''});
  const [cr, setCr] = useState(false);
  const [gen, setGen] = useState(false);
  const requireLogin = () => { if(!user) { showAlert('此操作需要登录，请先登录', '提示'); window.location.hash = '#/login'; return false; } return true; };
  const create = async () => { if(!requireLogin()) return; if(!f.title)return; setCr(true); try{const p=await P(`${API}/novel/projects/`,f);setShow(false);setF({title:'',genre:'',synopsis:'',style_guide:'',world_setting:''});onRef();const full=await F(`${API}/novel/project/${p.id}/`);onSel(full);}catch(e){showAlert(e.message, '错误')} setCr(false); };
  const autoGen = async () => {
    if(!requireLogin()) return;
    setGen(true);
    try {
      const res = await P(`${API}/novel/generate-idea/`, f);
      setF({...f, ...res});
    } catch(e) {
      showAlert("生成失败: " + e.message, '错误');
    }
    setGen(false);
  };
  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:20}}>
        <div><h2 style={{fontFamily:'var(--serif)',fontSize:26}}>作品广场</h2><p style={{color:'var(--fg3)',fontSize:12,marginTop:3}}>选择一部作品或创建新作</p></div>
        <button className="btn btn-p" onClick={()=>{ if(requireLogin()) setShow(true); }}>+ 新建作品</button>
      </div>
      {ps.length===0?<div className="empty"><h3>还没有作品</h3><p>创建您的第一部小说，开始AI辅助无限记忆创作之旅</p></div>:
      <div className="g2">{ps.map(p=>(
        <div key={p.id} className="card" style={{cursor:'pointer'}} onClick={()=>onSel(p)}>
          <h3>{p.title}</h3><p style={{fontSize:12,color:'var(--fg3)'}}>{p.genre}</p>
          <p style={{fontSize:13,color:'var(--fg2)',margin:'6px 0'}}>{p.synopsis}</p>
          <div style={{display:'flex',gap:16,fontSize:12,color:'var(--fg3)'}}>
            <span>{p.chapter_count} 章</span><span>{p.total_words?.toLocaleString()} 字</span>
          </div>
        </div>
      ))}</div>}
      {show&&<div className="modal-ov" onClick={()=>!gen&&setShow(false)}><div className="modal" onClick={e=>e.stopPropagation()} style={{position:'relative', overflow:'hidden'}}>
        {gen && <div style={{position:'absolute',top:0,left:0,right:0,height:3,background:'linear-gradient(to right, transparent, var(--gold), transparent)',animation:'shimmer 1.5s infinite linear', backgroundSize:'200% 100%', zIndex:2}} />}
        <h2 style={{display:'flex', alignItems:'center', gap:8}}>
          新建作品 {gen && <span style={{fontSize:12, color:'var(--gold)', fontWeight:'normal', animation:'ai-pulse 2s infinite', padding:'2px 8px', borderRadius:10, background:'rgba(219,185,122,0.1)', display:'inline-flex', alignItems:'center', gap:4}}><Icon name="spark" size={12} /> 脑洞生成中...</span>}
        </h2>
        
        <div className="fg"><label>书名 *</label><input className={gen?'input-shimmer':''} disabled={gen} value={f.title} onChange={e=>setF({...f,title:e.target.value})} placeholder="输入书名..."/></div>
        <div className="fg"><label>类型</label><input className={gen?'input-shimmer':''} disabled={gen} value={f.genre} onChange={e=>setF({...f,genre:e.target.value})} placeholder="玄幻、仙侠、都市、科幻..."/></div>
        <div className="fg"><label>简介</label><textarea className={gen?'input-shimmer':''} disabled={gen} value={f.synopsis} onChange={e=>setF({...f,synopsis:e.target.value})} placeholder="故事简介..." rows={3}/></div>
        <div className="fg"><label>风格指导</label><textarea className={gen?'input-shimmer':''} disabled={gen} value={f.style_guide} onChange={e=>setF({...f,style_guide:e.target.value})} placeholder="写作风格偏好..." rows={2}/></div>
        <div className="fg"><label>世界设定</label><textarea className={gen?'input-shimmer':''} disabled={gen} value={f.world_setting} onChange={e=>setF({...f,world_setting:e.target.value})} placeholder="世界观设定..." rows={3}/></div>
        <div style={{display:'flex',gap:8,justifyContent:'flex-end', marginTop:20}}>
          <button className={`btn btn-ai ${gen?'generating':''}`} onClick={autoGen} disabled={gen} style={{marginRight:'auto',display:'inline-flex',alignItems:'center',gap:6}}>
            <Icon name="spark" size={12} />
            {gen?'脑洞持续展开中...':'AI 脑洞补全'}
          </button>
          <button className="btn btn-s" onClick={()=>setShow(false)} disabled={gen}>取消</button>
          <button className="btn btn-p" onClick={create} disabled={cr||gen}>{cr?'创建中...':'创建作品'}</button>
        </div>
      </div></div>}
    </div>
  );
}

function Proj({p, onRef, goWrite, user}) {
  const [gen, setGen] = useState(false); const [ins, setIns] = useState('');
  const [showAdd, setShowAdd] = useState(false); const [nc, setNc] = useState({title:'',outline:''});
  const requireLogin = () => { if(!user) { showAlert('此操作需要登录，请先登录', '提示'); window.location.hash = '#/login'; return false; } return true; };
  const genOutline = async () => { if(!requireLogin()) return; setGen(true); try{await P(`${API}/novel/project/${p.id}/outline/`,{instruction:ins});onRef();}catch(e){showAlert(e.message, '错误')} setGen(false); };
  const addCh = async () => { if(!requireLogin()) return; try{await P(`${API}/novel/project/${p.id}/chapters/`,nc);setShowAdd(false);setNc({title:'',outline:''});onRef();}catch(e){showAlert(e.message, '错误')} };
  return (
    <div>
      <div className="card" style={{marginBottom:16}}>
        <h3>{p.title}</h3><p style={{fontSize:13,color:'var(--fg2)'}}>{p.synopsis}</p>
        {p.world_setting&&(
          <p style={{fontSize:12,color:'var(--fg3)',marginTop:6}}>
            <span className="with-ic">
              <Icon name="map" size={12} />
              <span>{p.world_setting.substring(0,200)}...</span>
            </span>
          </p>
        )}
      </div>
      <div style={{display:'flex',gap:8,marginBottom:14,alignItems:'center'}}>
        <input value={ins} onChange={e=>setIns(e.target.value)} placeholder="可选：描述故事方向，指导大纲生成..." style={{flex:1}}/>
        <button className="btn btn-p" onClick={genOutline} disabled={gen}>
          {gen ? '生成中...' : (
            <span className="with-ic">
              <Icon name="spark" size={14} />
              生成大纲
            </span>
          )}
        </button>
        <button className="btn btn-s" onClick={()=>{ if(requireLogin()) setShowAdd(true); }}>+ 添加章节</button>
      </div>
      {p.chapters?.length>0?p.chapters.map(ch=>(
        <div key={ch.id} className="ch-item" onClick={goWrite}>
          <div className="ch-n">{ch.number}</div>
          <div className="ch-info"><h4>{ch.title}</h4><p>{ch.outline?.substring(0,100)||'暂无大纲'}</p></div>
          <span style={{fontSize:12,color:'var(--fg3)'}}>{ch.word_count}字</span>
          <span className={`ch-st ${ch.status}`}>{STATUS_MAP[ch.status]||ch.status}</span>
        </div>
      )):<div className="empty"><h3>还没有章节</h3><p>生成大纲或手动添加章节</p></div>}
      {showAdd&&<div className="modal-ov" onClick={()=>setShowAdd(false)}><div className="modal" onClick={e=>e.stopPropagation()}>
        <h2>添加章节</h2>
        <div className="fg"><label>标题</label><input value={nc.title} onChange={e=>setNc({...nc,title:e.target.value})}/></div>
        <div className="fg"><label>大纲</label><textarea value={nc.outline} onChange={e=>setNc({...nc,outline:e.target.value})} rows={4}/></div>
        <div style={{display:'flex',gap:8,justifyContent:'flex-end'}}>
          <button className="btn btn-s" onClick={()=>setShowAdd(false)}>取消</button>
          <button className="btn btn-p" onClick={addCh}>添加</button>
        </div>
      </div></div>}
    </div>
  );
}

function Write({p, onRef, onUsage, user}) {
  const chs = p.chapters||[];
  const [sel, setSel] = useState(null);
  const [cd, setCd] = useState(null);
  const [wr, setWr] = useState(false);
  const [ins, setIns] = useState('');
  const [tab, setTab] = useState('write');
  // context menu state
  const [ctxMenu, setCtxMenu] = useState(null); // {x, y}
  const [selRange, setSelRange] = useState(null); // {start, end, text}
  const [refining, setRefining] = useState(false);
  // custom prompt modal
  const [customModal, setCustomModal] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');
  const taRef = React.useRef(null);

  // Compute word count client-side from content (real-time, correct for CJK)
  const wordCount = React.useMemo(() => {
    const t = cd?.content || '';
    const cjk = (t.match(/[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]/g)||[]).length;
    const asc = (t.match(/[a-zA-Z0-9]+/g)||[]).length;
    return cjk + asc;
  }, [cd?.content]);

  const requireLogin = () => { if(!user) { showAlert('此操作需要登录，请先登录', '提示'); window.location.hash = '#/login'; return false; } return true; };
  const load = async (ch) => { setSel(ch); const d = await F(`${API}/novel/chapter/${ch.id}/`); setCd(d); };

  const _streamChapter = async (url) => {
    const base = cd?.content || '';
    const sep = base ? '\n\n' : '';
    const token = localStorage.getItem('mf_token');
    const hdrs = {'Content-Type':'application/json'};
    if(token) hdrs['Authorization'] = `Token ${token}`;
    const resp = await fetch(url, {method:'POST', headers:hdrs, body:JSON.stringify({instruction:ins})});
    if(!resp.ok) throw new Error(`${resp.status}: ${await resp.text()}`);
    const reader = resp.body.getReader(); const dec = new TextDecoder();
    let buf=''; let acc='';
    while(true) {
      const {done,value} = await reader.read(); if(done) break;
      buf += dec.decode(value,{stream:true});
      const lns = buf.split('\n'); buf = lns.pop();
      for(const ln of lns) {
        if(!ln.startsWith('data: ')) continue;
        let ev; try{ ev=JSON.parse(ln.slice(6)); }catch{ continue; }
        if(ev.type==='chunk'){ acc+=ev.text; setCd(p=>({...p,content:base+sep+acc})); }
        else if(ev.type==='done'){ onRef&&onRef(); onUsage&&onUsage(); }
        else if(ev.type==='error'){ throw new Error(ev.message); }
      }
    }
  };

  const doWrite = async () => {
    if(!requireLogin()) return; if(!sel) return; setWr(true);
    try { await _streamChapter(`${API}/novel/chapter/${sel.id}/write-stream/`); }
    catch(e){ showAlert(e.message, '错误'); }
    setWr(false);
  };

  const doCont = async () => {
    if(!requireLogin()) return; if(!sel) return; setWr(true);
    try { await _streamChapter(`${API}/novel/chapter/${sel.id}/continue-stream/`); }
    catch(e){ showAlert(e.message, '错误'); }
    setWr(false);
  };

  const doSave = async () => { if(!requireLogin()) return; if(!cd)return; await U(`${API}/novel/chapter/${cd.id}/`,{content:cd.content}); onRef(); };

  // handle right-click on textarea
  const handleContextMenu = (e) => {
    const ta = taRef.current;
    if(!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const text = ta.value.substring(start, end).trim();
    if(!text) return; // only show menu when text is selected
    e.preventDefault();
    setSelRange({start, end, text});
    setCtxMenu({x: e.clientX, y: e.clientY});
  };

  const closeCtxMenu = () => setCtxMenu(null);

  // stream refine and replace selected text
  const doRefine = async (mode, customInstruction='') => {
    if(!requireLogin()) return;
    if(!sel || !selRange) return;
    closeCtxMenu();
    setRefining(true);
    try {
      const token = localStorage.getItem('mf_token');
      const hdrs = {'Content-Type':'application/json'};
      if(token) hdrs['Authorization'] = `Token ${token}`;
      const body = {selected_text: selRange.text, mode, custom_instruction: customInstruction};
      const resp = await fetch(`${API}/novel/chapter/${sel.id}/refine-stream/`, {method:'POST', headers:hdrs, body:JSON.stringify(body)});
      if(!resp.ok) throw new Error(`${resp.status}: ${await resp.text()}`);
      const reader = resp.body.getReader(); const dec = new TextDecoder();
      let buf=''; let acc='';
      // snapshot content before streaming starts
      const originalContent = cd?.content || '';
      const before = originalContent.substring(0, selRange.start);
      const after = originalContent.substring(selRange.end);
      while(true) {
        const {done,value} = await reader.read(); if(done) break;
        buf += dec.decode(value,{stream:true});
        const lns = buf.split('\n'); buf = lns.pop();
        for(const ln of lns) {
          if(!ln.startsWith('data: ')) continue;
          let ev; try{ ev=JSON.parse(ln.slice(6)); }catch{ continue; }
          if(ev.type==='chunk'){ acc+=ev.text; setCd(p=>({...p,content:before+acc+after})); }
          else if(ev.type==='done'){ onUsage&&onUsage(); }
          else if(ev.type==='error'){ throw new Error(ev.message); }
        }
      }
      // update selRange to new selection end
      setSelRange(null);
    } catch(e){ showAlert(e.message, '错误'); }
    setRefining(false);
  };

  const openCustomModal = () => { setCtxMenu(null); setCustomPrompt(''); setCustomModal(true); };
  const submitCustom = () => { setCustomModal(false); doRefine('custom', customPrompt); };

  // close ctx menu on click outside
  React.useEffect(() => {
    if(!ctxMenu) return;
    const handler = () => closeCtxMenu();
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [ctxMenu]);

  return (
    <div className="split">
      {/* Right-click Context Menu */}
      {ctxMenu && (
        <div className="ctx-menu" style={{left:ctxMenu.x, top:ctxMenu.y}} onClick={e=>e.stopPropagation()}>
          <div className="ctx-item" onClick={()=>doRefine('expand')}>
            <span className="ctx-icon"><Icon name="spark" size={12} /></span>扩写
          </div>
          <div className="ctx-item" onClick={()=>doRefine('condense')}>
            <span className="ctx-icon"><Icon name="triangle" size={10} /></span>精简
          </div>
          <div className="ctx-sep"/>
          <div className="ctx-item" onClick={openCustomModal}>
            <span className="ctx-icon"><Icon name="pen" size={12} /></span>输入AI提示词…
          </div>
        </div>
      )}
      {/* Custom Prompt Modal */}
      {customModal && (
        <div className="refine-ov" onClick={()=>setCustomModal(false)}>
          <div className="refine-box" onClick={e=>e.stopPropagation()}>
            <h4>AI润色提示词</h4>
            <p style={{fontSize:12,color:'var(--fg3)',marginBottom:8}}>
              选中文本：<em style={{color:'var(--gold)'}}>{selRange?.text?.slice(0,60)}{selRange?.text?.length>60?'…':''}</em>
            </p>
            <textarea
              value={customPrompt}
              onChange={e=>setCustomPrompt(e.target.value)}
              placeholder="请输入AI润色指令，例如：改成更诗意的风格、增加紧张感、用古风文言…"
              autoFocus
              onKeyDown={e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey))submitCustom();}}
            />
            <div className="row">
              <button className="btn btn-s btn-sm" onClick={()=>setCustomModal(false)}>取消</button>
              <button className="btn btn-p" onClick={submitCustom} disabled={!customPrompt.trim()}>确认润色</button>
            </div>
          </div>
        </div>
      )}
      <div className="split-l">
        {!sel?<div>
          <div style={{display:'flex',alignItems:'center',marginBottom:14}}>
            <h3 style={{fontFamily:'var(--serif)',fontSize:18,flex:1}}>选择章节</h3>
            <span style={{fontSize:12,color:'var(--fg3)'}}>共 {(p.total_words||0).toLocaleString()} 字</span>
          </div>
          {chs.map(ch=>(<div key={ch.id} className="ch-item" onClick={()=>load(ch)}>
            <div className="ch-n">{ch.number}</div>
            <div className="ch-info"><h4>{ch.title}</h4><p>{ch.word_count.toLocaleString()}字 · {STATUS_MAP[ch.status]||ch.status}</p></div>
          </div>))}
        </div>:<div>
          <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}>
            <button className="btn btn-s btn-sm" onClick={()=>{setSel(null);setCd(null)}}>← 返回</button>
            <h3 style={{fontFamily:'var(--serif)',fontSize:16}}>第{sel.number}章: {sel.title}</h3>
            <span style={{fontSize:12,color:'var(--fg3)',marginLeft:'auto'}}>{wordCount.toLocaleString()} 字</span>
          </div>
          <div className="tabs">
            <div className={`tab ${tab==='write'?'on':''}`} onClick={()=>setTab('write')}>写作</div>
            <div className={`tab ${tab==='outline'?'on':''}`} onClick={()=>setTab('outline')}>大纲</div>
          </div>
          {tab==='write'&&<>
            <div style={{marginBottom:10,display:'flex',gap:8}}>
              <input value={ins} onChange={e=>setIns(e.target.value)} placeholder="给AI的指令（可选）..." style={{flex:1}}/>
              <button className="btn btn-p" onClick={doWrite} disabled={wr||refining}>
                {wr ? '写作中...' : (
                  <span className="with-ic">
                    <Icon name="pen" size={14} />
                    撰写
                  </span>
                )}
              </button>
              <button className="btn btn-s" onClick={doCont} disabled={wr||refining}>→ 续写</button>
              <button className="btn btn-s btn-sm" onClick={doSave}>保存</button>
            </div>
            {wr&&<div className="load">正在检索记忆、分析演变历史，流式生成内容中...</div>}
            {refining&&<div className="load">AI润色中，正在检索记忆与上下文...</div>}
            <textarea
              ref={taRef}
              className="ed"
              value={cd?.content||''}
              onChange={e=>setCd({...cd,content:e.target.value})}
              placeholder="章节内容将在此流式输出显示...&#10;&#10;提示：选中文本后右键可扩写、精简或自定义AI润色"
              onContextMenu={handleContextMenu}
            />
          </>}
          {tab==='outline'&&<div className="card"><p style={{fontSize:14,lineHeight:1.7,whiteSpace:'pre-wrap'}}>{cd?.outline||'暂无大纲'}</p></div>}
        </div>}
      </div>
      <div className="split-r">
        <h4 style={{fontSize:12,color:'var(--fg3)',marginBottom:10,letterSpacing:1}}>Agent 活动日志</h4>
        <MiniLogs pid={p.id}/>
      </div>
    </div>
  );
}

function Pyramid({pid, user}) {
  const [st, setSt] = useState(null);
  const [cons, setCons] = useState(false);
  const [q, setQ] = useState(''); const [rr, setRr] = useState(null); const [ret, setRet] = useState(false);
  const [vl, setVl] = useState(null); const [ln, setLn] = useState([]);
  const [nd, setNd] = useState(null);

  const requireLogin = () => { if(!user) { showAlert('此操作需要登录，请先登录', '提示'); window.location.hash = '#/login'; return false; } return true; };

  useEffect(() => { F(`${API}/memory/${pid}/stats/`).then(setSt); }, [pid]);

  const lvColors = ['var(--gold)','var(--purple)','var(--blue)','var(--green)','var(--red)'];
  const lvNames = ['世界','大陆','王国','城池','街巷'];

  const consolidate = async () => { if(!requireLogin()) return; setCons(true); try{await P(`${API}/memory/${pid}/consolidate/`,{target:'universe'});F(`${API}/memory/${pid}/stats/`).then(setSt);}catch(e){showAlert(e.message, '错误')} setCons(false); };
  const retrieve = async () => { if(!q)return; setRet(true); try{const r=await P(`${API}/memory/${pid}/retrieve/`,{query:q});setRr(r);}catch(e){showAlert(e.message, '错误')} setRet(false); };
  const viewLv = async (lv) => { setVl(lv); const n=await F(`${API}/memory/${pid}/nodes/?level=${lv}&limit=30`);setLn(n); };
  const viewNode = async (id) => { const d=await F(`${API}/memory/node/${id}/`);setNd(d); };

  return (
    <div>
      <div style={{display:'flex',gap:8,marginBottom:16}}>
        <button className="btn btn-p" onClick={consolidate} disabled={cons}>
          {cons ? '整合中...' : (
            <span className="with-ic">
              <Icon name="refresh" size={14} />
              整合记忆
            </span>
          )}
        </button>
      </div>
      {st&&<div className="stats-g">
        {[['节点',st.total_nodes],['链接',st.total_links],['快照',st.total_snapshots],['角色',st.characters],['角色快照',st.char_snapshots],['时间线事件',st.timeline_events],['预估Token',(st.estimated_tokens/1000).toFixed(0)+'K']].map(([l,v],i)=>(
          <div key={i} className="sc"><div className="sv" style={{fontSize:22}}>{v}</div><div className="sl">{l}</div></div>
        ))}
      </div>}
      <div className="card" style={{marginBottom:16}}>
        <h3>记忆金字塔</h3>
        <div className="pyr">{lvNames.map((n,i)=>{
          const c = st ? (st[n]||0) : 0;
          const w = 20 + i * 20;
          return (<div key={i} className="pyr-lv" onClick={()=>viewLv(i)}>
            <span className="pyr-lb">L{i} {n}</span>
            <div className="pyr-bar" style={{width:`${w}%`,background:lvColors[i]+'25',borderLeft:`3px solid ${lvColors[i]}`}}>
              <span style={{color:lvColors[i]}}>{n}</span><span className="pyr-cnt">{c}</span>
            </div>
          </div>);
        })}</div>
      </div>
      <div className="card" style={{marginBottom:16}}>
        <h3>记忆检索测试</h3>
        <div style={{display:'flex',gap:8,marginTop:8}}>
          <input value={q} onChange={e=>setQ(e.target.value)} placeholder="输入查询测试记忆检索效果..." style={{flex:1}}/>
          <button className="btn btn-p" onClick={retrieve} disabled={ret}>
            {ret ? '检索中...' : (
              <span className="with-ic">
                <Icon name="search" size={14} />
                检索
              </span>
            )}
          </button>
        </div>
        {rr&&<div style={{marginTop:10}}>
          <div style={{fontSize:11,color:'var(--fg3)',marginBottom:6}}>检索到 {rr.chars} 字符 (~{rr.estimated_tokens} tokens)</div>
          <div style={{background:'var(--bg)',border:'1px solid var(--border)',borderRadius:'var(--r)',padding:12,maxHeight:350,overflow:'auto',fontSize:12,lineHeight:1.6,whiteSpace:'pre-wrap',color:'var(--fg2)'}}>{rr.context}</div>
        </div>}
      </div>
      {vl!==null&&<div className="card">
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:10}}>
          <h3>层级{vl}: {lvNames[vl]} ({ln.length}个节点)</h3>
          <button className="btn btn-s btn-sm" onClick={()=>{setVl(null);setNd(null)}}>关闭</button>
        </div>
        {ln.map(n=>(
          <div key={n.id} style={{padding:6,borderBottom:'1px solid var(--border)',cursor:'pointer',fontSize:12}} onClick={()=>viewNode(n.id)}>
            <span style={{color:'var(--gold)'}}>{n.title}</span>
            <span style={{color:'var(--fg3)',fontSize:10,marginLeft:8}}>v{n.version} · 访问{n.access_count}次 · {n.children_count}个子节点 · 第{n.chapter_index}章</span>
            <p style={{color:'var(--fg2)',fontSize:11,marginTop:3}}>{n.summary}</p>
          </div>
        ))}
      </div>}
      {nd&&<div className="modal-ov" onClick={()=>setNd(null)}><div className="modal" onClick={e=>e.stopPropagation()} style={{maxWidth:700}}>
        <h2>{nd.title}</h2>
        <div style={{display:'flex',gap:6,flexWrap:'wrap',margin:'8px 0'}}>
          <span className="tag">层级{nd.level}: {nd.level_name}</span>
          <span className="tag">类型: {nd.node_type}</span>
          <span className="tag">版本: v{nd.version}</span>
          <span className="tag">重要度: {nd.importance}</span>
          <span className="tag">访问: {nd.access_count}次</span>
        </div>
        <div style={{marginBottom:10}}>
          <h4 style={{fontSize:12,color:'var(--fg3)',marginBottom:3}}>摘要</h4>
          <p style={{fontSize:13,lineHeight:1.6,color:'var(--fg2)',whiteSpace:'pre-wrap'}}>{nd.summary}</p>
        </div>
        {nd.content&&<div style={{marginBottom:10}}>
          <h4 style={{fontSize:12,color:'var(--fg3)',marginBottom:3}}>完整内容</h4>
          <div style={{background:'var(--bg)',padding:10,borderRadius:'var(--r)',maxHeight:250,overflow:'auto',fontSize:12,lineHeight:1.6,whiteSpace:'pre-wrap'}}>{nd.content}</div>
        </div>}
        {nd.snapshots?.length>0&&<div style={{marginBottom:10}}>
          <h4 style={{fontSize:12,color:'var(--fg3)',marginBottom:6}}>
            <span className="with-ic">
              <Icon name="clock" size={12} />
              记忆演变历史 ({nd.snapshots.length}个版本)
            </span>
          </h4>
          <div className="evo-track">{nd.snapshots.map((s,i)=>(
            <div key={i} className="evo-node">
              <div className="evo-ch">v{s.version} · 第{s.chapter_index}章</div>
              <div className="evo-state">{s.summary}</div>
              <div className="evo-change">
                <span className="with-ic">
                  <Icon name="note" size={12} />
                  {s.change_reason||'初始版本'}
                </span>
              </div>
            </div>
          ))}</div>
        </div>}
        {nd.children?.length>0&&<div style={{marginBottom:10}}>
          <h4 style={{fontSize:12,color:'var(--fg3)',marginBottom:3}}>子节点 ({nd.children.length})</h4>
          {nd.children.map(c=>(<div key={c.id} style={{fontSize:11,padding:3,cursor:'pointer',color:'var(--gold)'}} onClick={()=>viewNode(c.id)}>[{c.level_name}] {c.title}</div>))}
        </div>}
      </div></div>}
    </div>
  );
}

function Timeline({pid}) {
  const [events, setEvents] = useState([]);
  const [filter, setFilter] = useState('');
  useEffect(() => { loadE(); }, [pid]);
  const loadE = () => {
    const url = filter ? `${API}/memory/${pid}/timeline/?type=${filter}` : `${API}/memory/${pid}/timeline/`;
    F(url).then(setEvents);
  };
  useEffect(()=>{loadE()},[filter]);

  const types = [['','全部'],['plot','剧情'],['character','角色变化'],['relation','关系变化'],['turning','转折'],['foreshadow','伏笔'],['reveal','揭示']];

  const grouped = {};
  events.forEach(e => {
    const k = `第${e.chapter_index}章`;
    if (!grouped[k]) grouped[k] = [];
    grouped[k].push(e);
  });

  return (
    <div>
      <h2 style={{fontFamily:'var(--serif)',fontSize:22,marginBottom:4}}>故事时间线</h2>
      <p style={{color:'var(--fg3)',fontSize:12,marginBottom:16}}>记忆随时间的动态变化 · 角色成长轨迹 · 剧情演变脉络</p>
      <div style={{display:'flex',gap:6,marginBottom:20,flexWrap:'wrap'}}>
        {types.map(([v,l])=>(<button key={v} className={`btn btn-sm ${filter===v?'btn-p':'btn-s'}`} onClick={()=>setFilter(v)}>{l}</button>))}
      </div>
      {events.length===0?<div className="empty"><h3>暂无时间线事件</h3><p>开始写作后，Agent会自动提取故事事件并构建时间线</p></div>:
      <div>{Object.entries(grouped).map(([ch, evts])=>(
        <div key={ch} style={{marginBottom:24}}>
          <div style={{fontSize:13,fontWeight:600,color:'var(--gold)',marginBottom:10,padding:'4px 0',borderBottom:'1px solid var(--border)'}}>{ch}</div>
          <div className="tl">{evts.map(e=>(
            <div key={e.id} className={`tl-item ${e.event_type}`}>
              <div className="tl-ch">{e.event_type_display} {e.story_time&&`· ${e.story_time}`}</div>
              <div className="tl-title">{e.title}</div>
              <div className="tl-desc">{e.description}</div>
              {e.characters_involved?.length>0&&(
                <div className="tl-chars">
                  <span className="with-ic">
                    <Icon name="user" size={12} />
                    {e.characters_involved.join('、')}
                  </span>
                </div>
              )}
              {e.impact&&(
                <div className="tl-impact">
                  <span className="with-ic">
                    <Icon name="bolt" size={12} />
                    影响: {e.impact}
                  </span>
                </div>
              )}
            </div>
          ))}</div>
        </div>
      ))}</div>}
    </div>
  );
}

function Chars({pid, user}) {
  const [cs, setCs] = useState([]);
  const [sel, setSel] = useState(null);
  const [detail, setDetail] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [f, setF] = useState({name:'',description:'',traits:''});
  const [ext, setExt] = useState('');
  const [exting, setExting] = useState(false);

  const requireLogin = () => { if(!user) { showAlert('此操作需要登录，请先登录', '提示'); window.location.hash = '#/login'; return false; } return true; };

  useEffect(()=>{loadC()},[pid]);
  const loadC = () => F(`${API}/memory/${pid}/characters/`).then(setCs);

  const viewChar = async (id) => {
    const d = await F(`${API}/memory/character/${id}/`);
    setDetail(d); setSel(id);
  };

  const addC = async () => {
    if(!requireLogin()) return;
    const traits = f.traits.split(/[,，]/).map(t=>t.trim()).filter(Boolean);
    await P(`${API}/memory/${pid}/characters/`,{...f,traits});
    setShowAdd(false);setF({name:'',description:'',traits:''});loadC();
  };
  const extC = async () => { if(!ext)return; if(!requireLogin()) return; setExting(true); try{await P(`${API}/memory/${pid}/extract-characters/`,{text:ext});loadC();setExt('');}catch(e){showAlert(e.message, '错误')} setExting(false); };

  return (
    <div>
      <div style={{display:'flex',gap:8,marginBottom:16}}>
        <button className="btn btn-p" onClick={()=>{ if(requireLogin()) setShowAdd(true); }}>+ 添加角色</button>
      </div>
      <div className="card" style={{marginBottom:16}}>
        <h3 style={{fontSize:14,marginBottom:6}}>从文本自动提取角色</h3>
        <textarea value={ext} onChange={e=>setExt(e.target.value)} placeholder="粘贴故事文本，自动识别并提取角色信息..." rows={3} style={{width:'100%',marginBottom:6}}/>
        <button className="btn btn-s" onClick={extC} disabled={exting}>
          {exting ? '提取中...' : (
            <span className="with-ic">
              <Icon name="spark" size={14} />
              智能提取
            </span>
          )}
        </button>
      </div>
      {cs.length===0?<div className="empty"><h3>暂无角色</h3><p>手动添加或从文本自动提取角色</p></div>:
      <div className="g2">{cs.map(c=>(
        <div key={c.id} className="card" style={{cursor:'pointer'}} onClick={()=>viewChar(c.id)}>
          <h4 style={{fontFamily:'var(--serif)',fontSize:16,color:'var(--gold2)'}}>{c.name}</h4>
          {c.aliases?.length>0&&<p style={{fontSize:10,color:'var(--fg3)'}}>别名: {c.aliases.join('、')}</p>}
          <p style={{fontSize:12,color:'var(--fg2)',margin:'6px 0',lineHeight:1.5}}>{c.description}</p>
          {c.current_state&&<p style={{fontSize:11,color:'var(--cyan)',marginBottom:4}}>当前状态: {c.current_state}</p>}
          <div style={{display:'flex',gap:4,flexWrap:'wrap',alignItems:'center'}}>
            {c.traits?.map((t,i)=><span key={i} className="tag">{t}</span>)}
            <span style={{fontSize:10,color:'var(--fg3)',marginLeft:'auto'}}>{c.snapshot_count}个快照</span>
          </div>
        </div>
      ))}</div>}

      {detail&&<div className="modal-ov" onClick={()=>{setDetail(null);setSel(null)}}><div className="modal" onClick={e=>e.stopPropagation()} style={{maxWidth:700}}>
        <h2>
          <span className="with-ic">
            <Icon name="user" size={16} />
            {detail.name}
          </span>
        </h2>
        <p style={{fontSize:13,color:'var(--fg2)',lineHeight:1.6,margin:'8px 0'}}>{detail.description}</p>
        {detail.backstory&&<p style={{fontSize:12,color:'var(--fg3)',marginBottom:8}}>背景: {detail.backstory}</p>}
        {detail.current_state&&<div className="card" style={{borderColor:'var(--cyan)',marginBottom:12}}>
          <h4 style={{fontSize:12,color:'var(--cyan)',marginBottom:3}}>
            <span className="with-ic">
              <Icon name="eye" size={12} />
              当前状态
            </span>
          </h4>
          <p style={{fontSize:13,lineHeight:1.5}}>{detail.current_state}</p>
        </div>}
        {detail.traits?.length>0&&<div style={{display:'flex',gap:4,flexWrap:'wrap',marginBottom:12}}>{detail.traits.map((t,i)=><span key={i} className="tag">{t}</span>)}</div>}

        {detail.snapshots?.length>0&&<div>
          <h4 style={{fontSize:13,color:'var(--fg3)',marginBottom:8}}>
            <span className="with-ic">
              <Icon name="clock" size={12} />
              角色演变轨迹 ({detail.snapshots.length}个时间点)
            </span>
          </h4>
          <div className="evo-track">{detail.snapshots.map((s,i)=>(
            <div key={i} className="evo-node" style={{minWidth:200}}>
              <div className="evo-ch">第{s.chapter_index}章</div>
              <div className="evo-state">{s.state||'—'}</div>
              {s.beliefs&&(
                <div style={{fontSize:11,color:'var(--orange)',marginTop:3}}>
                  <span className="with-ic">
                    <Icon name="thought" size={12} />
                    信念: {s.beliefs}
                  </span>
                </div>
              )}
              {s.goals&&(
                <div style={{fontSize:11,color:'var(--green)',marginTop:2}}>
                  <span className="with-ic">
                    <Icon name="target" size={12} />
                    目标: {s.goals}
                  </span>
                </div>
              )}
              {s.traits?.length>0&&<div style={{display:'flex',gap:3,flexWrap:'wrap',marginTop:3}}>{s.traits.map((t,j)=><span key={j} style={{fontSize:9,padding:'1px 4px',borderRadius:3,background:'var(--bg4)',color:'var(--fg3)'}}>{t}</span>)}</div>}
              <div className="evo-change">
                <span className="with-ic">
                  <Icon name="note" size={12} />
                  {s.change_description}
                </span>
              </div>
            </div>
          ))}</div>
        </div>}
      </div></div>}

      {showAdd&&<div className="modal-ov" onClick={()=>setShowAdd(false)}><div className="modal" onClick={e=>e.stopPropagation()}>
        <h2>添加角色</h2>
        <div className="fg"><label>姓名 *</label><input value={f.name} onChange={e=>setF({...f,name:e.target.value})}/></div>
        <div className="fg"><label>描述</label><textarea value={f.description} onChange={e=>setF({...f,description:e.target.value})} rows={3}/></div>
        <div className="fg"><label>性格特征 (逗号分隔)</label><input value={f.traits} onChange={e=>setF({...f,traits:e.target.value})} placeholder="勇敢，狡诈，忠诚..."/></div>
        <div style={{display:'flex',gap:8,justifyContent:'flex-end'}}>
          <button className="btn btn-s" onClick={()=>setShowAdd(false)}>取消</button>
          <button className="btn btn-p" onClick={addC}>添加</button>
        </div>
      </div></div>}
    </div>
  );
}

function Chat({pid, onUsage, user}) {
  const [msgs, setMsgs] = useState([]); const [inp, setInp] = useState(''); const [snd, setSnd] = useState(false);
  const ref = useRef(null);
  const requireLogin = () => { if(!user) { showAlert('此操作需要登录，请先登录', '提示'); window.location.hash = '#/login'; return false; } return true; };
  useEffect(()=>{ref.current?.scrollIntoView({behavior:'smooth'})},[msgs]);
  const send = async () => {
    if(!requireLogin()) return;
    if(!inp.trim()||snd)return; const m=inp.trim(); setInp('');
    setMsgs(p=>[...p,{r:'u',c:m}]); setSnd(true);
    try{const r=await P(`${API}/novel/project/${pid}/chat/`,{message:m});setMsgs(p=>[...p,{r:'a',c:r.response}]);onUsage&&onUsage();}
    catch(e){setMsgs(p=>[...p,{r:'a',c:`错误: ${e.message}`}]);}
    setSnd(false);
  };
  return (
    <div className="cht">
      <div className="cht-msgs">
        {msgs.length===0&&<div className="empty"><h3>剧情顾问</h3><p>询问故事相关问题，Agent会在记忆金字塔中检索上下文并追溯角色演变历史来回答。<br/>例如："主角在第3章之后信念有什么变化？" "目前有哪些未解决的伏笔？"</p></div>}
        {msgs.map((m,i)=>(
          <div key={i} className={`cht-m ${m.r==='u'?'u':'a'}`}>
            <div className="cht-lb">{m.r==='u'?'你':'Agent'}</div>
            <div className="cht-bbl">{m.c}</div>
          </div>
        ))}
        {snd&&<div className="load">Agent正在思考...</div>}
        <div ref={ref}/>
      </div>
      <div className="cht-in">
        <input value={inp} onChange={e=>setInp(e.target.value)} onKeyDown={e=>e.key==='Enter'&&send()} placeholder="询问故事相关问题..."/>
        <button className="btn btn-p" onClick={send} disabled={snd}>发送</button>
      </div>
    </div>
  );
}

function Logs({pid}) {
  const [logs, setLogs] = useState([]); const [ar, setAr] = useState(true);
  const load = useCallback(()=>{
    const u = pid?`${API}/core/logs/?project_id=${pid}&limit=100`:`${API}/core/logs/?limit=100`;
    F(u).then(setLogs).catch(()=>{});
  },[pid]);
  useEffect(()=>{load();if(ar){const id=setInterval(load,3000);return()=>clearInterval(id)}},[load,ar]);
  return (
    <div>
      <div style={{display:'flex',gap:8,marginBottom:14,alignItems:'center'}}>
        <button className="btn btn-s btn-sm" onClick={load}>
          <span className="with-ic">
            <Icon name="refresh" size={12} />
            刷新
          </span>
        </button>
        <label style={{fontSize:11,color:'var(--fg3)',display:'flex',alignItems:'center',gap:4}}>
          <input type="checkbox" checked={ar} onChange={e=>setAr(e.target.checked)}/> 自动刷新
        </label>
        <span style={{fontSize:11,color:'var(--fg3)',marginLeft:'auto'}}>{logs.length} 条记录</span>
      </div>
      {logs.map(l=>(
        <div key={l.id} className="log-i">
          <span className="log-tm">{new Date(l.created_at).toLocaleTimeString('zh-CN')}</span>
          <span className={`log-b ${l.level}`}>{l.level}</span>
          <div style={{flex:1,minWidth:0}}>
            <div className="log-tt">{l.title}</div>
            {l.content&&<div className="log-ct">{l.content.substring(0,300)}</div>}
          </div>
        </div>
      ))}
      {logs.length===0&&<div className="empty"><p>暂无日志。开始写作后将显示Agent的全部活动。</p></div>}
    </div>
  );
}

function MiniLogs({pid}) {
  const [logs, setLogs] = useState([]);
  useEffect(()=>{
    const ld=()=>F(`${API}/core/logs/?project_id=${pid}&limit=20`).then(setLogs).catch(()=>{});
    ld(); const id=setInterval(ld,2000); return()=>clearInterval(id);
  },[pid]);
  return (<div>{logs.map(l=>(
    <div key={l.id} style={{marginBottom:7,fontSize:10,borderLeft:`2px solid ${
      l.level==='llm'?'var(--cyan)':l.level==='memory'?'var(--gold)':l.level==='think'?'var(--blue)':l.level==='error'?'var(--red)':'var(--fg3)'
    }`,paddingLeft:7}}>
      <div style={{display:'flex',gap:5,alignItems:'center'}}>
        <span className={`log-b ${l.level}`} style={{fontSize:8,padding:'0 3px'}}>{l.level}</span>
        <span style={{color:'var(--fg3)',fontFamily:'var(--mono)',fontSize:9}}>{new Date(l.created_at).toLocaleTimeString('zh-CN')}</span>
      </div>
      <div style={{color:'var(--fg2)',marginTop:1}}>{l.title}</div>
    </div>
  ))}</div>);
}

{% endverbatim %}
{% verbatim %}
function Settings({cfg, onSave}) {
  const [newKey, setNewKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);

  const saveUserKey = async () => {
    if (!newKey.trim()) return showAlert('请输入API密钥', '提示');

    // 先显示免责声明
    showDialog({
      title: 'API 密钥使用免责声明',
      message: `<div style="line-height:1.8">
        <p style="margin-bottom:12px"><strong style="color:var(--gold)">重要提示：</strong></p>
        <ul style="margin:0;padding-left:20px;">
          <li style="margin-bottom:8px">本平台<strong>不对</strong>您的 API 调用和费用支出承担任何责任</li>
          <li style="margin-bottom:8px">所有 API 消耗均由您的 API 密钥所属账户直接计费</li>
          <li style="margin-bottom:8px"><strong style="color:var(--gold)">强烈建议</strong>您使用<strong style="color:var(--gold)">月付套餐</strong>而非按量付费，以避免意外高额账单</li>
          <li style="margin-bottom:8px">请妥善保管您的 API 密钥，不要泄露给他人</li>
        </ul>
        <p style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border2)">
          点击"我已了解并同意"即表示您接受以上条款
        </p>
      </div>`,
      confirmText: '我已了解并同意',
      cancelText: '取消',
      showCancel: true,
      type: 'warning',
      onConfirm: async () => {
        setSaving(true);
        try {
          await F(`${API}/auth/user-api-key/`, {method:'POST', body:JSON.stringify({api_key:newKey.trim()})});
          setNewKey('');
          onSave();
          showAlert('API 密钥已保存', '成功');
        } catch(e) {
          showAlert(e.message, '保存失败');
        }
        setSaving(false);
      }
    });
  };

  const removeUserKey = async () => {
    const confirmed = await showConfirm('确定要移除您的API密钥吗？移除后将使用平台密钥（如有）', '确认移除');
    if (!confirmed) return;

    setRemoving(true);
    try {
      await F(`${API}/auth/user-api-key/`, {method:'DELETE'});
      onSave();
      showAlert('API 密钥已移除', '成功');
    } catch(e) {
      showAlert(e.message, '移除失败');
    }
    setRemoving(false);
  };

  const usingUserKey = cfg?.user_key_configured;
  const platformConfigured = cfg?.platform_configured;
  const platformAllowed = cfg?.platform_allowed ?? platformConfigured;
  const platformOk = platformAllowed;

  return (
    <div style={{maxWidth:560}}>
      <h2 style={{fontFamily:'var(--serif)',fontSize:22,marginBottom:16}}>API 密钥设置</h2>

      {/* Current status */}
      <div className="card" style={{marginBottom:20,borderColor: usingUserKey?'var(--blue)': platformOk?'var(--green)':'var(--red)'}}>
        <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:6}}>
          <Icon name={usingUserKey ? 'key' : platformOk ? 'check' : 'alert'} size={16} />
          <span style={{fontWeight:500,fontSize:13,color: usingUserKey?'var(--blue)': platformOk?'var(--green)':'var(--red)'}}>
            {usingUserKey?'使用您的专属密钥': platformOk?'使用平台密钥':'未配置任何密钥'}
          </span>
        </div>
        {usingUserKey && <p style={{fontSize:12,color:'var(--fg3)'}}>当前密钥: {cfg.api_key_preview} &nbsp;·&nbsp; 对话模型: {cfg.chat_model}</p>}
        {!usingUserKey && platformOk && <p style={{fontSize:12,color:'var(--fg3)'}}>平台提供 · 对话模型: {cfg.chat_model}</p>}
        {!usingUserKey && !platformOk && (
          <p style={{fontSize:12,color:'var(--fg3)'}}>
            {platformConfigured ? '平台密钥仅对登录用户可用，请添加您的API密钥或登录使用平台额度' : '请添加您的API密钥以使用本应用'}
          </p>
        )}
      </div>

      {/* User key management */}
      <h3 style={{fontFamily:'var(--serif)',fontSize:15,marginBottom:10,color:'var(--fg2)'}}>
        {usingUserKey ? '更换 / 移除您的密钥' : '添加您的专属密钥'}
      </h3>
      <p style={{fontSize:12,color:'var(--fg3)',marginBottom:12,lineHeight:1.7}}>
        使用自己的密钥可独立计费，不受平台配额限制。获取密钥请访问&nbsp;
        <a href="https://open.bigmodel.cn" target="_blank" style={{color:'var(--blue)'}}>open.bigmodel.cn</a>。
      </p>
      <div className="fg">
        <label>{usingUserKey ? '输入新密钥（留空则不更换）' : '您的 API 密钥'}</label>
        <input type="password" value={newKey} onChange={e=>setNewKey(e.target.value)} placeholder="输入密钥..."/>
      </div>
      <div style={{display:'flex',gap:8,marginBottom:24}}>
        <button className="btn btn-p" onClick={saveUserKey} disabled={saving||!newKey.trim()}>{saving?'保存中...':'保存密钥'}</button>
        {usingUserKey && <button className="btn btn-d btn-sm" onClick={removeUserKey} disabled={removing} style={{alignSelf:'center'}}>{removing?'移除中...':'移除密钥'}</button>}
      </div>

      {/* Platform key info */}
      <div className="card" style={{borderColor:'var(--border2)',marginBottom:24}}>
        <p style={{fontSize:12,color:'var(--fg2)',lineHeight:1.7}}>
          <b style={{color:'var(--fg)'}}>平台密钥：</b>
          {platformConfigured ? (
            <span style={{color:'var(--green)'}}>
              <span className="with-ic">
                <Icon name="check" size={12} />
                已配置（由管理员管理）
              </span>
            </span>
          ) : (
            <span style={{color:'var(--fg3)'}}>未配置</span>
          )}
          <br/>平台密钥由管理员在后台统一设置，您无需额外配置即可使用平台额度。
          {platformConfigured && !platformAllowed && <span style={{color:'var(--fg3)'}}> 访客模式下需要登录后才能使用平台额度。</span>}
          {usingUserKey && <span style={{color:'var(--fg3)'}}> 当您设置了专属密钥后，系统优先使用您的密钥。</span>}
        </p>
      </div>

      <div style={{marginTop:32}}>
        <h3 style={{fontFamily:'var(--serif)',fontSize:16,marginBottom:10}}>关于记忆熔炉</h3>
        <div className="card">
          <p style={{fontSize:12,lineHeight:1.8,color:'var(--fg2)'}}>
            记忆熔炉实现了基于 H-MEM 和 MemGPT 研究的分层记忆金字塔系统，
            专为中文网络小说长篇创作设计。核心特性：
          </p>
          <div style={{fontSize:12,lineHeight:1.8,color:'var(--fg2)',marginTop:8}}>
            <p>
              <span className="with-ic">
                <Icon name="triangle" size={12} />
                <b style={{color:'var(--gold)'}}>L0 世界</b> — 全局故事概览、主题基调
              </span>
            </p>
            <p>
              <span className="with-ic">
                <Icon name="triangle" size={12} />
                <b style={{color:'var(--purple)'}}>L1 大陆</b> — 主要故事线/篇章
              </span>
            </p>
            <p>
              <span className="with-ic">
                <Icon name="triangle" size={12} />
                <b style={{color:'var(--blue)'}}>L2 王国</b> — 章节摘要
              </span>
            </p>
            <p>
              <span className="with-ic">
                <Icon name="triangle" size={12} />
                <b style={{color:'var(--green)'}}>L3 城池</b> — 场景级细节
              </span>
            </p>
            <p>
              <span className="with-ic">
                <Icon name="triangle" size={12} />
                <b style={{color:'var(--red)'}}>L4 街巷</b> — 原始文本块 + 向量嵌入
              </span>
            </p>
          </div>
          <p style={{fontSize:12,lineHeight:1.8,color:'var(--fg2)',marginTop:10}}>
            <b>动态记忆演变：</b>每个记忆节点都有版本历史，角色有成长快照。
            Agent在写作时不仅检索当前记忆，还能追溯信念、目标、关系的变化轨迹——
            就像人类回忆自己理念和观点的动态变化。
          </p>
          <p style={{fontSize:12,lineHeight:1.8,color:'var(--fg2)',marginTop:6}}>
            <b>时间线系统：</b>自动从文本提取剧情事件、角色变化、转折点、伏笔，
            构建完整的故事时间线。让Agent对故事的演变脉络有全局视野。
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Theme System ──
const THEMES = [
  {id:'dark_gold', name:'暗金', swatches:['#08080b','#c9a86c','#5a8ac4'],
   vars:{bg:'#08080b',bg2:'#0f1014',bg3:'#181820',bg4:'#22222c',bg5:'#2c2c38',gold:'#c9a86c','gold2':'#dbb97a','gold-dim':'#8a7548'}},
  {id:'dark_blue', name:'深蓝', swatches:['#07090f','#5a8ac4','#5ac4b4'],
   vars:{bg:'#07090f',bg2:'#0c1220',bg3:'#131a2e',bg4:'#1c2540',bg5:'#243050',gold:'#5a8ac4','gold2':'#6a9ad4','gold-dim':'#3a5a94'}},
  {id:'dark_green', name:'暗翠', swatches:['#06100a','#3eb87a','#5ac4b4'],
   vars:{bg:'#06100a',bg2:'#0c1810',bg3:'#142218',bg4:'#1c2e22',bg5:'#243a2c',gold:'#3eb87a','gold2':'#4ec88a','gold-dim':'#1e884a'}},
  {id:'dark_purple', name:'紫夜', swatches:['#09070e','#9a6ac4','#c45a9a'],
   vars:{bg:'#09070e',bg2:'#110e1a',bg3:'#1a1428',bg4:'#221c36',bg5:'#2c2444',gold:'#9a6ac4','gold2':'#aa7ad4','gold-dim':'#6a3a94'}},
];

const ACCENT_PRESETS = [
  '#c9a86c','#dbb97a','#5a8ac4','#3eb87a','#9a6ac4',
  '#c45a5a','#5ac4b4','#d49a5a','#e87890','#68c87a',
];

const STATIC_APPS = [
  {name:'学术研究站', slug:'paper_lab', description:'论文深度阅读 · 零幻觉检索 · 精确引用 · 知识探索 · 辅助写作', icon:'search', color:'#5ac4b4'},
  {name:'知识图谱', slug:'knowledge_graph', description:'LLM自动提取 · 图谱可视化 · 跨应用知识链接 · PageRank · 路径探索', icon:'share-2', color:'#c9a86c'},
  {name:'代码助手', slug:'code_agent', description:'AI辅助代码重构 · 行级Diff审查 · 记忆金字塔 · 版本历史 · 跨文件理解', icon:'code', color:'#5a8ac4'},
  {name:'Claude Bridge', slug:'claude_bridge', description:'本地 Claude Code 远程接入 · 全工具可视化 · 权限管控 · Diff预览 · 多端同步', icon:'zap', color:'#e85d2f'},
  {name:'扫描增强', slug:'scan_enhance', description:'浏览器端处理 · 曲面平整化 · 透视校正 · CLAHE增强 · 自适应二值化 · 纠偏 · 降噪 · 零服务器CPU', icon:'scan', color:'#5ac480'},
  {name:'AI 题库', slug:'question_bank', description:'拍题OCR识别 · GLM-4.7解答 · 视觉模型几何题 · 最终答案沉淀 · 共享题库 · 点赞收藏评论', icon:'book', color:'#e8a05a'},
  {name:'文档阅读器', slug:'doc_reader', description:'PDF/MD阅读 · GLM-OCR解析 · 可视化分段 · 多选交互 · 智能问答 · 翻译总结', icon:'file-text', color:'#c9a86c'},
  {name:'放逐之城', slug:'banished', description:'Canvas 2D城市建造 · 资源链 · 村民AI · 水源系统 · 季节循环 · 全球交易市场 · AI协同托管', icon:'home', color:'#5ac480'},
  {name:'MineAI Chat', slug:'chat', description:'原生集成的对标ChatGPT界面的全能AI对话，支持切换模型与渲染LaTeX、代码', icon:'chat', color:'#5a8ac4'},
];

function applyTheme(vars) {
  Object.entries(vars).forEach(([k,v]) => document.documentElement.style.setProperty(`--${k}`, v));
}

const isLight = (hex) => {
  try {
    const c = hex.replace('#','');
    const r=parseInt(c.slice(0,2),16), g=parseInt(c.slice(2,4),16), b=parseInt(c.slice(4,6),16);
    return (r*299+g*587+b*114)/1000 > 128;
  } catch { return false; }
};

function ThemeSettings({onClose}) {
  const [tid, setTid] = useState(() => localStorage.getItem('mf_tid') || 'dark_gold');
  const [accent, setAccent] = useState(() => localStorage.getItem('mf_accent') || '');

  const selTheme = (t) => {
    setTid(t.id); setAccent('');
    localStorage.setItem('mf_tid', t.id);
    localStorage.removeItem('mf_accent');
    applyTheme(t.vars);
  };

  const selAccent = (c) => {
    setAccent(c);
    localStorage.setItem('mf_accent', c);
    document.documentElement.style.setProperty('--gold', c);
    document.documentElement.style.setProperty('--gold2', c);
    const base = THEMES.find(t => t.id === tid);
    if (base) {
      const {gold:_g, 'gold2':_g2, 'gold-dim':_gd, ...rest} = base.vars;
      applyTheme(rest);
    }
  };

  const reset = () => {
    setTid('dark_gold'); setAccent('');
    localStorage.removeItem('mf_tid'); localStorage.removeItem('mf_accent');
    applyTheme(THEMES[0].vars);
  };

  return (
    <div className="modal-ov" onClick={e => e.target===e.currentTarget && onClose()}>
      <div className="modal" style={{maxWidth:400}}>
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:20}}>
          <h2 style={{margin:0,fontSize:18}}>个性化设置</h2>
          <button className="btn btn-s btn-sm" onClick={onClose} style={{padding:'4px 8px'}}><Icon name="refresh" size={14} /></button>
        </div>
        
        <div style={{marginBottom:24}}>
          <div className="sec-title" style={{marginBottom:12,fontSize:10,opacity:0.6}}>主题视觉</div>
          <div className="tp-presets" style={{gridTemplateColumns:'repeat(2, 1fr)',gap:10}}>
            {THEMES.map(t => (
              <div key={t.id} className={`tp-preset${tid===t.id&&!accent?' on':''}`} 
                onClick={() => selTheme(t)}
                style={{padding:'12px',borderRadius:10,border:'1px solid var(--border)'}}>
                <div className="tp-swatches" style={{marginBottom:8}}>
                  {t.swatches.map((c,i) => <div key={i} className="tp-sw" style={{background:c,width:16,height:16,borderRadius:4}} />)}
                </div>
                <div className="tp-pn" style={{fontSize:12}}>{t.name}</div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="sec-title" style={{marginBottom:12,fontSize:10,opacity:0.6}}>强调色</div>
          <div className="csw-grid" style={{gridTemplateColumns:'repeat(5, 1fr)',gap:8}}>
            {ACCENT_PRESETS.map(c => (
              <div key={c} className={`csw${accent===c?' on':''}`} 
                style={{background:c,height:32,borderRadius:8}} 
                onClick={() => selAccent(c)} />
            ))}
          </div>
          <div className="tp-row" style={{marginTop:16,display:'flex',alignItems:'center',gap:12}}>
            <label style={{fontSize:12,color:'var(--fg2)'}}>自定义色值</label>
            <input type="color" value={accent||'#c9a86c'} 
              onChange={e => selAccent(e.target.value)}
              style={{width:40,height:28,padding:2,borderRadius:4,background:'var(--bg3)',border:'1px solid var(--border2)'}} />
          </div>
        </div>

        <div style={{marginTop:32,display:'flex',justifyContent:'space-between'}}>
          <button className="btn btn-s btn-sm" onClick={reset}>恢复默认</button>
          <button className="btn btn-p btn-sm" onClick={onClose}>完成</button>
        </div>
      </div>
    </div>
  );
}

function AppColorModal({app, appColors, onSave, onClose}) {
  const [color, setColor] = useState(appColors[app.slug] || app.color || '#c9a86c');
  return (
    <div className="modal-ov" onClick={e => e.target===e.currentTarget && onClose()}>
      <div className="modal" style={{maxWidth:300}}>
        <h2 style={{fontSize:16,marginBottom:14}}>自定义「{app.name}」颜色</h2>
        <div className="csw-grid">
          {ACCENT_PRESETS.map(c => (
            <div key={c} className={`csw${color===c?' on':''}`} style={{background:c}} onClick={() => setColor(c)} />
          ))}
        </div>
        <div className="tp-row" style={{marginTop:10}}>
          <label>自定义颜色</label>
          <input type="color" value={color} onChange={e => setColor(e.target.value)} />
        </div>
        <div style={{display:'flex',gap:8,marginTop:16,justifyContent:'flex-end'}}>
          <button className="btn btn-s btn-sm" onClick={onClose}>取消</button>
          <button className="btn btn-p btn-sm" onClick={() => { onSave(app.slug, color); onClose(); }}>保存</button>
        </div>
      </div>
    </div>
  );
}

// ── 功能导航图谱 ─────────────────────────────────────────────────
const KG_API_BASE = '/api/kg';
const SLUG_MAP = {
  '网文写作':'memoryforge','学术研究站':'paper_lab','知识图谱':'knowledge_graph',
  '代码助手':'code_agent','Claude Bridge':'claude_bridge','OCR 工作室':'ocr_studio',
  '扫描增强':'scan_enhance','AI 题库':'question_bank','放逐之城':'banished','MineAI Chat':'chat',
};

{% endverbatim %}
{% verbatim %}
function FeatureNavMap({onNavigate}) {
  const [open, setOpen] = useState(false);
  const [elements, setElements] = useState([]);
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const [query, setQuery] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [hint, setHint] = useState('');

  useEffect(() => {
    fetch(`${KG_API_BASE}/platform/`).then(r=>r.json()).then(d => {
      const els = [
        ...d.nodes.map(n => ({data:{...n.data, _color: n.data.color}})),
        ...d.edges,
      ];
      setElements(els);
    }).catch(()=>{});
  }, []);

  useEffect(() => {
    if (!open || !containerRef.current || !window.cytoscape || !elements.length) return;
    if (cyRef.current) { cyRef.current.destroy(); cyRef.current = null; }
    const cy = window.cytoscape({
      container: containerRef.current,
      elements,
      style: [
        { selector:'node', style:{
          'background-color': e => e.data('_color') || '#888',
          'label': 'data(label)', 'color':'#e8e4df', 'font-size':'10px',
          'font-family':'Noto Sans SC, sans-serif',
          'text-valign':'bottom', 'text-halign':'center', 'text-margin-y':'3px',
          'width': e => e.data('importance') >= 0.8 ? 32 : 20,
          'height': e => e.data('importance') >= 0.8 ? 32 : 20,
          'border-width':1.5, 'border-color': e => e.data('_color') || '#888', 'border-opacity':0.6,
        }},
        { selector:'node.highlighted', style:{'border-width':3,'border-opacity':1,'background-opacity':1}},
        { selector:'node.dimmed', style:{'opacity':0.2}},
        { selector:'edge', style:{
          'width':1.2, 'line-color':'rgba(90,90,120,0.4)',
          'target-arrow-color':'rgba(90,90,120,0.5)',
          'target-arrow-shape':'triangle', 'curve-style':'bezier',
          'opacity':0.6,
        }},
        { selector:'edge.dimmed', style:{'opacity':0.05}},
      ],
      layout:{ name:'cose', animate:false, padding:30, nodeRepulsion:4000, idealEdgeLength:60 },
      userZoomingEnabled:true, userPanningEnabled:true, boxSelectionEnabled:false,
    });
    cy.on('mouseover','node', e => {
      const n = e.target;
      const neighbors = n.neighborhood();
      cy.elements().addClass('dimmed');
      n.removeClass('dimmed').addClass('highlighted');
      neighbors.removeClass('dimmed');
    });
    cy.on('mouseout','node', () => {
      cy.elements().removeClass('dimmed highlighted');
    });
    cy.on('tap','node', e => {
      const label = e.target.data('label');
      const slug = SLUG_MAP[label];
      if (slug) onNavigate(slug);
    });
    cyRef.current = cy;
    return () => { if (cyRef.current) { cyRef.current.destroy(); cyRef.current = null; }};
  }, [open, elements]);

  const doAiNav = async () => {
    if (!query.trim() || aiLoading) return;
    setAiLoading(true); setHint('');
    try {
      const appLabels = Object.keys(SLUG_MAP).join('、');
      const messages = [{role:'user',content:`用户说：「${query}」\n\n平台应用列表：${appLabels}\n\n请分析用户最可能需要哪个应用（可以多个），用JSON格式回复，只输出：{"highlight":["应用名1","应用名2"]}`}];
      let buf = '';
      const _tok = localStorage.getItem('mf_token');
      for await (const chunk of streamSSE(`/api/core/chat-stream/`, {messages, stream:true}, _tok)) {
        if (chunk.content) buf += chunk.content;
      }
      const m = buf.match(/\{[^}]*"highlight"[^}]*\}/);
      if (m) {
        try {
          const parsed = JSON.parse(m[0]);
          const labels = parsed.highlight || [];
          if (cyRef.current && labels.length) {
            cyRef.current.elements().removeClass('highlighted dimmed');
            cyRef.current.elements().addClass('dimmed');
            labels.forEach(lbl => {
              cyRef.current.nodes().filter(n => n.data('label') === lbl).forEach(n => {
                n.removeClass('dimmed').addClass('highlighted');
                n.neighborhood().removeClass('dimmed');
              });
            });
            setHint(`推荐：${labels.join('、')}`);
          }
        } catch(e) {}
      }
    } catch(e) {}
    setAiLoading(false);
  };

  return (
    <div style={{marginBottom:20,borderRadius:'var(--r)',border:'1px solid var(--border2)',overflow:'hidden',background:'var(--bg2)'}}>
      <div onClick={() => setOpen(o=>!o)} style={{padding:'10px 16px',cursor:'pointer',display:'flex',alignItems:'center',gap:10,userSelect:'none'}}>
        <Icon name="share-2" size={16} stroke={1.5} style={{color:'var(--gold)',flexShrink:0}} />
        <span style={{fontWeight:500,fontSize:13,color:'var(--fg)'}}>功能导航图谱</span>
        <span style={{fontSize:11,color:'var(--fg3)',marginLeft:4}}>点击节点直接跳转应用</span>
        <Icon name={open?'chevron-up':'chevron-down'} size={14} stroke={2} style={{color:'var(--fg3)',marginLeft:'auto'}} />
      </div>
      {open && (
        <div style={{borderTop:'1px solid var(--border)'}}>
          <div ref={containerRef} style={{width:'100%',height:320,background:'var(--bg)'}} />
          <div style={{padding:'8px 12px',borderTop:'1px solid var(--border)',display:'flex',gap:8,alignItems:'center'}}>
            <input value={query} onChange={e=>setQuery(e.target.value)}
              onKeyDown={e=>e.key==='Enter'&&doAiNav()}
              placeholder="描述你想做的事，AI 帮你找到合适的应用..."
              style={{flex:1,fontSize:12,padding:'5px 10px'}} />
            <button className="btn btn-p" onClick={doAiNav} disabled={aiLoading} style={{fontSize:12,padding:'5px 12px'}}>
              {aiLoading?'..':'AI 导航'}
            </button>
            {hint && <span style={{fontSize:11,color:'var(--gold)'}}>{hint}</span>}
          </div>
          <div style={{padding:'0 12px 6px',fontSize:11,color:'var(--fg3)'}}>
            点击图谱节点可直接跳转应用 · 鼠标悬停高亮关联节点
          </div>
        </div>
      )}
    </div>
  );
}

function PlatformHome({user, onLogout, siteConfig}) {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [aiRec, setAiRec] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [showTheme, setShowTheme] = useState(false);
  const [editApp, setEditApp] = useState(null);
  const [openMenu, setOpenMenu] = useState(null);
  const [appColors, setAppColors] = useState({});
  const [pinnedApps, setPinnedApps] = useState([]);
  const [appOrder, setAppOrder] = useState([]);
  const [dragOver, setDragOver] = useState(null);
  const [draggingSlug, setDraggingSlug] = useState(null);
  const dragRef = useRef(null);
  const longPressTimer = useRef(null);

  // Per-user namespace
  const ns = useCallback((k) => user?.is_guest ? `mf:guest:${k}` : user?.email ? `mf:${user.email}:${k}` : `mf:guest:${k}`, [user?.email, user?.is_guest]);
  const savePref = useCallback((k, v) => localStorage.setItem(ns(k), JSON.stringify(v)), [ns]);
  const getPref = useCallback((k, def) => { try { return JSON.parse(localStorage.getItem(ns(k))) ?? def; } catch { return def; } }, [ns]);

  // Load per-user prefs when user resolves
  useEffect(() => {
    setAppColors(getPref('colors', {}));
    setPinnedApps(getPref('pinned', []));
    setAppOrder(getPref('order', []));
  }, [user?.email, user?.is_guest]);

  // Apply stored theme on mount
  useEffect(() => {
    const tid = localStorage.getItem('mf_tid') || 'dark_gold';
    const t = THEMES.find(t => t.id === tid);
    if (t) applyTheme(t.vars);
    const accent = localStorage.getItem('mf_accent');
    if (accent) {
      document.documentElement.style.setProperty('--gold', accent);
      document.documentElement.style.setProperty('--gold2', accent);
    }
    F(`${API}/platform/apps/`)
      .then(data => { setApps(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  // Close menu on outside click
  useEffect(() => {
    if (!openMenu) return;
    const h = (e) => {
      if (!e.target.closest('.app-menu-wrap')) setOpenMenu(null);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [openMenu]);

  const allApps = useMemo(() => {
    const slugs = new Set(apps.map(a => a.slug));
    return [...apps, ...STATIC_APPS.filter(a => !slugs.has(a.slug))];
  }, [apps]);

  const filteredApps = useMemo(() => {
    if (!query.trim()) return allApps;
    const q = query.toLowerCase();
    return allApps.filter(a => a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q));
  }, [allApps, query]);

  // Pinned first, then custom order
  const sortedApps = useMemo(() => {
    const list = [...filteredApps];
    if (appOrder.length) {
      list.sort((a, b) => {
        const ia = appOrder.indexOf(a.slug), ib = appOrder.indexOf(b.slug);
        if (ia < 0 && ib < 0) return 0;
        if (ia < 0) return 1;
        if (ib < 0) return -1;
        return ia - ib;
      });
    }
    list.sort((a, b) => {
      const pa = pinnedApps.includes(a.slug), pb = pinnedApps.includes(b.slug);
      return pa === pb ? 0 : pa ? -1 : 1;
    });
    return list;
  }, [filteredApps, appOrder, pinnedApps]);

  const u = user?.usage || {};
  const quota = user?.quota;
  const pct = (v, max) => max ? Math.min(100, Math.round(v / max * 100)) : 0;
  // Default: gold for all apps
  const getColor = (app) => appColors[app.slug] || '#c9a86c';

  const saveAppColor = (slug, color) => {
    const next = {...appColors, [slug]: color};
    setAppColors(next);
    savePref('colors', next);
  };

  const togglePin = (slug) => {
    const next = pinnedApps.includes(slug) ? pinnedApps.filter(s => s !== slug) : [...pinnedApps, slug];
    setPinnedApps(next);
    savePref('pinned', next);
  };

  const handleShare = (app) => {
    const url = `${location.origin}/#/app/${app.slug}`;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(() => {
        const orig = document.title;
        document.title = `已复制 ${app.name} 链接`;
        setTimeout(() => { document.title = orig; }, 1500);
      }).catch(() => {
        prompt('请手动复制链接:', url);
      });
    } else {
      prompt('请手动复制链接:', url);
    }
  };

  const handleFeedback = (app) => {
    // 打开反馈表单或链接到反馈页面
    const feedbackUrl = 'https://github.com/anthropics/claude-code/issues';
    window.open(feedbackUrl, '_blank');
  };

  // Drag & drop reorder
  const handleDrop = (targetSlug) => {
    const src = dragRef.current;
    if (!src || src === targetSlug) return;
    const slugs = sortedApps.map(a => a.slug);
    const from = slugs.indexOf(src), to = slugs.indexOf(targetSlug);
    if (from < 0 || to < 0) return;
    slugs.splice(from, 1);
    slugs.splice(to, 0, src);
    dragRef.current = null;
    setAppOrder(slugs);
    savePref('order', slugs);
  };

  const goApp = (app) => {
    if (draggingSlug) return;
    if (!user) { window.location.hash = '#/login'; return; }
    if (app.slug === 'novel_share') window.location.href = '/share/';
    else window.location.hash = `#/app/${app.slug}`;
  };

  const aiRecommend = async () => {
    if (!query.trim() || aiLoading) return;
    if (!user) { window.location.hash = '#/login'; return; }
    setAiLoading(true); setAiRec('');
    const appList = allApps.map(a => `- ${a.name}: ${a.description}`).join('\n');
    const msg = `用户需求: "${query}"\n\n平台可用应用:\n${appList}\n\n请推荐最合适的1-2个应用并简要说明原因，格式简洁。`;
    const token = localStorage.getItem('mf_token');
    const hdrs = {'Content-Type':'application/json'};
    if (token) hdrs['Authorization'] = `Token ${token}`;
    try {
      const resp = await fetch(`${API}/core/chat-stream/`, {method:'POST', headers:hdrs, body:JSON.stringify({message:msg})});
      if (!resp.ok) throw new Error(await resp.text());
      const reader = resp.body.getReader(); const dec = new TextDecoder();
      let buf = '', full = '';
      while (true) {
        const {done, value} = await reader.read(); if (done) break;
        buf += dec.decode(value, {stream:true});
        const lns = buf.split('\n'); buf = lns.pop();
        for (const ln of lns) {
          if (!ln.startsWith('data: ')) continue;
          let ev; try { ev = JSON.parse(ln.slice(6)); } catch { continue; }
          if (ev.type==='chunk') { full += ev.text; setAiRec(full); }
          else if (ev.type==='done') { setAiRec(full); }
        }
      }
    } catch { setAiRec('推荐失败，请稍后再试'); }
    setAiLoading(false);
  };

  return (
    <div className="dash-wrap">
      <nav className="dash-nav">
        <div className="dash-logo">
          <img src="/static/favicon-mineai.svg" alt="MineAI" style={{width:16,height:16,display:'inline-block'}} />
          {siteConfig?.site_title || 'MineAI'}
        </div>
        <div className="dash-sw">
          <div className="dash-sw-ic"><Icon name="search" size={14} /></div>
          <input
            placeholder="搜索应用，或描述需求让 AI 推荐…"
            value={query}
            onChange={e => { setQuery(e.target.value); setAiRec(''); }}
            onKeyDown={e => e.key === 'Enter' && aiRecommend()}
          />
        </div>
        <div className="dash-right">
          {query.trim() && (
            <button className={`btn btn-sm${aiLoading ? ' btn-ai generating' : ' btn-ai'}`}
              onClick={aiRecommend} disabled={aiLoading}
              style={{display:'inline-flex',alignItems:'center',gap:6}}>
              <Icon name="spark" size={12} />
              {aiLoading ? 'AI 推荐中…' : 'AI 推荐'}
            </button>
          )}
          <button className="btn btn-s btn-sm" onClick={() => setShowTheme(true)} title="个性化设置" style={{padding:'6px'}}><Icon name="adjust" size={16} /></button>
          {user ? (
            <>
              <span style={{fontSize:12,color:'var(--fg3)',maxWidth:160,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{displayName(user)}</span>
              {user.is_guest
                ? <button className="btn btn-p btn-sm" onClick={() => { window.location.hash = '#/login'; }}>登录</button>
                : <>
                    <button className="btn btn-s btn-sm" onClick={() => { window.location.hash = '#/profile'; }}
                      style={{display:'inline-flex',alignItems:'center',gap:4}}>
                      <Icon name="user" size={13}/> 个人中心
                    </button>
                    <button className="btn btn-s btn-sm" onClick={onLogout}>退出</button>
                  </>
              }
            </>
          ) : (
            <button className="btn btn-p btn-sm" onClick={() => { window.location.hash = '#/login'; }}>登录 / 注册</button>
          )}
        </div>
      </nav>

      <div className="dash-body">
        {/* Token Stats */}
        {user && (
          <div style={{marginBottom:28}}>
            <div className="sec-hd">
              <div className="sec-title">Token 用量</div>
              <span style={{fontSize:11,color:'var(--fg3)'}}>
                {user.has_own_key ? '自有 API 密钥 · 无限额度' : quota ? `今日已用 ${pct(u.daily_prompt_count||0, quota.daily_prompt_count)}%` : ''}
              </span>
            </div>
            <div className="stat-grid">
              <div className="stat-c">
                <div className="stat-v" style={{color:'var(--gold2)'}}>{(u.prompt_count||0).toLocaleString()}</div>
                <div className="stat-l">总提问次数</div>
                {quota && <>
                  <div className="stat-bar"><div className="stat-fill" style={{width:`${pct(u.daily_prompt_count||0,quota.daily_prompt_count)}%`,background:'var(--gold)'}} /></div>
                  <div style={{fontSize:10,color:'var(--fg3)',marginTop:3}}>今日 {u.daily_prompt_count||0} / {quota.daily_prompt_count}</div>
                </>}
              </div>
              <div className="stat-c">
                <div className="stat-v" style={{color:'var(--cyan)'}}>{((u.total_tokens||0)/1000).toFixed(1)}<span style={{fontSize:14}}>K</span></div>
                <div className="stat-l">累计 Token</div>
                <div style={{fontSize:10,color:'var(--fg3)',marginTop:6}}>
                  输入 {((u.input_tokens||0)/1000).toFixed(1)}K · 输出 {((u.output_tokens||0)/1000).toFixed(1)}K
                </div>
              </div>
              {quota && <>
                <div className="stat-c">
                  <div className="stat-v" style={{color:'var(--blue)'}}>{((u.daily_input_tokens||0)/1000).toFixed(1)}<span style={{fontSize:14}}>K</span></div>
                  <div className="stat-l">今日输入</div>
                  <div className="stat-bar"><div className="stat-fill" style={{width:`${pct(u.daily_input_tokens||0,quota.daily_input_tokens)}%`,background:'var(--blue)'}} /></div>
                  <div style={{fontSize:10,color:'var(--fg3)',marginTop:3}}>限额 {(quota.daily_input_tokens/1000).toFixed(0)}K</div>
                </div>
                <div className="stat-c">
                  <div className="stat-v" style={{color:'var(--green)'}}>{((u.daily_output_tokens||0)/1000).toFixed(1)}<span style={{fontSize:14}}>K</span></div>
                  <div className="stat-l">今日输出</div>
                  <div className="stat-bar"><div className="stat-fill" style={{width:`${pct(u.daily_output_tokens||0,quota.daily_output_tokens)}%`,background:'var(--green)'}} /></div>
                  <div style={{fontSize:10,color:'var(--fg3)',marginTop:3}}>限额 {(quota.daily_output_tokens/1000).toFixed(0)}K</div>
                </div>
              </>}
            </div>
          </div>
        )}

        {/* 功能导航图谱 */}
        <FeatureNavMap onNavigate={(slug) => { window.location.hash = `#/app/${slug}`; }} />

        {/* Apps grid */}
        <div>
          <div className="sec-hd">
            <div className="sec-title">应用</div>
            {query.trim() && <span style={{fontSize:12,color:'var(--fg3)'}}>找到 {sortedApps.length} 个</span>}
          </div>
          {loading ? (
            <div className="load">加载中...</div>
          ) : sortedApps.length === 0 ? (
            <div className="empty"><h3>未找到相关应用</h3><p>试试「AI 推荐」</p></div>
          ) : (
            <div className="apps-grid2">
              {sortedApps.map(app => {
                const color = getColor(app);
                const icStyle = {color, background:hexToRgba(color,.12)||'var(--bg3)', border:`1px solid ${hexToRgba(color,.28)||'var(--border)'}`};
                const pinned = pinnedApps.includes(app.slug);
                const isDragging = draggingSlug === app.slug;
                const isOver = dragOver === app.slug;
                return (
                  <div key={app.slug}
                    className={`ac2${isOver?' drag-over':''}${isDragging?' dragging':''}`}
                    style={{
                      borderColor: appColors[app.slug] ? hexToRgba(color,.35)||'var(--border)' : 'var(--border)',
                      position:'relative', cursor: isDragging ? 'grabbing' : 'grab'
                    }}
                    draggable
                    onDragStart={e => {
                      dragRef.current = app.slug;
                      setDraggingSlug(app.slug);
                      e.dataTransfer.effectAllowed = 'move';
                      e.dataTransfer.setData('text/plain', app.slug);
                    }}
                    onDragOver={e => { e.preventDefault(); if (dragRef.current !== app.slug) setDragOver(app.slug); }}
                    onDrop={e => { e.preventDefault(); handleDrop(app.slug); setDragOver(null); setDraggingSlug(null); }}
                    onDragEnd={() => { dragRef.current = null; setDragOver(null); setDraggingSlug(null); }}
                    onClick={() => goApp(app)}
                  >
                    {pinned && <span className="ac2-pinmark"><Icon name="pin" size={11} /></span>}
                    {/* 3-dot menu */}
                    <div className="app-menu-wrap" onClick={e => e.stopPropagation()}>
                      <button className="app-menu-btn"
                        onClick={() => setOpenMenu(openMenu === app.slug ? null : app.slug)}>
                        <Icon name="dots" size={15} />
                      </button>
                      {openMenu === app.slug && (
                        <div className="app-menu">
                          <div className="app-menu-item" onClick={(e) => { e.stopPropagation(); handleShare(app); setOpenMenu(null); }}>
                            <Icon name="share" size={12} /> 分享链接
                          </div>
                          <div className="app-menu-item" onClick={(e) => { e.stopPropagation(); handleFeedback(app); setOpenMenu(null); }}>
                            <Icon name="message-square" size={12} /> 反馈
                          </div>
                          <div className="app-menu-sep" />
                          <div className="app-menu-item" onClick={(e) => { e.stopPropagation(); togglePin(app.slug); setOpenMenu(null); }}>
                            <Icon name="pin" size={12} /> {pinned ? '取消置顶' : '固定在首位'}
                          </div>
                          <div className="app-menu-sep" />
                          <div className="app-menu-item" onClick={(e) => { e.stopPropagation(); setEditApp(app); setOpenMenu(null); }}>
                            <Icon name="palette" size={12} /> 修改应用颜色
                          </div>
                        </div>
                      )}
                    </div>
                    <div style={{display:'flex',alignItems:'center',gap:12}}>
                      <div className="ac2-ico" style={icStyle}>
                        <Icon name={pickAppIcon(app)} size={24} stroke={1.7} />
                      </div>
                      <div className="ac2-name">{app.name}</div>
                    </div>
                    <div className="ac2-desc">{app.description}</div>
                    <div className="ac2-foot">
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {(aiRec || aiLoading) && (
            <div className="ai-rec">
              <div className="ai-rec-hd"><Icon name="spark" size={13} /> AI 应用推荐</div>
              <div className="ai-rec-txt">
                {aiRec || '思考中...'}
                {aiLoading && <span style={{opacity:.7, animation:'blink 1s infinite'}}>▌</span>}
              </div>
            </div>
          )}
        </div>
      </div>

      {showTheme && <ThemeSettings onClose={() => setShowTheme(false)} />}
      {editApp && <AppColorModal app={editApp} appColors={appColors} onSave={saveAppColor} onClose={() => setEditApp(null)} />}
    </div>
  );
}

function applyFavicon(favicon) {
  if (!favicon) return;
  let link = document.getElementById('site-favicon');
  if (!link) {
    link = document.createElement('link');
    link.id = 'site-favicon';
    link.rel = 'icon';
    document.head.appendChild(link);
  }
  if (favicon.startsWith('http') || favicon.startsWith('/') || favicon.startsWith('data:')) {
    link.type = favicon.endsWith('.ico') ? 'image/x-icon' : 'image/png';
    link.href = favicon;
  } else {
    // emoji — render as inline SVG
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">${favicon}</text></svg>`;
    link.type = 'image/svg+xml';
    link.href = `data:image/svg+xml,${encodeURIComponent(svg)}`;
  }
}

function Root() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [route, setRoute] = useState(window.location.hash || '#/');
  const [siteConfig, setSiteConfig] = useState(null);

  useEffect(() => {
    const handler = () => setRoute(window.location.hash || '#/');
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  useEffect(() => {
    fetch(`${API}/auth/site-config/`)
      .then(r => r.json())
      .then(cfg => {
        setSiteConfig(cfg);
        document.title = cfg.site_title || 'MineAI';
        applyFavicon(cfg.site_favicon || '/static/favicon-mineai.svg');
      })
      .catch(() => {});
  }, []);

  useEffect(() => { checkAuth(); }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('mf_token');
    if (!token) {
      try {
        const g = await P(`${API}/auth/guest/`, {});
        localStorage.setItem('mf_token', g.token);
        setUser({email: g.email, is_guest: true, token: g.token, usage: g.usage || {prompt_count:0, input_tokens:0, output_tokens:0, total_tokens:0}});
      } catch(e) {
        setUser(null);
      }
      setAuthChecked(true);
      return;
    }
    try {
      const me = await F(`${API}/auth/me/`);
      if (me.authenticated) setUser({...me, token});
      else {
        localStorage.removeItem('mf_token');
        const g = await P(`${API}/auth/guest/`, {});
        localStorage.setItem('mf_token', g.token);
        setUser({email: g.email, is_guest: true, token: g.token, usage: g.usage || {prompt_count:0, input_tokens:0, output_tokens:0, total_tokens:0}});
      }
    } catch(e) {
      localStorage.removeItem('mf_token');
      try {
        const g = await P(`${API}/auth/guest/`, {});
        localStorage.setItem('mf_token', g.token);
        setUser({email: g.email, is_guest: true, token: g.token, usage: g.usage || {prompt_count:0, input_tokens:0, output_tokens:0, total_tokens:0}});
      } catch {
        setUser(null);
      }
    }
    setAuthChecked(true);
  };

  const handleAuth = async (data) => {
    localStorage.setItem('mf_token', data.token);
    try {
      const me = await F(`${API}/auth/me/`);
      if (me.authenticated) setUser({...me, token: data.token});
      else setUser({email: data.email, is_guest: false, token: data.token, usage: {prompt_count:0, input_tokens:0, output_tokens:0, total_tokens:0}});
    } catch(e) {
      setUser({email: data.email, is_guest: false, token: data.token, usage: {prompt_count:0, input_tokens:0, output_tokens:0, total_tokens:0}});
    }
    setAuthChecked(true);
    window.location.hash = '#/';
  };

  const logout = async () => {
    if (user?.is_guest) {
      window.location.hash = '#/login';
      return;
    }
    try { await P(`${API}/auth/logout/`, {}); } catch(e) {}
    localStorage.removeItem('mf_token');
    setUser(null);
    await checkAuth();
    window.location.hash = '#/';
  };

  if (!authChecked) return (
    <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'100vh',background:'var(--bg)'}}>
      <div className="load">初始化中...</div>
    </div>
  );

  if (route === '#/login') {
    if (user && !user.is_guest) {
      window.setTimeout(() => { window.location.hash = '#/'; }, 0);
      return null;
    }
    return <AuthScreen onAuth={handleAuth} siteConfig={siteConfig} />;
  }

  if (route.startsWith('#/reset-password')) {
    return <ResetPasswordScreen siteConfig={siteConfig} />;
  }

  if (route === '#/app/memoryforge') {
    return <MemoryForgeApp user={user} onLogout={logout} onUpdateUser={setUser} />;
  }
  
  if (route === '#/app/ocr_studio') {
    return <OCRStudioApp user={user} onLogout={logout} onUpdateUser={setUser} />;
  }

  if (route === '#/app/paper_lab') {
    return <PaperLabApp user={user} onLogout={logout} onUpdateUser={setUser} />;
  }

  if (route === '#/app/knowledge_graph') {
    return <KGApp user={user} onLogout={logout} onUpdateUser={setUser} />;
  }

  if (route === '#/app/code_agent') {
    return <CodeAgentApp user={user} onLogout={logout} onUpdateUser={setUser} />;
  }

  if (route === '#/app/claude_bridge') {
    return <ClaudeBridgeApp user={user} onLogout={logout} onUpdateUser={setUser} />;
  }

  if (route === '#/app/scan_enhance') {
    return <ScanEnhanceApp user={user} onLogout={logout} onUpdateUser={setUser} />;
  }

  if (route === '#/app/question_bank') {
    return <QuestionBankApp user={user} onLogout={logout} onUpdateUser={setUser} />;
  }

  if (route === '#/app/doc_reader') {
    return <DocReaderApp user={user} onLogout={logout} onUpdateUser={setUser} />;
  }

  if (route === '#/app/banished') {
    return <BanishedApp user={user} onLogout={logout} onUpdateUser={setUser} />;
  }

  if (route === '#/app/chat') {
    return <ChatApp user={user} onLogout={logout} onUpdateUser={setUser} />;
  }

  if (route === '#/profile') {
    return <UserPanelApp user={user} onLogout={logout} onUpdateUser={setUser} siteConfig={siteConfig} />;
  }

  return <PlatformHome user={user} onLogout={logout} siteConfig={siteConfig} />;
}

{% endverbatim %}
{% verbatim %}
// ── OCR Studio 应用组件 ────────────────────────────────────────
// PDF 渲染与图片转换全部在浏览器端完成（PDF.js）
// 后端仅作为 OCR API 的 CORS 代理，不存储任何文件

function OCRStudioApp({user, onLogout, onUpdateUser}) {
  const [v, setV] = useState('upload');
  const [pages, setPages] = useState([]);   // [{id,name,dataUrl,status,result,error}]
  const [apiKey, setApiKey] = useState('');
  const [ocrPrompt, setOcrPrompt] = useState('');
  // 'platform'=使用平台密钥(仅登录非访客用户可用), 'own'=用户自填密钥
  const [keyMode, setKeyMode] = useState(() => (user && !user.is_guest) ? 'platform' : 'own');
  const [activePageIdx, setActivePageIdx] = useState(0);
  const [sbOpen, setSbOpen] = useState(false);
  const [pdfLoaded, setPdfLoaded] = useState(!!window.pdfjsLib);
  const pdfJsRef = useRef(window.pdfjsLib || null);

  // 动态加载 PDF.js CDN
  useEffect(() => {
    if (window.pdfjsLib) return;
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
    s.onload = () => {
      window.pdfjsLib.GlobalWorkerOptions.workerSrc =
        'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
      pdfJsRef.current = window.pdfjsLib;
      setPdfLoaded(true);
    };
    document.head.appendChild(s);
  }, []);

  const resetProject = () => { setPages([]); setActivePageIdx(0); setV('upload'); };
  const goTo = (view) => { setV(view); setSbOpen(false); };

  return (
    <div className="app">
      <div className={`sb${sbOpen?' open':''}`}>
        <div className="sb-back" onClick={() => { window.location.hash = '#/'; }}>← 返回 MineAI</div>
        <div className="sb-hd">
          <h1>OCR 工作室</h1>
          <p>文档识别 · 文字提取</p>
        </div>
        <div className="sb-nav">
          <div className="ns">
            <div className="ns-t">工作台</div>
            <div className={`ni${v==='upload'?' on':''}`} onClick={() => goTo('upload')}>
              <i><Icon name="upload" size={14} /></i>导入文件
            </div>
            {pages.length > 0 && (
              <div className={`ni${v==='work'?' on':''}`} onClick={() => goTo('work')}>
                <i><Icon name="file" size={14} /></i>识别工作台
                <span style={{marginLeft:'auto',fontSize:11,color:'var(--fg3)'}}>{pages.length}页</span>
              </div>
            )}
            {pages.some(p => p.status === 'done') && (
              <div className={`ni${v==='result'?' on':''}`} onClick={() => goTo('result')}>
                <i><Icon name="check" size={14} /></i>查看结果
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="main">
        <div className="top">
          <button className="menu-btn" onClick={() => setSbOpen(!sbOpen)}><Icon name="menu" size={18} /></button>
          <span className="top-t">
            {v==='upload'?'导入文件':v==='work'?'识别工作台':'识别结果'}
          </span>
          <div className="top-b">{displayName(user)}</div>
        </div>
        <div className="ct">
          {v === 'upload' && (
            <OCRUpload
              pdfJs={pdfJsRef} pdfLoaded={pdfLoaded}
              apiKey={apiKey} setApiKey={setApiKey}
              keyMode={keyMode} setKeyMode={setKeyMode}
              ocrPrompt={ocrPrompt} setOcrPrompt={setOcrPrompt}
              onPagesReady={(ps) => { setPages(ps); setActivePageIdx(0); setV('work'); }}
              user={user}
            />
          )}
          {v === 'work' && pages.length > 0 && (
            <OCRWork
              pages={pages} setPages={setPages}
              apiKey={apiKey} keyMode={keyMode} ocrPrompt={ocrPrompt}
              activePageIdx={activePageIdx} setActivePageIdx={setActivePageIdx}
              setV={setV} onReset={resetProject} user={user}
            />
          )}
          {v === 'result' && (
            <OCRResult
              pages={pages} initialIdx={activePageIdx}
              goBack={() => setV('work')}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function OCRUpload({pdfJs, pdfLoaded, apiKey, setApiKey, keyMode, setKeyMode, ocrPrompt, setOcrPrompt, onPagesReady, user}) {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState('');
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef();

  const processFile = async (file) => {
    if (!file) return;
    if (!user) { showAlert('请先登录', '提示'); window.location.hash = '#/login'; return; }
    const ext = file.name.toLowerCase().split('.').pop();
    if (!['pdf','png','jpg','jpeg','gif','bmp','tiff','webp'].includes(ext)) {
      showAlert('请选择 PDF 或图片文件', '提示'); return;
    }
    if (!pdfLoaded && ext === 'pdf') { showAlert('PDF.js 尚未加载，请稍后再试', '提示'); return; }
    setLoading(true);
    try {
      let ps = [];
      if (ext === 'pdf') {
        const buf = await file.arrayBuffer();
        setProgress('加载 PDF...');
        const pdf = await pdfJs.current.getDocument({data: buf}).promise;
        for (let i = 1; i <= pdf.numPages; i++) {
          setProgress(`渲染第 ${i} / ${pdf.numPages} 页...`);
          const page = await pdf.getPage(i);
          const vp = page.getViewport({scale: 1.5});
          const canvas = document.createElement('canvas');
          canvas.width = vp.width; canvas.height = vp.height;
          await page.render({canvasContext: canvas.getContext('2d'), viewport: vp}).promise;
          ps.push({id:`p${i}`, name:`第 ${i} 页`, dataUrl: canvas.toDataURL('image/png'), status:'idle', result:'', error:''});
        }
      } else {
        setProgress('读取图片...');
        const dataUrl = await new Promise((res, rej) => {
          const r = new FileReader(); r.onload = e => res(e.target.result); r.onerror = rej; r.readAsDataURL(file);
        });
        const img = await new Promise((res, rej) => { const i = new Image(); i.onload=()=>res(i); i.onerror=rej; i.src=dataUrl; });
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
        canvas.getContext('2d').drawImage(img, 0, 0);
        ps.push({id:'p1', name: file.name, dataUrl: canvas.toDataURL('image/png'), status:'idle', result:'', error:''});
      }
      onPagesReady(ps);
    } catch(e) {
      showAlert('文件处理失败: ' + e.message, '错误');
    }
    setLoading(false); setProgress('');
  };

  return (
    <div className="fade-in">
      <div style={{marginBottom:32}}>
        <h1 style={{fontFamily:'var(--serif)',fontSize:28,color:'var(--gold2)',marginBottom:8}}>OCR 工作室</h1>
        <p style={{color:'var(--fg2)',fontSize:14}}>PDF/图片在浏览器本地渲染，仅 OCR 请求发到后端代理，文件不上传服务器</p>
      </div>

      <div style={{display:'grid',gap:16,marginBottom:24}}>
        {/* 密钥来源选择：登录非访客用户可选平台密钥 */}
        <div>
          <label style={{display:'block',fontSize:11,color:'var(--fg2)',marginBottom:6}}>
            OCR API 密钥 <span style={{color:'var(--red)'}}>*</span>
          </label>
          {user && !user.is_guest ? (
            <div style={{display:'flex',gap:8,marginBottom:keyMode==='own'?10:0}}>
              {[
                {v:'platform', label:'使用平台密钥', hint:'由平台提供，无需填写'},
                {v:'own',      label:'使用自己的密钥', hint:'填写您的 GLM API Key'},
              ].map(opt => (
                <div key={opt.v}
                  onClick={() => setKeyMode(opt.v)}
                  style={{flex:1,cursor:'pointer',padding:'10px 14px',borderRadius:6,
                    border:`1px solid ${keyMode===opt.v?'var(--gold)':'var(--border2)'}`,
                    background:keyMode===opt.v?'rgba(201,168,108,.1)':'var(--bg3)',
                    transition:'all .15s'}}>
                  <div style={{display:'flex',alignItems:'center',gap:8}}>
                    <div style={{width:14,height:14,borderRadius:'50%',flexShrink:0,
                      border:`2px solid ${keyMode===opt.v?'var(--gold)':'var(--fg3)'}`,
                      background:keyMode===opt.v?'var(--gold)':'transparent'}}/>
                    <span style={{fontSize:13,fontWeight:500,color:keyMode===opt.v?'var(--gold2)':'var(--fg)'}}>{opt.label}</span>
                  </div>
                  <div style={{fontSize:11,color:'var(--fg3)',marginTop:4,paddingLeft:22}}>{opt.hint}</div>
                </div>
              ))}
            </div>
          ) : null}
          {/* 仅在"使用自己密钥"或未登录时显示输入框 */}
          {(keyMode === 'own' || !user || user.is_guest) && (
            <input type="password"
              style={{width:'100%',padding:10,background:'var(--bg3)',border:'1px solid var(--border2)',borderRadius:6,color:'var(--fg)'}}
              placeholder="输入您的 GLM / OCR API 密钥（不会上传服务器）..."
              value={apiKey} onChange={e => setApiKey(e.target.value)}
            />
          )}
        </div>
        <div>
          <label style={{display:'block',fontSize:11,color:'var(--fg2)',marginBottom:4}}>提示词（可选）</label>
          <textarea
            style={{width:'100%',minHeight:72,padding:10,background:'var(--bg3)',border:'1px solid var(--border2)',borderRadius:6,color:'var(--fg)',fontFamily:'inherit',resize:'vertical'}}
            placeholder="例如：以 Markdown 格式提取文本，保留表格和公式..."
            value={ocrPrompt} onChange={e => setOcrPrompt(e.target.value)}
          />
        </div>
      </div>

      <div
        style={{border:'2px dashed var(--border2)',borderRadius:12,padding:48,textAlign:'center',
          cursor:loading?'wait':'pointer',transition:'all .3s',
          borderColor:dragging?'var(--gold)':'var(--border2)',
          background:dragging?'var(--bg4)':'transparent', opacity:loading?0.7:1}}
        onDragOver={e=>{e.preventDefault();setDragging(true);}}
        onDragLeave={()=>setDragging(false)}
        onDrop={e=>{e.preventDefault();setDragging(false);if(!loading)processFile(e.dataTransfer.files[0]);}}
        onClick={()=>!loading&&fileRef.current?.click()}
      >
        <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.gif,.bmp,.tiff,.webp"
          hidden onChange={e=>processFile(e.target.files[0])} />
        {loading ? (
          <div style={{display:'flex',flexDirection:'column',alignItems:'center',gap:12}}>
            <div className="load" />
            <span style={{color:'var(--fg2)',fontSize:14}}>{progress}</span>
          </div>
        ) : (
          <>
            <div style={{marginBottom:12,color:'var(--gold)',display:'flex',justifyContent:'center'}}>
              <Icon name="upload" size={32} stroke={1.6} />
            </div>
            <div>
              <span style={{color:'var(--fg)',fontWeight:500}}>拖拽 PDF 或图片到这里</span>
              <span style={{color:'var(--fg3)'}}> 或点击选择文件</span>
            </div>
            <div style={{fontSize:12,color:'var(--fg3)',marginTop:8}}>
              支持 PDF、PNG、JPG、WebP 等 · 完全离线渲染
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function OCRWork({pages, setPages, apiKey, keyMode, ocrPrompt, activePageIdx, setActivePageIdx, setV, onReset, user}) {
  const [selected, setSelected] = useState(() => new Set(pages.map(p => p.id)));
  const [running, setRunning] = useState(false);
  const abortRef = useRef(false);

  const toggle = (id) => setSelected(prev => { const n=new Set(prev); n.has(id)?n.delete(id):n.add(id); return n; });
  const doneCount = pages.filter(p => p.status === 'done').length;
  const errorCount = pages.filter(p => p.status === 'error').length;
  const processingCount = pages.filter(p => p.status === 'processing').length;
  const statusColor = {idle:'var(--fg3)', processing:'var(--gold)', done:'var(--green)', error:'var(--red)'};

  const pendingSelected = [...selected].filter(id => pages.find(p => p.id===id && p.status!=='done')).length;

  const buildOcrBody = (b64) => {
    const body = {image_b64: b64, prompt: ocrPrompt};
    if (keyMode === 'own') body.api_key = apiKey;  // 平台模式不传，后端自动取平台密钥
    return body;
  };

  const runOCR = async () => {
    if (!user) { showAlert('请先登录', '提示'); window.location.hash='#/login'; return; }
    if (keyMode === 'own' && !apiKey.trim()) { showAlert('请先在导入页面填写 OCR API 密钥', '提示'); return; }
    const targets = pages.filter(p => selected.has(p.id) && p.status !== 'done');
    if (!targets.length) { showAlert('没有待处理页面（已完成的不会重复识别）', '提示'); return; }
    setRunning(true); abortRef.current = false;
    for (const page of targets) {
      if (abortRef.current) break;
      setPages(prev => prev.map(p => p.id===page.id ? {...p, status:'processing'} : p));
      const b64 = page.dataUrl.replace(/^data:image\/\w+;base64,/, '');
      try {
        const resp = await fetch(`${API}/ocr/recognize/`, {
          method:'POST',
          headers:{'Content-Type':'application/json','Authorization':`Token ${localStorage.getItem('mf_token')}`},
          body: JSON.stringify(buildOcrBody(b64)),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        setPages(prev => prev.map(p => p.id===page.id ? {...p, status:'done', result:data.text, error:''} : p));
      } catch(e) {
        setPages(prev => prev.map(p => p.id===page.id ? {...p, status:'error', error:e.message} : p));
      }
    }
    setRunning(false);
  };

  const retryPage = async (pageId) => {
    const page = pages.find(p => p.id===pageId);
    if (!page) return;
    if (keyMode === 'own' && !apiKey.trim()) return;
    setPages(prev => prev.map(p => p.id===pageId ? {...p, status:'processing', error:''} : p));
    const b64 = page.dataUrl.replace(/^data:image\/\w+;base64,/, '');
    try {
      const resp = await fetch(`${API}/ocr/recognize/`, {
        method:'POST',
        headers:{'Content-Type':'application/json','Authorization':`Token ${localStorage.getItem('mf_token')}`},
        body: JSON.stringify(buildOcrBody(b64)),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
      setPages(prev => prev.map(p => p.id===pageId ? {...p, status:'done', result:data.text, error:''} : p));
    } catch(e) {
      setPages(prev => prev.map(p => p.id===pageId ? {...p, status:'error', error:e.message} : p));
    }
  };

  const downloadMD = () => {
    const done = pages.filter(p => p.status==='done');
    if (!done.length) { showAlert('还没有已完成的结果', '提示'); return; }
    const content = done.map((p,i) => `+-${i+1}-+\n\n${p.result}`).join('\n\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([content],{type:'text/markdown'}));
    a.download = 'ocr_result.md'; a.click(); URL.revokeObjectURL(a.href);
  };

  return (
    <div className="fade-in">
      <div style={{display:'flex',alignItems:'flex-start',justifyContent:'space-between',marginBottom:20,flexWrap:'wrap',gap:12}}>
        <div>
          <h1 style={{fontFamily:'var(--serif)',fontSize:22,marginBottom:4}}>识别工作台</h1>
          <p style={{color:'var(--fg2)',fontSize:13}}>
            {pages.length} 页 · 已完成 {doneCount}
            {errorCount>0 && <span style={{color:'var(--red)'}}> · 失败 {errorCount}</span>}
            {processingCount>0 && <span style={{color:'var(--gold)'}}> · 处理中 {processingCount}</span>}
          </p>
        </div>
        <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
          {doneCount>0 && <>
            <button className="btn btn-sm btn-s" onClick={()=>setV('result')}>
              <span className="with-ic"><Icon name="file" size={14} />查看结果</span>
            </button>
            <button className="btn btn-sm btn-s" onClick={downloadMD}>
              <span className="with-ic"><Icon name="download" size={14} />下载 MD</span>
            </button>
          </>}
          <button className="btn btn-sm btn-s" onClick={onReset}>+ 新文件</button>
        </div>
      </div>

      <div style={{display:'flex',gap:8,marginBottom:16,flexWrap:'wrap'}}>
        <button className="btn btn-sm btn-s" onClick={()=>setSelected(new Set(pages.map(p=>p.id)))}>全选</button>
        <button className="btn btn-sm btn-s" onClick={()=>setSelected(new Set())}>取消</button>
        <button className="btn btn-sm btn-s" onClick={()=>setSelected(new Set(pages.filter(p=>p.status!=='done').map(p=>p.id)))}>选待处理</button>
        {!running
          ? <button className="btn btn-sm btn-p" onClick={runOCR} disabled={pendingSelected===0}>
              <span className="with-ic"><Icon name="search" size={14} />开始识别 ({pendingSelected})</span>
            </button>
          : <button className="btn btn-sm btn-d" onClick={()=>{abortRef.current=true;}}>停止</button>
        }
      </div>

      <div style={{display:'flex',gap:8,marginBottom:16,fontSize:11,color:'var(--fg3)',flexWrap:'wrap'}}>
        {[['idle','待处理'],['processing','处理中'],['done','已完成'],['error','错误']].map(([st,lb])=>(
          <span key={st} style={{display:'flex',alignItems:'center',gap:4}}>
            <span style={{width:8,height:8,borderRadius:'50%',background:statusColor[st],
              animation:st==='processing'?'pulse 1.5s infinite':'none'}} />{lb}
          </span>
        ))}
      </div>

      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(140px,1fr))',gap:12}}>
        {pages.map((p,idx)=>(
          <div key={p.id} style={{
            position:'relative',borderRadius:6,overflow:'hidden',cursor:'pointer',
            border:'2px solid',borderColor:selected.has(p.id)?'var(--gold)':'transparent',
            aspectRatio:'3/4',background:'var(--bg3)',transition:'all .2s',
          }}
          onClick={()=>{ if(p.status==='done'){setActivePageIdx(idx);setV('result');} else toggle(p.id); }}>
            <img src={p.dataUrl} alt={p.name} loading="lazy" style={{width:'100%',height:'100%',objectFit:'cover'}} />
            <div style={{position:'absolute',top:6,right:6,width:10,height:10,borderRadius:'50%',
              background:statusColor[p.status],animation:p.status==='processing'?'pulse 1.5s infinite':'none'}} />
            <div style={{position:'absolute',bottom:6,right:6,background:'rgba(0,0,0,.7)',
              color:'#fff',fontSize:10,padding:'2px 7px',borderRadius:99,fontWeight:500}}>{idx+1}</div>
            {selected.has(p.id) && p.status!=='done' && (
              <div style={{position:'absolute',top:6,left:6,width:20,height:20,borderRadius:4,
                background:'var(--gold)',display:'flex',alignItems:'center',justifyContent:'center',color:'#000'}}>
                <Icon name="check" size={12} />
              </div>
            )}
            {p.status==='error' && (
              <div style={{position:'absolute',inset:0,display:'flex',flexDirection:'column',alignItems:'center',
                justifyContent:'center',background:'rgba(0,0,0,.65)',gap:8,padding:8}}
                onClick={e=>{e.stopPropagation();retryPage(p.id);}}>
                <div style={{color:'var(--red)',fontSize:10}}>识别失败</div>
                <button className="btn btn-sm" style={{background:'var(--red)',color:'#fff',fontSize:11}}>
                  <span className="with-ic"><Icon name="refresh" size={11} />重试</span>
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {running && (
        <div style={{position:'fixed',bottom:24,left:'50%',transform:'translateX(-50%)',
          background:'var(--bg2)',border:'1px solid var(--border)',borderRadius:8,
          padding:'12px 20px',display:'flex',alignItems:'center',gap:12,
          boxShadow:'0 8px 32px rgba(0,0,0,.4)',zIndex:200}}>
          <div className="load" />
          <span style={{fontSize:13,color:'var(--fg2)'}}>识别中 · 已完成 {doneCount}/{pages.length}</span>
          <button className="btn btn-sm btn-d" onClick={()=>{abortRef.current=true;}}>停止</button>
        </div>
      )}
    </div>
  );
}

function OCRResult({pages, initialIdx, goBack}) {
  const done = useMemo(() => pages.filter(p => p.status==='done'), [pages]);
  // map initialIdx (global pages index) to done array index
  const [idx, setIdx] = useState(() => {
    const p = pages[initialIdx];
    const i = done.indexOf(p);
    return i >= 0 ? i : 0;
  });
  const current = done[idx];

  const downloadMD = () => {
    const content = done.map((p,i) => `+-${i+1}-+\n\n${p.result}`).join('\n\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([content],{type:'text/markdown'}));
    a.download = 'ocr_result.md'; a.click(); URL.revokeObjectURL(a.href);
  };

  if (!current) return (
    <div className="fade-in" style={{padding:32,textAlign:'center',color:'var(--fg3)'}}>
      暂无识别结果<br />
      <button className="btn btn-sm btn-s" style={{marginTop:16}} onClick={goBack}>← 返回</button>
    </div>
  );

  return (
    <div className="fade-in">
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:24,flexWrap:'wrap',gap:12}}>
        <div style={{display:'flex',alignItems:'center',gap:12}}>
          <button className="btn btn-sm btn-s" onClick={goBack}>← 返回</button>
          <h2 style={{fontSize:18,fontWeight:600}}>识别结果</h2>
        </div>
        <button className="btn btn-sm btn-s" onClick={downloadMD}>
          <span className="with-ic"><Icon name="download" size={14} />下载全部 MD</span>
        </button>
      </div>

      <div style={{display:'flex',alignItems:'center',justifyContent:'center',gap:12,marginBottom:20,flexWrap:'wrap'}}>
        <button className="btn btn-sm btn-s" disabled={idx<=0} onClick={()=>setIdx(i=>i-1)}>← 上一页</button>
        <div style={{display:'flex',gap:4,flexWrap:'wrap',justifyContent:'center'}}>
          {done.map((p,i)=>(
            <button key={p.id} onClick={()=>setIdx(i)} style={{
              width:32,height:32,borderRadius:6,border:'1px solid',fontSize:12,fontWeight:500,cursor:'pointer',
              borderColor:i===idx?'var(--gold)':'var(--border)',
              background:i===idx?'var(--bg4)':'transparent',
              color:i===idx?'var(--gold2)':'var(--fg3)',transition:'all .2s',
            }}>{pages.indexOf(p)+1}</button>
          ))}
        </div>
        <button className="btn btn-sm btn-s" disabled={idx>=done.length-1} onClick={()=>setIdx(i=>i+1)}>下一页 →</button>
      </div>

      <div className="card" style={{padding:32,minHeight:400}}>
        <div style={{fontSize:11,color:'var(--fg3)',marginBottom:16,fontWeight:500}}>{current.name}</div>
        <div style={{fontSize:14,lineHeight:1.75,color:'var(--fg)',whiteSpace:'pre-wrap',wordBreak:'break-word'}}>
          {current.result}
        </div>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════
// 学术研究站 PaperLabApp
// ═══════════════════════════════════════════════════════════════

const PA = `${API}/paper`;

// ── 工具函数 ──
const renderMd = (text) => {
  if (!text) return '';
  try {
    const html = marked.parse(text, {breaks: true, gfm: true});
    return html;
  } catch(e) { return text; }
};

{% endverbatim %}
{% verbatim %}
const typeset = (el) => {
  if (!el || !window.MathJax || !window.MathJax.typesetPromise) return;
  window.MathJax.typesetPromise([el]).catch(()=>{});
};

// ── Citation Chip 组件 ──
function CitationChip({cite, onClick}) {
  return (
    <span className="cite-chip" onClick={onClick} title={`跳转到: ${cite.cite_key}`}>
      <span style={{display:'inline-flex',alignItems:'center',gap:4}}>
        <Icon name="file" size={12} />
        {cite.lit_title ? cite.lit_title.slice(0,20) + (cite.lit_title.length>20?'…':'') : cite.file_ref}:L{cite.line_start}-{cite.line_end}
      </span>
    </span>
  );
}

// ── Markdown+MathJax 渲染器 ──
function MdRender({content, className='', style={}}) {
  const ref = useRef(null);
  const html = renderMd(content);
  useEffect(() => { if (ref.current) typeset(ref.current); }, [content]);
  return (
    <div ref={ref} className={className} style={style}
      dangerouslySetInnerHTML={{__html: html}} />
  );
}

// ── 文献阅读器（带行号、高亮、公式渲染）──
function LiteratureViewer({lit, highlightLines=null, onLineClick, onCreateNote}) {
  const containerRef = useRef(null);
  const [lines, setLines] = useState([]);
  const [selRange, setSelRange] = useState(null);

  useEffect(() => {
    if (!lit?.content) { setLines([]); return; }
    setLines(lit.content.split('\n'));
  }, [lit?.id, lit?.content]);

  useEffect(() => {
    if (containerRef.current) typeset(containerRef.current);
  }, [lines]);

  useEffect(() => {
    if (highlightLines && containerRef.current) {
      const el = containerRef.current.querySelector(`[data-line="${highlightLines[0]}"]`);
      if (el) el.scrollIntoView({behavior:'smooth', block:'center'});
    }
  }, [highlightLines]);

  if (!lit) return <div className="empty"><h3>选择文献开始阅读</h3></div>;

  const isHighlighted = (i) => {
    if (!highlightLines) return false;
    return i+1 >= highlightLines[0] && i+1 <= highlightLines[1];
  };

  return (
    <div ref={containerRef} className="pl-viewer" style={{paddingLeft:60}}>
      <div style={{marginBottom:20,paddingBottom:14,borderBottom:'1px solid var(--border)'}}>
        <h2 style={{fontFamily:'var(--serif)',fontSize:20,color:'var(--gold2)',marginBottom:4}}>{lit.title}</h2>
        {lit.authors && <div style={{fontSize:12,color:'var(--fg2)'}}>{lit.authors} {lit.year ? `(${lit.year})` : ''} {lit.journal ? `· ${lit.journal}` : ''}</div>}
        <div style={{display:'flex',gap:8,marginTop:8,flexWrap:'wrap'}}>
          <span style={{fontSize:10,padding:'2px 7px',borderRadius:4,background:'var(--bg4)',color:'var(--fg3)'}}>{lit.language === 'en' ? '英文' : lit.language === 'zh' ? '中文' : '混合'}</span>
          <span style={{fontSize:10,padding:'2px 7px',borderRadius:4,background:'var(--bg4)',color:'var(--fg3)'}}>{lit.total_lines} 行</span>
          {lit.is_indexed && <span style={{fontSize:10,padding:'2px 7px',borderRadius:4,background:'rgba(94,184,122,.15)',color:'var(--green)',display:'inline-flex',alignItems:'center',gap:4}}><Icon name="check" size={10} /> 已索引</span>}
        </div>
      </div>
      {lines.map((line, i) => {
        const lineNum = i + 1;
        const hl = isHighlighted(i);
        // Detect heading for structure
        const isH1 = line.startsWith('# ');
        const isH2 = line.startsWith('## ');
        const isH3 = line.startsWith('### ');
        return (
          <div key={i} data-line={lineNum} className={`pl-line-anchor${hl?' hl':''}`}
            style={{position:'relative', cursor: onLineClick ? 'pointer' : 'default'}}
            onClick={() => onLineClick && onLineClick(lineNum, line)}>
            <span className="pl-line-num" onClick={e => {
              e.stopPropagation();
              onCreateNote && onCreateNote(lineNum, lineNum, line);
            }}>{lineNum}</span>
            <MdRender content={line || '\u00A0'}
              className={isH1?'':isH2?'':isH3?'':''}
              style={{display:'block', minHeight:'1.5em'}} />
          </div>
        );
      })}
    </div>
  );
}

// ── Token 统计迷你面板 ──
function TokenMiniPanel({onRefresh}) {
  const [stats, setStats] = useState(null);
  const load = () => F(`${PA}/token-stats/`).then(setStats).catch(()=>{});
  useEffect(() => { load(); }, []);
  useEffect(() => { if(onRefresh) { onRefresh.current = load; } }, []);
  if (!stats) return null;
  return (
    <div style={{padding:'8px 12px',borderTop:'1px solid var(--border)',background:'var(--bg2)'}}>
      <div style={{display:'flex',justifyContent:'space-between',marginBottom:4}}>
        <span style={{fontSize:10,color:'var(--fg3)',letterSpacing:1}}>TOKEN 用量</span>
        <button onClick={load} style={{background:'none',color:'var(--fg3)',fontSize:9,padding:'1px 5px',border:'1px solid var(--border)',borderRadius:3,cursor:'pointer'}}>刷新</button>
      </div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:4}}>
        <div style={{background:'var(--bg3)',borderRadius:4,padding:'4px 6px',textAlign:'center'}}>
          <div style={{fontFamily:'var(--mono)',fontSize:13,color:'var(--gold2)',fontWeight:500}}>{((stats.total_tokens||0)/1000).toFixed(1)}K</div>
          <div style={{fontSize:9,color:'var(--fg3)'}}>总Token</div>
        </div>
        <div style={{background:'var(--bg3)',borderRadius:4,padding:'4px 6px',textAlign:'center'}}>
          <div style={{fontFamily:'var(--mono)',fontSize:13,color:'var(--cyan)',fontWeight:500}}>{stats.prompt_count||0}</div>
          <div style={{fontSize:9,color:'var(--fg3)'}}>提交次数</div>
        </div>
        <div style={{background:'var(--bg3)',borderRadius:4,padding:'4px 6px',textAlign:'center'}}>
          <div style={{fontFamily:'var(--mono)',fontSize:11,color:'var(--blue)',fontWeight:500}}>{((stats.daily_input||0)/1000).toFixed(1)}K</div>
          <div style={{fontSize:9,color:'var(--fg3)'}}>今日输入</div>
        </div>
        <div style={{background:'var(--bg3)',borderRadius:4,padding:'4px 6px',textAlign:'center'}}>
          <div style={{fontFamily:'var(--mono)',fontSize:11,color:'var(--green)',fontWeight:500}}>{((stats.daily_output||0)/1000).toFixed(1)}K</div>
          <div style={{fontSize:9,color:'var(--fg3)'}}>今日输出</div>
        </div>
      </div>
    </div>
  );
}

// ── 文献库 ──
function LiteratureLibrary({project, onOpenLit, onRefresh}) {
  const [lits, setLits] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({title:'',authors:'',year:'',journal:'',abstract:'',content:'',language:'zh'});
  const [ocrProjects, setOcrProjects] = useState([]);
  const [ocrForm, setOcrForm] = useState({ocr_project_id:'',title:'',authors:'',year:'',language:'en'});

  const load = () => {
    F(`${PA}/projects/${project.id}/literatures/`).then(setLits).catch(()=>{});
  };
  useEffect(() => { load(); }, [project.id]);

  const addLit = async () => {
    if (!form.title.trim()) return showAlert('请输入文献标题', '提示');
    setLoading(true);
    try {
      await P(`${PA}/projects/${project.id}/literatures/`, form);
      setShowAdd(false); setForm({title:'',authors:'',year:'',journal:'',abstract:'',content:'',language:'zh'});
      load(); onRefresh && onRefresh();
    } catch(e) { showAlert('添加失败: ' + e.message, '错误'); }
    setLoading(false);
  };

  const loadOcrProjects = () => {
    F(`${PA}/ocr-projects/`).then(setOcrProjects).catch(()=>{});
  };

  const importFromOcr = async () => {
    if (!ocrForm.ocr_project_id) return showAlert('请选择OCR项目', '提示');
    setLoading(true);
    try {
      await P(`${PA}/projects/${project.id}/literatures/import-ocr/`, ocrForm);
      setShowImport(false); load(); onRefresh && onRefresh();
    } catch(e) { showAlert('导入失败: ' + e.message, '错误'); }
    setLoading(false);
  };

  const deleteLit = async (id) => {
    const confirmed = await showConfirm('确认删除此文献？');
    if (!confirmed) return;
    try { await F(`${PA}/literatures/${id}/`, {method:'DELETE'}); load(); } catch(e) {}
  };

  const reindex = async (id, e) => {
    e.stopPropagation();
    try {
      await P(`${PA}/literatures/${id}/reindex/`, {});
      showAlert('正在重建索引，请稍候刷新', '提示');
    } catch(e) { showAlert('操作失败', '错误'); }
  };

  return (
    <div className="pl-fade">
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
        <h3 style={{fontFamily:'var(--serif)',fontSize:18}}>文献库</h3>
        <div style={{display:'flex',gap:8}}>
          <button className="btn btn-sm btn-s" onClick={() => { setShowImport(true); loadOcrProjects(); }}>
            <span style={{display:'inline-flex',alignItems:'center',gap:6}}>
              <Icon name="download" size={12} />
              从OCR导入
            </span>
          </button>
          <button className="btn btn-sm btn-p" onClick={() => setShowAdd(true)}>+ 添加文献</button>
        </div>
      </div>

      {lits.length === 0 ? (
        <div className="empty"><h3>暂无文献</h3><p>请添加文献或从OCR工作室导入</p></div>
      ) : lits.map(lit => (
        <div key={lit.id} className="card" style={{cursor:'pointer',marginBottom:10}}
          onClick={() => onOpenLit(lit)}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',gap:12}}>
            <div style={{flex:1}}>
              <div style={{fontFamily:'var(--serif)',fontSize:15,color:'var(--fg)',marginBottom:4}}>{lit.title}</div>
              {lit.authors && <div style={{fontSize:12,color:'var(--fg2)'}}>{lit.authors} {lit.year ? `(${lit.year})` : ''}</div>}
              <div style={{display:'flex',gap:6,marginTop:6,flexWrap:'wrap'}}>
                <span style={{fontSize:10,padding:'2px 6px',borderRadius:3,background:'var(--bg4)',color:'var(--fg3)'}}>{lit.source_type === 'ocr' ? 'OCR' : lit.source_type === 'manual' ? '手动' : '上传'}</span>
                <span style={{fontSize:10,padding:'2px 6px',borderRadius:3,background:'var(--bg4)',color:'var(--fg3)'}}>{lit.total_lines}行 / {lit.chunk_count}块</span>
                {lit.is_indexed ? <span style={{fontSize:10,padding:'2px 6px',borderRadius:3,background:'rgba(94,184,122,.15)',color:'var(--green)',display:'inline-flex',alignItems:'center',gap:4}}><Icon name="check" size={10} /> 已索引</span>
                  : <span style={{fontSize:10,padding:'2px 6px',borderRadius:3,background:'rgba(196,90,90,.15)',color:'var(--red)'}}>未索引</span>}
              </div>
            </div>
            <div style={{display:'flex',gap:6,flexShrink:0}}>
              {!lit.is_indexed && <button className="btn btn-sm btn-s" onClick={e => reindex(lit.id, e)}>建立索引</button>}
              <button className="btn btn-sm btn-s" onClick={e => { e.stopPropagation(); deleteLit(lit.id); }} style={{color:'var(--red)'}}>删除</button>
            </div>
          </div>
          <div style={{marginTop:8,fontFamily:'var(--mono)',fontSize:10,color:'var(--fg3)'}}>
            <span style={{display:'inline-flex',alignItems:'center',gap:6}}>
              <Icon name="link" size={11} />
              {lit.file_ref}
            </span>
          </div>
        </div>
      ))}

      {/* 添加文献对话框 */}
      {showAdd && (
        <div className="modal-ov" onClick={() => setShowAdd(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2>添加文献</h2>
            <div className="fg"><label>标题 *</label><input value={form.title} onChange={e=>setForm({...form,title:e.target.value})} placeholder="论文/书籍标题" /></div>
            <div className="g2">
              <div className="fg"><label>作者</label><input value={form.authors} onChange={e=>setForm({...form,authors:e.target.value})} /></div>
              <div className="fg"><label>年份</label><input value={form.year} onChange={e=>setForm({...form,year:e.target.value})} /></div>
            </div>
            <div className="fg"><label>期刊/来源</label><input value={form.journal} onChange={e=>setForm({...form,journal:e.target.value})} /></div>
            <div className="fg"><label>摘要</label><textarea value={form.abstract} onChange={e=>setForm({...form,abstract:e.target.value})} rows={3} /></div>
            <div className="fg"><label>语言</label>
              <select value={form.language} onChange={e=>setForm({...form,language:e.target.value})}>
                <option value="zh">中文</option><option value="en">英文</option><option value="mixed">混合</option>
              </select>
            </div>
            <div className="fg"><label>全文内容（Markdown格式，支持公式）</label>
              <textarea value={form.content} onChange={e=>setForm({...form,content:e.target.value})} rows={10} placeholder="粘贴论文全文（Markdown格式）..." />
            </div>
            <div style={{display:'flex',gap:8,justifyContent:'flex-end'}}>
              <button className="btn btn-s" onClick={() => setShowAdd(false)}>取消</button>
              <button className="btn btn-p" onClick={addLit} disabled={loading}>{loading?'添加中...':'添加文献'}</button>
            </div>
          </div>
        </div>
      )}

      {/* OCR导入对话框 */}
      {showImport && (
        <div className="modal-ov" onClick={() => setShowImport(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2>从OCR工作室导入</h2>
            <p style={{fontSize:12,color:'var(--fg2)',marginBottom:12}}>选择已完成OCR的项目，系统将自动合并所有页面内容并建立索引</p>
            <div className="fg"><label>OCR项目 *</label>
              <select value={ocrForm.ocr_project_id} onChange={e=>setOcrForm({...ocrForm,ocr_project_id:e.target.value})}>
                <option value="">-- 选择OCR项目 --</option>
                {ocrProjects.filter(p=>p.can_import).map(p => (
                  <option key={p.id} value={p.id}>{p.name} ({p.done_pages}/{p.total_pages}页)</option>
                ))}
              </select>
            </div>
            <div className="fg"><label>文献标题（留空则使用文件名）</label><input value={ocrForm.title} onChange={e=>setOcrForm({...ocrForm,title:e.target.value})} /></div>
            <div className="g2">
              <div className="fg"><label>作者</label><input value={ocrForm.authors} onChange={e=>setOcrForm({...ocrForm,authors:e.target.value})} /></div>
              <div className="fg"><label>年份</label><input value={ocrForm.year} onChange={e=>setOcrForm({...ocrForm,year:e.target.value})} /></div>
            </div>
            <div className="fg"><label>语言</label>
              <select value={ocrForm.language} onChange={e=>setOcrForm({...ocrForm,language:e.target.value})}>
                <option value="en">英文</option><option value="zh">中文</option><option value="mixed">混合</option>
              </select>
            </div>
            <div style={{display:'flex',gap:8,justifyContent:'flex-end'}}>
              <button className="btn btn-s" onClick={() => setShowImport(false)}>取消</button>
              <button className="btn btn-p" onClick={importFromOcr} disabled={loading}>{loading?'导入中...':'导入文献'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 阅读台：文献+笔记 双栏 ──
function ReadingDesk({project, lit, onCiteJump, user}) {
  const [notes, setNotes] = useState([]);
  const [hlLines, setHlLines] = useState(null);
  const [noteModal, setNoteModal] = useState(null);
  const [noteForm, setNoteForm] = useState({content:'',note_type:'annotation',title:''});
  const [litDetail, setLitDetail] = useState(null);

  useEffect(() => {
    if (lit) {
      F(`${PA}/literatures/${lit.id}/`).then(setLitDetail).catch(()=>{});
      F(`${PA}/projects/${project.id}/notes/`).then(ns => setNotes(ns.filter(n=>n.lit_id===lit.id))).catch(()=>{});
    }
  }, [lit?.id]);

  const openNote = (lineStart, lineEnd, text) => {
    setNoteModal({lineStart, lineEnd, text});
    setNoteForm({content:'', note_type:'annotation', title:''});
  };

  const saveNote = async () => {
    if (!noteForm.content.trim()) return;
    try {
      await P(`${PA}/projects/${project.id}/notes/`, {
        lit_id: lit.id,
        note_type: noteForm.note_type,
        title: noteForm.title,
        content: noteForm.content,
        cited_line_start: noteModal.lineStart,
        cited_line_end: noteModal.lineEnd,
        cited_text: noteModal.text,
      });
      setNoteModal(null);
      F(`${PA}/projects/${project.id}/notes/`).then(ns => setNotes(ns.filter(n=>n.lit_id===lit.id)));
    } catch(e) { showAlert('保存失败', '错误'); }
  };

  const deleteNote = async (id) => {
    const confirmed = await showConfirm('删除此笔记？');
    if (!confirmed) return;
    try {
      await F(`${PA}/notes/${id}/`, {method:'DELETE'});
      setNotes(ns => ns.filter(n=>n.id!==id));
    } catch(e) {}
  };

  const NOTE_TYPE_LABELS = {annotation:'标注',summary:'摘要',comment:'评论',question:'疑问',insight:'洞见',connection:'关联'};
  const NOTE_COLORS = {annotation:'var(--gold)',summary:'var(--blue)',comment:'var(--fg2)',question:'var(--cyan)',insight:'var(--green)',connection:'var(--purple)'};

  if (!lit) return (
    <div className="empty" style={{paddingTop:80}}>
      <h3>请先选择文献</h3>
      <p>从文献库中选择一篇文献开始阅读</p>
    </div>
  );

  return (
    <div className="pl-split">
      {/* 左：文献内容 */}
      <div className="pl-lit-panel">
        <div style={{padding:'8px 16px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',gap:8,background:'var(--bg2)',flexShrink:0}}>
          <span style={{fontSize:12,color:'var(--fg2)',flex:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{lit.title}</span>
          {hlLines && (
            <span className="cite-chip" style={{cursor:'default'}}>L{hlLines[0]}-{hlLines[1]}</span>
          )}
          {hlLines && <button className="btn btn-sm btn-s" onClick={() => setHlLines(null)}>清除高亮</button>}
        </div>
        <LiteratureViewer
          lit={litDetail}
          highlightLines={hlLines}
          onLineClick={(lineNum, text) => openNote(lineNum, lineNum, text)}
          onCreateNote={openNote}
        />
      </div>

      {/* 右：笔记面板 */}
      <div className="pl-side-panel">
        <div style={{padding:'12px 14px',borderBottom:'1px solid var(--border)',fontWeight:500,fontSize:13,color:'var(--fg2)'}}>
          <span style={{display:'inline-flex',alignItems:'center',gap:6}}>
            <Icon name="note" size={12} />
            笔记 ({notes.length})
          </span>
        </div>
        <div style={{flex:1,overflow:'auto',padding:12}}>
          {notes.length === 0 && (
            <div style={{textAlign:'center',padding:30,color:'var(--fg3)',fontSize:12}}>
              点击文献行号 (①) 创建标注笔记
            </div>
          )}
          {notes.map(note => (
            <div key={note.id} className={`pl-note-item ${note.note_type.slice(0,3)}`}
              style={{borderLeftColor: NOTE_COLORS[note.note_type]||'var(--gold)'}}
              onClick={() => note.cited_line_start && setHlLines([note.cited_line_start, note.cited_line_end||note.cited_line_start])}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:4}}>
                <span style={{fontSize:10,color:NOTE_COLORS[note.note_type]||'var(--gold)',fontWeight:500}}>{NOTE_TYPE_LABELS[note.note_type]||note.note_type}</span>
                <div style={{display:'flex',gap:4,alignItems:'center'}}>
                  {note.citation && <span className="cite-chip" style={{fontSize:9}}>{note.citation}</span>}
                  <button onClick={e=>{e.stopPropagation();deleteNote(note.id);}} style={{background:'none',border:'none',color:'var(--fg3)',cursor:'pointer',fontSize:12,padding:'0 2px'}}>
                    <Icon name="x" size={12} />
                  </button>
                </div>
              </div>
              {note.cited_text && <div style={{fontSize:11,color:'var(--fg3)',fontStyle:'italic',marginBottom:4,borderLeft:'2px solid var(--border2)',paddingLeft:6}}>{note.cited_text.slice(0,100)}</div>}
              <div style={{fontSize:12,color:'var(--fg)',lineHeight:1.5}}>{note.content}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 创建笔记对话框 */}
      {noteModal && (
        <div className="modal-ov" onClick={() => setNoteModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{maxWidth:480}}>
            <h2>创建笔记</h2>
            {noteModal.text && (
              <div style={{background:'var(--bg3)',borderRadius:6,padding:'8px 12px',marginBottom:12,fontSize:12,color:'var(--fg2)',borderLeft:'3px solid var(--gold)',fontStyle:'italic'}}>
                {noteModal.text.slice(0,200)}
              </div>
            )}
            <div style={{fontSize:11,color:'var(--fg3)',marginBottom:12,fontFamily:'var(--mono)'}}>
              引用位置: L{noteModal.lineStart}{noteModal.lineEnd !== noteModal.lineStart ? `-${noteModal.lineEnd}` : ''}
            </div>
            <div className="fg"><label>笔记类型</label>
              <select value={noteForm.note_type} onChange={e=>setNoteForm({...noteForm,note_type:e.target.value})}>
                {Object.entries(NOTE_TYPE_LABELS).map(([k,v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div className="fg"><label>标题（可选）</label><input value={noteForm.title} onChange={e=>setNoteForm({...noteForm,title:e.target.value})} /></div>
            <div className="fg"><label>笔记内容</label><textarea value={noteForm.content} onChange={e=>setNoteForm({...noteForm,content:e.target.value})} rows={5} placeholder="写下你的思考、理解或问题..." autoFocus /></div>
            <div style={{display:'flex',gap:8,justifyContent:'flex-end'}}>
              <button className="btn btn-s" onClick={() => setNoteModal(null)}>取消</button>
              <button className="btn btn-p" onClick={saveNote}>保存笔记</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 知识检索 ──
function KnowledgeSearch({project, onJumpToLit}) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(10);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await P(`${PA}/projects/${project.id}/search/`, {query, top_k: topK});
      setResults(res.results || []);
    } catch(e) { showAlert('检索失败: ' + e.message, '错误'); }
    setLoading(false);
  };

  const explore = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await P(`${PA}/projects/${project.id}/explore/`, {query, depth: 2});
      // Show as results
      const chunks = [];
      (res.layers||[]).forEach(l => l.chunks && chunks.push(...l.chunks.map(c => ({...c, score: c.score||0.5, preview: c.preview||''}))));
      setResults(chunks);
      if (res.summary) showAlert('探索摘要:\n\n' + res.summary, '探索结果');
    } catch(e) { showAlert('探索失败: ' + e.message, '错误'); }
    setLoading(false);
  };

  const maxScore = results.length > 0 ? Math.max(...results.map(r=>r.score||0)) : 1;

  return (
    <div className="pl-fade">
      <h3 style={{fontFamily:'var(--serif)',fontSize:18,marginBottom:16}}>知识检索</h3>
      <div style={{display:'flex',gap:8,marginBottom:16}}>
        <input value={query} onChange={e=>setQuery(e.target.value)}
          onKeyDown={e=>e.key==='Enter'&&search()}
          placeholder="输入研究问题或关键词..."
          style={{flex:1}} />
        <select value={topK} onChange={e=>setTopK(Number(e.target.value))} style={{width:80}}>
          {[5,10,20,30].map(k=><option key={k} value={k}>{k}条</option>)}
        </select>
              <button className="btn btn-p" onClick={search} disabled={loading} style={{display:'inline-flex',alignItems:'center',gap:6}}>
                <Icon name="search" size={12} />
                {loading?'检索中...':'检索'}
              </button>
              <button className="btn btn-s" onClick={explore} disabled={loading} title="深度探索：从查询出发，逐层展开相关概念"
                style={{display:'inline-flex',alignItems:'center',gap:6}}>
                <Icon name="map" size={12} />
                探索
              </button>
      </div>

      {results.length > 0 && (
        <div style={{marginBottom:8,fontSize:12,color:'var(--fg3)'}}>找到 {results.length} 个相关片段</div>
      )}

      {results.map((r, i) => (
        <div key={i} className="pl-search-result pl-fade" onClick={() => onJumpToLit && onJumpToLit(r.lit_id, r.line_start, r.line_end)}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:6}}>
            <div style={{flex:1}}>
              <div style={{fontFamily:'var(--serif)',fontSize:13,color:'var(--fg)',marginBottom:2}}>{r.lit_title}</div>
              {r.heading && <div style={{fontSize:10,color:'var(--gold-dim)',marginBottom:4}}>§ {r.heading}</div>}
            </div>
            <span className="cite-chip" style={{marginLeft:8,flexShrink:0}}>{r.cite_key}</span>
          </div>
          <div style={{fontSize:12,color:'var(--fg2)',lineHeight:1.6}}>{r.preview}</div>
          <div className="score-bar" style={{marginTop:8}}>
            <div className="score-fill" style={{width:`${Math.round((r.score/maxScore)*100)}%`}} />
          </div>
          <div style={{display:'flex',justify:'space-between',marginTop:4,gap:8}}>
            <span style={{fontSize:10,color:'var(--fg3)',fontFamily:'var(--mono)'}}>{r.cite_key}</span>
            <span style={{fontSize:10,color:'var(--fg3)'}}>{r.chunk_type}</span>
          </div>
        </div>
      ))}

      {!loading && results.length === 0 && query && (
        <div className="empty"><h3>未找到结果</h3><p>尝试换一个查询词，或先确认文献已建立索引</p></div>
      )}
    </div>
  );
}

// ── 研究讨论 ──
function ResearchChat({project, user, onTokenRefresh}) {
  const [convs, setConvs] = useState([]);
  const [curConv, setCurConv] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const [inp, setInp] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');
  const [curCitations, setCurCitations] = useState([]);
  const [retrieving, setRetrieving] = useState(false);
  const msgEndRef = useRef(null);
  const msgRef = useRef(null);

  useEffect(() => { loadConvs(); }, [project.id]);
  useEffect(() => { msgEndRef.current?.scrollIntoView({behavior:'smooth'}); }, [msgs, streamText]);
  useEffect(() => {
    if (curConv) {
      F(`${PA}/conversations/${curConv.id}/`).then(d => { setMsgs(d.messages || []); }).catch(()=>{});
    }
  }, [curConv?.id]);

  useEffect(() => {
    if (msgRef.current) typeset(msgRef.current);
  }, [msgs, streamText]);

  const loadConvs = () => {
    F(`${PA}/projects/${project.id}/conversations/`).then(setConvs).catch(()=>{});
  };

  const newConv = async () => {
    const c = await P(`${PA}/projects/${project.id}/conversations/`, {title:'新对话'});
    setCurConv(c); setMsgs([]); loadConvs();
  };

  const send = async () => {
    if (!inp.trim() || streaming) return;
    if (!curConv) { showAlert('请先创建对话', '提示'); return; }
    const m = inp.trim(); setInp('');
    setMsgs(prev => [...prev, {role:'user', content:m, citations:[]}]);
    setStreaming(true); setStreamText(''); setCurCitations([]); setRetrieving(true);

    const token = localStorage.getItem('mf_token');
    const hdrs = {'Content-Type':'application/json', 'Authorization': `Token ${token}`};

    try {
      const resp = await fetch(`${PA}/conversations/${curConv.id}/chat/`, {
        method:'POST', headers:hdrs, body:JSON.stringify({message:m})
      });
      if (!resp.ok) throw new Error(await resp.text());
      const reader = resp.body.getReader(); const dec = new TextDecoder();
      let buf=''; let full=''; let cites=[];
      while(true) {
        const {done, value} = await reader.read(); if(done) break;
        buf += dec.decode(value, {stream:true});
        const lns = buf.split('\n'); buf = lns.pop();
        for(const ln of lns) {
          if(!ln.startsWith('data: ')) continue;
          let ev; try{ ev=JSON.parse(ln.slice(6)); }catch{ continue; }
          if(ev.type==='retrieval_start') { setRetrieving(true); }
          else if(ev.type==='citations') { cites=ev.citations||[]; setCurCitations(cites); setRetrieving(false); }
          else if(ev.type==='chunk') { full+=ev.text; setStreamText(full); }
          else if(ev.type==='done') {
            setMsgs(prev => [...prev, {role:'assistant', content:full, citations:cites}]);
            setStreamText(''); onTokenRefresh && onTokenRefresh();
          }
        }
      }
    } catch(e) {
      setMsgs(prev=>[...prev,{role:'assistant',content:`错误: ${e.message}`,citations:[]}]);
      setStreamText('');
    }
    setStreaming(false); setRetrieving(false);
  };

  return (
    <div style={{display:'flex',height:'calc(100vh - 88px)',overflow:'hidden'}}>
      {/* 对话列表侧栏 */}
      <div style={{width:180,borderRight:'1px solid var(--border)',display:'flex',flexDirection:'column',flexShrink:0}}>
        <div style={{padding:'10px 8px',borderBottom:'1px solid var(--border)'}}>
          <button className="btn btn-p btn-sm" style={{width:'100%'}} onClick={newConv}>+ 新对话</button>
        </div>
        <div style={{flex:1,overflow:'auto',padding:'6px 4px'}}>
          {convs.map(c => (
            <div key={c.id} className={`ni${curConv?.id===c.id?' on':''}`} onClick={() => setCurConv(c)} style={{marginBottom:2}}>
              <i><Icon name="chat" size={12}/></i>
              <span style={{flex:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',fontSize:12}}>{c.title}</span>
              <span style={{fontSize:10,color:'var(--fg3)'}}>{c.msg_count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 聊天区 */}
      <div style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden'}}>
        {!curConv ? (
          <div className="empty" style={{paddingTop:80}}>
            <h3>开始研究对话</h3>
            <p>点击「新对话」，Agent 将基于您的文献库回答问题</p>
            <div style={{marginTop:16,padding:16,background:'var(--bg3)',borderRadius:8,maxWidth:400,margin:'16px auto 0',textAlign:'left'}}>
              <div style={{fontSize:12,color:'var(--gold2)',fontWeight:500,marginBottom:8,display:'inline-flex',alignItems:'center',gap:6}}>
                <Icon name="bolt" size={12} />
                零幻觉保证
              </div>
              <div style={{fontSize:12,color:'var(--fg2)',lineHeight:1.7}}>Agent 只从您导入的文献库中检索答案，每个观点必须附带精确引用（格式：文件名:L行号-行号），绝不凭空推测。</div>
            </div>
          </div>
        ) : (
          <>
            <div ref={msgRef} style={{flex:1,overflow:'auto',padding:16,display:'flex',flexDirection:'column',gap:12}}>
              {msgs.length === 0 && (
                <div style={{textAlign:'center',padding:40,color:'var(--fg3)'}}>
                  <div style={{marginBottom:8}}><Icon name="search" size={24} /></div>
                  <div>提问后，Agent 将自动检索文献库并给出有引用的回答</div>
                </div>
              )}
              {msgs.map((m, i) => (
                <div key={i} className={`cht-m${m.role==='user'?' u':' a'}`}>
                  <div className={`pl-msg-bubble ${m.role}`}>
                    {m.role === 'assistant' ? (
                      <MdRender content={m.content} />
                    ) : (
                      <span>{m.content}</span>
                    )}
                  </div>
                  {m.role === 'assistant' && m.citations && m.citations.length > 0 && (
                    <div style={{display:'flex',flexWrap:'wrap',gap:4,marginTop:6,paddingLeft:4}}>
                      <span style={{fontSize:10,color:'var(--fg3)'}}>引用:</span>
                      {m.citations.map((c,ci) => (
                        <CitationChip key={ci} cite={c} onClick={() => {}} />
                      ))}
                    </div>
                  )}
                </div>
              ))}

              {/* 检索状态 */}
              {retrieving && (
                <div style={{display:'flex',alignItems:'center',gap:8,color:'var(--fg3)',fontSize:12}}>
                  <div className="load" style={{padding:0}}/>
                  <span>正在检索文献库...</span>
                </div>
              )}

              {/* 当前引用预览 */}
              {curCitations.length > 0 && !retrieving && (
                <div style={{padding:'8px 12px',background:'rgba(90,138,196,.08)',borderRadius:6,border:'1px solid rgba(90,138,196,.2)'}}>
                <div style={{fontSize:10,color:'var(--blue)',marginBottom:6,display:'inline-flex',alignItems:'center',gap:6}}>
                  <Icon name="link" size={11} />
                  检索到的文献片段
                </div>
                  <div style={{display:'flex',flexWrap:'wrap',gap:4}}>
                    {curCitations.map((c,i) => <CitationChip key={i} cite={c} />)}
                  </div>
                </div>
              )}

              {/* 流式输出 */}
              {streamText && (
                <div className="cht-m a">
                  <div className="pl-msg-bubble assistant">
                    <MdRender content={streamText} />
                    <span style={{display:'inline-block',width:6,height:14,background:'var(--gold)',marginLeft:2,verticalAlign:'middle',animation:'blink 1s infinite'}} />
                  </div>
                </div>
              )}
              <div ref={msgEndRef} />
            </div>

            <div style={{padding:'10px 14px',borderTop:'1px solid var(--border)',display:'flex',gap:8}}>
              <textarea value={inp} onChange={e=>setInp(e.target.value)}
                onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}}}
                placeholder="提问（回车发送，Shift+回车换行）&#10;例：这些文献对XX问题的核心观点是什么？"
                style={{flex:1,resize:'none',minHeight:64,maxHeight:120,fontSize:13,lineHeight:1.5}} />
              <button className={`btn btn-p${streaming?' generating':''}`} onClick={send} disabled={streaming} style={{alignSelf:'flex-end',padding:'10px 16px'}}>
                {streaming ? '...' : '发送'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ── 写作台 ──
function WritingDesk({project, user, onTokenRefresh}) {
  const [drafts, setDrafts] = useState([]);
  const [curDraft, setCurDraft] = useState(null);
  const [content, setContent] = useState('');
  const [preview, setPreview] = useState(false);
  const [assistInp, setAssistInp] = useState('');
  const [assisting, setAssisting] = useState(false);
  const [assistResult, setAssistResult] = useState('');
  const [citations, setCitations] = useState([]);
  const [dirty, setDirty] = useState(false);
  const previewRef = useRef(null);

  useEffect(() => { loadDrafts(); }, [project.id]);
  useEffect(() => { if(preview && previewRef.current) typeset(previewRef.current); }, [preview, content]);

  const loadDrafts = () => {
    F(`${PA}/projects/${project.id}/drafts/`).then(setDrafts).catch(()=>{});
  };

  const newDraft = async () => {
    const title = prompt('草稿标题:');
    if (!title?.trim()) return;
    const d = await P(`${PA}/projects/${project.id}/drafts/`, {title: title.trim()});
    setCurDraft(d); setContent(''); setDirty(false); loadDrafts();
  };

  const selectDraft = async (d) => {
    const full = await F(`${PA}/drafts/${d.id}/`);
    setCurDraft(full); setContent(full.content||''); setDirty(false);
  };

  const saveDraft = async () => {
    if (!curDraft) return;
    await U(`${PA}/drafts/${curDraft.id}/`, {content});
    setDirty(false);
  };

  const requestAssist = async () => {
    if (!curDraft || !assistInp.trim()) return;
    setAssisting(true); setAssistResult(''); setCitations([]);

    const token = localStorage.getItem('mf_token');
    const hdrs = {'Content-Type':'application/json','Authorization':`Token ${token}`};
    try {
      const resp = await fetch(`${PA}/drafts/${curDraft.id}/assist/`, {
        method:'POST', headers:hdrs,
        body:JSON.stringify({instruction:assistInp, section_context:content.slice(-800)})
      });
      if (!resp.ok) throw new Error(await resp.text());
      const reader = resp.body.getReader(); const dec = new TextDecoder();
      let buf=''; let full='';
      while(true) {
        const {done, value} = await reader.read(); if(done) break;
        buf += dec.decode(value,{stream:true});
        const lns = buf.split('\n'); buf = lns.pop();
        for(const ln of lns) {
          if(!ln.startsWith('data: ')) continue;
          let ev; try{ ev=JSON.parse(ln.slice(6)); }catch{ continue; }
          if(ev.type==='citations') { setCitations(ev.citations||[]); }
          else if(ev.type==='chunk') { full+=ev.text; setAssistResult(full); }
          else if(ev.type==='done') { onTokenRefresh && onTokenRefresh(); }
        }
      }
    } catch(e) { setAssistResult('错误: ' + e.message); }
    setAssisting(false);
  };

  const insertResult = () => {
    if (!assistResult) return;
    setContent(c => c + '\n\n' + assistResult);
    setAssistResult(''); setCitations([]); setDirty(true);
  };

  return (
    <div style={{display:'flex',height:'calc(100vh - 88px)',overflow:'hidden'}}>
      {/* 草稿列表 */}
      <div style={{width:180,borderRight:'1px solid var(--border)',display:'flex',flexDirection:'column',flexShrink:0}}>
        <div style={{padding:'10px 8px',borderBottom:'1px solid var(--border)'}}>
          <button className="btn btn-p btn-sm" style={{width:'100%'}} onClick={newDraft}>+ 新草稿</button>
        </div>
        <div style={{flex:1,overflow:'auto',padding:'6px 4px'}}>
          {drafts.map(d => (
            <div key={d.id} className={`ni${curDraft?.id===d.id?' on':''}`} onClick={()=>selectDraft(d)} style={{marginBottom:2}}>
              <i><Icon name="pen" size={12}/></i>
              <span style={{flex:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',fontSize:12}}>{d.title}</span>
              <span style={{fontSize:10,color:'var(--fg3)'}}>{d.word_count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 写作区 */}
      {!curDraft ? (
        <div className="empty" style={{flex:1,paddingTop:80}}>
          <h3>写作台</h3>
          <p>创建或选择草稿，AI 辅助写作将自动附带文献引用</p>
        </div>
      ) : (
        <div style={{flex:1,display:'flex',overflow:'hidden'}}>
          {/* 编辑器 */}
          <div style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden'}}>
            <div style={{padding:'8px 14px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',gap:8,background:'var(--bg2)',flexShrink:0}}>
              <span style={{flex:1,fontSize:13,fontWeight:500}}>{curDraft.title}</span>
              {dirty && <span style={{fontSize:11,color:'var(--gold)'}}>● 未保存</span>}
              <button className="btn btn-sm btn-s" onClick={() => setPreview(p=>!p)}>{preview?'编辑':'预览'}</button>
              <button className="btn btn-sm btn-p" onClick={saveDraft}>保存</button>
            </div>
            {preview ? (
              <div ref={previewRef} className="pl-viewer" style={{flex:1,overflow:'auto',padding:24}}>
                <MdRender content={content} />
              </div>
            ) : (
              <textarea className="pl-draft-ed" style={{flex:1,borderRadius:0,border:'none',borderBottom:'1px solid var(--border)'}}
                value={content} onChange={e=>{setContent(e.target.value);setDirty(true);}}
                placeholder="在此写作... 支持 Markdown 和 LaTeX 公式（$ ... $ 或 $$ ... $$）" />
            )}
          </div>

          {/* AI辅助侧栏 */}
          <div className="pl-side-panel" style={{borderLeft:'1px solid var(--border)'}}>
            <div style={{padding:'12px 14px',borderBottom:'1px solid var(--border)',fontSize:13,fontWeight:500,color:'var(--fg2)'}}>
              <span style={{display:'inline-flex',alignItems:'center',gap:6}}>
                <Icon name="bot" size={13} />
                AI写作辅助
              </span>
            </div>
            <div style={{flex:1,overflow:'auto',padding:12}}>
              <div style={{fontSize:12,color:'var(--fg3)',marginBottom:12,lineHeight:1.6}}>
                AI 将从文献库检索相关内容，生成带精确引用的写作建议
              </div>
              <textarea value={assistInp} onChange={e=>setAssistInp(e.target.value)}
                placeholder="例：分析XX方法的优缺点，或：概述目前研究现状..."
                style={{width:'100%',minHeight:80,fontSize:12,resize:'vertical',marginBottom:8}} />
              <button className={`btn btn-p btn-sm${assisting?' generating':''}`} onClick={requestAssist} disabled={assisting} style={{width:'100%',marginBottom:12}}>
                {assisting ? '生成中...' : '生成带引用的内容'}
              </button>

              {citations.length > 0 && (
                <div style={{marginBottom:10}}>
                  <div style={{fontSize:10,color:'var(--fg3)',marginBottom:4}}>检索到的引用:</div>
                  <div style={{display:'flex',flexWrap:'wrap',gap:4}}>
                    {citations.map((c,i) => <CitationChip key={i} cite={c} />)}
                  </div>
                </div>
              )}

              {assistResult && (
                <div>
                  <div style={{fontSize:10,color:'var(--green)',marginBottom:6,display:'inline-flex',alignItems:'center',gap:4}}><Icon name="check" size={10} /> 生成结果</div>
                  <div style={{background:'var(--bg3)',borderRadius:6,padding:10,fontSize:12,lineHeight:1.6,marginBottom:8,maxHeight:300,overflow:'auto',color:'var(--fg)'}}>
                    <MdRender content={assistResult} />
                  </div>
                  <button className="btn btn-s btn-sm" style={{width:'100%'}} onClick={insertResult}>↓ 插入到草稿</button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 启发灯塔 ──
function IdeaLighthouse({project, user, onTokenRefresh}) {
  const [ideas, setIdeas] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [focusQuery, setFocusQuery] = useState('');

  const IDEA_LABELS = {gap:'研究空白',contradiction:'文献矛盾',extension:'扩展方向',method:'方法创新',connection:'跨领域',hypothesis:'研究假设'};
  const IDEA_COLORS = {gap:'var(--cyan)',contradiction:'var(--red)',extension:'var(--green)',method:'var(--gold)',connection:'var(--purple)',hypothesis:'var(--blue)'};

  useEffect(() => { loadIdeas(); }, [project.id]);

  const loadIdeas = () => {
    F(`${PA}/projects/${project.id}/ideas/`).then(setIdeas).catch(()=>{});
  };

  const generate = async () => {
    setGenerating(true);
    try {
      const res = await P(`${PA}/projects/${project.id}/ideas/generate/`, {focus_query: focusQuery});
      setIdeas(prev => [...(res.ideas||[]).map(i=>({...i})), ...prev]);
      onTokenRefresh && onTokenRefresh();
    } catch(e) { showAlert('生成失败: ' + e.message, '错误'); }
    setGenerating(false);
  };

  const deleteIdea = async (id) => {
    try {
      await F(`${PA}/ideas/${id}/`, {method:'DELETE'});
      setIdeas(prev => prev.filter(i=>i.id!==id));
    } catch(e) {}
  };

  const starIdea = async (id, starred) => {
    try {
      await U(`${PA}/ideas/${id}/`, {is_starred: !starred});
      setIdeas(prev => prev.map(i => i.id===id ? {...i,is_starred:!starred} : i));
    } catch(e) {}
  };

  return (
    <div className="pl-fade">
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
        <h3 style={{fontFamily:'var(--serif)',fontSize:18}}>启发灯塔</h3>
        <span style={{fontSize:12,color:'var(--fg3)'}}>基于文献库的研究灵感（必须有文献依据）</span>
      </div>

      <div className="card" style={{marginBottom:20,borderColor:'var(--gold-dim)'}}>
        <div style={{fontSize:13,color:'var(--gold2)',fontWeight:500,marginBottom:8,display:'inline-flex',alignItems:'center',gap:6}}>
          <Icon name="alert" size={12} />
          设计原则
        </div>
        <div style={{fontSize:12,color:'var(--fg2)',lineHeight:1.7}}>
          启发灯塔的所有灵感均来自您的文献库，每条灵感必须附带具体的文献依据。Agent 不会天马行空，只会在现有文献基础上发现研究机会。
        </div>
      </div>

      <div style={{display:'flex',gap:8,marginBottom:20}}>
        <input value={focusQuery} onChange={e=>setFocusQuery(e.target.value)}
          placeholder="聚焦方向（留空则基于整个项目）..."
          style={{flex:1}} />
        <button className={`btn btn-p${generating?' generating':''}`} onClick={generate} disabled={generating}
          style={{display:'inline-flex',alignItems:'center',gap:6}}>
          <Icon name="spark" size={12} />
          {generating ? '分析中...' : '生成灵感'}
        </button>
      </div>

      {ideas.length === 0 && !generating && (
        <div className="empty"><h3>暂无灵感</h3><p>点击「生成灵感」，Agent 将分析文献库寻找研究机会</p></div>
      )}

      {ideas.map(idea => (
        <div key={idea.id} className={`pl-idea-card ${idea.idea_type}`}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:8}}>
            <div>
              <span style={{fontSize:10,padding:'2px 7px',borderRadius:4,background:`rgba(128,128,128,.15)`,color:IDEA_COLORS[idea.idea_type]||'var(--fg2)',fontWeight:500,marginRight:6}}>
                {IDEA_LABELS[idea.idea_type]||idea.idea_type}
              </span>
              <span style={{fontFamily:'var(--serif)',fontSize:15,color:'var(--fg)'}}>{idea.title}</span>
            </div>
            <div style={{display:'flex',gap:6,flexShrink:0}}>
              <button onClick={() => starIdea(idea.id, idea.is_starred)} style={{background:'none',border:'none',cursor:'pointer',color:idea.is_starred?'var(--gold)':'var(--fg3)'}}>
                <Icon name="star" size={14} style={{opacity: idea.is_starred ? 1 : 0.4}} />
              </button>
              <button onClick={() => deleteIdea(idea.id)} style={{background:'none',border:'none',cursor:'pointer',fontSize:13,color:'var(--fg3)'}}>
                <Icon name="x" size={12} />
              </button>
            </div>
          </div>
          <div style={{fontSize:13,color:'var(--fg2)',lineHeight:1.7,marginBottom:8}}>{idea.description}</div>
          {idea.evidence_summary && (
            <div style={{fontSize:11,color:'var(--fg3)',borderTop:'1px solid var(--border)',paddingTop:8,marginTop:4,lineHeight:1.6}}>
              <span style={{color:'var(--gold-dim)'}}>文献依据: </span>
              {idea.evidence_summary}
            </div>
          )}
          {idea.evidence_chunks && idea.evidence_chunks.length > 0 && (
            <div style={{display:'flex',flexWrap:'wrap',gap:4,marginTop:6}}>
              {idea.evidence_chunks.map((c,i) => (
                <span key={i} className="cite-chip">{c.cite}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── 项目笔记汇总 ──
function NotesOverview({project, onJumpToLit}) {
  const [notes, setNotes] = useState([]);
  const NOTE_TYPE_LABELS = {annotation:'标注',summary:'摘要',comment:'评论',question:'疑问',insight:'洞见',connection:'关联'};
  useEffect(() => {
    F(`${PA}/projects/${project.id}/notes/`).then(setNotes).catch(()=>{});
  }, [project.id]);

  return (
    <div className="pl-fade">
      <h3 style={{fontFamily:'var(--serif)',fontSize:18,marginBottom:16}}>研究笔记 ({notes.length})</h3>
      {notes.length === 0 && <div className="empty"><h3>暂无笔记</h3><p>在阅读台中点击行号创建标注</p></div>}
      {notes.map(note => (
        <div key={note.id} className="card" style={{marginBottom:10,cursor:'pointer'}}
          onClick={() => note.lit_id && onJumpToLit && onJumpToLit(note.lit_id, note.cited_line_start, note.cited_line_end)}>
          <div style={{display:'flex',justifyContent:'space-between',marginBottom:6}}>
            <div>
              <span style={{fontSize:11,color:'var(--gold-dim)',marginRight:8}}>{NOTE_TYPE_LABELS[note.note_type]||note.note_type}</span>
              {note.title && <span style={{fontSize:13,fontWeight:500}}>{note.title}</span>}
            </div>
            {note.citation && <span className="cite-chip">{note.citation}</span>}
          </div>
          {note.cited_text && <div style={{fontSize:11,color:'var(--fg3)',fontStyle:'italic',marginBottom:6,borderLeft:'2px solid var(--border2)',paddingLeft:6}}>{note.cited_text.slice(0,100)}</div>}
          <div style={{fontSize:13,color:'var(--fg)',lineHeight:1.6}}>{note.content}</div>
          <div style={{fontSize:10,color:'var(--fg3)',marginTop:6}}>{note.lit_title}</div>
        </div>
      ))}
    </div>
  );
}

// ── 主 PaperLabApp ──
function PaperLabApp({user, onLogout, onUpdateUser}) {
  const [v, setV] = useState('projects');
  const [projects, setProjects] = useState([]);
  const [curProject, setCurProject] = useState(null);
  const [curLit, setCurLit] = useState(null);
  const [hlLines, setHlLines] = useState(null);
  const [sbOpen, setSbOpen] = useState(false);
  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjForm, setNewProjForm] = useState({title:'',description:'',domain:'',research_questions:''});
  const tokenRefreshRef = useRef(null);

  useEffect(() => { loadProjects(); }, []);

  const loadProjects = () => {
    F(`${PA}/projects/`).then(setProjects).catch(()=>{});
  };

  const createProject = async () => {
    if (!newProjForm.title.trim()) return showAlert('请输入项目标题', '提示');
    try {
      const p = await P(`${PA}/projects/`, newProjForm);
      setShowNewProject(false);
      setNewProjForm({title:'',description:'',domain:'',research_questions:''});
      loadProjects();
    } catch(e) { showAlert('创建失败: ' + e.message, '错误'); }
  };

  const selectProject = (p) => {
    setCurProject(p); setCurLit(null); setHlLines(null); setV('library');
  };

  const openLit = (lit) => {
    setCurLit(lit); setHlLines(null); setV('reading');
  };

  const jumpToLit = (litId, lineStart, lineEnd) => {
    F(`${PA}/literatures/${litId}/`).then(lit => {
      setCurLit(lit);
      setHlLines(lineStart ? [lineStart, lineEnd || lineStart] : null);
      setV('reading');
    }).catch(()=>{});
  };

  const goTo = (view) => { setV(view); setSbOpen(false); };

  const tokenRefresh = () => {
    if (tokenRefreshRef.current) tokenRefreshRef.current();
    const token = localStorage.getItem('mf_token');
    F(`${API}/auth/me/`).then(me => { if(me.authenticated) onUpdateUser({...me, token}); }).catch(()=>{});
  };

  const NAV_GROUPS = [
    {
      label: '导航',
      items: [
        {id:'projects', icon:'grid', label:'研究项目'},
      ]
    },
    ...(curProject ? [{
      label: curProject.title,
      items: [
        {id:'library', icon:'book', label:'文献库'},
        {id:'reading', icon:'eye', label:'阅读台'},
        {id:'search', icon:'search', label:'知识检索'},
        {id:'chat', icon:'chat', label:'研究讨论'},
        {id:'notes', icon:'note', label:'研究笔记'},
        {id:'writing', icon:'pen', label:'写作台'},
        {id:'ideas', icon:'spark', label:'启发灯塔'},
      ]
    }] : []),
  ];

  const TOP_TITLES = {
    projects:'研究项目', library:'文献库', reading:'阅读台',
    search:'知识检索', chat:'研究讨论', notes:'研究笔记',
    writing:'写作台', ideas:'启发灯塔',
  };

  return (
    <div className="app">
      <div className={`sb-ov${sbOpen?' open':''}`} onClick={() => setSbOpen(false)} />
      <div className={`sb${sbOpen?' open':''}`}>
        <div className="sb-back" onClick={() => window.location.hash='#/'}>← 返回 MineAI</div>
        <div className="sb-hd"><h1>学术研究站</h1><p>零幻觉·精确引用·深度探索</p></div>
        <div className="sb-nav">
          {NAV_GROUPS.map(grp => (
            <div className="ns" key={grp.label}>
              <div className="ns-t">{grp.label}</div>
              {grp.items.map(item => (
                <div key={item.id} className={`ni${v===item.id?' on':''}`} onClick={() => goTo(item.id)}>
                  <i><Icon name={item.icon} size={14} /></i>{item.label}
                </div>
              ))}
            </div>
          ))}
        </div>
        <TokenMiniPanel onRefresh={tokenRefreshRef} />
        <div style={{padding:'6px 12px 10px'}}>
          <div style={{fontSize:11,color:'var(--fg3)',marginBottom:6,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',display:'flex',alignItems:'center',gap:6}}>
            <Icon name="user" size={14} />{displayName(user)}
          </div>
          <div style={{display:'flex',gap:6}}>
            <button onClick={onLogout} style={{flex:1,padding:'5px 8px',borderRadius:'var(--r)',background:'var(--bg4)',color:'var(--fg3)',border:'1px solid var(--border2)',fontSize:12,cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',gap:4}}>
              <Icon name="logout" size={13} />退出
            </button>
          </div>
        </div>
      </div>

      <div className="main">
        <div className="top">
          <button className="menu-btn" onClick={() => setSbOpen(o=>!o)}><Icon name="menu" size={18} /></button>
          <span className="top-t">{TOP_TITLES[v]||v}</span>
          {curProject && v!=='projects' && (
            <span className="top-b">{curProject.title}</span>
          )}
          {curLit && (v==='reading') && (
            <span style={{fontSize:11,color:'var(--fg3)',fontFamily:'var(--mono)',marginLeft:4}}>
              {curLit.file_ref || curLit.title?.slice(0,20)}
            </span>
          )}
        </div>

        <div className={`ct${v==='reading'||v==='chat'||v==='writing'?'':''}`} style={v==='reading'||v==='chat'||v==='writing'?{padding:0,overflow:'hidden'}:{}}>
          {/* 研究项目列表 */}
          {v === 'projects' && (
            <div className="pl-fade">
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:20}}>
                <h2 style={{fontFamily:'var(--serif)',fontSize:22}}>研究项目</h2>
                <button className="btn btn-p" onClick={() => setShowNewProject(true)}>+ 新建项目</button>
              </div>

              <div className="card" style={{marginBottom:20,borderColor:'var(--cyan)',background:'rgba(90,196,180,.05)'}}>
                <div style={{fontSize:13,color:'var(--cyan)',fontWeight:500,marginBottom:6,display:'inline-flex',alignItems:'center',gap:6}}>
                  <Icon name="search" size={12} />
                  学术研究站设计理念
                </div>
                <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:8,fontSize:12,color:'var(--fg2)'}}>
                  <div><Icon name="bolt" size={12} /> <b>零幻觉</b>：仅引用文献库中的真实内容</div>
                  <div><Icon name="link" size={12} /> <b>精确引用</b>：文件名:L行号-行号 可点击跳转</div>
                  <div><Icon name="map" size={12} /> <b>深度探索</b>：Agent 自动在知识迷宫中导航</div>
                  <div><Icon name="pen" size={12} /> <b>辅助写作</b>：每段内容自动附带文献依据</div>
                  <div><Icon name="file" size={12} /> <b>OCR绑定</b>：与OCR工作室深度集成</div>
                  <div><Icon name="spark" size={12} /> <b>启发灯塔</b>：基于文献的研究灵感</div>
                </div>
              </div>

              {projects.length === 0 ? (
                <div className="empty"><h3>暂无研究项目</h3><p>创建第一个研究项目，开始你的学术研究之旅</p></div>
              ) : (
                <div className="g2">
                  {projects.map(p => (
                    <div key={p.id} className="card" style={{cursor:'pointer',transition:'all .2s'}}
                      onClick={() => selectProject(p)}
                      onMouseEnter={e=>e.currentTarget.style.borderColor='var(--cyan)'}
                      onMouseLeave={e=>e.currentTarget.style.borderColor=''}>
                      <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start'}}>
                        <h3 style={{fontFamily:'var(--serif)',fontSize:16,color:'var(--gold2)'}}>{p.title}</h3>
                        <div style={{display:'flex',gap:6}}>
                          <span style={{fontSize:10,padding:'2px 6px',borderRadius:3,background:'rgba(90,196,180,.1)',color:'var(--cyan)'}}>{p.lit_count}篇文献</span>
                          <span style={{fontSize:10,padding:'2px 6px',borderRadius:3,background:'var(--bg4)',color:'var(--fg3)'}}>{p.note_count}条笔记</span>
                        </div>
                      </div>
                      {p.domain && <div style={{fontSize:12,color:'var(--blue)',marginTop:4}}># {p.domain}</div>}
                      {p.description && <div style={{fontSize:12,color:'var(--fg2)',marginTop:6,lineHeight:1.5}}>{p.description.slice(0,100)}</div>}
                      {p.research_questions && (
                        <div style={{fontSize:11,color:'var(--fg3)',marginTop:6,borderTop:'1px solid var(--border)',paddingTop:6}}>
                          研究问题: {p.research_questions.slice(0,80)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {showNewProject && (
                <div className="modal-ov" onClick={() => setShowNewProject(false)}>
                  <div className="modal" onClick={e => e.stopPropagation()}>
                    <h2>新建研究项目</h2>
                    <div className="fg"><label>项目标题 *</label><input value={newProjForm.title} onChange={e=>setNewProjForm({...newProjForm,title:e.target.value})} autoFocus /></div>
                    <div className="fg"><label>研究领域</label><input value={newProjForm.domain} onChange={e=>setNewProjForm({...newProjForm,domain:e.target.value})} placeholder="如：深度学习、材料科学..." /></div>
                    <div className="fg"><label>项目描述</label><textarea value={newProjForm.description} onChange={e=>setNewProjForm({...newProjForm,description:e.target.value})} rows={3} /></div>
                    <div className="fg"><label>核心研究问题</label><textarea value={newProjForm.research_questions} onChange={e=>setNewProjForm({...newProjForm,research_questions:e.target.value})} rows={4} placeholder="描述你要研究的核心问题，Agent 将基于此聚焦分析..." /></div>
                    <div style={{display:'flex',gap:8,justifyContent:'flex-end'}}>
                      <button className="btn btn-s" onClick={() => setShowNewProject(false)}>取消</button>
                      <button className="btn btn-p" onClick={createProject}>创建项目</button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 需要项目的视图 */}
          {!curProject && v !== 'projects' && (
            <div className="empty"><h3>请先选择研究项目</h3><button className="btn btn-p" onClick={()=>goTo('projects')}>选择项目</button></div>
          )}

          {curProject && v === 'library' && (
            <LiteratureLibrary project={curProject} onOpenLit={openLit} />
          )}

          {curProject && v === 'reading' && (
            <ReadingDesk project={curProject} lit={curLit} onCiteJump={jumpToLit} user={user} />
          )}

          {curProject && v === 'search' && (
            <KnowledgeSearch project={curProject} onJumpToLit={jumpToLit} />
          )}

          {curProject && v === 'chat' && (
            <ResearchChat project={curProject} user={user} onTokenRefresh={tokenRefresh} />
          )}

          {curProject && v === 'notes' && (
            <NotesOverview project={curProject} onJumpToLit={jumpToLit} />
          )}

          {curProject && v === 'writing' && (
            <WritingDesk project={curProject} user={user} onTokenRefresh={tokenRefresh} />
          )}

          {curProject && v === 'ideas' && (
            <IdeaLighthouse project={curProject} user={user} onTokenRefresh={tokenRefresh} />
          )}
        </div>
      </div>
    </div>
  );
}

{% endverbatim %}
{% verbatim %}
// ── 知识图谱 应用 ────────────────────────────────────────────────

const KG_API = `${API}/kg`;

// 节点类型颜色映射
const KG_NODE_COLORS = {
  concept: '#c9a86c',
  entity: '#5ac4b4',
  event: '#d49a5a',
  claim: '#5a8ac4',
  method: '#9a6ac4',
  result: '#5eb87a',
  character: '#c45a5a',
  paper: '#5ab4c4',
  place: '#a0b45a',
  term: '#c45aaa',
  memory: '#dbb97a',
};

const KG_NODE_LABELS = {
  concept:'概念', entity:'实体', event:'事件', claim:'论断',
  method:'方法', result:'结论', character:'人物', paper:'论文',
  place:'地点', term:'术语', memory:'记忆',
};

const KG_RELATION_LABELS = {
  supports:'支持', contradicts:'矛盾', causes:'导致', extends:'扩展',
  related_to:'相关', defines:'定义', exemplifies:'举例', cites:'引用',
  part_of:'组成', leads_to:'推导', opposes:'对立', has_method:'使用方法',
  has_result:'得出结论', is_a:'属于', instance_of:'实例化',
  precedes:'先于', follows:'后于',
};

// ── Cytoscape图谱可视化 ──────────────────────────────────────────

function KGCytoGraph({elements, onNodeClick, selectedNodeId}) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !window.cytoscape) return;

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = window.cytoscape({
      container: containerRef.current,
      elements: elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (ele) => ele.data('_color') || KG_NODE_COLORS[ele.data('type')] || '#888888',
            'label': 'data(label)',
            'color': '#e8e4df',
            'font-size': '11px',
            'font-family': 'Noto Sans SC, sans-serif',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': '4px',
            'width': (ele) => Math.max(18, 12 + (ele.data('importance') || 0.5) * 24),
            'height': (ele) => Math.max(18, 12 + (ele.data('importance') || 0.5) * 24),
            'border-width': 1.5,
            'border-color': (ele) => ele.data('_color') || KG_NODE_COLORS[ele.data('type')] || '#888888',
            'border-opacity': 0.6,
            'background-opacity': 0.85,
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-opacity': 1,
            'background-opacity': 1,
          }
        },
        {
          selector: 'edge',
          style: {
            'width': (ele) => Math.max(1, (ele.data('weight') || 1) * 1.5),
            'line-color': 'rgba(90,90,120,0.6)',
            'target-arrow-color': 'rgba(90,90,120,0.8)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(relation_label)',
            'font-size': '9px',
            'color': 'rgba(160,154,146,0.7)',
            'text-rotation': 'autorotate',
            'font-family': 'Noto Sans SC, sans-serif',
            'opacity': 0.8,
          }
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': 'var(--gold)',
            'target-arrow-color': 'var(--gold)',
            'opacity': 1,
          }
        }
      ],
      layout: {
        name: 'cose',
        animate: false,
        nodeRepulsion: 8000,
        idealEdgeLength: 100,
        gravity: 0.25,
        numIter: 1000,
      },
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    });

    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      if (onNodeClick) onNodeClick({
        id: node.id(),
        label: node.data('label'),
        type: node.data('type'),
        importance: node.data('importance'),
        description: node.data('description'),
        source_ref: node.data('source_ref'),
      });
    });

    cyRef.current = cy;

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [elements]);

  // 高亮选中节点
  useEffect(() => {
    if (!cyRef.current || !selectedNodeId) return;
    cyRef.current.$(':selected').unselect();
    cyRef.current.$(`#${selectedNodeId}`).select();
  }, [selectedNodeId]);

  return (
    <div ref={containerRef} style={{
      width:'100%', height:'100%',
      background:'var(--bg)',
      borderRadius:'var(--r)',
    }} />
  );
}

// ── 图谱项目列表 ──────────────────────────────────────────────────

function KGProjectList({onSelect}) {
  const [projects, setProjects] = useState([]);
  const [platformKG, setPlatformKG] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [cloning, setCloning] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [userProjects, platform] = await Promise.all([
        F(`${KG_API}/projects/`),
        fetch(`${KG_API}/platform/`).then(r=>r.json()),
      ]);
      setProjects(userProjects);
      // 构造平台图谱虚拟对象
      setPlatformKG({
        _platform: true,
        title: '平台功能图谱',
        description: '了解 MineAI 平台各应用的所有功能，只读',
        node_count: platform.nodes.length,
        edge_count: platform.edges.length,
      });
    } catch(e) {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const createProject = async () => {
    if (!newTitle.trim()) return;
    try {
      await P(`${KG_API}/projects/`, {title: newTitle.trim(), description: newDesc});
      setNewTitle(''); setNewDesc(''); setShowNew(false);
      load();
    } catch(e) { showAlert('创建失败', '错误'); }
  };

  const clonePlatform = async (e) => {
    e.stopPropagation();
    setCloning(true);
    try {
      const res = await P(`${KG_API}/platform/clone/`, {});
      if (res && res.id) { load(); showAlert(`已克隆为"${res.title}"，可在我的图谱中编辑`, '克隆成功'); }
    } catch(e) { showAlert('克隆失败', '错误'); }
    setCloning(false);
  };

  const deleteProject = async (id, e) => {
    e.stopPropagation();
    const confirmed = await showConfirm('确认删除图谱？此操作不可撤销');
    if (!confirmed) return;
    try {
      await fetch(`${KG_API}/projects/${id}/`, {
        method:'DELETE', headers:{'Authorization':`Token ${localStorage.getItem('mf_token')}`}
      });
      load();
    } catch(e) {}
  };

  if (loading) return <div className="load" style={{padding:40}}>加载中...</div>;

  return (
    <div style={{padding:24,maxWidth:700}}>
      {/* 平台内置图谱 */}
      {platformKG && (
        <div style={{marginBottom:24}}>
          <div style={{fontSize:11,color:'var(--fg3)',textTransform:'uppercase',letterSpacing:'.06em',marginBottom:10}}>
            平台内置
          </div>
          <div onClick={() => onSelect(platformKG)}
            style={{background:'var(--bg3)',border:'1px solid rgba(201,168,108,.4)',borderRadius:'var(--r)',
              padding:'14px 16px',cursor:'pointer',display:'flex',alignItems:'center',gap:12,
              transition:'border-color .15s'}}
            onMouseEnter={e=>e.currentTarget.style.borderColor='var(--gold)'}
            onMouseLeave={e=>e.currentTarget.style.borderColor='rgba(201,168,108,.4)'}
          >
            <div style={{width:40,height:40,borderRadius:8,background:'rgba(201,168,108,.15)',
              border:'1px solid rgba(201,168,108,.3)',display:'flex',alignItems:'center',
              justifyContent:'center',flexShrink:0}}>
              <Icon name="share-2" size={20} stroke={1.5} style={{color:'var(--gold)'}} />
            </div>
            <div style={{flex:1,minWidth:0}}>
              <div style={{fontWeight:600,marginBottom:3,display:'flex',alignItems:'center',gap:8}}>
                {platformKG.title}
                <span style={{fontSize:11,padding:'1px 6px',borderRadius:10,
                  background:'rgba(201,168,108,.15)',color:'var(--gold)',border:'1px solid rgba(201,168,108,.3)'}}>
                  只读
                </span>
              </div>
              <div style={{color:'var(--fg3)',fontSize:12}}>
                {platformKG.node_count} 功能节点 · {platformKG.edge_count} 关联关系
              </div>
            </div>
            <button onClick={clonePlatform} disabled={cloning}
              style={{background:'rgba(201,168,108,.12)',color:'var(--gold)',
                border:'1px solid rgba(201,168,108,.3)',borderRadius:6,
                padding:'5px 10px',fontSize:12,cursor:'pointer',whiteSpace:'nowrap'}}>
              {cloning ? '克隆中...' : '克隆到我的图谱'}
            </button>
          </div>
        </div>
      )}

      {/* 我的图谱 */}
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:12}}>
        <div style={{fontSize:11,color:'var(--fg3)',textTransform:'uppercase',letterSpacing:'.06em'}}>我的图谱</div>
        <button className="btn btn-p" onClick={() => setShowNew(true)}>+ 新建图谱</button>
      </div>

      {showNew && (
        <div style={{background:'var(--bg3)',border:'1px solid var(--border2)',borderRadius:'var(--r)',padding:16,marginBottom:16}}>
          <input value={newTitle} onChange={e=>setNewTitle(e.target.value)} placeholder="图谱名称" style={{width:'100%',marginBottom:8}} />
          <textarea value={newDesc} onChange={e=>setNewDesc(e.target.value)} placeholder="描述（可选）" style={{width:'100%',marginBottom:8,minHeight:60}} />
          <div style={{display:'flex',gap:8}}>
            <button className="btn btn-p" onClick={createProject}>创建</button>
            <button className="btn" onClick={() => setShowNew(false)}>取消</button>
          </div>
        </div>
      )}

      {projects.length === 0 && (
        <div style={{color:'var(--fg3)',textAlign:'center',padding:40,fontSize:13}}>
          暂无知识图谱，点击"新建图谱"开始构建，或克隆平台图谱进行编辑
        </div>
      )}

      <div style={{display:'flex',flexDirection:'column',gap:10}}>
        {projects.map(p => (
          <div key={p.id} onClick={() => onSelect(p)}
            style={{background:'var(--bg3)',border:'1px solid var(--border2)',borderRadius:'var(--r)',
              padding:'14px 16px',cursor:'pointer',transition:'border-color .15s',
              display:'flex',alignItems:'center',gap:12}}
            onMouseEnter={e=>e.currentTarget.style.borderColor='var(--gold)'}
            onMouseLeave={e=>e.currentTarget.style.borderColor='var(--border2)'}
          >
            <div style={{width:40,height:40,borderRadius:8,background:'rgba(201,168,108,.12)',
              border:'1px solid rgba(201,168,108,.25)',display:'flex',alignItems:'center',
              justifyContent:'center',flexShrink:0}}>
              <Icon name="share-2" size={20} stroke={1.5} style={{color:'var(--gold)'}} />
            </div>
            <div style={{flex:1,minWidth:0}}>
              <div style={{fontWeight:600,marginBottom:3}}>{p.title}</div>
              <div style={{color:'var(--fg3)',fontSize:12}}>
                {p.source_app !== 'manual' && <span style={{marginRight:8}}>[{p.source_app}]</span>}
                {p.node_count} 节点 · {p.edge_count} 边 · {new Date(p.updated_at).toLocaleDateString()}
              </div>
            </div>
            <button onClick={(e) => deleteProject(p.id, e)}
              style={{background:'transparent',color:'var(--fg3)',padding:'4px 8px',fontSize:12}}>
              删除
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── 图谱可视化视图 ────────────────────────────────────────────────

function KGGraphView({kg}) {
  const isPlatform = kg && kg._platform === true;
  const [elements, setElements] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodePanel, setNodePanel] = useState(null);
  const [maxNodes, setMaxNodes] = useState(100);
  const [stats, setStats] = useState({nodes:0, edges:0});

  const loadGraph = async () => {
    setLoading(true);
    try {
      if (isPlatform) {
        const data = await fetch(`${KG_API}/platform/`).then(r=>r.json());
        // 平台图谱节点用 color 字段着色
        const els = [
          ...data.nodes.map(n => ({
            data: {
              ...n.data,
              // 用节点自带颜色覆盖
              _color: n.data.color,
            }
          })),
          ...data.edges,
        ];
        setElements(els);
        setStats({nodes: data.nodes.length, edges: data.edges.length});
      } else {
        const data = await F(`${KG_API}/projects/${kg.id}/graph/?max_nodes=${maxNodes}`);
        setElements(data.elements || []);
        setStats({nodes: data.node_count, edges: data.edge_count});
      }
    } catch(e) {}
    setLoading(false);
  };

  useEffect(() => { loadGraph(); }, [kg._platform ? 'platform' : kg.id, maxNodes]);

  const handleNodeClick = async (nodeInfo) => {
    setSelectedNode(nodeInfo.id);
    if (isPlatform) { setNodePanel(nodeInfo); return; }
    // 获取节点详情
    try {
      const detail = await F(`${KG_API}/projects/${kg.id}/nodes/${nodeInfo.id}/`);
      setNodePanel(detail);
    } catch(e) {
      setNodePanel(nodeInfo);
    }
  };

  return (
    <div style={{display:'flex',height:'100%',gap:0}}>
      {/* 图谱区域 */}
      <div style={{flex:1,position:'relative',minWidth:0}}>
        {loading && (
          <div style={{position:'absolute',top:16,left:'50%',transform:'translateX(-50%)',
            background:'var(--bg3)',padding:'6px 16px',borderRadius:20,zIndex:10,
            fontSize:12,color:'var(--fg2)'}}>加载中...</div>
        )}
        <div style={{position:'absolute',top:12,left:12,zIndex:10,display:'flex',gap:8,alignItems:'center'}}>
          <select value={maxNodes} onChange={e=>setMaxNodes(Number(e.target.value))}
            style={{padding:'4px 8px',fontSize:12,background:'var(--bg3)'}}>
            <option value={50}>50节点</option>
            <option value={100}>100节点</option>
            <option value={200}>200节点</option>
          </select>
          <button className="btn" style={{fontSize:12,padding:'4px 12px'}} onClick={loadGraph}>刷新</button>
          <span style={{fontSize:11,color:'var(--fg3)',background:'var(--bg3)',padding:'3px 8px',borderRadius:12}}>
            {stats.nodes} 节点 · {stats.edges} 边
          </span>
        </div>

        {/* 节点类型图例 */}
        <div style={{position:'absolute',bottom:12,left:12,zIndex:10,
          background:'rgba(8,8,11,.85)',borderRadius:'var(--r)',padding:'8px 12px',
          display:'flex',flexWrap:'wrap',gap:'4px 12px',maxWidth:320}}>
          {Object.entries(KG_NODE_COLORS).slice(0,8).map(([type, color]) => (
            <span key={type} style={{display:'flex',alignItems:'center',gap:4,fontSize:11,color:'var(--fg2)'}}>
              <span style={{width:8,height:8,borderRadius:'50%',background:color,display:'inline-block'}} />
              {KG_NODE_LABELS[type]}
            </span>
          ))}
        </div>

        {elements.length > 0 ? (
          <KGCytoGraph elements={elements} onNodeClick={handleNodeClick} selectedNodeId={selectedNode} />
        ) : (
          !loading && (
            <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'100%',color:'var(--fg3)'}}>
              暂无节点数据，请先提取知识
            </div>
          )
        )}
      </div>

      {/* 节点详情面板 */}
      {nodePanel && (
        <div style={{width:280,background:'var(--bg2)',borderLeft:'1px solid var(--border)',
          padding:16,overflowY:'auto',flexShrink:0}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
            <span style={{fontWeight:600,fontSize:14}}>{nodePanel.label}</span>
            <button onClick={() => setNodePanel(null)}
              style={{background:'transparent',color:'var(--fg3)',fontSize:16}}>×</button>
          </div>
          <div style={{display:'flex',gap:6,marginBottom:10}}>
            <span style={{fontSize:11,padding:'2px 8px',borderRadius:10,
              background:`${KG_NODE_COLORS[nodePanel.node_type]}22`,
              color: KG_NODE_COLORS[nodePanel.node_type]}}>
              {KG_NODE_LABELS[nodePanel.node_type]}
            </span>
            <span style={{fontSize:11,color:'var(--fg3)'}}>重要度 {(nodePanel.importance||0).toFixed(2)}</span>
          </div>
          {nodePanel.description && (
            <p style={{color:'var(--fg2)',fontSize:12,marginBottom:10,lineHeight:1.6}}>{nodePanel.description}</p>
          )}
          {nodePanel.source_ref && (
            <div style={{fontSize:11,color:'var(--gold)',marginBottom:10}}>来源: {nodePanel.source_ref}</div>
          )}
          {nodePanel.keywords && nodePanel.keywords.length > 0 && (
            <div style={{marginBottom:10}}>
              <div style={{fontSize:11,color:'var(--fg3)',marginBottom:4}}>关键词</div>
              <div style={{display:'flex',flexWrap:'wrap',gap:4}}>
                {nodePanel.keywords.map((k,i) => (
                  <span key={i} style={{fontSize:11,padding:'2px 6px',background:'var(--bg4)',borderRadius:10}}>{k}</span>
                ))}
              </div>
            </div>
          )}
          {nodePanel.out_edges && nodePanel.out_edges.length > 0 && (
            <div style={{marginBottom:10}}>
              <div style={{fontSize:11,color:'var(--fg3)',marginBottom:4}}>出边 ({nodePanel.out_edges.length})</div>
              {nodePanel.out_edges.map(e => (
                <div key={e.edge_id} style={{fontSize:11,color:'var(--fg2)',padding:'3px 0',
                  borderBottom:'1px solid var(--border)'}}>
                  <span style={{color:'var(--cyan)'}}>{e.relation_label}</span> → {e.target_label}
                </div>
              ))}
            </div>
          )}
          {nodePanel.in_edges && nodePanel.in_edges.length > 0 && (
            <div>
              <div style={{fontSize:11,color:'var(--fg3)',marginBottom:4}}>入边 ({nodePanel.in_edges.length})</div>
              {nodePanel.in_edges.map(e => (
                <div key={e.edge_id} style={{fontSize:11,color:'var(--fg2)',padding:'3px 0',
                  borderBottom:'1px solid var(--border)'}}>
                  {e.source_label} <span style={{color:'var(--orange)'}}>{e.relation_label}</span> →
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── 节点管理 ──────────────────────────────────────────────────────

function KGNodeManager({kg}) {
  const [nodes, setNodes] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('');
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [addLabel, setAddLabel] = useState('');
  const [addType, setAddType] = useState('concept');
  const [addDesc, setAddDesc] = useState('');
  const LIMIT = 30;

  const load = async () => {
    setLoading(true);
    try {
      let url = `${KG_API}/projects/${kg.id}/nodes/?limit=${LIMIT}&offset=${offset}`;
      if (search) url += `&q=${encodeURIComponent(search)}`;
      if (filterType) url += `&type=${filterType}`;
      const data = await F(url);
      setNodes(data.nodes || []);
      setTotal(data.total || 0);
    } catch(e) {}
    setLoading(false);
  };

  useEffect(() => { load(); }, [kg.id, offset, filterType]);
  useEffect(() => { setOffset(0); }, [search, filterType]);

  const addNode = async () => {
    if (!addLabel.trim()) return;
    try {
      await P(`${KG_API}/projects/${kg.id}/nodes/`, {
        label: addLabel.trim(), node_type: addType, description: addDesc,
      });
      setAddLabel(''); setAddDesc(''); setShowAdd(false);
      load();
    } catch(e) { showAlert('添加失败', '错误'); }
  };

  const deleteNode = async (id) => {
    const confirmed = await showConfirm('确认删除节点？相关边也会被删除');
    if (!confirmed) return;
    try {
      await fetch(`${KG_API}/projects/${kg.id}/nodes/${id}/`, {
        method:'DELETE', headers:{'Authorization':`Token ${localStorage.getItem('mf_token')}`}
      });
      load();
    } catch(e) {}
  };

  return (
    <div style={{padding:20,height:'100%',display:'flex',flexDirection:'column'}}>
      <div style={{display:'flex',gap:8,marginBottom:16,flexWrap:'wrap',alignItems:'center'}}>
        <input value={search} onChange={e=>setSearch(e.target.value)}
          onKeyDown={e=>e.key==='Enter'&&load()}
          placeholder="搜索节点..." style={{flex:1,minWidth:160}} />
        <select value={filterType} onChange={e=>setFilterType(e.target.value)}
          style={{padding:'8px',background:'var(--bg3)',fontSize:13}}>
          <option value="">所有类型</option>
          {Object.entries(KG_NODE_LABELS).map(([k,v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <button className="btn" onClick={load} style={{fontSize:12}}>搜索</button>
        <button className="btn btn-p" style={{fontSize:12}}
          onClick={() => setShowAdd(!showAdd)}>+ 添加节点</button>
      </div>

      {showAdd && (
        <div style={{background:'var(--bg3)',borderRadius:'var(--r)',border:'1px solid var(--border2)',
          padding:14,marginBottom:14}}>
          <div style={{display:'flex',gap:8,marginBottom:8}}>
            <input value={addLabel} onChange={e=>setAddLabel(e.target.value)} placeholder="节点标签" style={{flex:1}} />
            <select value={addType} onChange={e=>setAddType(e.target.value)}
              style={{padding:'8px',background:'var(--bg3)',fontSize:13}}>
              {Object.entries(KG_NODE_LABELS).map(([k,v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <textarea value={addDesc} onChange={e=>setAddDesc(e.target.value)} placeholder="描述（可选）"
            style={{width:'100%',marginBottom:8,minHeight:50}} />
          <div style={{display:'flex',gap:8}}>
            <button className="btn btn-p" style={{fontSize:12}} onClick={addNode}>添加</button>
            <button className="btn" style={{fontSize:12}} onClick={() => setShowAdd(false)}>取消</button>
          </div>
        </div>
      )}

      <div style={{fontSize:12,color:'var(--fg3)',marginBottom:10}}>
        共 {total} 个节点 {search && `（搜索"${search}"）`}
      </div>

      <div style={{flex:1,overflowY:'auto'}}>
        {loading ? <div className="load" style={{padding:20}}>加载中...</div> : (
          <table style={{width:'100%',borderCollapse:'collapse',fontSize:13}}>
            <thead>
              <tr style={{borderBottom:'1px solid var(--border2)'}}>
                <th style={{padding:'8px 6px',textAlign:'left',color:'var(--fg3)',fontWeight:400}}>标签</th>
                <th style={{padding:'8px 6px',textAlign:'left',color:'var(--fg3)',fontWeight:400,width:70}}>类型</th>
                <th style={{padding:'8px 6px',textAlign:'left',color:'var(--fg3)',fontWeight:400,width:60}}>重要度</th>
                <th style={{padding:'8px 6px',textAlign:'left',color:'var(--fg3)',fontWeight:400}}>描述</th>
                <th style={{padding:'8px 6px',width:50}}></th>
              </tr>
            </thead>
            <tbody>
              {nodes.map(n => (
                <tr key={n.id} style={{borderBottom:'1px solid var(--border)'}}>
                  <td style={{padding:'8px 6px',fontWeight:500}}>
                    <span style={{display:'inline-block',width:8,height:8,borderRadius:'50%',
                      background:KG_NODE_COLORS[n.node_type]||'#888',marginRight:6}} />
                    {n.label}
                  </td>
                  <td style={{padding:'8px 6px',color:'var(--fg3)',fontSize:11}}>
                    {KG_NODE_LABELS[n.node_type]}
                  </td>
                  <td style={{padding:'8px 6px',color:'var(--fg2)',fontSize:11}}>
                    {n.importance.toFixed(2)}
                  </td>
                  <td style={{padding:'8px 6px',color:'var(--fg2)',maxWidth:300,
                    overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
                    {n.description || <span style={{color:'var(--fg3)'}}>-</span>}
                  </td>
                  <td style={{padding:'8px 6px',textAlign:'right'}}>
                    <button onClick={() => deleteNode(n.id)}
                      style={{background:'transparent',color:'var(--fg3)',fontSize:11,padding:'2px 6px'}}>
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div style={{display:'flex',gap:8,marginTop:12,justifyContent:'center'}}>
        <button className="btn" disabled={offset===0} onClick={() => setOffset(Math.max(0,offset-LIMIT))}
          style={{fontSize:12}}>上一页</button>
        <span style={{padding:'6px 12px',fontSize:12,color:'var(--fg3)'}}>
          {Math.floor(offset/LIMIT)+1} / {Math.ceil(total/LIMIT)||1}
        </span>
        <button className="btn" disabled={offset+LIMIT>=total} onClick={() => setOffset(offset+LIMIT)}
          style={{fontSize:12}}>下一页</button>
      </div>
    </div>
  );
}

// ── 知识探索（搜索+子图+路径） ────────────────────────────────────

function KGExplorer({kg}) {
  const [mode, setMode] = useState('search'); // search|subgraph|path
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('');
  const [target, setTarget] = useState('');
  const [results, setResults] = useState(null);
  const [subElements, setSubElements] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  const doSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await P(`${KG_API}/projects/${kg.id}/search/`, {query, top_k:20});
      setResults(data.nodes || []);
      setStats({duration_ms: data.duration_ms});
    } catch(e) {}
    setLoading(false);
  };

  const doSubgraph = async () => {
    if (!query.trim() && !source.trim()) return;
    setLoading(true);
    try {
      const payload = {max_depth:2, max_nodes:50};
      if (query.trim()) payload.seed_labels = query.split(',').map(s=>s.trim()).filter(Boolean);
      const data = await P(`${KG_API}/projects/${kg.id}/subgraph/`, payload);
      setSubElements(data.elements || []);
      setStats(data.stats);
    } catch(e) {}
    setLoading(false);
  };

  const doPath = async () => {
    if (!source.trim() || !target.trim()) return;
    setLoading(true);
    try {
      const data = await P(`${KG_API}/projects/${kg.id}/path/`, {source, target});
      setResults(data);
      setStats({duration_ms: data.duration_ms});
    } catch(e) {}
    setLoading(false);
  };

  return (
    <div style={{padding:20,height:'100%',display:'flex',flexDirection:'column'}}>
      <div style={{display:'flex',gap:0,marginBottom:16,background:'var(--bg3)',
        borderRadius:'var(--r)',padding:3,alignSelf:'flex-start'}}>
        {[['search','节点搜索'],['subgraph','子图探索'],['path','路径搜索']].map(([m,l]) => (
          <button key={m} onClick={() => {setMode(m);setResults(null);setSubElements([]);setStats(null);}}
            style={{padding:'6px 16px',borderRadius:'calc(var(--r) - 2px)',fontSize:13,
              background:mode===m?'var(--gold)':'transparent',
              color:mode===m?'#0a0a0c':'var(--fg2)'}}>
            {l}
          </button>
        ))}
      </div>

      <div style={{display:'flex',gap:8,marginBottom:16,alignItems:'center'}}>
        {mode === 'path' ? (
          <>
            <input value={source} onChange={e=>setSource(e.target.value)} placeholder="起始概念" style={{flex:1}} />
            <span style={{color:'var(--fg3)',fontSize:16}}>→</span>
            <input value={target} onChange={e=>setTarget(e.target.value)} placeholder="目标概念" style={{flex:1}} />
          </>
        ) : (
          <input value={query} onChange={e=>setQuery(e.target.value)}
            onKeyDown={e=>e.key==='Enter'&&(mode==='search'?doSearch():doSubgraph())}
            placeholder={mode==='subgraph'?'输入种子概念（逗号分隔）':'搜索节点关键词...'}
            style={{flex:1}} />
        )}
        <button className="btn btn-p" style={{fontSize:13}}
          onClick={mode==='search'?doSearch:mode==='subgraph'?doSubgraph:doPath}
          disabled={loading}>
          {loading?'...':(mode==='path'?'查找路径':mode==='subgraph'?'展开子图':'搜索')}
        </button>
      </div>

      {stats && (
        <div style={{fontSize:11,color:'var(--fg3)',marginBottom:10}}>
          耗时 {stats.duration_ms}ms
          {stats.nodes !== undefined && ` · ${stats.nodes}节点 · ${stats.edges}边`}
          {stats.nodes_traversed !== undefined && ` · 遍历${stats.nodes_traversed}节点`}
        </div>
      )}

      {/* 搜索结果 */}
      {mode === 'search' && results && (
        <div style={{flex:1,overflowY:'auto'}}>
          {results.length === 0 ? (
            <div style={{color:'var(--fg3)',padding:20}}>无匹配节点</div>
          ) : results.map(n => (
            <div key={n.id} style={{padding:'10px 12px',background:'var(--bg3)',
              borderRadius:'var(--r)',marginBottom:6,
              borderLeft:`3px solid ${KG_NODE_COLORS[n.node_type]||'#888'}`}}>
              <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:4}}>
                <span style={{fontWeight:600}}>{n.label}</span>
                <span style={{fontSize:11,color:KG_NODE_COLORS[n.node_type]}}>{KG_NODE_LABELS[n.node_type]}</span>
                <span style={{fontSize:11,color:'var(--fg3)',marginLeft:'auto'}}>重要度 {n.importance.toFixed(2)}</span>
              </div>
              {n.description && <div style={{fontSize:12,color:'var(--fg2)'}}>{n.description}</div>}
              {n.source_ref && <div style={{fontSize:11,color:'var(--gold)',marginTop:3}}>{n.source_ref}</div>}
            </div>
          ))}
        </div>
      )}

      {/* 路径结果 */}
      {mode === 'path' && results && (
        <div style={{flex:1,overflowY:'auto'}}>
          {!results.found ? (
            <div style={{color:'var(--fg3)',padding:20}}>未找到路径（可尝试增大max_length）</div>
          ) : (
            <div>
              <div style={{color:'var(--green)',marginBottom:12,fontSize:13}}>
                找到路径，长度 {results.length}
              </div>
              <div style={{display:'flex',flexWrap:'wrap',alignItems:'center',gap:4}}>
                {results.path_nodes && results.path_nodes.map((n, i) => (
                  <React.Fragment key={n.id}>
                    <span style={{padding:'4px 10px',background:'var(--bg3)',
                      border:`1px solid ${KG_NODE_COLORS[n.type]||'#888'}`,
                      borderRadius:16,fontSize:12,color:KG_NODE_COLORS[n.type]}}>
                      {n.label}
                    </span>
                    {i < results.path_edges.length && (
                      <span style={{fontSize:11,color:'var(--fg3)',padding:'0 4px'}}>
                        —[{results.path_edges[i].relation}]→
                      </span>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 子图可视化 */}
      {mode === 'subgraph' && subElements.length > 0 && (
        <div style={{flex:1,minHeight:0}}>
          <KGCytoGraph elements={subElements} onNodeClick={n=>setSelectedNode(n)} selectedNodeId={selectedNode?.id} />
        </div>
      )}
    </div>
  );
}

// ── AI提取知识 ────────────────────────────────────────────────────

function KGExtractor({kg}) {
  const [text, setText] = useState('');
  const [sourceRef, setSourceRef] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [chatQ, setChatQ] = useState('');
  const [chatAnswer, setChatAnswer] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [tab, setTab] = useState('extract');

  const extract = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const data = await P(`${KG_API}/projects/${kg.id}/extract/`, {
        text, source_ref: sourceRef,
      });
      setResult(data);
    } catch(e) { showAlert('提取失败', '错误'); }
    setLoading(false);
  };

  const computeRank = async () => {
    try {
      const data = await P(`${KG_API}/projects/${kg.id}/rank/`, {});
      showAlert(`PageRank计算完成，更新了 ${data.updated} 个节点，耗时 ${data.duration_ms}ms`, '计算完成');
    } catch(e) { showAlert('计算失败', '错误'); }
  };

  const doChat = async () => {
    if (!chatQ.trim()) return;
    setChatLoading(true);
    setChatAnswer('');
    try {
      const token = localStorage.getItem('mf_token');
      const res = await fetch(`${KG_API}/projects/${kg.id}/chat/`, {
        method: 'POST',
        headers: {'Content-Type':'application/json','Authorization':`Token ${token}`},
        body: JSON.stringify({question: chatQ}),
      });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        buf += decoder.decode(value, {stream:true});
        const lines = buf.split('\n');
        buf = lines.pop();
        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          try {
            const d = JSON.parse(line.slice(5));
            if (d.type === 'chunk') setChatAnswer(a => a + d.text);
          } catch(e) {}
        }
      }
    } catch(e) { setChatAnswer('错误: ' + e.message); }
    setChatLoading(false);
  };

  return (
    <div style={{padding:20,height:'100%',display:'flex',flexDirection:'column'}}>
      <div style={{display:'flex',gap:0,marginBottom:16,background:'var(--bg3)',
        borderRadius:'var(--r)',padding:3,alignSelf:'flex-start'}}>
        {[['extract','提取知识'],['chat','图谱问答']].map(([t,l]) => (
          <button key={t} onClick={() => setTab(t)}
            style={{padding:'6px 16px',borderRadius:'calc(var(--r) - 2px)',fontSize:13,
              background:tab===t?'var(--gold)':'transparent',
              color:tab===t?'#0a0a0c':'var(--fg2)'}}>
            {l}
          </button>
        ))}
      </div>

      {tab === 'extract' && (
        <div style={{display:'flex',flexDirection:'column',gap:10,flex:1}}>
          <input value={sourceRef} onChange={e=>setSourceRef(e.target.value)}
            placeholder="来源引用（如 paper.md:L45-60，可选）" style={{width:'100%'}} />
          <textarea value={text} onChange={e=>setText(e.target.value)}
            placeholder="粘贴要提取知识的文本（最多4000字）..."
            style={{flex:1,minHeight:200,width:'100%',resize:'none',fontFamily:'var(--mono)',fontSize:12}} />
          <div style={{display:'flex',gap:8,alignItems:'center'}}>
            <button className="btn btn-p"
              onClick={extract} disabled={loading||!text.trim()}>
              {loading ? '提取中...' : 'AI提取知识'}
            </button>
            <button className="btn" onClick={computeRank} style={{fontSize:12}}>
              重算PageRank
            </button>
          </div>
          {result && (
            <div style={{background:'var(--bg3)',borderRadius:'var(--r)',padding:14,
              border:'1px solid var(--border2)'}}>
              {result.error ? (
                <div style={{color:'var(--red)'}}>提取失败: {result.error}</div>
              ) : (
                <div>
                  <div style={{color:'var(--green)',marginBottom:6}}>
                    提取成功！新增 {result.nodes_created} 节点、{result.edges_created} 条边
                  </div>
                  <div style={{fontSize:12,color:'var(--fg3)'}}>
                    图谱现有 {result.total_nodes} 节点、{result.total_edges} 条边
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {tab === 'chat' && (
        <div style={{display:'flex',flexDirection:'column',gap:10,flex:1}}>
          <div style={{color:'var(--fg3)',fontSize:12,padding:'8px 12px',background:'var(--bg3)',
            borderRadius:'var(--r)'}}>
            基于当前知识图谱内容回答问题，不会编造图谱外信息
          </div>
          <div style={{flex:1,background:'var(--bg3)',borderRadius:'var(--r)',padding:14,
            overflowY:'auto',minHeight:150,fontFamily:'var(--mono)',fontSize:13,lineHeight:1.7,
            whiteSpace:'pre-wrap',color:'var(--fg)'}}>
            {chatAnswer || <span style={{color:'var(--fg3)'}}>回答将显示在这里...</span>}
          </div>
          <div style={{display:'flex',gap:8}}>
            <input value={chatQ} onChange={e=>setChatQ(e.target.value)}
              onKeyDown={e=>e.key==='Enter'&&!e.shiftKey&&doChat()}
              placeholder="基于知识图谱提问..." style={{flex:1}} />
            <button className="btn btn-p"
              onClick={doChat} disabled={chatLoading||!chatQ.trim()}>
              {chatLoading?'..':'发送'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 统计分析 ──────────────────────────────────────────────────────

function KGAnalytics({kg}) {
  const [stats, setStats] = useState(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const url = `${KG_API}/stats/?days=${days}${kg?`&kg_id=${kg.id}`:''}`;
      const data = await F(url);
      setStats(data);
    } catch(e) {}
    setLoading(false);
  };

  useEffect(() => { load(); }, [days, kg?.id]);

  const OPERATION_LABELS = {
    extract_text:'文本提取', add_node:'添加节点', add_edge:'添加边',
    query_subgraph:'查询子图', search_nodes:'搜索节点', find_path:'路径搜索',
    batch_extract:'批量提取', get_context:'获取上下文', compute_rank:'计算排名',
    bfs_traverse:'BFS遍历',
  };

  if (loading) return <div className="load" style={{padding:40}}>加载中...</div>;
  if (!stats) return null;

  const agg = stats.aggregates || {};

  return (
    <div style={{padding:20,height:'100%',overflowY:'auto'}}>
      <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:20}}>
        <h3 style={{fontSize:15,color:'var(--gold)'}}>调用统计</h3>
        <select value={days} onChange={e=>setDays(Number(e.target.value))}
          style={{padding:'4px 8px',fontSize:12,background:'var(--bg3)'}}>
          <option value={7}>近7天</option>
          <option value={30}>近30天</option>
          <option value={90}>近90天</option>
        </select>
        <button className="btn" style={{fontSize:12}} onClick={load}>刷新</button>
      </div>

      {/* 汇总指标 */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(160px,1fr))',gap:10,marginBottom:20}}>
        {[
          ['总调用次数', stats.total_calls, '次'],
          ['总耗时', Math.round((agg.total_duration_ms||0)/1000), '秒'],
          ['LLM输入Token', agg.total_tokens_in||0, ''],
          ['LLM输出Token', agg.total_tokens_out||0, ''],
          ['遍历节点', agg.total_nodes_traversed||0, '个'],
          ['遍历边', agg.total_edges_traversed||0, '条'],
          ['平均耗时', Math.round(agg.avg_duration_ms||0), 'ms'],
        ].map(([label, val, unit]) => (
          <div key={label} style={{background:'var(--bg3)',borderRadius:'var(--r)',
            padding:'12px 14px',border:'1px solid var(--border2)'}}>
            <div style={{fontSize:11,color:'var(--fg3)',marginBottom:4}}>{label}</div>
            <div style={{fontSize:18,fontWeight:600,color:'var(--gold)'}}>
              {typeof val === 'number' ? val.toLocaleString() : val}
              <span style={{fontSize:12,fontWeight:400,color:'var(--fg3)',marginLeft:3}}>{unit}</span>
            </div>
          </div>
        ))}
      </div>

      {/* 按操作分类 */}
      {stats.by_operation && stats.by_operation.length > 0 && (
        <div style={{marginBottom:20}}>
          <div style={{fontSize:13,color:'var(--fg2)',marginBottom:10,fontWeight:500}}>操作分布</div>
          {stats.by_operation.map(op => (
            <div key={op.operation} style={{display:'flex',alignItems:'center',gap:8,marginBottom:6}}>
              <span style={{width:80,fontSize:12,color:'var(--fg3)'}}>{OPERATION_LABELS[op.operation]||op.operation}</span>
              <div style={{flex:1,height:16,background:'var(--bg3)',borderRadius:8,overflow:'hidden'}}>
                <div style={{height:'100%',background:'var(--gold)',opacity:0.7,
                  width:`${Math.min(100, (op.count/stats.total_calls)*100)}%`,
                  borderRadius:8,transition:'width .3s'}} />
              </div>
              <span style={{width:40,fontSize:12,color:'var(--fg2)',textAlign:'right'}}>{op.count}</span>
            </div>
          ))}
        </div>
      )}

      {/* 最近日志 */}
      {stats.recent_logs && stats.recent_logs.length > 0 && (
        <div>
          <div style={{fontSize:13,color:'var(--fg2)',marginBottom:10,fontWeight:500}}>最近调用记录</div>
          <div style={{background:'var(--bg3)',borderRadius:'var(--r)',overflow:'hidden'}}>
            {stats.recent_logs.map(log => (
              <div key={log.id} style={{padding:'8px 12px',borderBottom:'1px solid var(--border)',
                display:'flex',alignItems:'center',gap:8,fontSize:12}}>
                <span style={{color:log.success?'var(--green)':'var(--red)',fontSize:10}}>●</span>
                <span style={{width:90,color:'var(--fg2)'}}>{OPERATION_LABELS[log.operation]||log.operation}</span>
                <span style={{width:60,color:'var(--fg3)'}}>{log.caller_app}</span>
                <span style={{width:55,color:'var(--fg2)'}}>{log.duration_ms}ms</span>
                {log.nodes_created > 0 && <span style={{color:'var(--green)'}}>+{log.nodes_created}节点</span>}
                {log.edges_created > 0 && <span style={{color:'var(--cyan)'}}>+{log.edges_created}边</span>}
                {(log.llm_tokens_input||0) > 0 && (
                  <span style={{color:'var(--gold)',fontSize:11,marginLeft:'auto'}}>
                    {log.llm_tokens_input}+{log.llm_tokens_output} tok
                  </span>
                )}
                <span style={{color:'var(--fg3)',fontSize:11,marginLeft:'auto'}}>
                  {new Date(log.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── 主应用组件 ────────────────────────────────────────────────────

function KGApp({user, onLogout, onUpdateUser}) {
  const [v, setV] = useState('projects');
  const [currentKG, setCurrentKG] = useState(null);
  const [sbOpen, setSbOpen] = useState(true);

  const isPlatformKG = currentKG && currentKG._platform === true;
  // 平台图谱只展示图谱可视化，不允许编辑
  const navItems = currentKG ? (isPlatformKG ? [
    {id:'graph', label:'图谱可视化', icon:'share-2'},
  ] : [
    {id:'graph', label:'图谱可视化', icon:'share-2'},
    {id:'explorer', label:'知识探索', icon:'search'},
    {id:'nodes', label:'节点管理', icon:'list'},
    {id:'extract', label:'AI提取', icon:'zap'},
    {id:'analytics', label:'统计分析', icon:'bar-chart-2'},
  ]) : [];

  const topNavItems = [
    {id:'projects', label:'所有图谱', icon:'folder'},
    {id:'analytics_global', label:'全局统计', icon:'activity'},
  ];

  return (
    <div className="app">
      {/* 侧边栏 */}
      <div className="sb" style={{display:'flex',flexDirection:'column'}}>
        <div style={{padding:'16px 14px 12px',borderBottom:'1px solid var(--border)',
          display:'flex',alignItems:'center',gap:10}}>
          <div style={{width:32,height:32,borderRadius:8,background:'rgba(201,168,108,.15)',
            display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>
            <Icon name="share-2" size={18} stroke={1.5} style={{color:'var(--gold)'}} />
          </div>
          <div>
            <div style={{fontWeight:700,fontSize:14,color:'var(--fg)',fontFamily:'var(--serif)'}}>知识图谱</div>
            {currentKG && <div style={{fontSize:11,color:'var(--gold)',marginTop:1,maxWidth:130,
              overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{currentKG.title}</div>}
          </div>
        </div>

        <nav style={{flex:1,overflowY:'auto',padding:'8px 0'}}>
          {/* 顶层导航 */}
          {topNavItems.map(item => (
            <div key={item.id} onClick={() => {setV(item.id);if(item.id==='projects')setCurrentKG(null);}}
              style={{padding:'8px 14px',cursor:'pointer',display:'flex',alignItems:'center',gap:8,
                background: v===item.id?'rgba(201,168,108,.12)':'transparent',
                color: v===item.id?'var(--gold)':'var(--fg2)',
                borderLeft: v===item.id?'2px solid var(--gold)':'2px solid transparent',
                fontSize:13}}>
              <Icon name={item.icon} size={15} stroke={1.5} />
              {item.label}
            </div>
          ))}

          {/* 当前图谱导航 */}
          {currentKG && (
            <>
              <div style={{padding:'10px 14px 4px',fontSize:11,color:'var(--fg3)',textTransform:'uppercase',letterSpacing:'.05em'}}>
                当前图谱
              </div>
              {navItems.map(item => (
                <div key={item.id} onClick={() => setV(item.id)}
                  style={{padding:'8px 14px 8px 20px',cursor:'pointer',display:'flex',alignItems:'center',gap:8,
                    background: v===item.id?'rgba(201,168,108,.12)':'transparent',
                    color: v===item.id?'var(--gold)':'var(--fg2)',
                    borderLeft: v===item.id?'2px solid var(--gold)':'2px solid transparent',
                    fontSize:13}}>
                  <Icon name={item.icon} size={14} stroke={1.5} />
                  {item.label}
                </div>
              ))}
            </>
          )}
        </nav>

        <div style={{padding:'10px 14px',borderTop:'1px solid var(--border)'}}>
          <div style={{fontSize:11,color:'var(--fg3)',marginBottom:6}}>{displayName(user)}</div>
          <div style={{display:'flex',gap:6}}>
            <button onClick={() => {window.location.hash='#/';}}
              style={{flex:1,background:'var(--bg3)',color:'var(--fg2)',
                padding:'5px 0',borderRadius:'var(--r)',fontSize:11}}>
              ← MineAI 首页
            </button>
            <button onClick={onLogout}
              style={{flex:1,background:'var(--bg3)',color:'var(--fg2)',
                padding:'5px 0',borderRadius:'var(--r)',fontSize:11}}>
              退出
            </button>
          </div>
        </div>
      </div>

      {/* 主内容 */}
      <div style={{flex:1,display:'flex',flexDirection:'column',minWidth:0,overflow:'hidden'}}>
        {/* 标题栏 */}
        <div style={{height:46,borderBottom:'1px solid var(--border)',display:'flex',
          alignItems:'center',padding:'0 16px',gap:12,background:'var(--bg2)',flexShrink:0}}>
          {currentKG && (
            <button onClick={() => {setCurrentKG(null);setV('projects');}}
              style={{background:'transparent',color:'var(--fg3)',fontSize:12,
                display:'flex',alignItems:'center',gap:4}}>
              ← 返回
            </button>
          )}
          <span style={{fontSize:14,fontWeight:500,color:'var(--fg)'}}>
            {v==='projects'?'知识图谱项目':
             v==='analytics_global'?'全局统计':
             v==='graph'?'图谱可视化':
             v==='explorer'?'知识探索':
             v==='nodes'?'节点管理':
             v==='extract'?'AI提取知识':
             v==='analytics'?'统计分析':''}
          </span>
          {currentKG && (
            <span style={{fontSize:12,color:'var(--fg3)',marginLeft:'auto'}}>
              {currentKG.node_count} 节点 · {currentKG.edge_count} 边
            </span>
          )}
        </div>

        {/* 视图内容 */}
        <div style={{flex:1,overflow:'auto',minHeight:0}}>
          {v === 'projects' && (
            <KGProjectList onSelect={(kg) => {setCurrentKG(kg);setV('graph');}} />
          )}
          {v === 'analytics_global' && <KGAnalytics kg={null} />}
          {currentKG && v === 'graph' && <KGGraphView kg={currentKG} />}
          {currentKG && v === 'explorer' && <KGExplorer kg={currentKG} />}
          {currentKG && v === 'nodes' && <KGNodeManager kg={currentKG} />}
          {currentKG && v === 'extract' && <KGExtractor kg={currentKG} />}
          {currentKG && v === 'analytics' && <KGAnalytics kg={currentKG} />}
        </div>
      </div>
    </div>
  );
}

// ── 代码助手 CodeAgentApp ──────────────────────────────────────

// ---- helper: parse diff blocks from raw SSE text ----
function parseDiffBlocks(text) {
  const blocks = [];
  const re = /<<<<\n?([\s\S]*?)\n?====\n?([\s\S]*?)\n?>>>>/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    blocks.push({ original: m[1].trim(), replacement: m[2].trim() });
  }
  return blocks;
}

// ---- helper: streaming fetch ----
async function* streamSSE(url, body, token) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type':'application/json','Authorization':`Token ${token}`},
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`${resp.status}: ${await resp.text()}`);
  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf = '';
  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    buf += dec.decode(value, {stream: true});
    const lines = buf.split('\n');
    buf = lines.pop();
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try { yield JSON.parse(line.slice(6)); } catch {}
      }
    }
  }
}

{% endverbatim %}
{% verbatim %}
// ---- DiffBlock: single diff with accept/reject ----
function DiffBlock({diff, index, onAccept, onReject, accepted, rejected}) {
  const st = accepted ? 'accepted' : rejected ? 'rejected' : 'pending';
  return (
    <div style={{marginBottom:10, border:`1px solid ${st==='accepted'?'var(--green)':st==='rejected'?'var(--red)':'var(--border2)'}`, borderRadius:6, overflow:'hidden', fontSize:12}}>
      <div style={{display:'flex',alignItems:'center',padding:'4px 8px',background:'var(--bg4)',gap:8}}>
        <span style={{fontFamily:'var(--mono)',fontSize:11,color:'var(--fg3)'}}>变更 #{index+1}</span>
        <span style={{marginLeft:'auto',display:'flex',gap:6}}>
          {st==='pending' && <>
            <button className="btn btn-sm" style={{background:'var(--green)',color:'#000',padding:'2px 8px',display:'inline-flex',alignItems:'center',gap:6}} onClick={()=>onAccept(index)}>
              <Icon name="check" size={11} /> 接受
            </button>
            <button className="btn btn-sm" style={{background:'var(--red)',color:'#fff',padding:'2px 8px',display:'inline-flex',alignItems:'center',gap:6}} onClick={()=>onReject(index)}>
              <Icon name="x" size={11} /> 拒绝
            </button>
          </>}
          {st==='accepted' && <span style={{color:'var(--green)',fontSize:11,display:'inline-flex',alignItems:'center',gap:4}}><Icon name="check" size={11} /> 已接受</span>}
          {st==='rejected' && <span style={{color:'var(--red)',fontSize:11,display:'inline-flex',alignItems:'center',gap:4}}><Icon name="x" size={11} /> 已拒绝</span>}
        </span>
      </div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr'}}>
        <div style={{padding:'6px 8px',background:'rgba(196,90,90,.08)',borderRight:'1px solid var(--border)'}}>
          <div style={{fontSize:10,color:'var(--red)',marginBottom:3}}>原始</div>
          <pre style={{margin:0,fontFamily:'var(--mono)',whiteSpace:'pre-wrap',wordBreak:'break-word',color:'var(--fg2)',fontSize:11,lineHeight:1.5}}>{diff.original}</pre>
        </div>
        <div style={{padding:'6px 8px',background:'rgba(94,184,122,.08)'}}>
          <div style={{fontSize:10,color:'var(--green)',marginBottom:3}}>修改后</div>
          <pre style={{margin:0,fontFamily:'var(--mono)',whiteSpace:'pre-wrap',wordBreak:'break-word',color:'var(--fg)',fontSize:11,lineHeight:1.5}}>{diff.replacement}</pre>
        </div>
      </div>
    </div>
  );
}

// ---- FileTree ----
function FileTree({files, selectedId, onSelect, onDelete}) {
  // Group by directory prefix
  const tree = {};
  files.forEach(f => {
    const parts = f.path.split('/');
    const dir = parts.length > 1 ? parts.slice(0,-1).join('/') : '';
    if (!tree[dir]) tree[dir] = [];
    tree[dir].push(f);
  });

  const langColor = {python:'var(--blue)',javascript:'var(--gold)',typescript:'var(--blue)',
    go:'var(--cyan)',rust:'var(--orange)',java:'var(--red)',html:'var(--orange)',
    css:'var(--purple)',json:'var(--green)',markdown:'var(--fg2)',bash:'var(--green)'};

  return (
    <div style={{fontSize:12}}>
      {Object.entries(tree).sort().map(([dir, dirFiles]) => (
        <div key={dir}>
          {dir && <div style={{padding:'4px 10px 2px',fontSize:10,color:'var(--fg3)',letterSpacing:1}}>{dir}/</div>}
          {dirFiles.map(f => {
            const name = f.path.split('/').pop();
            const isSelected = f.id === selectedId;
            return (
              <div key={f.id}
                style={{display:'flex',alignItems:'center',gap:6,padding:'5px 10px',
                  borderRadius:4,cursor:'pointer',
                  background: isSelected ? 'var(--bg4)' : 'transparent',
                  color: isSelected ? 'var(--fg)' : 'var(--fg2)'}}
                onClick={() => onSelect(f)}>
                <span style={{fontFamily:'var(--mono)',fontSize:10,color:langColor[f.language]||'var(--fg3)',width:14,textAlign:'center',flexShrink:0}}>
                  {f.language ? f.language[0].toUpperCase() : '?'}
                </span>
                <span style={{flex:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{name}</span>
                {f.modified && <span style={{color:'var(--orange)',fontSize:10,flexShrink:0}} title="已修改未保存">●</span>}
                <span style={{fontSize:10,color:'var(--fg3)'}}>{f.size>1024?`${(f.size/1024).toFixed(1)}k`:`${f.size}b`}</span>
                {onDelete && <button onClick={e=>{e.stopPropagation();onDelete(f.id);}}
                  style={{background:'none',color:'var(--fg3)',fontSize:11,padding:'0 3px',lineHeight:1}} title="删除"><Icon name="x" size={11} /></button>}
              </div>
            );
          })}
        </div>
      ))}
      {files.length === 0 && <div style={{padding:'20px 10px',color:'var(--fg3)',textAlign:'center',fontSize:12}}>暂无文件<br/>上传代码文件开始</div>}
    </div>
  );
}

// ---- 客户端 apply diffs（本地模式不走服务端）----
function applyDiffsLocally(content, acceptedDiffs) {
  let result = content;
  let applied = 0;
  for (const diff of acceptedDiffs) {
    const idx = result.indexOf(diff.original);
    if (idx !== -1) {
      result = result.slice(0, idx) + diff.replacement + result.slice(idx + diff.original.length);
      applied++;
    }
  }
  return {content: result, applied};
}

// ---- 跳过目录名（本地扫描）----
const SKIP_DIRS = new Set(['.git','node_modules','__pycache__','dist','build',
  'venv','.venv','coverage','.next','.nuxt','target','.cache','vendor','bower_components']);

// ---- Main CodeAgentApp ----
function CodeAgentApp({user, onLogout, onUpdateUser}) {
  const [v, setV] = useState('home');
  const [projects, setProjects] = useState([]);
  const [proj, setProj] = useState(null);
  const [files, setFiles] = useState([]);
  const [selFile, setSelFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [diffs, setDiffs] = useState([]);
  const [diffStates, setDiffStates] = useState({}); // {idx: 'accepted'|'rejected'}
  const [chatInput, setChatInput] = useState('');
  const [editInstruction, setEditInstruction] = useState('');
  const [generating, setGenerating] = useState(false);
  const [rightPanel, setRightPanel] = useState('chat'); // 'chat' | 'diffs' | 'versions'
  const [versions, setVersions] = useState([]);
  const [sbOpen, setSbOpen] = useState(false);
  const [showNewProj, setShowNewProj] = useState(false);
  const [newProjData, setNewProjData] = useState({name:'',description:'',language:''});
  const [memStats, setMemStats] = useState(null);
  const [streaming, setStreaming] = useState('');

  // ── 本地模式状态 ──
  const [uploadMode, setUploadMode] = useState('local'); // 'local' | 'server'
  const [dirHandle, setDirHandle] = useState(null);      // FSA 句柄
  const [localFiles, setLocalFiles] = useState({});      // {path: {content, handle, modified}}
  const [selLocalPath, setSelLocalPath] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(null); // {scanned, currentFile, skipped}
  const [chatHistory, setChatHistory] = useState([]);     // 本地模式多轮历史
  const [localContextPaths, setLocalContextPaths] = useState(new Set());
  const [fsaSupported] = useState(() => 'showDirectoryPicker' in window);
  const [serverLimits, setServerLimits] = useState({max_files:100,max_total_mb:50,max_file_kb:1024});
  const [pendingDiskSave, setPendingDiskSave] = useState(false); // 本地模式是否有未写盘变更

  const chatEndRef = useRef(null);
  const scanAbortRef = useRef(false);
  const token = localStorage.getItem('mf_token');

  useEffect(() => { loadProjects(); loadServerLimits(); }, []);
  useEffect(() => { chatEndRef.current?.scrollIntoView({behavior:'smooth'}); }, [messages, streaming]);

  const loadProjects = async () => {
    try { setProjects(await F(`${API}/code/projects/`)); } catch {}
  };

  const loadServerLimits = async () => {
    try { setServerLimits(await F(`${API}/code/upload-limits/`)); } catch {}
  };

  const openProject = async (p) => {
    setProj(p);
    setSelFile(null); setSelLocalPath(null); setFileContent('');
    setDiffs([]); setDiffStates({}); setMessages([]); setChatHistory([]);
    setSession(null); setVersions([]);
    try {
      const detail = await F(`${API}/code/projects/${p.id}/`);
      setFiles(detail.files || []);
      setProj(detail);
      if (uploadMode === 'server') {
        const ss = await P(`${API}/code/projects/${p.id}/sessions/`, {title:'主对话'});
        setSession(ss);
        const sDetail = await F(`${API}/code/sessions/${ss.id}/`);
        setMessages(sDetail.messages || []);
      }
    } catch {}
    setV('project');
    setSbOpen(false);
  };

  // ── 服务端模式：选择文件 ──
  const selectFile = async (f) => {
    setSelFile(f); setSelLocalPath(null);
    setDiffs([]); setDiffStates({});
    try {
      const detail = await F(`${API}/code/files/${f.id}/`);
      setFileContent(detail.content || '');
      setSelFile(detail);
    } catch {}
  };

  // ── 本地模式：选择文件 ──
  const selectLocalFile = (path) => {
    setSelLocalPath(path); setSelFile(null);
    setFileContent(localFiles[path]?.content || '');
    setDiffs([]); setDiffStates({});
    setPendingDiskSave(false);
  };

  // ── 统一保存入口 ──
  const saveFile = async () => {
    if (uploadMode === 'server') {
      if (!selFile) return;
      try {
        await U(`${API}/code/files/${selFile.id}/`, {content:fileContent, change_summary:'手动编辑'});
        setFiles(files.map(ff => ff.id === selFile.id ? {...ff, size:fileContent.length} : ff));
      } catch(e) { showAlert('保存失败: ' + e.message, '错误'); }
    } else {
      // 本地模式：更新内存 state，并写回磁盘（如果有 FSA 句柄）
      if (!selLocalPath) return;
      const entry = localFiles[selLocalPath];
      setLocalFiles(p => ({...p, [selLocalPath]: {...p[selLocalPath], content: fileContent, modified: false}}));
      setPendingDiskSave(false);
      if (entry?.handle) {
        try {
          const writable = await entry.handle.createWritable();
          await writable.write(fileContent);
          await writable.close();
        } catch(e) { showAlert('写入磁盘失败: ' + e.message, '错误'); }
      }
    }
  };

  // ── 下载当前文件（本地模式回退）──
  const downloadLocalFile = () => {
    if (!selLocalPath) return;
    const blob = new Blob([fileContent], {type: 'text/plain'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = selLocalPath.split('/').pop();
    a.click();
    URL.revokeObjectURL(a.href);
  };

  // ── 本地模式：FSA API 递归扫描目录 ──
  const scanDir = async (handle, basePath, depth, collected) => {
    if (depth > 8 || Object.keys(collected).length >= 500 || scanAbortRef.current) return;
    for await (const [name, entry] of handle.entries()) {
      if (scanAbortRef.current) return;
      const isHidden = name.startsWith('.');
      if (entry.kind === 'directory') {
        if (isHidden || SKIP_DIRS.has(name.toLowerCase())) continue;
        const subPath = basePath ? `${basePath}/${name}` : name;
        await scanDir(entry, subPath, depth + 1, collected);
      } else {
        const file = await entry.getFile();
        const filePath = basePath ? `${basePath}/${name}` : name;
        if (file.size > 1024 * 1024) continue; // skip >1MB
        try {
          const text = await file.text();
          collected[filePath] = {content: text, handle: entry, modified: false};
          setScanProgress({scanned: Object.keys(collected).length, currentFile: filePath});
        } catch {}
      }
    }
  };

  // ── 本地模式：打开文件夹（FSA API）──
  const openDirectory = async () => {
    try {
      const handle = await window.showDirectoryPicker({mode: 'readwrite'});
      setDirHandle(handle);
      setLocalFiles({});
      setSelLocalPath(null);
      setFileContent('');
      setScanning(true);
      setScanProgress({scanned: 0, currentFile: ''});
      scanAbortRef.current = false;
      const collected = {};
      await scanDir(handle, '', 0, collected);
      setLocalFiles(collected);
      setScanProgress(null);
      setScanning(false);
    } catch(e) {
      setScanning(false);
      setScanProgress(null);
      if (e.name !== 'AbortError') showAlert('打开目录失败: ' + e.message, '错误');
    }
  };

  // ── webkitdirectory / 文件上传入口（服务端模式 + 本地回退）──
  const uploadFiles = async (fileList) => {
    const allFiles = Array.from(fileList);
    if (uploadMode === 'local') {
      // 本地模式：只加载到内存，不发到服务器
      setScanning(true);
      setScanProgress({scanned: 0, currentFile: ''});
      const collected = {};
      const maxCount = 500;
      for (const file of allFiles.slice(0, maxCount)) {
        if (scanAbortRef.current) break;
        const path = file.webkitRelativePath || file.name;
        if (file.size > 1024 * 1024) continue;
        try {
          const text = await file.text();
          collected[path] = {content: text, handle: null, modified: false};
          setScanProgress({scanned: Object.keys(collected).length, currentFile: path});
        } catch {}
      }
      setLocalFiles(prev => ({...prev, ...collected}));
      setScanProgress(null);
      setScanning(false);
    } else {
      // 服务端模式：前端预检后 POST 到服务器
      const maxCount = serverLimits.max_files;
      const maxMB = serverLimits.max_total_mb;
      const filtered = allFiles.slice(0, maxCount);
      let totalSize = 0;
      const reads = [];
      for (const file of filtered) {
        if (file.size > serverLimits.max_file_kb * 1024) continue;
        totalSize += file.size;
        if (totalSize > maxMB * 1024 * 1024) break;
        reads.push(new Promise(res => {
          const reader = new FileReader();
          reader.onload = e => res({path: file.webkitRelativePath || file.name, content: e.target.result});
          reader.onerror = () => res(null);
          reader.readAsText(file);
        }));
      }
      const resolved = (await Promise.all(reads)).filter(Boolean);
      try {
        const res = await P(`${API}/code/projects/${proj.id}/files/batch/`, {files: resolved});
        if (res.rejected?.length) {
          const rejMsg = res.rejected.slice(0, 5).map(r => `${r.path}: ${r.reason}`).join('\n');
          showAlert(`${res.saved} 个文件已上传，${res.rejected.length} 个被拒绝：\n${rejMsg}`, '上传结果');
        }
        const detail = await F(`${API}/code/projects/${proj.id}/`);
        setFiles(detail.files || []);
        loadMemStats();
      } catch(e) { showAlert('上传失败: ' + e.message, '错误'); }
    }
  };

  const deleteFile = async (fileId) => {
    const confirmed = await showConfirm('确认删除此文件？');
    if (!confirmed) return;
    try {
      await F(`${API}/code/files/${fileId}/`, {method:'DELETE', headers:{'Authorization':`Token ${token}`}});
      setFiles(files.filter(f => f.id !== fileId));
      if (selFile?.id === fileId) { setSelFile(null); setFileContent(''); }
    } catch {}
  };

  const loadMemStats = async () => {
    if (!proj) return;
    try { setMemStats(await F(`${API}/code/projects/${proj.id}/memory/`)); } catch {}
  };

  const loadVersions = async () => {
    if (!selFile) return;
    try {
      const vs = await F(`${API}/code/files/${selFile.id}/versions/`);
      setVersions(vs);
      setRightPanel('versions');
    } catch {}
  };

  const rollback = async (version) => {
    if (!selFile) return;
    const confirmed = await showConfirm(`回滚到版本 v${version}？`);
    if (!confirmed) return;
    try {
      const res = await P(`${API}/code/files/${selFile.id}/rollback/`, {version});
      const detail = await F(`${API}/code/files/${selFile.id}/`);
      setFileContent(detail.content);
      setSelFile(detail);
      setFiles(files.map(f => f.id === selFile.id ? {...f, current_version: detail.current_version} : f));
      showAlert(`已回滚到 v${version}`, '成功');
    } catch(e) { showAlert('回滚失败: ' + e.message, '错误'); }
  };

  // --- AI 对话（流式）---
  const sendChat = async () => {
    if (!chatInput.trim() || generating) return;
    if (uploadMode === 'server' && !session) return;
    const msg = chatInput.trim();
    setChatInput('');
    setMessages(prev => [...prev, {id:Date.now(), role:'user', content:msg}]);
    setGenerating(true); setStreaming(''); setRightPanel('chat');
    let full = '';
    try {
      if (uploadMode === 'local') {
        // 本地模式：调用无状态端点，内容在 body 中，不写 DB
        const ctxFiles = Array.from(localContextPaths)
          .filter(p => p !== selLocalPath)
          .map(p => ({path: p, content: localFiles[p]?.content || ''}));
        for await (const ev of streamSSE(`${API}/code/local/chat/`, {
          message: msg,
          current_file: selLocalPath ? {path: selLocalPath, content: fileContent} : null,
          context_files: ctxFiles,
          history: chatHistory.slice(-20),
        }, token)) {
          if (ev.type === 'chunk') { full += ev.text; setStreaming(full); }
          if (ev.type === 'done') break;
          if (ev.type === 'error') throw new Error(ev.message);
        }
        setChatHistory(prev => [...prev,
          {role:'user', content:msg},
          {role:'assistant', content:full}]);
      } else {
        // 服务端模式：原有逻辑
        for await (const ev of streamSSE(`${API}/code/sessions/${session.id}/chat/`, {
          message: msg, file_id: selFile?.id
        }, token)) {
          if (ev.type === 'chunk') { full += ev.text; setStreaming(full); }
          if (ev.type === 'done') break;
          if (ev.type === 'error') throw new Error(ev.message);
        }
      }
      setMessages(prev => [...prev, {id:Date.now()+1, role:'assistant', content:full}]);
    } catch(e) {
      setMessages(prev => [...prev, {id:Date.now()+1, role:'assistant', content:`错误: ${e.message}`}]);
    } finally { setGenerating(false); setStreaming(''); }
  };

  // --- 代码编辑建议（流式 Diff）---
  const suggestEdits = async () => {
    const hasFile = uploadMode === 'local' ? !!selLocalPath : !!selFile;
    if (!hasFile || !editInstruction.trim() || generating) return;
    setGenerating(true); setDiffs([]); setDiffStates({});
    setRightPanel('diffs'); setStreaming('');
    let raw = '';
    try {
      if (uploadMode === 'local') {
        const ctxFiles = Array.from(localContextPaths)
          .filter(p => p !== selLocalPath)
          .map(p => ({path: p, content: localFiles[p]?.content || ''}));
        for await (const ev of streamSSE(`${API}/code/local/suggest/`, {
          file_path: selLocalPath,
          content: fileContent,
          instruction: editInstruction,
          context_files: ctxFiles,
        }, token)) {
          if (ev.type === 'chunk') { raw += ev.text; setStreaming(raw); }
          if (ev.type === 'diffs') { setDiffs(ev.diffs); setStreaming(''); }
          if (ev.type === 'done') break;
          if (ev.type === 'error') throw new Error(ev.message);
        }
      } else {
        for await (const ev of streamSSE(`${API}/code/files/${selFile.id}/suggest/`, {
          instruction: editInstruction
        }, token)) {
          if (ev.type === 'chunk') { raw += ev.text; setStreaming(raw); }
          if (ev.type === 'diffs') { setDiffs(ev.diffs); setStreaming(''); }
          if (ev.type === 'done') break;
          if (ev.type === 'error') throw new Error(ev.message);
        }
      }
    } catch(e) {
      setMessages(prev => [...prev, {role:'assistant', content:`编辑建议失败: ${e.message}`}]);
    } finally { setGenerating(false); setStreaming(''); }
  };

  // --- 应用选中的 Diff ---
  const applyDiffs = async () => {
    const accepted = diffs.filter((_, i) => diffStates[i] === 'accepted');
    if (!accepted.length) return showAlert('请先选择要接受的修改', '提示');

    if (uploadMode === 'local') {
      // 本地模式：在浏览器内直接 apply，不调用服务器
      const {content: newContent, applied} = applyDiffsLocally(fileContent, accepted);
      setFileContent(newContent);
      if (selLocalPath) {
        setLocalFiles(p => ({...p, [selLocalPath]: {...p[selLocalPath], content: newContent, modified: true}}));
        setPendingDiskSave(true);
      }
      setDiffs([]); setDiffStates({}); setEditInstruction(''); setRightPanel('chat');
      setMessages(prev => [...prev, {id:Date.now(), role:'assistant',
        content:`已应用 ${applied} 处修改（本地预览，点击"写入磁盘"或"下载"保存）`}]);
    } else {
      try {
        const res = await P(`${API}/code/files/${selFile.id}/apply_diffs/`, {
          diffs: accepted, change_summary: editInstruction || 'AI建议'
        });
        setFileContent(res.new_content);
        setSelFile(prev => ({...prev, current_version: res.current_version}));
        setDiffs([]); setDiffStates({}); setEditInstruction(''); setRightPanel('chat');
        setMessages(prev => [...prev, {id:Date.now(), role:'assistant',
          content:`已应用 ${res.applied_count} 处修改，当前版本 v${res.current_version}`}]);
      } catch(e) { showAlert('应用失败: ' + e.message, '错误'); }
    }
  };

  const createProject = async () => {
    if (!newProjData.name.trim()) return;
    try {
      const p = await P(`${API}/code/projects/`, newProjData);
      await loadProjects();
      setShowNewProj(false);
      setNewProjData({name:'',description:'',language:''});
      openProject(p);
    } catch(e) { showAlert('创建失败: ' + e.message, '错误'); }
  };

  const deleteProject = async (id) => {
    const confirmed = await showConfirm('确认删除整个项目？');
    if (!confirmed) return;
    try {
      await F(`${API}/code/projects/${id}/`, {method:'DELETE', headers:{'Authorization':`Token ${token}`}});
      await loadProjects();
      if (proj?.id === id) { setV('home'); setProj(null); }
    } catch {}
  };

  // ─── 首页：项目列表 ───
  if (v === 'home') {
    return (
      <div className="app">
        <div className={`sb ${sbOpen?'open':''}`}>
          <div className="sb-hd">
            <h1>代码助手</h1>
            <p>AI · 记忆 · Diff</p>
          </div>
          <div className="sb-nav">
            <div className="ns"><div className="ns-t">项目</div>
              {projects.map(p => (
                <div key={p.id} className="ni" onClick={()=>openProject(p)}>
                  <i>{'</>'}</i>{p.name}
                </div>
              ))}
            </div>
          </div>
          <div style={{padding:'10px 8px',borderTop:'1px solid var(--border)'}}>
            <button className="btn btn-s" style={{width:'100%',fontSize:12}} onClick={()=>window.location.hash='#/'}>← 返回 MineAI</button>
          </div>
        </div>
        <div className="main">
          <div className="top">
            <button className="menu-btn" onClick={()=>setSbOpen(!sbOpen)}><Icon name="menu" size={18} /></button>
            <span className="top-t">代码助手</span>
            <button className="btn btn-p btn-sm" onClick={()=>setShowNewProj(true)}>+ 新建项目</button>
          </div>
          <div className="ct">
            {projects.length === 0
              ? <div className="empty"><h3>代码助手</h3><p>上传代码项目，AI 帮你理解、重构、生成代码</p><br/>
                  <button className="btn btn-p" onClick={()=>setShowNewProj(true)}>新建项目</button></div>
              : <div className="g3">
                  {projects.map(p => (
                    <div key={p.id} className="card" style={{cursor:'pointer'}} onClick={()=>openProject(p)}>
                      <div style={{display:'flex',alignItems:'center',gap:10}}>
                        <span style={{fontFamily:'var(--mono)',fontSize:18,color:'var(--blue)'}}>{'</>'}</span>
                        <div>
                          <div style={{fontFamily:'var(--serif)',fontSize:16,color:'var(--fg)'}}>{p.name}</div>
                          <div style={{fontSize:11,color:'var(--fg3)'}}>{p.language || '未设定语言'} · {p.file_count} 文件</div>
                        </div>
                      </div>
                      <div style={{fontSize:12,color:'var(--fg2)',marginTop:4}}>{p.description||'暂无描述'}</div>
                      <div style={{display:'flex',justifyContent:'flex-end',marginTop:8}}>
                        <button className="btn btn-sm" style={{background:'var(--red)',color:'#fff',fontSize:11}}
                          onClick={e=>{e.stopPropagation();deleteProject(p.id);}}>删除</button>
                      </div>
                    </div>
                  ))}
                </div>
            }
          </div>
        </div>
        {showNewProj && (
          <div className="modal-ov" onClick={e=>e.target===e.currentTarget&&setShowNewProj(false)}>
            <div className="modal">
              <h2>新建代码项目</h2>
              <div className="fg"><label>项目名称</label><input value={newProjData.name} onChange={e=>setNewProjData(p=>({...p,name:e.target.value}))} placeholder="我的项目"/></div>
              <div className="fg"><label>描述</label><textarea value={newProjData.description} onChange={e=>setNewProjData(p=>({...p,description:e.target.value}))} placeholder="项目简介..." style={{minHeight:60}}/></div>
              <div className="fg"><label>主要语言</label><input value={newProjData.language} onChange={e=>setNewProjData(p=>({...p,language:e.target.value}))} placeholder="python / javascript / go..."/></div>
              <div style={{display:'flex',gap:8,justifyContent:'flex-end',marginTop:16}}>
                <button className="btn btn-s" onClick={()=>setShowNewProj(false)}>取消</button>
                <button className="btn btn-p" onClick={createProject}>创建</button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ─── 项目工作区 ───
  const acceptedCount = Object.values(diffStates).filter(s=>s==='accepted').length;

  // 当前激活的文件路径（两种模式统一）
  const activeFilePath = uploadMode === 'local' ? selLocalPath : selFile?.path;
  const hasActiveFile = uploadMode === 'local' ? !!selLocalPath : !!selFile;

  // 本地模式的文件列表（转换为 FileTree 兼容格式）
  const localFileList = Object.entries(localFiles).map(([path, f]) => ({
    id: path, path, language: detectLangLocal(path), size: f.content.length, modified: f.modified,
  }));
  function detectLangLocal(path) {
    const extMap = {'.py':'python','.js':'javascript','.ts':'typescript','.tsx':'tsx','.jsx':'jsx',
      '.java':'java','.go':'go','.rs':'rust','.cpp':'cpp','.c':'c','.cs':'csharp','.rb':'ruby',
      '.php':'php','.swift':'swift','.kt':'kotlin','.sh':'bash','.yml':'yaml','.yaml':'yaml',
      '.json':'json','.html':'html','.css':'css','.sql':'sql','.md':'markdown','.vue':'vue'};
    const ext = path.slice(path.lastIndexOf('.')).toLowerCase();
    return extMap[ext] || 'text';
  }

  return (
    <div className="app">
      {/* ─ 侧边栏：文件树 ─ */}
      <div className={`sb ${sbOpen?'open':''}`} style={{width:230}}>
        <div className="sb-hd">
          <h1 style={{fontSize:15,cursor:'pointer'}} onClick={()=>{setV('home');setProj(null);setSbOpen(false);}}>← {proj?.name||'代码助手'}</h1>
          <p style={{fontSize:10,color:'var(--blue)'}}>{proj?.language||''}</p>
        </div>

        {/* 模式切换 */}
        <div style={{padding:'6px 10px',borderBottom:'1px solid var(--border)',display:'flex',gap:4}}>
          <button className={`btn btn-sm${uploadMode==='local'?' btn-p':' btn-s'}`}
            style={{flex:1,fontSize:11}}
            onClick={()=>setUploadMode('local')}>本地模式</button>
          <button className={`btn btn-sm${uploadMode==='server'?' btn-p':' btn-s'}`}
            style={{flex:1,fontSize:11}}
            onClick={()=>setUploadMode('server')}>服务端</button>
        </div>

        {/* 上传/打开文件夹 */}
        <div style={{padding:'8px 10px',borderBottom:'1px solid var(--border)'}}>
          {uploadMode === 'local' ? (
            <>
              {fsaSupported && (
                <button className="btn btn-s" style={{width:'100%',fontSize:11,marginBottom:4,
                  background:'var(--bg4)',border:'1px dashed var(--border2)',borderRadius:6}}
                  onClick={openDirectory} disabled={scanning}>
                  {scanning ? '扫描中…' : '打开本地文件夹'}
                </button>
              )}
              <label style={{display:'block',background:'var(--bg4)',border:'1px dashed var(--border2)',
                borderRadius:6,padding:'5px',textAlign:'center',cursor:'pointer',fontSize:11,color:'var(--fg2)'}}>
                {fsaSupported ? '或 上传文件夹' : '选择文件夹'}
                <input type="file" multiple webkitdirectory="" style={{display:'none'}}
                  onChange={e=>uploadFiles(e.target.files)} disabled={scanning}/>
              </label>
              <label style={{display:'block',background:'var(--bg4)',border:'1px dashed var(--border2)',
                borderRadius:6,padding:'5px',textAlign:'center',cursor:'pointer',fontSize:11,color:'var(--fg2)',marginTop:4}}>
                上传文件
                <input type="file" multiple style={{display:'none'}}
                  onChange={e=>uploadFiles(e.target.files)} disabled={scanning}/>
              </label>
            </>
          ) : (
            <>
              <div style={{fontSize:10,color:'var(--fg3)',marginBottom:4}}>
                限制：≤{serverLimits.max_files} 文件 · ≤{serverLimits.max_total_mb}MB
              </div>
              <label style={{display:'block',background:'var(--bg4)',border:'1px dashed var(--border2)',
                borderRadius:6,padding:'5px',textAlign:'center',cursor:'pointer',fontSize:11,color:'var(--fg2)'}}>
                上传文件夹到服务器
                <input type="file" multiple webkitdirectory="" style={{display:'none'}}
                  onChange={e=>uploadFiles(e.target.files)}/>
              </label>
              <label style={{display:'block',background:'var(--bg4)',border:'1px dashed var(--border2)',
                borderRadius:6,padding:'5px',textAlign:'center',cursor:'pointer',fontSize:11,color:'var(--fg2)',marginTop:4}}>
                上传文件
                <input type="file" multiple style={{display:'none'}}
                  onChange={e=>uploadFiles(e.target.files)}/>
              </label>
            </>
          )}
        </div>

        {/* 扫描进度 */}
        {scanning && scanProgress && (
          <div style={{padding:'10px',background:'var(--bg3)',borderBottom:'1px solid var(--border)'}}>
            <div style={{fontSize:11,color:'var(--gold)',marginBottom:4}}>
              正在扫描… 已发现 {scanProgress.scanned} 个文件
            </div>
            <div style={{fontSize:10,color:'var(--fg3)',overflow:'hidden',textOverflow:'ellipsis',
              whiteSpace:'nowrap',maxWidth:180}} title={scanProgress.currentFile}>
              {scanProgress.currentFile}
            </div>
            <button className="btn btn-sm btn-s" style={{marginTop:6,fontSize:10}}
              onClick={()=>{scanAbortRef.current=true;setScanning(false);setScanProgress(null);}}>取消</button>
          </div>
        )}

        {/* 文件树 */}
        <div style={{flex:1,overflowY:'auto',padding:'6px 0'}}>
          {uploadMode === 'local'
            ? <FileTree
                files={localFileList}
                selectedId={selLocalPath}
                onSelect={f => selectLocalFile(f.id)}
                onDelete={null}
              />
            : <FileTree files={files} selectedId={selFile?.id} onSelect={selectFile} onDelete={deleteFile} />
          }
        </div>

        {/* 服务端模式：记忆统计 */}
        {uploadMode === 'server' && (
          <div style={{padding:'8px 10px',borderTop:'1px solid var(--border)',fontSize:11}}>
            <div style={{color:'var(--fg3)',marginBottom:4,display:'flex',alignItems:'center',justifyContent:'space-between'}}>
              <span>记忆金字塔</span>
              <button style={{background:'none',color:'var(--gold)',fontSize:10}} onClick={loadMemStats}>刷新</button>
            </div>
            {memStats
              ? <div style={{color:'var(--gold)',fontFamily:'var(--mono)'}}>{memStats.total_nodes} 节点 · {memStats.total_content_chars?.toLocaleString()||0} 字符</div>
              : <div style={{color:'var(--fg3)'}}>点击刷新查看</div>
            }
          </div>
        )}

        {/* 本地模式：文件统计 */}
        {uploadMode === 'local' && localFileList.length > 0 && (
          <div style={{padding:'8px 10px',borderTop:'1px solid var(--border)',fontSize:11,color:'var(--fg3)'}}>
            {localFileList.length} 个文件
            {dirHandle && <span style={{color:'var(--gold)',marginLeft:6}}>· {dirHandle.name}</span>}
            <span style={{display:'block',fontSize:10,marginTop:2,color:'var(--gold)'}}>代码不上传服务器</span>
          </div>
        )}

        <div style={{padding:'8px 10px',borderTop:'1px solid var(--border)'}}>
          <button className="btn btn-s" style={{width:'100%',fontSize:11}}
            onClick={()=>window.location.hash='#/'}>← 返回 MineAI</button>
        </div>
      </div>
      <div className="sb-ov" onClick={()=>setSbOpen(false)} style={{display:sbOpen?'block':'none'}}/>

      {/* ─ 主内容：代码编辑器 + 右侧面板 ─ */}
      <div className="main" style={{flexDirection:'row',overflow:'hidden'}}>

        {/* 代码编辑区 */}
        <div style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden',borderRight:'1px solid var(--border)'}}>
          <div className="top" style={{justifyContent:'space-between'}}>
            <button className="menu-btn" onClick={()=>setSbOpen(!sbOpen)}><Icon name="menu" size={18} /></button>
            <span style={{fontFamily:'var(--mono)',fontSize:12,color:hasActiveFile?'var(--fg)':'var(--fg3)',flex:1,marginLeft:8,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
              {hasActiveFile ? activeFilePath : '← 选择文件'}
              {selFile && uploadMode==='server' && <span style={{fontSize:10,color:'var(--fg3)',marginLeft:8}}>v{selFile.current_version}</span>}
            </span>
            {/* 模式标识 chip */}
            <span style={{fontSize:10,padding:'2px 7px',borderRadius:10,marginRight:6,
              background: uploadMode==='local' ? 'rgba(212,175,55,.15)' : 'rgba(255,255,255,.06)',
              color: uploadMode==='local' ? 'var(--gold)' : 'var(--fg3)'}}>
              {uploadMode==='local' ? '本地 · 不上传' : '服务端'}
            </span>
            {hasActiveFile && <>
              <button className="btn btn-sm btn-s" onClick={saveFile} title="保存 (Ctrl+S)">保存</button>
              {uploadMode === 'local' && (
                <>
                  {dirHandle && localFiles[selLocalPath]?.handle &&
                    <button className="btn btn-sm btn-s" onClick={saveFile} title="写入磁盘" style={{color:'var(--gold)'}}>写盘</button>
                  }
                  <button className="btn btn-sm btn-s" onClick={downloadLocalFile} title="下载文件">下载</button>
                </>
              )}
              {uploadMode === 'server' && <button className="btn btn-sm btn-s" onClick={loadVersions}>历史</button>}
            </>}
          </div>

          {/* 编辑指令栏 */}
          {hasActiveFile && (
            <div style={{padding:'6px 12px',borderBottom:'1px solid var(--border)',display:'flex',gap:6,background:'var(--bg2)'}}>
              <input value={editInstruction} onChange={e=>setEditInstruction(e.target.value)}
                placeholder="输入修改指令，如：提取公共函数、添加错误处理、重命名变量…"
                style={{flex:1,fontSize:12}}
                onKeyDown={e=>e.key==='Enter'&&!e.shiftKey&&suggestEdits()}/>
              <button className={`btn btn-sm btn-ai${generating?' generating':''}`} onClick={suggestEdits} disabled={generating}
                style={{display:'inline-flex',alignItems:'center',gap:6}}>
                <Icon name="spark" size={12} />
                {generating?'生成中…':'AI建议'}
              </button>
              <button className="btn btn-sm btn-s" onClick={()=>{setRightPanel('chat');setChatInput(editInstruction);}}
                style={{display:'inline-flex',alignItems:'center',gap:6}}>
                <Icon name="chat" size={12} /> 询问
              </button>
            </div>
          )}

          {/* 未写盘提示条 */}
          {uploadMode === 'local' && pendingDiskSave && selLocalPath && (
            <div style={{padding:'4px 12px',background:'rgba(212,175,55,.1)',borderBottom:'1px solid var(--border)',
              display:'flex',alignItems:'center',gap:8,fontSize:11}}>
              <span style={{color:'var(--gold)'}}>● 已修改，尚未写入磁盘</span>
              {dirHandle && localFiles[selLocalPath]?.handle && (
                <button className="btn btn-sm" style={{background:'var(--gold)',color:'#000',padding:'2px 8px'}}
                  onClick={saveFile}>写入磁盘</button>
              )}
              <button className="btn btn-sm btn-s" style={{padding:'2px 8px'}} onClick={downloadLocalFile}>下载</button>
            </div>
          )}

          {/* 代码文本编辑器 */}
          {hasActiveFile
            ? <div style={{flex:1,position:'relative',overflow:'hidden'}}>
                {streaming && rightPanel==='diffs' && (
                  <div style={{position:'absolute',top:0,right:0,background:'var(--bg3)',border:'1px solid var(--border)',
                    borderRadius:6,padding:'6px 10px',zIndex:10,fontSize:11,color:'var(--fg3)',maxWidth:320,maxHeight:80,overflow:'hidden',margin:8}}>
                    <span style={{color:'var(--gold)'}}>AI分析中…</span> {streaming.slice(-80)}
                  </div>
                )}
                <textarea value={fileContent} onChange={e=>{
                    setFileContent(e.target.value);
                    if(uploadMode==='local'&&selLocalPath) setLocalFiles(p=>({...p,[selLocalPath]:{...p[selLocalPath],content:e.target.value,modified:true}}));
                  }}
                  style={{width:'100%',height:'100%',background:'var(--bg)',color:'var(--fg)',
                    fontFamily:'var(--mono)',fontSize:13,lineHeight:1.6,padding:'12px 16px',
                    border:'none',outline:'none',resize:'none',tabSize:4}}
                  onKeyDown={e=>{
                    if(e.key==='Tab'){e.preventDefault();const s=e.target.selectionStart,end=e.target.selectionEnd;
                      const val=e.target.value;const nv=val.slice(0,s)+'    '+val.slice(end);
                      setFileContent(nv);requestAnimationFrame(()=>{e.target.selectionStart=e.target.selectionEnd=s+4;});}
                    if(e.key==='s'&&(e.ctrlKey||e.metaKey)){e.preventDefault();saveFile();}
                  }}/>
              </div>
            : <div className="empty" style={{margin:'auto'}}>
                <h3 style={{fontSize:20}}>{'</>'}</h3>
                <p>
                  {uploadMode === 'local'
                    ? (fsaSupported ? '点击"打开本地文件夹"' : '点击"选择文件夹"') + '开始'
                    : '从左侧文件树选择文件或上传代码文件夹'}
                </p>
              </div>
          }
        </div>

        {/* ─ 右侧面板 ─ */}
        <div style={{width:360,display:'flex',flexDirection:'column',overflow:'hidden',background:'var(--bg2)',flexShrink:0}}>
          <div className="tabs" style={{padding:'0 8px',marginBottom:0}}>
            <div className={`tab${rightPanel==='chat'?' on':''}`} onClick={()=>setRightPanel('chat')}>对话</div>
            <div className={`tab${rightPanel==='diffs'?' on':''}`} onClick={()=>setRightPanel('diffs')}>
              Diff {diffs.length>0&&<span style={{fontSize:10,background:'var(--gold)',color:'#000',borderRadius:10,padding:'0 5px',marginLeft:4}}>{diffs.length}</span>}
            </div>
            {uploadMode === 'server' && (
              <div className={`tab${rightPanel==='versions'?' on':''}`} onClick={()=>{setRightPanel('versions');if(!versions.length&&selFile)loadVersions();}}>版本</div>
            )}
          </div>

          {/* 对话面板 */}
          {rightPanel==='chat' && (
            <div style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden'}}>
              <div style={{flex:1,overflowY:'auto',padding:'10px 12px'}}>
                {messages.length===0 && (
                  <div style={{textAlign:'center',padding:'30px 10px',color:'var(--fg3)',fontSize:12}}>
                    <div style={{marginBottom:8}}><Icon name="chat" size={28} /></div>
                    <div>询问代码逻辑、重构建议、bug 排查</div>
                    <div style={{marginTop:4,fontSize:11}}>
                      {uploadMode==='local' ? '本地模式：代码不会存储到服务器' : 'AI 会结合记忆中的全部代码作答'}
                    </div>
                  </div>
                )}
                {messages.map((m,i) => (
                  <div key={m.id||i} className={`cht-m ${m.role==='user'?'u':'a'}`}>
                    <div className="cht-lb">{m.role==='user'?'你':'AI助手'}</div>
                    <div className="cht-bbl" style={{whiteSpace:'pre-wrap',wordBreak:'break-word'}}>
                      {m.content}
                    </div>
                  </div>
                ))}
                {streaming && rightPanel==='chat' && (
                  <div className="cht-m a">
                    <div className="cht-lb">AI助手</div>
                    <div className="cht-bbl" style={{whiteSpace:'pre-wrap',wordBreak:'break-word'}}>{streaming}<span style={{animation:'blink 1s infinite',display:'inline-block',marginLeft:2}}>▌</span></div>
                  </div>
                )}
                <div ref={chatEndRef}/>
              </div>
              <div className="cht-in">
                <input value={chatInput} onChange={e=>setChatInput(e.target.value)}
                  placeholder="询问代码、请求解释或重构…"
                  onKeyDown={e=>e.key==='Enter'&&!e.shiftKey&&sendChat()}/>
                <button className={`btn btn-p btn-sm${generating?' generating':''}`} onClick={sendChat} disabled={generating}>发送</button>
              </div>
            </div>
          )}

          {/* Diff 面板 */}
          {rightPanel==='diffs' && (
            <div style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden'}}>
              {streaming && !diffs.length && (
                <div style={{padding:'12px',color:'var(--gold)',fontSize:12,display:'flex',alignItems:'center',gap:8}}>
                  <div className="load" style={{padding:0}}/>
                  AI 正在分析代码，生成修改建议…
                </div>
              )}
              {diffs.length === 0 && !streaming && (
                <div className="empty" style={{padding:'30px 10px'}}>
                  <p>在编辑器上方输入修改指令<br/>点击"AI建议"生成 Diff</p>
                </div>
              )}
              {diffs.length > 0 && (
                <>
                  <div style={{padding:'8px 12px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',gap:8}}>
                    <span style={{fontSize:12,color:'var(--fg2)'}}>{diffs.length} 处建议</span>
                    <button className="btn btn-sm" style={{background:'var(--green)',color:'#000'}}
                      onClick={()=>{const s={};diffs.forEach((_,i)=>s[i]='accepted');setDiffStates(s);}}>全部接受</button>
                    <button className="btn btn-sm btn-s"
                      onClick={()=>{const s={};diffs.forEach((_,i)=>s[i]='rejected');setDiffStates(s);}}>全部拒绝</button>
                    {acceptedCount > 0 &&
                      <button className="btn btn-sm btn-p" onClick={applyDiffs} style={{marginLeft:'auto'}}>
                        应用 {acceptedCount} 处
                      </button>
                    }
                  </div>
                  <div style={{flex:1,overflowY:'auto',padding:'10px 12px'}}>
                    {diffs.map((d,i) => (
                      <DiffBlock key={i} diff={d} index={i}
                        accepted={diffStates[i]==='accepted'}
                        rejected={diffStates[i]==='rejected'}
                        onAccept={idx=>setDiffStates(p=>({...p,[idx]:'accepted'}))}
                        onReject={idx=>setDiffStates(p=>({...p,[idx]:'rejected'}))}/>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* 版本历史面板（仅服务端模式）*/}
          {rightPanel==='versions' && uploadMode==='server' && (
            <div style={{flex:1,overflowY:'auto',padding:'10px 12px'}}>
              {!selFile && <div className="empty"><p>请先选择文件</p></div>}
              {selFile && versions.length === 0 && <div className="empty"><p>暂无历史版本</p></div>}
              {versions.map(v => (
                <div key={v.version} style={{padding:'10px 12px',border:'1px solid var(--border)',borderRadius:6,marginBottom:8}}>
                  <div style={{display:'flex',alignItems:'center',gap:8}}>
                    <span style={{fontFamily:'var(--mono)',fontSize:12,color:'var(--gold)'}}>v{v.version}</span>
                    <span style={{fontSize:11,color:'var(--fg2)',flex:1}}>{v.change_summary||'无说明'}</span>
                    <span style={{fontSize:10,color:'var(--fg3)'}}>{v.size} B</span>
                  </div>
                  <div style={{fontSize:10,color:'var(--fg3)',marginTop:3}}>{v.created_at?.slice(0,16)}</div>
                  <button className="btn btn-sm btn-s" style={{marginTop:6,fontSize:11}} onClick={()=>rollback(v.version)}>
                    回滚到此版本
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

{% endverbatim %}
{% verbatim %}
// ── Claude Bridge App ────────────────────────────────────────

// Tool metadata: icon text + color for each Claude Code tool
const TOOL_META = {
  Read:     {icon:'book',     label:'Read',      color:'var(--blue)'},
  Write:    {icon:'pen',      label:'Write',     color:'var(--gold)'},
  Edit:     {icon:'note',     label:'Edit',      color:'var(--gold)'},
  Bash:     {icon:'terminal', label:'Bash',      color:'var(--red)'},
  Glob:     {icon:'folder',   label:'Glob',      color:'var(--green)'},
  Grep:     {icon:'search',   label:'Grep',      color:'var(--cyan)'},
  LS:       {icon:'clipboard',label:'LS',        color:'var(--fg2)'},
  WebSearch:{icon:'globe',    label:'WebSearch', color:'var(--purple)'},
  WebFetch: {icon:'globe',    label:'WebFetch',  color:'var(--purple)'},
  TodoWrite:{icon:'check',    label:'TodoWrite', color:'var(--green)'},
  TodoRead: {icon:'pin',      label:'TodoRead',  color:'var(--fg2)'},
};

function toolMeta(name) {
  return TOOL_META[name] || {icon:'settings', label: name || 'Tool', color:'var(--fg3)'};
}

// ── Permission mode badge ──
function PermBadge({mode}) {
  const cfg = {
    full_auto:  {label:'全自动',  bg:'rgba(232,93,47,.18)', color:'#e85d2f'},
    read_only:  {label:'只读',    bg:'rgba(90,184,122,.18)', color:'var(--green)'},
    default:    {label:'默认',    bg:'rgba(255,255,255,.08)', color:'var(--fg3)'},
  }[mode] || {label: mode, bg:'rgba(255,255,255,.08)', color:'var(--fg3)'};
  return <span style={{fontSize:10,padding:'2px 7px',borderRadius:10,background:cfg.bg,color:cfg.color,fontWeight:600,letterSpacing:.5}}>{cfg.label}</span>;
}

// ── Status dot ──
function StatusDot({status, style={}}) {
  const c = {
    online:'var(--green)', pending:'var(--gold)', running:'var(--blue)',
    waiting:'var(--orange)', completed:'var(--green)', error:'var(--red)',
    cancelled:'var(--fg3)', offline:'var(--fg3)',
  }[status] || 'var(--fg3)';
  const pulse = ['running','waiting','pending'].includes(status);
  return (
    <span style={{display:'inline-block',width:7,height:7,borderRadius:'50%',
      background:c,flexShrink:0,
      boxShadow: pulse ? `0 0 0 2px ${c}44` : 'none',
      animation: pulse ? 'pulse 1.6s ease-in-out infinite' : 'none', ...style}}/>
  );
}

// ── Tool call card ──
function ToolUseCard({content}) {
  const [open, setOpen] = React.useState(false);
  const meta = toolMeta(content.tool_name);
  const inp = content.tool_input || {};

  // Pretty summary line
  const summary = (() => {
    if (inp.file_path) return inp.file_path;
    if (inp.command)   return inp.command;
    if (inp.pattern)   return inp.pattern;
    if (inp.path)      return inp.path;
    if (inp.old_string) return 'edit block';
    const keys = Object.keys(inp);
    return keys.length ? `${keys[0]}: ${String(inp[keys[0]]).slice(0,60)}` : '';
  })();

  return (
    <div style={{border:'1px solid var(--border2)',borderRadius:8,overflow:'hidden',marginBottom:6,fontSize:12}}>
      <div onClick={()=>setOpen(o=>!o)}
        style={{display:'flex',alignItems:'center',gap:8,padding:'7px 12px',background:'var(--bg3)',cursor:'pointer',userSelect:'none'}}>
        <span style={{display:'inline-flex',alignItems:'center'}}><Icon name={meta.icon} size={14} /></span>
        <span style={{fontWeight:600,color:meta.color,fontFamily:'var(--mono)',fontSize:11}}>{content.tool_name}</span>
        {summary && <span style={{color:'var(--fg3)',flex:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{summary}</span>}
        <span style={{color:'var(--fg3)',fontSize:10,marginLeft:'auto'}}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={{padding:'8px 12px',background:'var(--bg2)',borderTop:'1px solid var(--border)'}}>
          <pre style={{margin:0,fontFamily:'var(--mono)',fontSize:11,color:'var(--fg2)',whiteSpace:'pre-wrap',wordBreak:'break-all',maxHeight:200,overflowY:'auto'}}>
            {JSON.stringify(inp, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// ── Tool result card ──
function ToolResultCard({content}) {
  const [open, setOpen] = React.useState(false);
  const isErr = content.is_error;
  const text = content.content || '';
  const lines = text.split('\n').length;
  return (
    <div style={{border:`1px solid ${isErr?'var(--red)':'var(--border)'}`,borderRadius:8,overflow:'hidden',marginBottom:6,fontSize:12}}>
      <div onClick={()=>setOpen(o=>!o)}
        style={{display:'flex',alignItems:'center',gap:8,padding:'5px 12px',background:'var(--bg2)',cursor:'pointer',userSelect:'none'}}>
        <span style={{display:'inline-flex',alignItems:'center'}}>
          {isErr ? <Icon name="x" size={12} /> : <Icon name="check" size={12} />}
        </span>
        <span style={{color:isErr?'var(--red)':'var(--fg3)',fontFamily:'var(--mono)',fontSize:10,flex:1}}>
          {isErr ? '工具出错' : `结果 (${lines} 行)`}
        </span>
        <span style={{color:'var(--fg3)',fontSize:10}}>{open ? '▲' : '▼'}</span>
      </div>
      {open && text && (
        <div style={{padding:'8px 12px',borderTop:'1px solid var(--border)',background:'var(--bg)'}}>
          <pre style={{margin:0,fontFamily:'var(--mono)',fontSize:10,color:isErr?'var(--red)':'var(--fg2)',whiteSpace:'pre-wrap',wordBreak:'break-all',maxHeight:300,overflowY:'auto',lineHeight:1.5}}>
            {text}
          </pre>
        </div>
      )}
    </div>
  );
}

// ── Permission request card ──
function PermissionCard({content, onRespond}) {
  const [responded, setResponded] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const meta = toolMeta(content.tool_name);

  const respond = async (decision) => {
    setLoading(true);
    await onRespond(content.permission_id, decision);
    setResponded(decision);
    setLoading(false);
  };

  return (
    <div style={{border:`2px solid ${responded==='approved'?'var(--green)':responded==='denied'?'var(--red)':'var(--gold)'}`,
      borderRadius:10,padding:'12px 16px',marginBottom:8,background:'rgba(255,200,0,.04)'}}>
      <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}>
        <span style={{display:'inline-flex',alignItems:'center'}}><Icon name="alert" size={16} /></span>
        <div>
          <div style={{fontSize:12,fontWeight:700,color:'var(--gold)'}}>权限请求</div>
          <div style={{fontSize:11,color:'var(--fg3)'}}>Claude Code 请求使用工具</div>
        </div>
      </div>
      <div style={{display:'flex',alignItems:'center',gap:8,padding:'8px 12px',background:'var(--bg3)',borderRadius:6,marginBottom:10}}>
        <span style={{display:'inline-flex',alignItems:'center'}}><Icon name={meta.icon} size={14} /></span>
        <span style={{fontFamily:'var(--mono)',fontSize:12,color:meta.color,fontWeight:600}}>{content.tool_name}</span>
      </div>
      {content.tool_input && Object.keys(content.tool_input).length > 0 && (
        <pre style={{fontFamily:'var(--mono)',fontSize:10,color:'var(--fg3)',background:'var(--bg)',padding:'8px',borderRadius:4,marginBottom:10,overflow:'auto',maxHeight:120,whiteSpace:'pre-wrap',wordBreak:'break-all'}}>
          {JSON.stringify(content.tool_input, null, 2)}
        </pre>
      )}
      {!responded
        ? <div style={{display:'flex',gap:8}}>
            <button disabled={loading}
              onClick={()=>respond('approved')}
              className="btn" style={{flex:1,background:'var(--green)',color:'#000',fontWeight:700,fontSize:12,display:'inline-flex',alignItems:'center',justifyContent:'center',gap:6}}>
              <Icon name="check" size={12} /> 批准
            </button>
            <button disabled={loading}
              onClick={()=>respond('denied')}
              className="btn" style={{flex:1,background:'var(--red)',color:'#fff',fontWeight:700,fontSize:12,display:'inline-flex',alignItems:'center',justifyContent:'center',gap:6}}>
              <Icon name="x" size={12} /> 拒绝
            </button>
          </div>
        : <div style={{textAlign:'center',fontSize:12,color:responded==='approved'?'var(--green)':'var(--red)',fontWeight:600,padding:'4px 0'}}>
            {responded==='approved'
              ? <span style={{display:'inline-flex',alignItems:'center',gap:4}}><Icon name="check" size={12} /> 已批准</span>
              : <span style={{display:'inline-flex',alignItems:'center',gap:4}}><Icon name="x" size={12} /> 已拒绝</span>}
          </div>
      }
    </div>
  );
}

// ── System init card ──
function SystemInitCard({content}) {
  return (
    <div style={{border:'1px solid var(--border2)',borderRadius:10,padding:'12px 16px',marginBottom:8,background:'var(--bg2)'}}>
      <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:8}}>
        <span style={{display:'inline-flex',alignItems:'center'}}><Icon name="bot" size={16} /></span>
        <div>
          <div style={{fontSize:12,fontWeight:700,color:'var(--fg)'}}>Claude Code 会话已启动</div>
          {content.model && <div style={{fontSize:10,color:'var(--fg3)',fontFamily:'var(--mono)'}}>{content.model}</div>}
        </div>
      </div>
      {content.tools && content.tools.length > 0 && (
        <div style={{display:'flex',flexWrap:'wrap',gap:4}}>
          {content.tools.map(t => {
            const m = toolMeta(t);
            return (
              <span key={t} style={{fontSize:10,padding:'2px 6px',borderRadius:4,background:'var(--bg4)',color:m.color,fontFamily:'var(--mono)',display:'inline-flex',alignItems:'center',gap:4}}>
                <Icon name={m.icon} size={10} /> {t}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Result card ──
function ResultCard({content}) {
  const ok = !content.is_error;
  return (
    <div style={{border:`1px solid ${ok?'var(--green)':'var(--red)'}`,borderRadius:10,padding:'12px 16px',marginBottom:8,background:ok?'rgba(90,184,122,.05)':'rgba(196,90,90,.05)'}}>
      <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:6}}>
        <span style={{display:'inline-flex',alignItems:'center'}}>{ok ? <Icon name="check" size={16} /> : <Icon name="x" size={16} />}</span>
        <div style={{flex:1}}>
          <div style={{fontSize:12,fontWeight:700,color:ok?'var(--green)':'var(--red)'}}>
            {ok ? '任务完成' : '任务出错'}
          </div>
          {content.cost_usd > 0 && (
            <div style={{fontSize:10,color:'var(--fg3)'}}>
              花费 ${content.cost_usd.toFixed(4)}
            </div>
          )}
        </div>
      </div>
      {content.text && (
        <p style={{fontSize:12,color:'var(--fg2)',margin:0,lineHeight:1.6,whiteSpace:'pre-wrap'}}>{content.text}</p>
      )}
    </div>
  );
}

// ── Edit diff card (when Claude writes/edits files) ──
function EditDiffCard({content}) {
  const [open, setOpen] = React.useState(true);
  const inp = content.tool_input || {};
  const isWrite = content.tool_name === 'Write';
  const isEdit  = content.tool_name === 'Edit';
  const filePath = inp.file_path || inp.path || '';

  if (!isEdit && !isWrite) return null;

  return (
    <div style={{border:'1px solid var(--border2)',borderRadius:8,overflow:'hidden',marginBottom:6}}>
      <div onClick={()=>setOpen(o=>!o)}
        style={{display:'flex',alignItems:'center',gap:8,padding:'6px 12px',background:'var(--bg3)',cursor:'pointer'}}>
        <span style={{display:'inline-flex',alignItems:'center'}}>{isWrite ? <Icon name="pen" size={12} /> : <Icon name="note" size={12} />}</span>
        <span style={{fontFamily:'var(--mono)',fontSize:11,color:'var(--gold)',flex:1}}>{filePath || (isWrite?'写入文件':'编辑文件')}</span>
        <span style={{fontSize:10,color:'var(--fg3)'}}>{open?'▲':'▼'}</span>
      </div>
      {open && isEdit && inp.old_string !== undefined && (
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',fontSize:11}}>
          <div style={{padding:'8px 12px',background:'rgba(196,90,90,.08)',borderRight:'1px solid var(--border)'}}>
            <div style={{fontSize:9,color:'var(--red)',marginBottom:4,fontWeight:600}}>删除</div>
            <pre style={{margin:0,fontFamily:'var(--mono)',whiteSpace:'pre-wrap',wordBreak:'break-word',color:'var(--fg2)',lineHeight:1.5,maxHeight:200,overflow:'auto'}}>{inp.old_string}</pre>
          </div>
          <div style={{padding:'8px 12px',background:'rgba(90,184,122,.08)'}}>
            <div style={{fontSize:9,color:'var(--green)',marginBottom:4,fontWeight:600}}>新增</div>
            <pre style={{margin:0,fontFamily:'var(--mono)',whiteSpace:'pre-wrap',wordBreak:'break-word',color:'var(--fg)',lineHeight:1.5,maxHeight:200,overflow:'auto'}}>{inp.new_string}</pre>
          </div>
        </div>
      )}
      {open && isWrite && inp.content && (
        <div style={{padding:'8px 12px',background:'var(--bg)'}}>
          <pre style={{margin:0,fontFamily:'var(--mono)',fontSize:10,color:'var(--fg2)',whiteSpace:'pre-wrap',wordBreak:'break-all',maxHeight:300,overflowY:'auto',lineHeight:1.5}}>{inp.content.slice(0,3000)}</pre>
        </div>
      )}
    </div>
  );
}

// ── A single message in the feed ──
function BridgeMessageItem({msg, onRespond}) {
  const {direction, msg_type, content} = msg;

  // user input bubble
  if (msg_type === 'user_input') {
    return (
      <div className="cht-m u" style={{marginBottom:8}}>
        <div className="cht-lb">你</div>
        <div className="cht-bbl" style={{whiteSpace:'pre-wrap',wordBreak:'break-word'}}>{content.text}</div>
      </div>
    );
  }

  // Claude text bubble
  if (msg_type === 'text') {
    return (
      <div className="cht-m a" style={{marginBottom:8}}>
        <div className="cht-lb">Claude</div>
        <div className="cht-bbl" style={{whiteSpace:'pre-wrap',wordBreak:'break-word',lineHeight:1.7}}>{content.text}</div>
      </div>
    );
  }

  if (msg_type === 'system_init')       return <SystemInitCard content={content} />;
  if (msg_type === 'result')            return <ResultCard content={content} />;
  if (msg_type === 'permission_request') return <PermissionCard content={content} onRespond={onRespond} />;
  if (msg_type === 'permission_response') {
    const ok = content.decision === 'approved';
    return (
      <div style={{display:'flex',alignItems:'center',gap:6,fontSize:11,color:'var(--fg3)',marginBottom:6,padding:'4px 8px'}}>
        <span style={{display:'inline-flex',alignItems:'center'}}>{ok ? <Icon name="check" size={11} /> : <Icon name="x" size={11} />}</span>
        <span style={{color:ok?'var(--green)':'var(--red)'}}>
          {ok?'批准':'拒绝'} {content.tool_name}
        </span>
      </div>
    );
  }

  if (msg_type === 'tool_use') {
    const isFileMod = ['Write','Edit'].includes(content.tool_name);
    return isFileMod
      ? <EditDiffCard content={content} />
      : <ToolUseCard content={content} />;
  }

  if (msg_type === 'tool_result') return <ToolResultCard content={content} />;

  if (msg_type === 'error') {
    return (
      <div style={{border:'1px solid var(--red)',borderRadius:8,padding:'10px 14px',marginBottom:6,background:'rgba(196,90,90,.07)',fontSize:12}}>
        <div style={{color:'var(--red)',fontWeight:600,marginBottom:4,display:'inline-flex',alignItems:'center',gap:6}}><Icon name="x" size={12} /> 错误</div>
        <pre style={{margin:0,color:'var(--red)',fontFamily:'var(--mono)',fontSize:11,whiteSpace:'pre-wrap'}}>{content.text}</pre>
      </div>
    );
  }

  return null;
}

// ── New Session Modal ──
function NewSessionModal({connections, onClose, onCreated}) {
  const [connId, setConnId]   = React.useState(connections.find(c=>c.status==='online')?.id || '');
  const [dir, setDir]         = React.useState('~');
  const [prompt, setPrompt]   = React.useState('');
  const [pmode, setPmode]     = React.useState('default');
  const [loading, setLoading] = React.useState(false);
  const [err, setErr]         = React.useState('');

  const start = async () => {
    if (!connId)   return setErr('请选择一个在线的桥接连接');
    if (!prompt.trim()) return setErr('请输入任务描述');
    setLoading(true); setErr('');
    try {
      const res = await P(`${API}/bridge/connections/${connId}/sessions/`, {working_dir: dir, prompt, permission_mode: pmode});
      onCreated(connId, res.session_id);
      onClose();
    } catch(e) { setErr(e.message); }
    setLoading(false);
  };

  const onlineConns = connections.filter(c => c.status === 'online');

  return (
    <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,.55)',zIndex:1000,display:'flex',alignItems:'center',justifyContent:'center'}}
      onClick={e=>e.target===e.currentTarget&&onClose()}>
      <div style={{background:'var(--bg2)',border:'1px solid var(--border2)',borderRadius:14,padding:'28px 32px',width:'min(540px,95vw)',boxShadow:'0 20px 60px rgba(0,0,0,.5)'}}>
        <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:22}}>
          <span style={{display:'inline-flex',alignItems:'center'}}><Icon name="bolt" size={18} /></span>
          <h2 style={{fontSize:17,fontFamily:'var(--serif)',margin:0}}>新建 Claude Code 会话</h2>
        </div>

        <div className="fg" style={{marginBottom:14}}>
          <label>桥接客户端</label>
          {onlineConns.length === 0
            ? <div style={{padding:'8px 12px',borderRadius:6,background:'var(--bg3)',color:'var(--fg3)',fontSize:12,display:'inline-flex',alignItems:'center',gap:6}}>
                <Icon name="alert" size={12} /> 暂无在线连接，请先启动 claude_bridge.py
              </div>
            : <select value={connId} onChange={e=>setConnId(e.target.value)}>
                {onlineConns.map(c => <option key={c.id} value={c.id}>{c.name} ({c.os_info})</option>)}
              </select>
          }
        </div>

        <div className="fg" style={{marginBottom:14}}>
          <label>工作目录（本地路径）</label>
          <input value={dir} onChange={e=>setDir(e.target.value)} placeholder="~/projects/myapp" style={{fontFamily:'var(--mono)',fontSize:12}}/>
        </div>

        <div className="fg" style={{marginBottom:14}}>
          <label>权限模式</label>
          <select value={pmode} onChange={e=>setPmode(e.target.value)}>
            <option value="default">默认 — Claude Code 标准权限</option>
            <option value="full_auto">全自动 — 跳过所有权限确认（慎用）</option>
            <option value="read_only">只读 — 仅允许 Read / Glob / Grep</option>
          </select>
        </div>

        <div className="fg" style={{marginBottom:18}}>
          <label>任务描述 / 初始提示词</label>
          <textarea value={prompt} onChange={e=>setPrompt(e.target.value)} rows={4}
            placeholder="描述你希望 Claude Code 完成的任务，例如：分析 src/ 目录下的代码架构，找出潜在性能问题并给出优化建议…"
            style={{resize:'vertical',fontSize:13,lineHeight:1.6}}/>
        </div>

        {err && <div style={{color:'var(--red)',fontSize:12,marginBottom:12}}>{err}</div>}

        <div style={{display:'flex',gap:10,justifyContent:'flex-end'}}>
          <button className="btn btn-s" onClick={onClose}>取消</button>
          <button className="btn btn-p" onClick={start} disabled={loading || onlineConns.length===0}>
            {loading ? '启动中…' : '▶ 启动会话'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Setup Instructions Page ──
function BridgeSetupPage({user, onDownload}) {
  const [showManual, setShowManual] = React.useState(false);
  const token = localStorage.getItem('mf_token') || 'YOUR_TOKEN_HERE';
  const origin = window.location.origin;
  const installCmd = `curl -sSL ${origin}/api/bridge/install/?token=${token} | bash`;

  const copyCmd = () => {
    navigator.clipboard.writeText(installCmd);
    showAlert('已复制到剪贴板', '复制成功');
  };

  return (
    <div style={{flex:1,overflowY:'auto',display:'flex',alignItems:'flex-start',justifyContent:'center',padding:'40px 20px'}}>
      <div style={{maxWidth:600,width:'100%'}}>
        <div style={{textAlign:'center',marginBottom:36}}>
          <div style={{marginBottom:12}}><Icon name="bolt" size={48} /></div>
          <h1 style={{fontFamily:'var(--serif)',fontSize:26,marginBottom:8}}>Claude Bridge</h1>
          <p style={{color:'var(--fg3)',fontSize:14,lineHeight:1.7}}>
            将您本地的 Claude Code 连接到平台，在任何地方可视化监控和控制 AI 编码会话
          </p>
        </div>

        <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:12,marginBottom:32}}>
          {[
            {icon:'link',title:'安全连接',desc:'Token 认证，数据经由平台中转'},
            {icon:'eye',title:'全程可视',desc:'工具调用、文件 Diff、权限请求实时呈现'},
            {icon:'globe',title:'远程控制',desc:'在任何设备上发消息、审批权限'},
          ].map(f => (
            <div key={f.title} style={{border:'1px solid var(--border)',borderRadius:10,padding:'16px',textAlign:'center'}}>
              <div style={{marginBottom:8}}><Icon name={f.icon} size={22} /></div>
              <div style={{fontSize:12,fontWeight:700,marginBottom:4}}>{f.title}</div>
              <div style={{fontSize:11,color:'var(--fg3)',lineHeight:1.5}}>{f.desc}</div>
            </div>
          ))}
        </div>

        <div style={{border:'1px solid var(--border2)',borderRadius:12,overflow:'hidden',marginBottom:20}}>
          <div style={{padding:'14px 20px',background:'var(--bg3)',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',gap:10,justifyContent:'space-between'}}>
            <div style={{display:'flex',alignItems:'center',gap:10}}>
              <span style={{display:'inline-flex',alignItems:'center'}}><Icon name="rocket" size={16} /></span>
              <span style={{fontWeight:700,fontSize:14}}>一键安装</span>
            </div>
          </div>
          <div style={{padding:'24px'}}>
            <p style={{fontSize:13,color:'var(--fg2)',marginBottom:16}}>在您的服务器或本地终端执行以下命令，即可自动完成所有配置并启动服务：</p>
            
            <div style={{position:'relative',marginBottom:20}}>
              <pre style={{
                background:'var(--bg)',padding:'16px 50px 16px 16px',borderRadius:8,
                fontFamily:'var(--mono)',fontSize:12,color:'var(--gold2)',
                border:'1px solid var(--border2)',overflowX:'auto',whiteSpace:'pre-wrap',wordBreak:'break-all'
              }}>
                {installCmd}
              </pre>
              <button 
                onClick={copyCmd}
                style={{
                  position:'absolute',right:12,top:12,background:'var(--bg4)',color:'var(--fg2)',
                  padding:'6px',borderRadius:6,border:'1px solid var(--border2)',cursor:'pointer'
                }}
                title="复制代码"
              >
                <Icon name="clipboard" size={14} />
              </button>
            </div>

            <div style={{background:'rgba(201,168,108,0.05)',border:'1px solid rgba(201,168,108,0.2)',borderRadius:8,padding:'12px 14px',display:'flex',gap:12}}>
              <Icon name="alert" size={18} style={{color:'var(--gold)',flexShrink:0}} />
              <div style={{fontSize:12,color:'var(--fg2)',lineHeight:1.6}}>
                <strong>注意：</strong>安装脚本会自动检查 Python3 和 Node.js 环境，并尝试安装 <code>@anthropic-ai/claude-code</code>。安装完成后，会以 <code>systemd</code> (Linux) 或 <code>LaunchAgent</code> (macOS) 方式在后台运行。
              </div>
            </div>

            <div style={{textAlign:'center',marginTop:24}}>
              <button 
                className="btn-s" 
                style={{background:'none',border:'none',color:'var(--fg3)',fontSize:12,textDecoration:'underline'}}
                onClick={() => setShowManual(!showManual)}
              >
                {showManual ? '隐藏手动安装步骤' : '需要手动安装？查看传统步骤'}
              </button>
            </div>

            {showManual && (
              <div style={{marginTop:24,paddingTop:24,borderTop:'1px dotted var(--border2)'}}>
                {[
                  {n:1, title:'下载桥接脚本', content:
                    <div>
                      <p style={{fontSize:12,color:'var(--fg2)',marginBottom:10}}>点击下载预配置版本（已内嵌您的 Token）</p>
                      <button className="btn btn-p" style={{fontSize:12}} onClick={onDownload}>⬇ 下载 claude_bridge.py</button>
                    </div>
                  },
                  {n:2, title:'安装依赖', content:
                    <pre style={{background:'var(--bg)',padding:'10px 14px',borderRadius:6,fontFamily:'var(--mono)',fontSize:12,color:'var(--fg2)',margin:0}}>pip install requests</pre>
                  },
                  {n:3, title:'确保 Claude Code CLI 已安装', content:
                    <pre style={{background:'var(--bg)',padding:'10px 14px',borderRadius:6,fontFamily:'var(--mono)',fontSize:12,color:'var(--fg2)',margin:0}}>npm install -g @anthropic-ai/claude-code{'\n'}claude --version  # 验证安装</pre>
                  },
                  {n:4, title:'运行桥接客户端', content:
                    <pre style={{background:'var(--bg)',padding:'10px 14px',borderRadius:6,fontFamily:'var(--mono)',fontSize:12,color:'var(--fg2)',margin:0}}>python claude_bridge.py</pre>
                  },
                ].map(step => (
                  <div key={step.n} style={{display:'flex',gap:14,marginBottom:20}}>
                    <div style={{width:24,height:24,borderRadius:'50%',background:'var(--bg4)',color:'var(--fg3)',
                      display:'flex',alignItems:'center',justifyContent:'center',fontSize:11,fontWeight:700,flexShrink:0,border:'1px solid var(--border2)'}}>
                      {step.n}
                    </div>
                    <div style={{flex:1}}>
                      <div style={{fontSize:13,fontWeight:600,marginBottom:8}}>{step.title}</div>
                      {step.content}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Session view (message feed + input) ──
function BridgeSessionView({session, token}) {
  const [messages, setMessages]   = React.useState([]);
  const [status, setStatus]       = React.useState(session.status);
  const [modelInfo, setModelInfo] = React.useState(session.model_info || {});
  const [input, setInput]         = React.useState('');
  const [sending, setSending]     = React.useState(false);
  const [lastSeq, setLastSeq]     = React.useState(-1);
  const feedRef = React.useRef(null);
  const abortRef = React.useRef(null);

  const scrollDown = () => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  };

  // Connect SSE stream
  React.useEffect(() => {
    setMessages([]);
    setStatus(session.status);
    setModelInfo(session.model_info || {});
    setLastSeq(-1);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    (async () => {
      try {
        const resp = await fetch(
          `${API}/bridge/sessions/${session.id}/stream/?since=-1`,
          {headers: {'Authorization': `Token ${token}`}, signal: ctrl.signal}
        );
        if (!resp.ok) return;
        const reader = resp.body.getReader();
        const dec = new TextDecoder();
        let buf = '';
        while (true) {
          const {done, value} = await reader.read();
          if (done) break;
          buf += dec.decode(value, {stream: true});
          const lines = buf.split('\n');
          buf = lines.pop();
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
              const evt = JSON.parse(line.slice(6));
              if (evt.type === 'message') {
                setMessages(prev => {
                  if (prev.find(m => m.id === evt.id)) return prev;
                  return [...prev, evt];
                });
                setLastSeq(evt.seq);
                setTimeout(scrollDown, 50);
              } else if (evt.type === 'status' || evt.type === 'session_info') {
                setStatus(evt.status);
                if (evt.model_info) setModelInfo(evt.model_info);
              }
            } catch {}
          }
        }
      } catch (e) {
        if (e.name !== 'AbortError') console.warn('SSE error', e);
      }
    })();

    return () => ctrl.abort();
  }, [session.id]);

  const respondPermission = async (permId, decision) => {
    await P(`${API}/bridge/permissions/${permId}/respond/`, {decision});
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    setSending(true);
    try {
      await P(`${API}/bridge/sessions/${session.id}/send/`, {message: input.trim()});
      setInput('');
    } catch(e) { showAlert(e.message, '发送失败'); }
    setSending(false);
  };

  const cancelSession = async () => {
    const confirmed = await showConfirm('确认取消此会话？');
    if (!confirmed) return;
    try { await fetch(`${API}/bridge/sessions/${session.id}/`, {method:'DELETE', headers:{'Authorization':`Token ${token}`}}); }
    catch {}
  };

  const isActive = ['pending','running','waiting'].includes(status);
  const done     = ['completed','error','cancelled'].includes(status);

  const statusLabel = {
    pending:'等待桥接…', running:'运行中', waiting:'等待权限',
    completed:'已完成', error:'出错', cancelled:'已取消',
  }[status] || status;

  return (
    <div style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden'}}>
      {/* session top bar */}
      <div style={{padding:'8px 16px',borderBottom:'1px solid var(--border)',background:'var(--bg2)',display:'flex',alignItems:'center',gap:10,flexShrink:0}}>
        <StatusDot status={status}/>
        <span style={{fontSize:12,color:'var(--fg2)',fontFamily:'var(--mono)',flex:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
          {session.working_dir}
        </span>
        <PermBadge mode={session.permission_mode}/>
        <span style={{fontSize:11,padding:'3px 8px',borderRadius:6,
          background: status==='running'?'rgba(90,140,196,.2)':status==='completed'?'rgba(90,184,122,.2)':status==='error'?'rgba(196,90,90,.2)':'var(--bg3)',
          color: status==='running'?'var(--blue)':status==='completed'?'var(--green)':status==='error'?'var(--red)':'var(--fg3)',
          fontWeight:500}}>
          {statusLabel}
        </span>
        {modelInfo.total_cost_usd > 0 &&
          <span style={{fontSize:10,color:'var(--fg3)'}}>${modelInfo.total_cost_usd.toFixed(4)}</span>}
        {isActive &&
          <button className="btn btn-sm btn-d" style={{fontSize:11}} onClick={cancelSession}>取消</button>}
      </div>

      {/* initial prompt */}
      {session.initial_prompt && (
        <div style={{padding:'10px 16px',borderBottom:'1px solid var(--border)',background:'var(--bg3)',flexShrink:0}}>
          <div style={{fontSize:10,color:'var(--fg3)',marginBottom:3}}>任务描述</div>
          <div style={{fontSize:12,color:'var(--fg2)',lineHeight:1.6,whiteSpace:'pre-wrap'}}>{session.initial_prompt}</div>
        </div>
      )}

      {/* message feed */}
      <div ref={feedRef} style={{flex:1,overflowY:'auto',padding:'14px 16px'}}>
        {messages.length === 0 && isActive && (
          <div style={{textAlign:'center',padding:'40px 20px',color:'var(--fg3)',fontSize:13}}>
            <div style={{marginBottom:8,fontSize:24}}>◆</div>
            <div>等待 Claude Code 响应中</div>
            <div style={{fontSize:11,marginTop:6}}>桥接客户端正在处理…</div>
          </div>
        )}
        {messages.map((m,i) => (
          <BridgeMessageItem key={m.id||i} msg={m} onRespond={respondPermission}/>
        ))}
        {isActive && <div style={{textAlign:'center',padding:'8px 0',color:'var(--fg3)',fontSize:11}}>
          <span style={{animation:'blink 1s infinite'}}>▌</span>
        </div>}
      </div>

      {/* follow-up input */}
      {!done && (
        <div style={{padding:'10px 12px',borderTop:'1px solid var(--border)',background:'var(--bg2)',display:'flex',gap:8,flexShrink:0}}>
          <textarea value={input} onChange={e=>setInput(e.target.value)} rows={2}
            placeholder="发送跟进消息给 Claude Code…"
            style={{flex:1,resize:'none',fontSize:12,lineHeight:1.5}}
            onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();}}}/>
          <button className="btn btn-p" onClick={sendMessage} disabled={sending||!input.trim()} style={{alignSelf:'flex-end',fontSize:12}}>
            {sending?'…':'发送'}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────
function ClaudeBridgeApp({user, onLogout, onUpdateUser}) {
  const [connections, setConnections]       = React.useState([]);
  const [sessions, setSessions]             = React.useState([]);
  const [selectedSession, setSelectedSession] = React.useState(null);
  const [showNewModal, setShowNewModal]     = React.useState(false);
  const [showSetup, setShowSetup]           = React.useState(false);
  const [sbOpen, setSbOpen]                 = React.useState(false);
  const [loadingConns, setLoadingConns]     = React.useState(true);

  const token = user?.token || '';

  const loadConnections = async () => {
    try {
      const res = await F(`${API}/bridge/connections/`);
      setConnections(res);
      if (res.length === 0) setShowSetup(true);
    } catch {}
    setLoadingConns(false);
  };

  const loadSessions = async () => {
    try {
      const res = await F(`${API}/bridge/sessions/`);
      setSessions(res);
    } catch {}
  };

  React.useEffect(() => {
    loadConnections();
    loadSessions();
    const t = setInterval(() => { loadConnections(); loadSessions(); }, 8000);
    return () => clearInterval(t);
  }, []);

  const handleDownloadScript = async () => {
    try {
      const resp = await fetch(`${API}/bridge/client/script/`, {headers:{'Authorization':`Token ${token}`}});
      if (!resp.ok) throw new Error('下载失败');
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'claude_bridge.py'; a.click();
      URL.revokeObjectURL(url);
    } catch(e) { showAlert(e.message, '下载失败'); }
  };

  const handleSessionCreated = async (connId, sessionId) => {
    await loadSessions();
    // Auto-select the new session
    try {
      const s = await F(`${API}/bridge/sessions/${sessionId}/`);
      setSelectedSession(s);
      setSbOpen(false);
    } catch {}
  };

  const onlineCount = connections.filter(c => c.status === 'online').length;

  const statusColor = s => ({
    pending:'var(--gold)',running:'var(--blue)',waiting:'var(--orange)',
    completed:'var(--green)',error:'var(--red)',cancelled:'var(--fg3)',
  }[s] || 'var(--fg3)');

  return (
    <div style={{display:'flex',height:'100vh',flexDirection:'column',overflow:'hidden'}}>
      {/* top nav */}
      <div className="top" style={{flexShrink:0,justifyContent:'space-between',borderBottom:'1px solid var(--border)'}}>
        <button className="menu-btn" onClick={()=>setSbOpen(o=>!o)}><Icon name="menu" size={18} /></button>
        <div style={{display:'flex',alignItems:'center',gap:10}}>
          <span style={{display:'inline-flex',alignItems:'center'}}><Icon name="bolt" size={16} /></span>
          <span style={{fontFamily:'var(--serif)',fontSize:16,fontWeight:700}}>Claude Bridge</span>
          <span style={{fontSize:11,padding:'2px 8px',borderRadius:10,
            background: onlineCount>0?'rgba(90,184,122,.15)':'rgba(255,255,255,.06)',
            color: onlineCount>0?'var(--green)':'var(--fg3)'}}>
            {onlineCount} 在线
          </span>
        </div>
        <div style={{display:'flex',gap:8}}>
          <button className="btn btn-sm btn-s" onClick={handleDownloadScript} title="下载桥接客户端" style={{display:'inline-flex',alignItems:'center',gap:6}}>
            <Icon name="download" size={12} /> 脚本
          </button>
          <button className="btn btn-sm btn-p" onClick={()=>setShowNewModal(true)}>+ 新建会话</button>
          <button className="btn btn-sm btn-s" onClick={onLogout} style={{color:'var(--fg3)'}}>退出</button>
        </div>
      </div>

      <div style={{display:'flex',flex:1,overflow:'hidden'}}>
        {/* ── Sidebar ── */}
        <div className={`sb${sbOpen?' open':''}`} style={{width:260,display:'flex',flexDirection:'column',borderRight:'1px solid var(--border)',overflow:'hidden',background:'var(--bg2)'}}>
          <div style={{padding:'12px 12px 8px',borderBottom:'1px solid var(--border)',flexShrink:0}}>
            <div style={{fontSize:10,color:'var(--fg3)',letterSpacing:1,fontWeight:600,marginBottom:8}}>桥接连接</div>
            {loadingConns && <div style={{fontSize:12,color:'var(--fg3)',padding:'4px 0'}}>加载中…</div>}
            {connections.map(c => (
              <div key={c.id} style={{padding:'6px 8px',borderRadius:6,marginBottom:4,
                background:'var(--bg3)',display:'flex',alignItems:'center',gap:8}}>
                <StatusDot status={c.status}/>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{fontSize:12,fontWeight:500,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{c.name}</div>
                  <div style={{fontSize:10,color:'var(--fg3)'}}>{c.os_info || '—'}</div>
                </div>
                <span style={{fontSize:10,color:c.status==='online'?'var(--green)':'var(--fg3)',flexShrink:0}}>
                  {c.status==='online'?'在线':'离线'}
                </span>
              </div>
            ))}
            {connections.length === 0 && !loadingConns && (
              <div style={{fontSize:11,color:'var(--fg3)',padding:'4px 0',lineHeight:1.5}}>
                暂无连接<br/>
                <span style={{color:'var(--blue)',cursor:'pointer',textDecoration:'underline'}} onClick={handleDownloadScript}>下载脚本</span>后运行
              </div>
            )}
          </div>

          <div style={{flex:1,overflowY:'auto',padding:'8px'}}>
            <div style={{fontSize:10,color:'var(--fg3)',letterSpacing:1,fontWeight:600,padding:'4px 4px 8px'}}>最近会话</div>
            {sessions.map(s => (
              <div key={s.id}
                onClick={async ()=>{
                  try { const full = await F(`${API}/bridge/sessions/${s.id}/`); setSelectedSession(full); setSbOpen(false); }
                  catch {}
                }}
                style={{padding:'8px 10px',borderRadius:7,marginBottom:5,cursor:'pointer',
                  border:`1px solid ${selectedSession?.id===s.id?'var(--gold)':'var(--border)'}`,
                  background: selectedSession?.id===s.id?'var(--bg4)':'var(--bg3)'}}>
                <div style={{display:'flex',alignItems:'center',gap:6,marginBottom:3}}>
                  <StatusDot status={s.status} style={{width:6,height:6}}/>
                  <span style={{fontSize:10,color:statusColor(s.status),fontWeight:600}}>{
                    {pending:'等待',running:'运行中',waiting:'等待权限',completed:'完成',error:'出错',cancelled:'取消'}[s.status]||s.status
                  }</span>
                  <span style={{marginLeft:'auto',fontSize:9,color:'var(--fg3)'}}>{s.created_at?.slice(5,16)}</span>
                </div>
                <div style={{fontSize:11,color:'var(--fg2)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',marginBottom:2}}>
                  {s.initial_prompt || '(无描述)'}
                </div>
                <div style={{fontSize:10,color:'var(--fg3)',fontFamily:'var(--mono)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
                  {s.working_dir}
                </div>
              </div>
            ))}
            {sessions.length === 0 && (
              <div style={{padding:'20px 8px',textAlign:'center',color:'var(--fg3)',fontSize:12}}>
                暂无会话<br/>点击「+ 新建会话」开始
              </div>
            )}
          </div>

          <div style={{padding:'10px 12px',borderTop:'1px solid var(--border)',flexShrink:0}}>
            <button className="btn btn-p" style={{width:'100%',fontSize:12}} onClick={()=>setShowNewModal(true)}>
              + 新建 Claude Code 会话
            </button>
          </div>
        </div>

        {/* ── Main area ── */}
        {!selectedSession
          ? <BridgeSetupPage user={user} onDownload={handleDownloadScript}/>
          : <BridgeSessionView key={selectedSession.id} session={selectedSession} token={token}/>
        }
      </div>

      {showNewModal && (
        <NewSessionModal
          connections={connections}
          onClose={()=>setShowNewModal(false)}
          onCreated={handleSessionCreated}
        />
      )}
    </div>
  );
}

// ── 扫描增强 ScanEnhanceApp ────────────────────────────────────
// 所有算法运行在浏览器端 Web Worker 中，零服务器 CPU 占用

const SCAN_OPS = [
  { key:'curve_flatten',       label:'曲面平整化', desc:'逐列采样边缘+多项式拟合，重映射展平书页弯曲 [浏览器]', icon:'scan', params:[
    {name:'n_strips', label:'拟合精度', type:'range', min:10, max:80, step:5, default:40,
     hint:'值越大多项式次数越高，跟随曲线越精确'}
  ]},
  { key:'perspective_correct', label:'透视校正', desc:'检测文档四角，单应矩阵校正梯形失真 [浏览器]', icon:'scan', params:[] },
  { key:'deskew',              label:'自动纠偏', desc:'投影剖面打分法检测并旋转校正倾斜角 [浏览器]', icon:'triangle', params:[] },
  { key:'remove_shadow',       label:'去除阴影', desc:'形态膨胀+背景估计，归一化消除光照不均 [浏览器]', icon:'sun', params:[] },
  { key:'denoise',             label:'智能降噪', desc:'可分离盒式滤波近似高斯降噪 [浏览器]', icon:'spark', params:[
    {name:'strength', label:'强度', type:'range', min:1, max:30, step:1, default:10}
  ]},
  { key:'binarize',            label:'文档二值化', desc:'Otsu / 自适应均值 / Sauvola 三种方法可选 [浏览器]', icon:'adjust', params:[
    {name:'method', label:'算法', type:'select',
     options:[{v:'adaptive',label:'自适应均值（推荐）'},{v:'otsu',label:'Otsu 全局'},{v:'sauvola_approx',label:'Sauvola 局部'}],
     default:'adaptive'},
    {name:'block_size', label:'局部块大小', type:'range', min:5, max:51, step:2, default:21},
    {name:'C',          label:'偏移量 C', type:'range', min:0, max:30, step:1, default:10},
  ]},
  { key:'enhance_contrast',    label:'对比度增强', desc:'CLAHE 自适应直方图均衡，含裁剪防过曝 [浏览器]', icon:'adjust', params:[
    {name:'clip_limit', label:'裁剪上限', type:'range', min:0.5, max:10, step:0.5, default:2.5},
    {name:'tile_size',  label:'分块数量', type:'range', min:2,   max:16, step:1,   default:8},
  ]},
  { key:'sharpen',             label:'图像锐化', desc:'非锐化掩蔽（Unsharp Mask）使文字边缘更清晰 [浏览器]', icon:'target', params:[
    {name:'amount', label:'锐化量', type:'range', min:0.1, max:3, step:0.1, default:1.0}
  ]},
  { key:'whiten_background',   label:'背景漂白', desc:'将亮度超过阈值的像素强制置白 [浏览器]', icon:'grid', params:[
    {name:'threshold', label:'阈值', type:'range', min:100, max:250, step:5, default:200}
  ]},
  { key:'auto_crop',           label:'自动裁剪', desc:'扫描暗像素边界，裁剪到文档内容区域 [浏览器]', icon:'scan', params:[
    {name:'padding', label:'边距px', type:'range', min:0, max:50, step:2, default:10}
  ]},
  { key:'brightness_contrast', label:'亮度/对比度', desc:'线性变换调整整体亮度与对比度 [浏览器]', icon:'sun', params:[
    {name:'brightness', label:'亮度', type:'range', min:-100, max:100, step:5, default:0},
    {name:'contrast',   label:'对比度', type:'range', min:0.2, max:3, step:0.1, default:1.0},
  ]},
  { key:'grayscale', label:'灰度化', desc:'BT.601 权重转换为灰度图像 [浏览器]', icon:'layers', params:[] },
];

// ── Web Worker 内联代码（所有算法在此） ───────────────────────
const SCAN_WORKER_CODE = `'use strict';
/* ─────────────────────────────────────────────────────────────
   MineAI Scan Enhance — Browser-side Image Processing Worker
   全部算法纯 JS 实现，运行在独立线程，不占用服务器 CPU
   ───────────────────────────────────────────────────────────── */

// ── 工具函数 ─────────────────────────────────────────────────
function clamp8(v){return v<0?0:v>255?255:v}
function toGrayPx(r,g,b){return(77*r+150*g+29*b)>>8}
function toGrayArr(d,w,h){
  const g=new Uint8Array(w*h);
  for(let i=0;i<w*h;i++){const j=i*4;g[i]=toGrayPx(d[j],d[j+1],d[j+2]);}
  return g;
}
function grayToRgba(g,w,h){
  const o=new Uint8ClampedArray(w*h*4);
  for(let i=0;i<w*h;i++){const j=i*4;o[j]=o[j+1]=o[j+2]=g[i];o[j+3]=255;}
  return o;
}
function exCh(d,w,h,c){const o=new Uint8Array(w*h);for(let i=0;i<w*h;i++)o[i]=d[i*4+c];return o;}
function mergeCh(R,G,B,w,h){
  const o=new Uint8ClampedArray(w*h*4);
  for(let i=0;i<w*h;i++){o[i*4]=R[i];o[i*4+1]=G[i];o[i*4+2]=B[i];o[i*4+3]=255;}
  return o;
}

// ── 可分离盒式模糊（O(W*H)） ──────────────────────────────────
function boxBlur(g,w,h,r){
  if(r<=0)return new Uint8Array(g);
  const t=new Float32Array(w*h),o=new Uint8Array(w*h),inv=1/(2*r+1);
  for(let y=0;y<h;y++){
    let s=g[y*w]*r;
    for(let x=0;x<=r;x++)s+=g[y*w+Math.min(x,w-1)];
    for(let x=0;x<w;x++){
      t[y*w+x]=s*inv;
      s+=g[y*w+Math.min(x+r+1,w-1)];
      s-=g[y*w+Math.max(x-r,0)];
    }
  }
  for(let x=0;x<w;x++){
    let s=t[x]*r;
    for(let y=0;y<=r;y++)s+=t[Math.min(y,h-1)*w+x];
    for(let y=0;y<h;y++){
      o[y*w+x]=s*inv;
      s+=t[Math.min(y+r+1,h-1)*w+x];
      s-=t[Math.max(y-r,0)*w+x];
    }
  }
  return o;
}
function boxBlurRgba(d,w,h,r){return mergeCh(boxBlur(exCh(d,w,h,0),w,h,r),boxBlur(exCh(d,w,h,1),w,h,r),boxBlur(exCh(d,w,h,2),w,h,r),w,h);}

// 最大值膨胀
function maxFilt(g,w,h,r){
  const t=new Uint8Array(w*h),o=new Uint8Array(w*h);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){let m=0;for(let dx=-r;dx<=r;dx++){const nx=Math.max(0,Math.min(w-1,x+dx));if(g[y*w+nx]>m)m=g[y*w+nx];}t[y*w+x]=m;}
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){let m=0;for(let dy=-r;dy<=r;dy++){const ny=Math.max(0,Math.min(h-1,y+dy));if(t[ny*w+x]>m)m=t[ny*w+x];}o[y*w+x]=m;}
  return o;
}

// 近邻下采样
function downsample(d,w,h,sw,sh){
  const o=new Uint8ClampedArray(sw*sh*4),sx=w/sw,sy=h/sh;
  for(let y=0;y<sh;y++)for(let x=0;x<sw;x++){
    const si=(Math.floor(y*sy)*w+Math.floor(x*sx))*4,di=(y*sw+x)*4;
    o[di]=d[si];o[di+1]=d[si+1];o[di+2]=d[si+2];o[di+3]=255;
  }
  return o;
}

// 双线性采样（超出边界返回白色）
function bsamp(d,w,h,sx,sy){
  const x0=Math.floor(sx),y0=Math.floor(sy);
  if(x0<0||y0<0||x0>=w-1||y0>=h-1)return[255,255,255];
  const fx=sx-x0,fy=sy-y0,r=[];
  for(let c=0;c<3;c++){
    const v00=d[(y0*w+x0)*4+c],v10=d[(y0*w+x0+1)*4+c];
    const v01=d[((y0+1)*w+x0)*4+c],v11=d[((y0+1)*w+x0+1)*4+c];
    r.push(v00*(1-fx)*(1-fy)+v10*fx*(1-fy)+v01*(1-fx)*fy+v11*fx*fy);
  }
  return r;
}

// ── Otsu 全局阈值 ─────────────────────────────────────────────
function otsu(g,w,h){
  const hist=new Int32Array(256);for(let i=0;i<w*h;i++)hist[g[i]]++;
  const N=w*h;let s=0;for(let i=0;i<256;i++)s+=i*hist[i];
  let sB=0,wB=0,best=0,T=128;
  for(let t=0;t<256;t++){wB+=hist[t];if(!wB)continue;const wF=N-wB;if(!wF)break;sB+=t*hist[t];const v=wB*wF*(sB/wB-(s-sB)/wF)**2;if(v>best){best=v;T=t;}}
  return T;
}

// ── 积分图 ────────────────────────────────────────────────────
function buildII(g,w,h){
  const ii=new Float64Array((w+1)*(h+1));
  for(let y=1;y<=h;y++)for(let x=1;x<=w;x++){const v=g[(y-1)*w+(x-1)];ii[y*(w+1)+x]=v+ii[(y-1)*(w+1)+x]+ii[y*(w+1)+(x-1)]-ii[(y-1)*(w+1)+(x-1)];}
  return ii;
}
function buildII2(g,w,h){
  const ii=new Float64Array((w+1)*(h+1));
  for(let y=1;y<=h;y++)for(let x=1;x<=w;x++){const v=g[(y-1)*w+(x-1)];ii[y*(w+1)+x]=v*v+ii[(y-1)*(w+1)+x]+ii[y*(w+1)+(x-1)]-ii[(y-1)*(w+1)+(x-1)];}
  return ii;
}
function iiRect(ii,w,x1,y1,x2,y2){const W=w+1;return ii[(y2+1)*W+(x2+1)]-ii[y1*W+(x2+1)]-ii[(y2+1)*W+x1]+ii[y1*W+x1];}

// ── 多项式最小二乘拟合 ────────────────────────────────────────
function polySmooth(xs,ys,deg,xMin,xMax,totalW){
  if(xs.length<2)return new Float32Array(totalW).fill(ys[0]||0);
  const d=Math.min(deg,xs.length-1)+1,xR=xMax-xMin||1;
  const xn=xs.map(x=>2*(x-xMin)/xR-1);
  const ATA=Array.from({length:d},()=>new Float64Array(d)),ATy=new Float64Array(d);
  for(let i=0;i<xs.length;i++){
    const row=[];let xi=1;for(let j=0;j<d;j++){row.push(xi);xi*=xn[i];}
    for(let j=0;j<d;j++){ATy[j]+=row[j]*ys[i];for(let k=0;k<d;k++)ATA[j][k]+=row[j]*row[k];}
  }
  const mat=ATA.map((r,i)=>[...Array.from(r),ATy[i]]);
  for(let c=0;c<d;c++){
    let piv=c;for(let r=c+1;r<d;r++)if(Math.abs(mat[r][c])>Math.abs(mat[piv][c]))piv=r;
    [mat[c],mat[piv]]=[mat[piv],mat[c]];
    if(Math.abs(mat[c][c])<1e-12)continue;
    const p=mat[c][c];for(let j=c;j<=d;j++)mat[c][j]/=p;
    for(let r=0;r<d;r++){if(r===c)continue;const f=mat[r][c];for(let j=c;j<=d;j++)mat[r][j]-=f*mat[c][j];}
  }
  const co=mat.map(r=>r[d]);
  const res=new Float32Array(totalW);
  for(let x=0;x<totalW;x++){const xnv=2*(x-xMin)/xR-1;let v=0,xi=1;for(let j=0;j<d;j++){v+=co[j]*xi;xi*=xnv;}res[x]=v;}
  return res;
}

// ── 高斯消元（8x9 增广矩阵） ──────────────────────────────────
function gauss8(A){
  const n=8,M=A.map(r=>[...r]);
  for(let c=0;c<n;c++){
    let piv=c;for(let r=c+1;r<n;r++)if(Math.abs(M[r][c])>Math.abs(M[piv][c]))piv=r;
    [M[c],M[piv]]=[M[piv],M[c]];
    if(Math.abs(M[c][c])<1e-10)return null;
    const p=M[c][c];for(let j=c;j<=n;j++)M[c][j]/=p;
    for(let r=0;r<n;r++){if(r===c)continue;const f=M[r][c];for(let j=c;j<=n;j++)M[r][j]-=f*M[c][j];}
  }
  return M.map(r=>r[n]);
}
function inv3x3(m){
  const[a,b,c,d,e,f,g,h,k]=m,dt=a*(e*k-f*h)-b*(d*k-f*g)+c*(d*h-e*g);
  if(Math.abs(dt)<1e-10)return null;
  return[(e*k-f*h)/dt,(c*h-b*k)/dt,(b*f-c*e)/dt,(f*g-d*k)/dt,(a*k-c*g)/dt,(c*d-a*f)/dt,(d*h-e*g)/dt,(b*g-a*h)/dt,(a*e-b*d)/dt];
}
// DLT 单应矩阵（4 对点）
function homography4(src,dst){
  const A=[];
  for(let i=0;i<4;i++){const[x,y]=src[i],[xp,yp]=dst[i];A.push([x,y,1,0,0,0,-x*xp,-y*xp,xp]);A.push([0,0,0,x,y,1,-x*yp,-y*yp,yp]);}
  const h=gauss8(A.map(r=>[...r.slice(0,8),r[8]]));
  if(!h)return null;
  return[h[0],h[1],h[2],h[3],h[4],h[5],h[6],h[7],1];
}

// Sobel 边缘强度
function sobel(g,w,h){
  const e=new Uint8Array(w*h);
  for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
    const gx=-g[(y-1)*w+x-1]+g[(y-1)*w+x+1]-2*g[y*w+x-1]+2*g[y*w+x+1]-g[(y+1)*w+x-1]+g[(y+1)*w+x+1];
    const gy=-g[(y-1)*w+x-1]-2*g[(y-1)*w+x]-g[(y-1)*w+x+1]+g[(y+1)*w+x-1]+2*g[(y+1)*w+x]+g[(y+1)*w+x+1];
    e[y*w+x]=Math.min(255,Math.sqrt(gx*gx+gy*gy)|0);
  }
  return e;
}

// ══════════════════════════════════════════════════════════════
//  OpenCV.js 主线程加载（用于网格透视变换）
//  延迟加载，队列机制支持并发请求
// ══════════════════════════════════════════════════════════════
let cvReady = false;
let cvError = null;
let cvQueue = [];

function loadOpenCVMain() {
  if (cvReady) return Promise.resolve(window.cv);
  if (cvError) return Promise.reject(cvError);

  return new Promise((resolve, reject) => {
    cvQueue.push({ resolve, reject });

    if (cvQueue.length === 1) {
      // 首次加载
      const script = document.createElement('script');
      script.src = OPENCV_CDN_URLS[0];
      script.onload = () => {
        cvReady = true;
        cvQueue.forEach(q => q.resolve(window.cv));
        cvQueue = [];
      };
      script.onerror = () => {
        // 尝试备用 CDN
        if (OPENCV_CDN_URLS.length > 1) {
          script.src = OPENCV_CDN_URLS[1];
        } else {
          cvError = 'OpenCV.js 加载失败';
          cvQueue.forEach(q => q.reject(cvError));
          cvQueue = [];
        }
      };
      document.head.appendChild(script);
    }
  });
}

// ── 旋转图像（双线性插值） ─────────────────────────────────────
function rotateImg(d,w,h,angleDeg){
  const rad=angleDeg*Math.PI/180,cos=Math.cos(rad),sin=Math.sin(rad),cx=w/2,cy=h/2;
  const o=new Uint8ClampedArray(w*h*4);for(let i=3;i<o.length;i+=4)o[i]=255;
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    const dx=x-cx,dy=y-cy,sx=cos*dx+sin*dy+cx,sy=-sin*dx+cos*dy+cy;
    const rgb=bsamp(d,w,h,sx,sy),di=(y*w+x)*4;
    o[di]=rgb[0];o[di+1]=rgb[1];o[di+2]=rgb[2];o[di+3]=255;
  }
  return{data:o,w,h};
}

// ══════════════════════════════════════════════════════════════
//  图像处理操作
// ══════════════════════════════════════════════════════════════

function op_grayscale(d,w,h){
  const o=new Uint8ClampedArray(d);
  for(let i=0;i<w*h;i++){const j=i*4,g=toGrayPx(d[j],d[j+1],d[j+2]);o[j]=o[j+1]=o[j+2]=g;}
  return{data:o,w,h};
}

function op_brightness_contrast(d,w,h,{brightness=0,contrast=1}){
  const o=new Uint8ClampedArray(d.length);
  for(let i=0;i<d.length;i+=4){o[i]=clamp8(d[i]*contrast+brightness);o[i+1]=clamp8(d[i+1]*contrast+brightness);o[i+2]=clamp8(d[i+2]*contrast+brightness);o[i+3]=255;}
  return{data:o,w,h};
}

function op_denoise(d,w,h,{strength=10}){
  // 强度 1-30，映射到半径 1-8
  const r = Math.max(1, Math.round(strength * 0.25));
  return{data:boxBlurRgba(d,w,h,r),w,h};
}

function op_sharpen(d,w,h,{amount=1}){
  const bl=boxBlurRgba(d,w,h,2),o=new Uint8ClampedArray(d.length);
  for(let i=0;i<d.length;i+=4){o[i]=clamp8(d[i]*(1+amount)-bl[i]*amount);o[i+1]=clamp8(d[i+1]*(1+amount)-bl[i+1]*amount);o[i+2]=clamp8(d[i+2]*(1+amount)-bl[i+2]*amount);o[i+3]=255;}
  return{data:o,w,h};
}

function op_whiten_background(d,w,h,{threshold=200}){
  const o=new Uint8ClampedArray(d);
  for(let i=0;i<w*h;i++){const j=i*4;if(toGrayPx(d[j],d[j+1],d[j+2])>threshold){o[j]=o[j+1]=o[j+2]=255;}}
  return{data:o,w,h};
}

function op_binarize(d,w,h,{method='adaptive',block_size=21,C=10}){
  const gray=toGrayArr(d,w,h),bw=new Uint8Array(w*h);
  if(method==='otsu'){
    const t=otsu(gray,w,h);for(let i=0;i<w*h;i++)bw[i]=gray[i]>t?255:0;
  } else {
    const bs=block_size%2===1?block_size:block_size+1,half=(bs-1)>>1;
    const ii=buildII(gray,w,h),ii2=method==='sauvola_approx'?buildII2(gray,w,h):null;
    const k=0.3,R=128;
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const y1=Math.max(0,y-half),y2=Math.min(h-1,y+half),x1=Math.max(0,x-half),x2=Math.min(w-1,x+half);
      const cnt=(y2-y1+1)*(x2-x1+1),s=iiRect(ii,w,x1,y1,x2,y2),mean=s/cnt;
      let thr;
      if(method==='sauvola_approx'){const s2=iiRect(ii2,w,x1,y1,x2,y2);thr=mean*(1+k*(Math.sqrt(Math.max(0,s2/cnt-mean*mean))/R-1));}
      else{thr=mean-C;}
      bw[y*w+x]=gray[y*w+x]>thr?255:0;
    }
  }
  return{data:grayToRgba(bw,w,h),w,h};
}

// CLAHE 自适应直方图均衡化
function op_enhance_contrast(d,w,h,{clip_limit=2.5,tile_size=8}){
  const gray=toGrayArr(d,w,h),tgX=tile_size,tgY=tile_size;
  const tw=Math.ceil(w/tgX),th=Math.ceil(h/tgY);
  const luts=[];
  for(let ty=0;ty<tgY;ty++){
    luts[ty]=[];
    for(let tx=0;tx<tgX;tx++){
      const x0=tx*tw,x1=Math.min((tx+1)*tw,w),y0=ty*th,y1=Math.min((ty+1)*th,h);
      const hist=new Int32Array(256);let n=0;
      for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++){hist[gray[y*w+x]]++;n++;}
      const clip=Math.max(1,Math.floor(clip_limit*n/256));let ex=0;
      for(let i=0;i<256;i++){if(hist[i]>clip){ex+=hist[i]-clip;hist[i]=clip;}}
      const add=Math.floor(ex/256);for(let i=0;i<256;i++)hist[i]+=add;for(let i=0;i<ex%256;i++)hist[i]++;
      const lut=new Uint8Array(256);let cdf=0;
      for(let i=0;i<256;i++){cdf+=hist[i];lut[i]=Math.min(255,Math.round(cdf*255/n));}
      luts[ty].push(lut);
    }
  }
  const res=new Uint8Array(w*h);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    const v=gray[y*w+x],fx=(x+0.5)/tw-0.5,fy=(y+0.5)/th-0.5;
    const tx0=Math.max(0,Math.min(tgX-1,Math.floor(fx))),tx1=Math.min(tgX-1,tx0+1);
    const ty0=Math.max(0,Math.min(tgY-1,Math.floor(fy))),ty1=Math.min(tgY-1,ty0+1);
    const dx=Math.max(0,Math.min(1,fx-tx0)),dy=Math.max(0,Math.min(1,fy-ty0));
    res[y*w+x]=Math.round(luts[ty0][tx0][v]*(1-dx)*(1-dy)+luts[ty0][tx1][v]*dx*(1-dy)+luts[ty1][tx0][v]*(1-dx)*dy+luts[ty1][tx1][v]*dx*dy);
  }
  return{data:grayToRgba(res,w,h),w,h};
}

// 形态学去阴影：膨胀 → 背景估计 → 归一化
function op_remove_shadow(d,w,h){
  const chs=[exCh(d,w,h,0),exCh(d,w,h,1),exCh(d,w,h,2)].map(ch=>{
    const dil=maxFilt(ch,w,h,3),bg=boxBlur(dil,w,h,10);
    const diff=new Uint8Array(w*h);let mn=255,mx=0;
    for(let i=0;i<w*h;i++){diff[i]=255-Math.abs(ch[i]-bg[i]);if(diff[i]<mn)mn=diff[i];if(diff[i]>mx)mx=diff[i];}
    const rng=mx-mn||1,norm=new Uint8Array(w*h);
    for(let i=0;i<w*h;i++)norm[i]=Math.round((diff[i]-mn)*255/rng);
    return norm;
  });
  return{data:mergeCh(chs[0],chs[1],chs[2],w,h),w,h};
}

// 自动裁剪到内容区域
function op_auto_crop(d,w,h,{padding=10}){
  const gray=toGrayArr(d,w,h);let x0=w,y0=h,x1=0,y1=0;
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){if(gray[y*w+x]<240){if(x<x0)x0=x;if(x>x1)x1=x;if(y<y0)y0=y;if(y>y1)y1=y;}}
  if(x1<=x0||y1<=y0)return{data:d,w,h};
  x0=Math.max(0,x0-padding);y0=Math.max(0,y0-padding);x1=Math.min(w-1,x1+padding);y1=Math.min(h-1,y1+padding);
  const nw=x1-x0+1,nh=y1-y0+1,o=new Uint8ClampedArray(nw*nh*4);
  for(let y=0;y<nh;y++)for(let x=0;x<nw;x++){const si=((y+y0)*w+(x+x0))*4,di=(y*nw+x)*4;o[di]=d[si];o[di+1]=d[si+1];o[di+2]=d[si+2];o[di+3]=255;}
  return{data:o,w:nw,h:nh};
}

// 投影剖面法纠偏
function op_deskew(d,w,h){
  self.postMessage({status:'progress',msg:'纠偏：检测文字行角度…'});
  const sc=Math.min(1,600/Math.max(w,h)),sw=Math.round(w*sc),sh=Math.round(h*sc);
  const sd=downsample(d,w,h,sw,sh),gray=toGrayArr(sd,sw,sh);
  const t=otsu(gray,sw,sh),bin=new Uint8Array(sw*sh);
  for(let i=0;i<sw*sh;i++)bin[i]=gray[i]<t?1:0;
  let bestA=0,bestS=-1;
  const cx=sw/2,cy=sh/2;
  for(let a=-15;a<=15;a+=0.5){
    const rad=a*Math.PI/180,cos=Math.cos(rad),sin=Math.sin(rad);
    const rows=new Int32Array(sh*2);
    for(let y=0;y<sh;y++)for(let x=0;x<sw;x++){
      if(!bin[y*sw+x])continue;
      const r=Math.round((y-cy)*cos-(x-cx)*sin+cy+sh/2);
      if(r>=0&&r<sh*2)rows[r]++;
    }
    let s=0,s2=0;for(let i=0;i<sh*2;i++){s+=rows[i];s2+=rows[i]*rows[i];}
    const sc2=s2/(sh*2)-(s/(sh*2))**2;
    if(sc2>bestS){bestS=sc2;bestA=a;}
  }
  if(Math.abs(bestA)<0.3)return{data:d,w,h};
  self.postMessage({status:'progress',msg:'纠偏：旋转 '+bestA.toFixed(1)+'°…'});
  return rotateImg(d,w,h,-bestA);
}

// 单应矩阵透视校正
function op_perspective_correct(d,w,h){
  self.postMessage({status:'progress',msg:'透视校正：检测文档边缘…'});
  const sc=Math.min(1,800/Math.max(w,h)),sw=Math.round(w*sc),sh=Math.round(h*sc);
  const sd=downsample(d,w,h,sw,sh),gray=toGrayArr(sd,sw,sh);
  const edges=sobel(gray,sw,sh),thr=60,step=3;
  const cands=[];
  for(let y=0;y<sh;y+=step)for(let x=0;x<sw;x+=step)if(edges[y*sw+x]>thr)cands.push([x,y]);
  if(cands.length<20)return{data:d,w,h};
  // 找距4个角最近的边缘点
  const corners=[[0,0],[sw-1,0],[sw-1,sh-1],[0,sh-1]];
  const found=corners.map(([cx,cy])=>{
    let best=null,bd=Infinity;
    for(const[px,py]of cands){const dd=(px-cx)**2+(py-cy)**2;if(dd<bd){bd=dd;best=[px/sc,py/sc];}}
    return best;
  });
  if(found.some(p=>!p))return{data:d,w,h};
  const[tl,tr,br,bl]=found;
  const mw=Math.max(Math.hypot(br[0]-bl[0],br[1]-bl[1]),Math.hypot(tr[0]-tl[0],tr[1]-tl[1]))|0;
  const mh=Math.max(Math.hypot(tr[0]-br[0],tr[1]-br[1]),Math.hypot(tl[0]-bl[0],tl[1]-bl[1]))|0;
  if(mw<50||mh<50)return{data:d,w,h};
  const H=homography4(found,[[0,0],[mw-1,0],[mw-1,mh-1],[0,mh-1]]);
  if(!H)return{data:d,w,h};
  const Hi=inv3x3(H);if(!Hi)return{data:d,w,h};
  self.postMessage({status:'progress',msg:'透视校正：重映射中…'});
  const o=new Uint8ClampedArray(mw*mh*4);for(let i=3;i<o.length;i+=4)o[i]=255;
  for(let y=0;y<mh;y++)for(let x=0;x<mw;x++){
    const de=Hi[6]*x+Hi[7]*y+Hi[8];
    const sx=(Hi[0]*x+Hi[1]*y+Hi[2])/de,sy=(Hi[3]*x+Hi[4]*y+Hi[5])/de;
    const rgb=bsamp(d,w,h,sx,sy),di=(y*mw+x)*4;
    o[di]=rgb[0];o[di+1]=rgb[1];o[di+2]=rgb[2];o[di+3]=255;
  }
  return{data:o,w:mw,h:mh};
}

// ══════════════════════════════════════════════════════════════
//  曲面平整化 — 逐列边缘采样 + 多项式拟合 + 垂直重映射
//  核心算法：
//    1. Otsu 二值化找文字区域
//    2. 每列扫描首尾暗像素 → topY[x], botY[x]
//    3. 线性插值填补缺失列
//    4. 多项式最小二乘拟合 → topSmooth, botSmooth（消除噪声）
//    5. 逐输出像素：srcY = topSmooth[x] + ty*(botSmooth[x]-topSmooth[x])
//    6. 双线性插值采样，生成统一高度的平面图像
// ══════════════════════════════════════════════════════════════
function op_curve_flatten(d,w,h,{n_strips=40}){
  self.postMessage({status:'progress',msg:'曲面平整：扫描页面边缘…'});
  const gray=toGrayArr(d,w,h),thr=otsu(gray,w,h);
  const mg=Math.floor(h*0.03);
  const topY=new Float32Array(w).fill(-1),botY=new Float32Array(w).fill(-1);

  // 逐列找首/尾暗像素
  for(let x=0;x<w;x++){
    let top=-1,bot=-1;
    for(let y=mg;y<h-mg;y++){if(gray[y*w+x]<thr){if(top<0)top=y;bot=y;}}
    if(top>=0&&bot>top&&(bot-top)>h*0.07){topY[x]=top;botY[x]=bot;}
  }

  // 确定有效范围
  let xMin=w,xMax=0;
  for(let x=0;x<w;x++){if(topY[x]>=0){if(x<xMin)xMin=x;if(x>xMax)xMax=x;}}
  if(xMax-xMin<w*0.15)return{data:d,w,h};

  // 线性插值填补缺失列
  let lv=-1;
  for(let x=xMin;x<=xMax;x++){
    if(topY[x]>=0){
      if(lv>=0&&x-lv>1){for(let xi=lv+1;xi<x;xi++){const t=(xi-lv)/(x-lv);topY[xi]=topY[lv]*(1-t)+topY[x]*t;botY[xi]=botY[lv]*(1-t)+botY[x]*t;}}
      lv=x;
    }
  }

  // 收集有效样本
  const xs=[],tops=[],bots=[];
  for(let x=xMin;x<=xMax;x++){if(topY[x]>=0){xs.push(x);tops.push(topY[x]);bots.push(botY[x]);}}
  if(xs.length<4)return{data:d,w,h};

  // 多项式次数随拟合精度参数变化
  const deg=n_strips<=20?2:n_strips<=40?3:n_strips<=60?4:5;
  self.postMessage({status:'progress',msg:'曲面平整：多项式拟合（次数='+deg+'）…'});
  const topS=polySmooth(xs,tops,deg,xMin,xMax,w);
  const botS=polySmooth(xs,bots,deg,xMin,xMax,w);

  // 中值目标高度
  const hts=[];
  for(let x=xMin;x<=xMax;x++){const hv=botS[x]-topS[x];if(hv>10)hts.push(hv);}
  if(hts.length===0)return{data:d,w,h};
  hts.sort((a,b)=>a-b);
  const tgtH=Math.round(hts[hts.length>>1]);
  const outW=xMax-xMin,outH=tgtH;

  self.postMessage({status:'progress',msg:'曲面平整：逐像素重映射展平…'});
  const o=new Uint8ClampedArray(outW*outH*4);for(let i=3;i<o.length;i+=4)o[i]=255;

  for(let y=0;y<outH;y++){
    const ty=outH>1?y/(outH-1):0;
    for(let x=0;x<outW;x++){
      const sx=x+xMin,srcTop=topS[sx],srcBot=botS[sx];
      const srcY=srcTop+ty*(srcBot-srcTop);
      const rgb=bsamp(d,w,h,sx,srcY),di=(y*outW+x)*4;
      o[di]=rgb[0];o[di+1]=rgb[1];o[di+2]=rgb[2];o[di+3]=255;
    }
  }
  return{data:o,w:outW,h:outH};
}

// ── 处理流水线 ────────────────────────────────────────────────
const PIPELINE=['remove_shadow','curve_flatten','perspective_correct','deskew',
                'auto_crop','denoise','binarize','enhance_contrast',
                'whiten_background','sharpen','brightness_contrast','grayscale'];

function processImage(imgData,enabledOps,opParams){
  let{data,width:w,height:h}=imgData;
  data=new Uint8ClampedArray(data);
  for(const op of PIPELINE){
    if(!enabledOps[op])continue;
    const p=opParams[op]||{};
    let r;
    if     (op==='grayscale')          r=op_grayscale(data,w,h);
    else if(op==='brightness_contrast')r=op_brightness_contrast(data,w,h,p);
    else if(op==='denoise')            r=op_denoise(data,w,h,p);
    else if(op==='sharpen')            r=op_sharpen(data,w,h,p);
    else if(op==='whiten_background')  r=op_whiten_background(data,w,h,p);
    else if(op==='binarize')           r=op_binarize(data,w,h,p);
    else if(op==='enhance_contrast')   r=op_enhance_contrast(data,w,h,p);
    else if(op==='remove_shadow')      r=op_remove_shadow(data,w,h);
    else if(op==='auto_crop')          r=op_auto_crop(data,w,h,p);
    else if(op==='deskew')             r=op_deskew(data,w,h);
    else if(op==='perspective_correct')r=op_perspective_correct(data,w,h);
    else if(op==='curve_flatten')      r=op_curve_flatten(data,w,h,p);
    else continue;
    data=r.data;w=r.w;h=r.h;
  }
  return{data,w,h};
}

self.onmessage=function(e){
  const{imageData,enabledOps,opParams}=e.data;
  try{
    const r=processImage(imageData,enabledOps,opParams);
    self.postMessage({status:'ok',data:r.data,width:r.w,height:r.h},[r.data.buffer]);
  }catch(err){
    self.postMessage({status:'error',error:err.message||String(err)});
  }
};
`;

function createScanWorker(){
  const blob=new Blob([SCAN_WORKER_CODE],{type:'application/javascript'});
  const url=URL.createObjectURL(blob);
  const w=new Worker(url);
  // URL can be revoked immediately after Worker picks it up
  setTimeout(()=>URL.revokeObjectURL(url),1000);
  return w;
}

// PDF.js 动态加载
const PDFJS_CDN='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
const PDFJS_WORKER='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
async function loadPdfjsLib(){
  if(window.pdfjsLib)return window.pdfjsLib;
  return new Promise((resolve,reject)=>{
    const s=document.createElement('script');s.src=PDFJS_CDN;
    s.onload=()=>{window.pdfjsLib.GlobalWorkerOptions.workerSrc=PDFJS_WORKER;resolve(window.pdfjsLib);};
    s.onerror=reject;document.head.appendChild(s);
  });
}
{% endverbatim %}
{% verbatim %}

// ── CameraCapture 组件（可复用模块）──────────────────────────
// 使用 getUserMedia 显示实时取景器 + 拍照
// fallback: 若浏览器不支持则退化为 <input capture> 直接调起原生相机
function CameraCapture({ onCapture, onClose }) {
  const videoRef    = useRef(null);
  const streamRef   = useRef(null);
  const [facing, setFacing]   = useState('environment'); // 'environment'=后摄 'user'=前摄
  const [ready,  setReady]    = useState(false);
  const [err,    setErr]      = useState('');
  const [useNative, setUseNative] = useState(false); // fallback 模式

  const stopStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
  };

  const startCamera = useCallback(async (facingMode) => {
    stopStream(); setReady(false); setErr('');
    if (!navigator.mediaDevices?.getUserMedia) { setUseNative(true); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode, width: { ideal: 1920 }, height: { ideal: 1080 } }
      });
      streamRef.current = stream;
      if (videoRef.current) { videoRef.current.srcObject = stream; }
      setReady(true);
    } catch(e) {
      // HTTPS 未开启 / 权限拒绝时退化为原生 input
      if (e.name === 'NotAllowedError') setErr('摄像头权限被拒绝，请在浏览器设置中允许访问');
      else setUseNative(true);
    }
  }, []);

  useEffect(() => {
    startCamera(facing);
    return () => stopStream();
  }, [facing]); // eslint-disable-line

  // 点击"拍照"：从 video 帧截取到 canvas → dataURL
  const handleCapture = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const cv = document.createElement('canvas');
    cv.width = video.videoWidth; cv.height = video.videoHeight;
    cv.getContext('2d').drawImage(video, 0, 0);
    stopStream();
    onCapture(cv.toDataURL('image/jpeg', 0.92));
  };

  // fallback：<input capture> 触发原生相机
  const handleNativeCapture = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => onCapture(ev.target.result);
    reader.readAsDataURL(file);
  };

  return (
    <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,0.95)',zIndex:2000,
      display:'flex',flexDirection:'column'}}>
      {/* 顶栏 */}
      <div style={{display:'flex',alignItems:'center',padding:'12px 16px',
        borderBottom:'1px solid var(--border)',flexShrink:0}}>
        <span style={{flex:1,fontSize:14,color:'var(--fg)',fontWeight:500}}>相机拍照</span>
        <button onClick={()=>{ stopStream(); onClose(); }}
          style={{background:'none',color:'var(--fg2)',padding:'4px 8px',lineHeight:1}}>
          <Icon name="x" size={18}/>
        </button>
      </div>

      {/* 取景器 / 错误 / fallback */}
      <div style={{flex:1,position:'relative',overflow:'hidden',
        display:'flex',alignItems:'center',justifyContent:'center',background:'#000'}}>
        {useNative ? (
          <div style={{textAlign:'center',padding:24}}>
            <div style={{color:'var(--fg2)',fontSize:13,marginBottom:20,lineHeight:1.6}}>
              当前环境不支持实时取景（需要 HTTPS）<br/>点击下方按钮直接调起系统相机
            </div>
            <label className="btn btn-p" style={{padding:'12px 28px',fontSize:15,cursor:'pointer',
              display:'inline-flex',alignItems:'center',gap:8}}>
              <Icon name="scan" size={16}/> 打开相机
              <input type="file" accept="image/*" capture="environment"
                style={{display:'none'}} onChange={handleNativeCapture}/>
            </label>
          </div>
        ) : err ? (
          <div style={{color:'var(--red)',fontSize:13,padding:24,textAlign:'center',lineHeight:1.6}}>{err}</div>
        ) : (
          <video ref={videoRef} style={{maxWidth:'100%',maxHeight:'100%',objectFit:'contain'}}
            playsInline muted autoPlay/>
        )}
        {/* 取景框辅助线 */}
        {!useNative && !err && ready && (
          <div style={{position:'absolute',inset:0,pointerEvents:'none',
            display:'flex',alignItems:'center',justifyContent:'center'}}>
            <div style={{width:'72%',aspectRatio:'1.414/1',border:'2px solid rgba(201,168,108,0.6)',
              borderRadius:4,boxShadow:'0 0 0 9999px rgba(0,0,0,0.3)'}}/>
          </div>
        )}
      </div>

      {/* 底部操作栏 */}
      {!useNative && (
        <div style={{padding:'16px 20px',display:'flex',gap:12,justifyContent:'center',
          alignItems:'center',borderTop:'1px solid var(--border)',flexShrink:0,flexWrap:'wrap'}}>
          <button className="btn btn-s" onClick={()=>setFacing(f=>f==='environment'?'user':'environment')}
            style={{display:'inline-flex',alignItems:'center',gap:6}}>
            <Icon name="refresh" size={13}/> 切换摄像头
          </button>
          <button className="btn btn-p" onClick={handleCapture} disabled={!ready}
            style={{padding:'11px 36px',fontSize:15,display:'inline-flex',alignItems:'center',gap:8,
              borderRadius:'50px',minWidth:120}}>
            <Icon name="scan" size={16}/> 拍照
          </button>
          {/* 也提供 input capture 备用 */}
          <label className="btn btn-s" style={{cursor:'pointer',display:'inline-flex',alignItems:'center',gap:6}}>
            <Icon name="upload" size={13}/> 调用系统相机
            <input type="file" accept="image/*" capture="environment"
              style={{display:'none'}} onChange={handleNativeCapture}/>
          </label>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
//  图片拼接 — OpenCV.js WASM Web Worker
//  算法：AKAZE → BFMatcher/Lowe → 自动排序 → 中心锚点链式单应矩阵
//        → estimateGains色温校准 → 距离变换羽化融合
// ══════════════════════════════════════════════════════════════
const OPENCV_CDN_URLS = [
  'https://docs.opencv.org/4.8.0/opencv.js',
  'https://docs.opencv.org/4.9.0/opencv.js',
];

const STITCH_WORKER_CODE = `
'use strict';
/* ── OpenCV.js 加载 ── */
var cvReady = false, cvError = null, cvQueue = [];
function loadCv(urls) {
  var idx = 0;
  function tryNext() {
    if (idx >= urls.length) { cvError = 'OpenCV.js 所有 CDN 均加载失败'; notifyQueued(); return; }
    importScripts(urls[idx++]);
    // Module.onRuntimeInitialized 由 OpenCV.js 内部调用
  }
  self.Module = {
    onRuntimeInitialized: function() {
      cvReady = true;
      notifyQueued();
    }
  };
  try { tryNext(); } catch(e) { tryNext(); }
}
function notifyQueued() {
  var q = cvQueue.slice(); cvQueue = [];
  q.forEach(function(fn) { try { fn(); } catch(e) { self.postMessage({type:'error',msg:e.message||String(e)}); } });
}
function withCv(fn) {
  if (cvReady) fn();
  else cvQueue.push(fn);
}

/* ── 工具函数 ── */
var MAX_IN  = 1600; // 检测阶段最大边长
var MAX_OUT = 8000; // 输出画布最大边长

function prg(msg, pct) { self.postMessage({type:'progress', msg:msg, pct:pct}); }

function imgToMat(imgData) {
  // imgData: {data: Uint8ClampedArray, width, height}
  var mat = new cv.Mat(imgData.height, imgData.width, cv.CV_8UC4);
  mat.data.set(imgData.data);
  return mat; // RGBA
}

function scaleDown(mat, maxDim) {
  var sc = Math.min(1, maxDim / Math.max(mat.rows, mat.cols));
  if (sc >= 1) return mat.clone();
  var dst = new cv.Mat();
  cv.resize(mat, dst, new cv.Size(Math.round(mat.cols*sc), Math.round(mat.rows*sc)), 0, 0, cv.INTER_AREA);
  return dst;
}

function toGray(rgba) {
  var gray = new cv.Mat();
  cv.cvtColor(rgba, gray, cv.COLOR_RGBA2GRAY);
  return gray;
}

/* ── AKAZE 特征检测 ── */
function detectAKAZE(gray) {
  var akaze = new cv.AKAZE();
  akaze.setThreshold(0.0003);   // 默认 0.001，降低 = 更多特征点，拼接更鲁棒
  var kps   = new cv.KeyPointVector();
  var descs = new cv.Mat();
  akaze.detectAndCompute(gray, new cv.Mat(), kps, descs);
  akaze.delete();
  return {kps: kps, descs: descs};
}

/* ── BFMatcher + Lowe 比率测试 ── */
function loweMatch(d1, d2) {
  var bf = new cv.BFMatcher(cv.NORM_HAMMING, false);
  var knnM = new cv.DMatchVectorVector();
  bf.knnMatch(d1, d2, knnM, 2);
  bf.delete();
  var good = [];
  for (var i = 0; i < knnM.size(); i++) {
    var m = knnM.get(i);
    if (m.size() < 2) continue;
    var m0 = m.get(0), m1 = m.get(1);
    if (m0.distance < 0.70 * m1.distance) good.push({qi: m0.queryIdx, ti: m0.trainIdx});
  }
  knnM.delete();
  return good;
}

/* ── RANSAC 单应矩阵 ── */
function computeH(kps1, kps2, matches) {
  if (matches.length < 4) return null;
  var src = [], dst = [];
  matches.forEach(function(m) {
    var p1 = kps1.get(m.qi).pt, p2 = kps2.get(m.ti).pt;
    src.push(p1.x); src.push(p1.y);
    dst.push(p2.x); dst.push(p2.y);
  });
  var srcM = cv.matFromArray(matches.length, 1, cv.CV_32FC2, src);
  var dstM = cv.matFromArray(matches.length, 1, cv.CV_32FC2, dst);
  var mask = new cv.Mat();
  var H = cv.findHomography(srcM, dstM, cv.RANSAC, 2.5, mask);
  if (H && !H.empty()) {
    // 统计内点数，内点太少说明单应矩阵不可靠
    var inliers = 0;
    for (var i2 = 0; i2 < mask.rows; i2++) { if (mask.data[i2]) inliers++; }
    if (inliers < 8) { H.delete(); H = null; }
  }
  srcM.delete(); dstM.delete(); mask.delete();
  if (!H || H.empty()) return null;
  return H;
}

/* ── 贪心自动排序（找最优拼接顺序） ── */
function autoOrder(cnts, N) {
  // cnts[i][j] = i与j匹配点数；找从最高匹配对出发的链式路径
  var best = 0, bi = 0, bj = 1;
  for (var i = 0; i < N; i++) for (var j = i+1; j < N; j++) {
    if (cnts[i][j] > best) { best = cnts[i][j]; bi = i; bj = j; }
  }
  var ord = [bi, bj], used = {};
  used[bi] = used[bj] = true;
  while (ord.length < N) {
    var leftBest = -1, leftIdx = -1;
    for (var k = 0; k < N; k++) {
      if (used[k]) continue;
      if (cnts[k][ord[0]] > leftBest) { leftBest = cnts[k][ord[0]]; leftIdx = k; }
    }
    var rightBest = -1, rightIdx = -1;
    for (var k = 0; k < N; k++) {
      if (used[k]) continue;
      if (cnts[ord[ord.length-1]][k] > rightBest) { rightBest = cnts[ord[ord.length-1]][k]; rightIdx = k; }
    }
    if (leftBest >= rightBest && leftIdx >= 0) { ord.unshift(leftIdx); used[leftIdx] = true; }
    else if (rightIdx >= 0) { ord.push(rightIdx); used[rightIdx] = true; }
    else break;
  }
  return ord;
}

/* ── 透视投影单点 ── */
function tPt(d, x, y) {
  var w = d[6]*x + d[7]*y + d[8];
  return [(d[0]*x + d[1]*y + d[2])/w, (d[3]*x + d[4]*y + d[5])/w];
}

/* ── 2-pass Manhattan 距离变换（用于羽化权重） ── */
function fastDT(mask, w, h) {
  var dt = new Float32Array(w * h);
  var INF = w + h;
  // forward pass
  for (var y = 0; y < h; y++) for (var x = 0; x < w; x++) {
    var i = y * w + x;
    if (!mask[i]) { dt[i] = 0; continue; }
    var up   = y > 0     ? dt[(y-1)*w+x] + 1 : INF;
    var left = x > 0     ? dt[y*w+x-1]   + 1 : INF;
    dt[i] = Math.min(up, left);
  }
  // backward pass
  for (var y = h-1; y >= 0; y--) for (var x = w-1; x >= 0; x--) {
    var i = y * w + x;
    var down  = y < h-1 ? dt[(y+1)*w+x] + 1 : INF;
    var right = x < w-1 ? dt[y*w+x+1]   + 1 : INF;
    dt[i] = Math.min(dt[i], down, right);
  }
  return dt;
}

/* ══════════════════════════════════════════════════════════════
   estimateGains — 低分辨率预变形 + 逐通道均值比 + 链式传播
   解决不同照片白平衡/亮度不一致导致的拼缝割裂问题
   ══════════════════════════════════════════════════════════════ */
function estimateGains(mats, H_fin, ord, c, N, outW, outH) {
  var sc   = 0.25;                           // 低分辨率比例 (1/4)
  var lrW  = Math.max(4, Math.round(outW * sc));
  var lrH  = Math.max(4, Math.round(outH * sc));
  var lrSize = new cv.Size(lrW, lrH);

  // 生成每张图的低分辨率变形结果
  var lrWarped = [];
  for (var ii = 0; ii < N; ii++) {
    var idx = ord[ii];
    var rgba = mats[idx];                    // 已缩放的 RGBA cv.Mat
    var H = H_fin[ii];
    // H_lr = S · H · S^{-1}，其中 S = diag(sc, sc, 1)
    var d = H.data64F;
    var Hs = [d[0],d[1],d[2]*sc, d[3],d[4],d[5]*sc, d[6]/sc,d[7]/sc,d[8]];
    var hMat = cv.matFromArray(3, 3, cv.CV_64F, Hs);
    var warped = new cv.Mat();
    cv.warpPerspective(rgba, warped, hMat, lrSize, cv.INTER_LINEAR, cv.BORDER_CONSTANT, new cv.Scalar(0,0,0,0));
    hMat.delete();
    lrWarped.push(warped);
  }

  /* pairGain(refIdx, tgtIdx): 在重叠区计算 tgt 相对 ref 的逐通道增益
     令 g = mean_ref / mean_tgt（均值比），然后把 g 应用到 lrWarped[tgtIdx] 上（in-place） */
  function pairGain(refI, tgtI) {
    var ref = lrWarped[refI], tgt = lrWarped[tgtI];
    var sumR_ref = 0, sumG_ref = 0, sumB_ref = 0;
    var sumR_tgt = 0, sumG_tgt = 0, sumB_tgt = 0;
    var cnt = 0;
    var n = lrW * lrH;
    for (var p = 0; p < n; p++) {
      var aRef = ref.data[p*4+3], aTgt = tgt.data[p*4+3];
      if (aRef > 64 && aTgt > 64) {
        sumR_ref += ref.data[p*4];   sumG_ref += ref.data[p*4+1]; sumB_ref += ref.data[p*4+2];
        sumR_tgt += tgt.data[p*4];   sumG_tgt += tgt.data[p*4+1]; sumB_tgt += tgt.data[p*4+2];
        cnt++;
      }
    }
    if (cnt < 30) return [1, 1, 1]; // 重叠太少，不调整
    var gR = Math.max(0.25, Math.min(4, sumR_ref / (sumR_tgt || 1)));
    var gG = Math.max(0.25, Math.min(4, sumG_ref / (sumG_tgt || 1)));
    var gB = Math.max(0.25, Math.min(4, sumB_ref / (sumB_tgt || 1)));
    // 把增益 in-place 应用到 tgt 低分辨率变形结果（供后续相邻图参考）
    for (var p = 0; p < n; p++) {
      tgt.data[p*4]   = Math.min(255, Math.round(tgt.data[p*4]   * gR));
      tgt.data[p*4+1] = Math.min(255, Math.round(tgt.data[p*4+1] * gG));
      tgt.data[p*4+2] = Math.min(255, Math.round(tgt.data[p*4+2] * gB));
    }
    return [gR, gG, gB];
  }

  // gains[ii] 对应 ord[ii] 这张图的 [gR, gG, gB]
  var gains = new Array(N);
  // 中心图 = 基准，增益 = 1
  gains[c] = [1, 1, 1];

  // 向左传播：c-1 … 0
  for (var ii = c - 1; ii >= 0; ii--) {
    var g = pairGain(ii + 1, ii);
    var pg = gains[ii + 1];
    gains[ii] = [
      Math.max(0.25, Math.min(4, pg[0] * g[0])),
      Math.max(0.25, Math.min(4, pg[1] * g[1])),
      Math.max(0.25, Math.min(4, pg[2] * g[2]))
    ];
  }
  // 向右传播：c+1 … N-1
  for (var ii = c + 1; ii < N; ii++) {
    var g = pairGain(ii - 1, ii);
    var pg = gains[ii - 1];
    gains[ii] = [
      Math.max(0.25, Math.min(4, pg[0] * g[0])),
      Math.max(0.25, Math.min(4, pg[1] * g[1])),
      Math.max(0.25, Math.min(4, pg[2] * g[2]))
    ];
  }

  // 释放低分辨率变形结果
  lrWarped.forEach(function(m) { m.delete(); });
  return gains;
}

/* ══════════════════════════════════════════════════════════════
   doStitch — 主拼接流程
   ══════════════════════════════════════════════════════════════ */
function doStitch(data) {
  var imgs = data.imgs;   // [{data:Uint8ClampedArray, width, height}]
  var N = imgs.length;
  if (N < 2) throw new Error('至少需要 2 张图片');

  /* Stage A (2-28%): 图像解码 + 缩放 + AKAZE 检测 */
  prg('加载 OpenCV & 检测特征点…', 2);
  var mats = [], grays = [], feats = [];
  for (var i = 0; i < N; i++) {
    prg('AKAZE 检测第 ' + (i+1) + '/' + N + ' 张…', 2 + Math.round(26 * i / N));
    var rgba = imgToMat(imgs[i]);
    var small = scaleDown(rgba, MAX_IN);
    rgba.delete();
    var gray  = toGray(small);
    mats.push(small);
    grays.push(gray);
    feats.push(detectAKAZE(gray));
  }

  /* Stage B (30-42%): 全匹配矩阵 */
  prg('匹配所有图片对…', 30);
  var cnts = [], allM = [];
  for (var i = 0; i < N; i++) { cnts.push(new Array(N).fill(0)); allM.push(new Array(N).fill(null)); }
  for (var i = 0; i < N; i++) for (var j = i+1; j < N; j++) {
    var m = loweMatch(feats[i].descs, feats[j].descs);
    cnts[i][j] = cnts[j][i] = m.length;
    allM[i][j] = m;
    allM[j][i] = m.map(function(x) { return {qi: x.ti, ti: x.qi}; });
  }

  /* Stage C (42-50%): 自动排序 */
  prg('自动排序…', 42);
  var ord = autoOrder(cnts, N);
  var c = Math.floor((N-1)/2); // 中心锚点索引（在 ord 里的位置）

  /* Stage D (50-64%): 链式单应矩阵（以中心图为基准） */
  prg('计算单应矩阵（RANSAC）…', 50);
  var H_tot  = new Array(N); // ord[ii] 到 canvas 坐标的变换（相对中心图）
  var H_fin  = new Array(N); // 最终加上平移的变换
  // 中心图：单位矩阵
  H_tot[c] = cv.matFromArray(3, 3, cv.CV_64F, [1,0,0, 0,1,0, 0,0,1]);

  function gMul(A, B) { // 矩阵乘法
    var R = new cv.Mat(); cv.gemm(A, B, 1, new cv.Mat(), 0, R); return R;
  }

  // 向左：ord[c-1], ord[c-2], … ord[0]
  for (var ii = c - 1; ii >= 0; ii--) {
    var i1 = ord[ii+1], i0 = ord[ii];
    var H = computeH(feats[i0].kps, feats[i1].kps, allM[i0][i1]);
    if (!H) H = cv.matFromArray(3, 3, cv.CV_64F, [1,0,0, 0,1,0, 0,0,1]);
    H_tot[ii] = gMul(H_tot[ii+1], H);
    H.delete();
  }
  // 向右：ord[c+1], ord[c+2], … ord[N-1]
  for (var ii = c + 1; ii < N; ii++) {
    var i0 = ord[ii-1], i1 = ord[ii];
    var H = computeH(feats[i1].kps, feats[i0].kps, allM[i1][i0]);
    if (!H) H = cv.matFromArray(3, 3, cv.CV_64F, [1,0,0, 0,1,0, 0,0,1]);
    H_tot[ii] = gMul(H_tot[ii-1], H);
    H.delete();
  }

  // 清理特征点
  feats.forEach(function(f) { f.kps.delete(); f.descs.delete(); });
  grays.forEach(function(g) { g.delete(); });

  /* Stage E (64-66%): 计算输出画布范围 */
  prg('计算画布范围…', 64);
  var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (var ii = 0; ii < N; ii++) {
    var m = mats[ord[ii]], d = H_tot[ii].data64F;
    [[0,0],[m.cols,0],[m.cols,m.rows],[0,m.rows]].forEach(function(pt) {
      var p = tPt(d, pt[0], pt[1]);
      if (p[0] < minX) minX = p[0]; if (p[0] > maxX) maxX = p[0];
      if (p[1] < minY) minY = p[1]; if (p[1] > maxY) maxY = p[1];
    });
  }
  var outW = Math.min(MAX_OUT, Math.ceil(maxX - minX));
  var outH = Math.min(MAX_OUT, Math.ceil(maxY - minY));
  var sc   = Math.min(1, MAX_OUT / Math.max(outW, outH));
  outW = Math.round(outW * sc); outH = Math.round(outH * sc);

  // 平移矩阵 T（将所有像素移到正坐标）
  var tx = -minX * sc, ty = -minY * sc;
  var T = [sc,0,tx, 0,sc,ty, 0,0,1];

  // H_fin = T · H_tot
  var Tmat = cv.matFromArray(3, 3, cv.CV_64F, T);
  for (var ii = 0; ii < N; ii++) {
    H_fin[ii] = gMul(Tmat, H_tot[ii]);
    H_tot[ii].delete();
  }
  Tmat.delete();

  /* Stage E2 (66-68%): 色温/亮度自动校准 */
  prg('色温亮度校准…', 66);
  var gains = estimateGains(mats, H_fin, ord, c, N, outW, outH);

  /* Stage F+G (68-96%): 逐张扭曲 + 距离变换权重羽化融合 */
  var accR  = new Float32Array(outW * outH);
  var accG  = new Float32Array(outW * outH);
  var accB  = new Float32Array(outW * outH);
  var accWt = new Float32Array(outW * outH);
  var outSize = new cv.Size(outW, outH);

  for (var ii = 0; ii < N; ii++) {
    prg('融合第 ' + (ii+1) + '/' + N + ' 张…', 68 + Math.round(28 * ii / N));
    var mat = mats[ord[ii]];
    var warped = new cv.Mat();
    cv.warpPerspective(mat, warped, H_fin[ii], outSize, cv.INTER_LINEAR, cv.BORDER_CONSTANT, new cv.Scalar(0,0,0,0));
    H_fin[ii].delete();

    // 构造 alpha mask，计算距离变换权重
    var mask = new Uint8Array(outW * outH);
    var wd   = warped.data;
    for (var p = 0; p < outW * outH; p++) { mask[p] = wd[p*4+3] > 10 ? 1 : 0; }
    var dt = fastDT(mask, outW, outH);

    // 应用增益 + 距离权重融合
    var g = gains[ii];
    for (var p = 0; p < outW * outH; p++) {
      var wt = dt[p];
      if (wt <= 0) continue;
      accR[p]  += Math.min(255, wd[p*4]   * g[0]) * wt;
      accG[p]  += Math.min(255, wd[p*4+1] * g[1]) * wt;
      accB[p]  += Math.min(255, wd[p*4+2] * g[2]) * wt;
      accWt[p] += wt;
    }
    warped.delete();
  }

  // 清理输入 mats
  mats.forEach(function(m) { m.delete(); });

  /* Stage H (96-100%): 归一化输出 */
  prg('输出结果…', 96);
  var out = new Uint8ClampedArray(outW * outH * 4);
  for (var p = 0; p < outW * outH; p++) {
    var wt = accWt[p];
    if (wt > 0) {
      out[p*4]   = Math.round(accR[p]  / wt);
      out[p*4+1] = Math.round(accG[p]  / wt);
      out[p*4+2] = Math.round(accB[p]  / wt);
      out[p*4+3] = 255;
    }
  }
  prg('完成', 100);
  self.postMessage({type:'done', data: out.buffer, width: outW, height: outH}, [out.buffer]);
}

/* ── Worker 入口 ── */
self.onmessage = function(e) {
  if (e.data.type === 'init') {
    loadCv(e.data.urls);
    return;
  }
  if (e.data.type === 'stitch') {
    withCv(function() {
      try { doStitch(e.data); }
      catch(err) { self.postMessage({type:'error', msg: err.message || String(err)}); }
    });
  }
};
`;

function createStitchWorker() {
  const blob = new Blob([STITCH_WORKER_CODE], {type: 'application/javascript'});
  const url  = URL.createObjectURL(blob);
  const w    = new Worker(url);
  setTimeout(() => URL.revokeObjectURL(url), 15000); // WASM 加载需要时间
  return w;
}

// ══════════════════════════════════════════════════════════════
//  CloudUploadPanel — 云端图片上传 + 历史记录
// ══════════════════════════════════════════════════════════════
const UPLOAD_ALLOWED_EXTS = new Set(['.jpg','.jpeg','.png','.webp','.gif','.bmp','.tiff','.tif']);
const UPLOAD_MAX_MB = 50;

function CloudUploadPanel({ onSendToStitch }) {
  const [uploads,    setUploads]    = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [uploading,  setUploading]  = useState(false);
  const [uploadPct,  setUploadPct]  = useState(0);
  const [err,        setErr]        = useState('');
  const [success,    setSuccess]    = useState('');
  const dropRef = useRef(null);

  // ── 加载历史记录 ──────────────────────────────────────────
  const loadUploads = useCallback(async () => {
    setLoading(true);
    try {
      const data = await F('/api/scan/uploads/');
      setUploads(data);
    } catch(e) { setErr('加载记录失败：' + e.message); }
    setLoading(false);
  }, []);

  useEffect(() => { loadUploads(); }, []);

  // ── 前端预校验 ─────────────────────────────────────────────
  function validateFile(file) {
    const ext = ('.' + file.name.split('.').pop()).toLowerCase();
    if (!UPLOAD_ALLOWED_EXTS.has(ext))
      return `不支持的格式：${ext}（仅允许图片格式）`;
    if (file.size > UPLOAD_MAX_MB * 1024 * 1024)
      return `文件过大：${(file.size/1024/1024).toFixed(1)} MB（限 ${UPLOAD_MAX_MB} MB）`;
    return null;
  }

  // ── 上传 ──────────────────────────────────────────────────
  const handleUpload = async (file) => {
    setErr(''); setSuccess('');
    const pre = validateFile(file);
    if (pre) { setErr(pre); return; }
    setUploading(true); setUploadPct(0);

    try {
      const form = new FormData();
      form.append('file', file);
      // XMLHttpRequest 以获取上传进度
      const result = await new Promise((res, rej) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/scan/uploads/');
        // Django Token Auth — Get from localStorage
        const token = localStorage.getItem('mf_token');
        if (token) xhr.setRequestHeader('Authorization', `Token ${token}`);
        // CSRF fallback
        const csrf = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
        xhr.setRequestHeader('X-CSRFToken', csrf);
        
        xhr.upload.onprogress = e => { if (e.lengthComputable) setUploadPct(Math.round(e.loaded/e.total*90)); };
        xhr.onload = () => {
          if (xhr.status === 201) res(JSON.parse(xhr.responseText));
          else { try { rej(JSON.parse(xhr.responseText)); } catch { rej({error: '上传失败 ' + xhr.status}); } }
        };
        xhr.onerror = () => rej({error: '网络错误'});
        xhr.send(form);
      });
      setUploadPct(100);
      setSuccess(`上传成功：${result.original_name}`);
      setUploads(prev => [result, ...prev]);
    } catch(e) {
      setErr(e.error || '上传失败');
    }
    setUploading(false); setTimeout(() => setUploadPct(0), 800);
  };

  // ── 删除 ──────────────────────────────────────────────────
  const handleDelete = async (id) => {
    try {
      const token = localStorage.getItem('mf_token');
      const headers = {};
      if (token) headers['Authorization'] = `Token ${token}`;
      const csrf = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
      headers['X-CSRFToken'] = csrf;

      const r = await fetch(`/api/scan/uploads/${id}/`, {
        method: 'DELETE',
        headers: headers,
      });
      if (r.status === 204) setUploads(prev => prev.filter(u => u.id !== id));
      else setErr('删除失败');
    } catch { setErr('网络错误'); }
  };

  const formatSize = (bytes) => bytes >= 1048576
    ? (bytes/1048576).toFixed(1) + ' MB'
    : (bytes/1024).toFixed(0) + ' KB';

  const onZoneDrop = (e) => {
    e.preventDefault();
    if (dropRef.current) dropRef.current.style.borderColor = 'var(--border2)';
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  return (
    <div style={{flex:1, display:'flex', overflow:'hidden', minHeight:0}}>

      {/* 左侧面板 */}
      <div style={{width:260, borderRight:'1px solid var(--border)', display:'flex',
        flexDirection:'column', background:'var(--bg2)', flexShrink:0, overflow:'hidden'}}>

        <div style={{padding:'10px 14px', borderBottom:'1px solid var(--border)',
          fontSize:11, color:'var(--fg3)', letterSpacing:2}}>上传图片</div>

        {/* 拖拽上传区 */}
        <label ref={dropRef}
          onDragOver={e => { e.preventDefault(); dropRef.current.style.borderColor='var(--gold)'; }}
          onDragLeave={() => { dropRef.current.style.borderColor='var(--border2)'; }}
          onDrop={onZoneDrop}
          style={{margin:'12px 10px', borderRadius:8, border:'2px dashed var(--border2)',
            minHeight:120, display:'flex', flexDirection:'column', alignItems:'center',
            justifyContent:'center', gap:8, cursor: uploading ? 'wait' : 'pointer',
            transition:'border-color .2s', background:'var(--bg3)', padding:'14px 10px', textAlign:'center'}}>
          <Icon name="upload" size={24}/>
          <div style={{fontSize:11, fontWeight:500, color:'var(--fg2)'}}>
            {uploading ? '上传中…' : '点击 / 拖拽图片'}
          </div>
          <div style={{fontSize:9, color:'var(--fg3)', lineHeight:1.5}}>
            最大 50 MB · JPG PNG WEBP GIF BMP
          </div>
          <input type="file" accept="image/*" style={{display:'none'}} disabled={uploading}
            onChange={e => e.target.files[0] && handleUpload(e.target.files[0])}/>
        </label>

        {/* 进度条 */}
        {uploading && (
          <div style={{padding:'0 12px 8px'}}>
            <div style={{height:4, background:'var(--bg4)', borderRadius:2, overflow:'hidden'}}>
              <div style={{height:'100%', background:'var(--gold)', width: uploadPct + '%',
                transition:'width .3s', boxShadow:'0 0 6px var(--gold)'}}/>
            </div>
            <div style={{fontSize:9, color:'var(--cyan)', marginTop:3, textAlign:'right'}}>{uploadPct}%</div>
          </div>
        )}

        {/* 消息 */}
        {err && (
          <div style={{margin:'0 10px 6px', padding:'5px 10px', borderRadius:4,
            background:'rgba(196,90,90,.15)', border:'1px solid var(--red)', fontSize:10, color:'var(--red)'}}>
            {err} <button onClick={() => setErr('')} style={{float:'right', background:'none', border:'none', color:'var(--red)', cursor:'pointer'}}>×</button>
          </div>
        )}
        {success && (
          <div style={{margin:'0 10px 6px', padding:'5px 10px', borderRadius:4,
            background:'rgba(94,184,122,.12)', border:'1px solid var(--green)', fontSize:10, color:'var(--green)'}}>
            {success} <button onClick={() => setSuccess('')} style={{float:'right', background:'none', border:'none', color:'var(--green)', cursor:'pointer'}}>×</button>
          </div>
        )}

        <div style={{padding:'4px 12px 4px', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <span style={{fontSize:10, color:'var(--fg3)'}}>上传记录 {uploads.length}/200</span>
          <button onClick={loadUploads} style={{background:'none', border:'none', color:'var(--fg3)',
            fontSize:10, cursor:'pointer', padding:'2px 4px'}}>刷新</button>
        </div>

        <div style={{padding:'10px 10px', borderTop:'1px solid var(--border)'}}>
          <div style={{fontSize:9, color:'var(--fg3)', lineHeight:1.7}}>
            上传到云端后可在任意设备访问<br/>
            文件加密存储 · 不会被他人看到<br/>
            点击「→ 送入拼接」可直接拼图
          </div>
        </div>
      </div>

      {/* 右侧历史列表 */}
      <div style={{flex:1, overflow:'auto', padding:'16px 20px', background:'var(--bg)'}}>
        {loading ? (
          <div style={{textAlign:'center', paddingTop:40, color:'var(--fg3)'}}>
            <Icon name="refresh" size={28}/>
            <div style={{marginTop:10, fontSize:12}}>加载中…</div>
          </div>
        ) : uploads.length === 0 ? (
          <div style={{textAlign:'center', paddingTop:60, color:'var(--fg3)'}}>
            <div style={{marginBottom:12}}><Icon name="image" size={48}/></div>
            <div style={{fontSize:14, color:'var(--gold2)', marginBottom:8}}>云端图库为空</div>
            <div style={{fontSize:11, lineHeight:1.8}}>
              上传图片后在此查看记录<br/>
              上传的图片可直接用于图片拼接
            </div>
          </div>
        ) : (
          <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(160px, 1fr))', gap:14}}>
            {uploads.map(u => (
              <div key={u.id} style={{borderRadius:8, overflow:'hidden', border:'1px solid var(--border2)',
                background:'var(--bg2)', display:'flex', flexDirection:'column'}}>
                <div style={{aspectRatio:'4/3', overflow:'hidden', background:'#111'}}>
                  <img src={u.url} alt={u.original_name}
                    style={{width:'100%', height:'100%', objectFit:'cover'}}
                    loading="lazy"
                    onError={e => { e.currentTarget.style.display='none'; }}/>
                </div>
                <div style={{padding:'8px 10px', flex:1, display:'flex', flexDirection:'column', gap:4}}>
                  <div style={{fontSize:10, color:'var(--fg2)', overflow:'hidden',
                    textOverflow:'ellipsis', whiteSpace:'nowrap', fontWeight:500}}
                    title={u.original_name}>{u.original_name}</div>
                  <div style={{fontSize:9, color:'var(--fg3)'}}>
                    {formatSize(u.file_size)} · {new Date(u.created_at).toLocaleDateString('zh-CN')}
                  </div>
                  <div style={{display:'flex', gap:5, marginTop:2}}>
                    {onSendToStitch && (
                      <button onClick={() => onSendToStitch(u.url, u.original_name)}
                        style={{flex:1, fontSize:9, padding:'3px 0', borderRadius:3, cursor:'pointer',
                          background:'var(--gold)', color:'#1a180e', border:'none', fontWeight:600}}>
                        → 送入拼接
                      </button>
                    )}
                    <button onClick={() => handleDelete(u.id)}
                      style={{fontSize:9, padding:'3px 6px', borderRadius:3, cursor:'pointer',
                        background:'rgba(196,90,90,.15)', color:'var(--red)', border:'1px solid var(--red)'}}>
                      删除
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
//  applyPerspectiveMesh — 网格单元独立透视变换
//  每个四边形单元独立计算单应矩阵，变换到矩形
//  使用 OpenCV.js 进行透视变换
// ══════════════════════════════════════════════════════════════
async function applyPerspectiveMesh(srcData, pts, rows, cols) {
  // 等待 OpenCV.js 加载
  const cv = await loadOpenCVMain();

  // 1. 计算输出尺寸（基于外围四个角点）
  const [tl, tr, br, bl] = [
    pts[0][0],
    pts[0][cols-1],
    pts[rows-1][cols-1],
    pts[rows-1][0]
  ];

  // 计算四个边长，取最大值作为输出尺寸
  const topLen = Math.hypot(tr[0] - tl[0], tr[1] - tl[1]);
  const botLen = Math.hypot(br[0] - bl[0], br[1] - bl[1]);
  const leftLen = Math.hypot(bl[0] - tl[0], bl[1] - tl[1]);
  const rightLen = Math.hypot(br[0] - tr[0], br[1] - tr[1]);

  const outW = Math.round(Math.max(topLen, botLen));
  const outH = Math.round(Math.max(leftLen, rightLen));

  // 2. 创建输出 Mat
  const dstMat = new cv.Mat(outH, outW, cv.CV_8UC4);
  const srcMat = cv.matFromImageData(srcData);

  // 3. 为每个网格单元创建独立透视变换
  const cellW = outW / (cols - 1);
  const cellH = outH / (rows - 1);

  for (let r = 0; r < rows - 1; r++) {
    for (let c = 0; c < cols - 1; c++) {
      const srcQuad = [
        pts[r][c][0], pts[r][c][1],      // TL
        pts[r][c+1][0], pts[r][c+1][1],    // TR
        pts[r+1][c+1][0], pts[r+1][c+1][1],  // BR
        pts[r+1][c][0], pts[r+1][c][1]     // BL
      ];
      const dstQuad = [
        c * cellW, r * cellH,
        (c+1) * cellW, r * cellH,
        (c+1) * cellW, (r+1) * cellH,
        c * cellW, (r+1) * cellH
      ];

      // OpenCV.js 需要的格式
      const srcMatPts = cv.matFromArray(4, 1, cv.CV_32FC2, srcQuad);
      const dstMatPts = cv.matFromArray(4, 1, cv.CV_32FC2, dstQuad);

      // 计算单应矩阵
      const M = cv.getPerspectiveTransform(srcMatPts, dstMatPts);

      // 创建临时单元输出（略大一点以避免边缘空白）
      const cellOutW = Math.round(cellW) + 4;
      const cellOutH = Math.round(cellH) + 4;
      const cellMat = new cv.Mat(cellOutH, cellOutW, cv.CV_8UC4);

      // 应用透视变换
      cv.warpPerspective(
        srcMat, cellMat, M,
        new cv.Size(cellOutW, cellOutH),
        cv.INTER_LINEAR,
        cv.BORDER_CONSTANT,
        new cv.Scalar(0, 0, 0, 0)
      );

      // 将变换后的单元复制到输出 Mat
      const startX = Math.round(c * cellW) - 2;
      const startY = Math.round(r * cellH) - 2;
      const roiX = Math.max(0, startX);
      const roiY = Math.max(0, startY);
      const roiW = Math.min(cellOutW, outW - roiX);
      const roiH = Math.min(cellOutH, outH - roiY);

      if (roiW > 0 && roiH > 0) {
        const cellROI = cellMat.roi(new cv.Rect(roiX - startX, roiY - startY, roiW, roiH));
        const dstROI = dstMat.roi(new cv.Rect(roiX, roiY, roiW, roiH));
        cellROI.copyTo(dstROI);
        cellROI.delete();
        dstROI.delete();
      }

      // 清理
      srcMatPts.delete();
      dstMatPts.delete();
      M.delete();
      cellMat.delete();
    }
  }

  // 4. 转换为 ImageData
  const result = new ImageData(
    new Uint8ClampedArray(dstMat.data),
    dstMat.cols,
    dstMat.rows
  );

  // 清理
  dstMat.delete();
  srcMat.delete();

  return result;
}

// ══════════════════════════════════════════════════════════════
//  applyMeshWarp — 保留原实现作为降级方案（纯 JS 双线性插值）
// ══════════════════════════════════════════════════════════════
function applyMeshWarp(srcData, pts, rows, cols, outW, outH) {
  const dst = new Uint8ClampedArray(outW * outH * 4);
  const src = srcData.data, sw = srcData.width, sh = srcData.height;
  const cellW = outW / (cols-1), cellH = outH / (rows-1);
  for (let py = 0; py < outH; py++) {
    for (let px = 0; px < outW; px++) {
      const ci = Math.min(cols-2, Math.floor(px/cellW));
      const ri = Math.min(rows-2, Math.floor(py/cellH));
      const s = (px - ci*cellW)/cellW, t = (py - ri*cellH)/cellH;
      const p00=pts[ri][ci], p10=pts[ri][ci+1], p01=pts[ri+1][ci], p11=pts[ri+1][ci+1];
      const sx2=p00[0]*(1-s)*(1-t)+p10[0]*s*(1-t)+p01[0]*(1-s)*t+p11[0]*s*t;
      const sy2=p00[1]*(1-s)*(1-t)+p10[1]*s*(1-t)+p01[1]*(1-s)*t+p11[1]*s*t;
      const x0=Math.floor(sx2), y0=Math.floor(sy2), x1=x0+1, y1=y0+1;
      const ds=sx2-x0, dt=sy2-y0, di=(py*outW+px)*4;
      if (x0>=0&&y0>=0&&x1<sw&&y1<sh) {
        const i00=(y0*sw+x0)*4,i10=(y0*sw+x1)*4,i01=(y1*sw+x0)*4,i11=(y1*sw+x1)*4;
        for (let ch=0;ch<3;ch++)
          dst[di+ch]=Math.round(src[i00+ch]*(1-ds)*(1-dt)+src[i10+ch]*ds*(1-dt)+
                                 src[i01+ch]*(1-ds)*dt   +src[i11+ch]*ds*dt);
        dst[di+3]=255;
      }
    }
  }
  return dst;
}

// ══════════════════════════════════════════════════════════════
//  autoDetectBorder — 扫描图像边缘，生成贴边初始网格（Coons patch）
//  返回 pts[r][c] = [x,y]，坐标在原图空间
//
//  算法：
//  1. 扫描内容 bbox（每隔 2px 采样）
//  2. 从 bbox 四角对角线扫描找到真实内容角点 TL/TR/BL/BR
//  3. 沿角点连线采样 top/bot/left/right 四条边界曲线（端点强制一致）
//  4. Coons patch 插值 → 所有格线无交叉
// ══════════════════════════════════════════════════════════════
function autoDetectBorder(imgData, rows, cols, origW, origH) {
  const d = imgData.data, dw = imgData.width, dh = imgData.height;
  const scx = origW / dw, scy = origH / dh;
  const hit = (x, y) => {
    const xi = Math.max(0, Math.min(dw-1, Math.round(x)));
    const yi = Math.max(0, Math.min(dh-1, Math.round(y)));
    const idx = (yi*dw+xi)*4;
    return d[idx]+d[idx+1]+d[idx+2] > 45;
  };

  // ── 1. 内容 bounding box ──────────────────────────────────
  let minX=dw, maxX=0, minY=dh, maxY=0;
  for (let y=0; y<dh; y+=2) for (let x=0; x<dw; x+=2) {
    if (hit(x,y)) {
      if (x<minX) minX=x; if (x>maxX) maxX=x;
      if (y<minY) minY=y; if (y>maxY) maxY=y;
    }
  }
  if (maxX<=minX || maxY<=minY) {
    // fallback 均匀网格
    return Array.from({length:rows}, (_,r) =>
      Array.from({length:cols}, (_,c) =>
        [c/(cols>1?cols-1:1)*origW, r/(rows>1?rows-1:1)*origH]));
  }

  // ── 2. 对角线扫描找到 4 个真实内容角点 ────────────────────
  const W = maxX-minX, H = maxY-minY;
  const maxD = Math.ceil(Math.sqrt(W*W + H*H));
  let TL=null, TR=null, BL=null, BR=null;
  for (let dd=0; dd<=maxD && !(TL&&TR&&BL&&BR); dd++) {
    const fx = dd*W/maxD, fy = dd*H/maxD;
    if (!TL && hit(minX+fx, minY+fy)) TL = [minX+fx, minY+fy];
    if (!TR && hit(maxX-fx, minY+fy)) TR = [maxX-fx, minY+fy];
    if (!BL && hit(minX+fx, maxY-fy)) BL = [minX+fx, maxY-fy];
    if (!BR && hit(maxX-fx, maxY-fy)) BR = [maxX-fx, maxY-fy];
  }
  TL=TL||[minX,minY]; TR=TR||[maxX,minY];
  BL=BL||[minX,maxY]; BR=BR||[maxX,maxY];

  // ── 3. 沿角点连线采样四条边界曲线 ─────────────────────────
  // top：沿 TL→TR 参数化，找每列的上边界 y
  const topCurve = Array.from({length:cols}, (_,c) => {
    const s = cols>1 ? c/(cols-1) : 0;
    const lx = TL[0]+(TR[0]-TL[0])*s, ly0 = TL[1]+(TR[1]-TL[1])*s;
    for (let y=minY; y<=maxY; y++) { if (hit(lx,y)) return [lx*scx, y*scy]; }
    return [lx*scx, ly0*scy];
  });
  // bot：沿 BL→BR 参数化，找每列的下边界 y
  const botCurve = Array.from({length:cols}, (_,c) => {
    const s = cols>1 ? c/(cols-1) : 0;
    const lx = BL[0]+(BR[0]-BL[0])*s, ly0 = BL[1]+(BR[1]-BL[1])*s;
    for (let y=maxY; y>=minY; y--) { if (hit(lx,y)) return [lx*scx, y*scy]; }
    return [lx*scx, ly0*scy];
  });
  // left：沿 TL→BL 参数化，找每行的左边界 x
  const leftCurve = Array.from({length:rows}, (_,r) => {
    const t = rows>1 ? r/(rows-1) : 0;
    const ly = TL[1]+(BL[1]-TL[1])*t, lx0 = TL[0]+(BL[0]-TL[0])*t;
    for (let x=minX; x<=maxX; x++) { if (hit(x,ly)) return [x*scx, ly*scy]; }
    return [lx0*scx, ly*scy];
  });
  // right：沿 TR→BR 参数化，找每行的右边界 x
  const rightCurve = Array.from({length:rows}, (_,r) => {
    const t = rows>1 ? r/(rows-1) : 0;
    const ly = TR[1]+(BR[1]-TR[1])*t, lx0 = TR[0]+(BR[0]-TR[0])*t;
    for (let x=maxX; x>=minX; x--) { if (hit(x,ly)) return [x*scx, ly*scy]; }
    return [lx0*scx, ly*scy];
  });

  // 强制四条曲线端点完全一致（Coons patch 必要条件）
  const tlS=[TL[0]*scx,TL[1]*scy], trS=[TR[0]*scx,TR[1]*scy];
  const blS=[BL[0]*scx,BL[1]*scy], brS=[BR[0]*scx,BR[1]*scy];
  topCurve[0]=leftCurve[0]=tlS;
  topCurve[cols-1]=rightCurve[0]=trS;
  botCurve[0]=leftCurve[rows-1]=blS;
  botCurve[cols-1]=rightCurve[rows-1]=brS;

  // ── 4. Coons patch 插值 ────────────────────────────────────
  return Array.from({length:rows}, (_,r) => {
    const t = rows>1 ? r/(rows-1) : 0;
    const [Lx,Ly] = leftCurve[r], [Rx,Ry] = rightCurve[r];
    return Array.from({length:cols}, (_,c) => {
      const s = cols>1 ? c/(cols-1) : 0;
      const [Tx,Ty] = topCurve[c], [Bx,By] = botCurve[c];
      const x = (1-t)*Tx+t*Bx+(1-s)*Lx+s*Rx
                -((1-s)*(1-t)*tlS[0]+s*(1-t)*trS[0]+(1-s)*t*blS[0]+s*t*brS[0]);
      const y = (1-t)*Ty+t*By+(1-s)*Ly+s*Ry
                -((1-s)*(1-t)*tlS[1]+s*(1-t)*trS[1]+(1-s)*t*blS[1]+s*t*brS[1]);
      return [Math.max(0,Math.min(origW,x)), Math.max(0,Math.min(origH,y))];
    });
  });
}

// ══════════════════════════════════════════════════════════════
//  detectStitchSeams — 检测拼接缝并生成网格点
//  策略：
//  1. 计算 Sobel 梯度幅值
//  2. 分析梯度方向，找出"异常"的边缘线（拼接缝特征）
//  3. 沿拼接缝生成额外控制点
//  4. 使用双线性插值填充完整网格（确保不交叉）
// ══════════════════════════════════════════════════════════════
async function detectStitchSeams(imgData, rows, cols, origW, origH, onProgress) {
  const d = imgData.data, dw = imgData.width, dh = imgData.height;
  const scx = origW / dw, scy = origH / dh;

  onProgress?.({ msg: '计算梯度...', pct: 20 });

  // 1. 转灰度 + Sobel 梯度
  const gray = new Uint8Array(dw * dh);
  for (let i = 0; i < dw * dh; i++) {
    const idx = i * 4;
    gray[i] = Math.round(d[idx] * 0.299 + d[idx+1] * 0.587 + d[idx+2] * 0.114);
  }
  const edge = sobel(gray, dw, dh);

  onProgress?.({ msg: '检测拼接缝...', pct: 50 });

  // 2. 找强边缘点（梯度 > 阈值）
  const strongEdges = [];
  const threshold = 40;
  for (let i = 0; i < edge.length; i++) {
    if (edge[i] > threshold) {
      const x = (i % dw) * scx;
      const y = Math.floor(i / dw) * scy;
      strongEdges.push([x, y, edge[i]]);
    }
  }

  // 3. 聚类边缘点为"拼接缝区域"
  const seamRegions = clusterEdges(strongEdges, 30);

  onProgress?.({ msg: '生成网格点...', pct: 80 });

  // 4. 基础网格（外围 + 均匀内部）
  const baseGrid = uniformPts(rows, cols, origW, origH);

  // 5. 在拼接缝区域影响网格（简化版：直接使用 Coons patch）
  const finalGrid = coonsPatchFromBorder(baseGrid, seamRegions, origW, origH);

  onProgress?.({ msg: '完成', pct: 100 });
  return finalGrid;
}

// 辅助函数：聚类边缘点
function clusterEdges(edges, distThreshold) {
  const clusters = [];
  const visited = new Set();

  for (const edge of edges) {
    const key = `${edge[0]},${edge[1]}`;
    if (visited.has(key)) continue;
    visited.add(key);

    const cluster = [edge];
    for (const other of edges) {
      if (edge === other) continue;
      const d = Math.hypot(edge[0] - other[0], edge[1] - other[1]);
      if (d < distThreshold) {
        cluster.push(other);
        visited.add(`${other[0]},${other[1]}`);
      }
    }

    if (cluster.length > 10) {
      const cx = cluster.reduce((s, p) => s + p[0], 0) / cluster.length;
      const cy = cluster.reduce((s, p) => s + p[1], 0) / cluster.length;
      clusters.push({ center: [cx, cy], points: cluster });
    }
  }

  return clusters;
}

// 辅助函数：均匀网格点
function uniformPts(rows, cols, w, h) {
  return Array.from({length: rows}, (_, r) =>
    Array.from({length: cols}, (_, c) =>
      [w * c/(cols>1?cols-1:1), h * r/(rows>1?rows-1:1)]));
}

// 辅助函数：Coons patch 插值（简化版，保持边界一致）
function coonsPatchFromBorder(baseGrid, constraints, origW, origH) {
  // 对于拼接图像，我们仍然使用基础的 autoDetectBorder 逻辑
  // 但在某些区域增加采样密度
  // 这里暂时返回基础网格，实际应用中可以基于 constraints 调整
  return baseGrid;
}

// ══════════════════════════════════════════════════════════════
//  snapToEdge — 吸附到强边缘（用于控制点拖拽）
// ══════════════════════════════════════════════════════════════
function snapToEdge(x, y, edgeData) {
  const { edge, width, height, scale } = edgeData;
  const searchRadius = 15;
  const minX = Math.max(0, Math.floor((x - searchRadius) / scale));
  const maxX = Math.min(width - 1, Math.ceil((x + searchRadius) / scale));
  const minY = Math.max(0, Math.floor((y - searchRadius) / scale));
  const maxY = Math.min(height - 1, Math.ceil((y + searchRadius) / scale));

  let bestEdge = null;
  let bestDist = searchRadius;
  let bestStrength = 0;

  for (let py = minY; py <= maxY; py++) {
    for (let px = minX; px <= maxX; px++) {
      const idx = py * width + px;
      if (edge[idx] > 50) {
        const ex = px * scale;
        const ey = py * scale;
        const dist = Math.hypot(x - ex, y - ey);
        if (dist < bestDist || (dist < bestDist * 1.2 && edge[idx] > bestStrength)) {
          bestDist = dist;
          bestStrength = edge[idx];
          bestEdge = { x: ex, y: ey };
        }
      }
    }
  }

  return bestEdge;
}

// ══════════════════════════════════════════════════════════════
//  MeshEditor — 拼接结果网格展平编辑器
// ══════════════════════════════════════════════════════════════
function MeshEditor({ resultUrl, resultSize, onComplete, onCancel }) {
  const [gridRows, setGridRows] = React.useState(5);
  const [gridCols, setGridCols] = React.useState(5);
  const [pts, setPts] = React.useState(null);
  const [dragging, setDragging] = React.useState(null);
  const [dispW, setDispW] = React.useState(0);
  const [dispH, setDispH] = React.useState(0);
  const [applying, setApplying] = React.useState(false);
  const [detectProgress, setDetectProgress] = React.useState(null);
  const [snapEnabled, setSnapEnabled] = React.useState(true);
  const [constrainGrid, setConstrainGrid] = React.useState(true);
  const [imgEdgeData, setImgEdgeData] = React.useState(null);
  const imgRef = React.useRef(null);
  const imgDataRef = React.useRef(null);   // 低分辨率像素缓存，供重新检测用
  const rafRef = React.useRef(null);

  // 均匀网格（fallback）
  const uniformPts = (rows, cols) =>
    Array.from({length: rows}, (_, r) =>
      Array.from({length: cols}, (_, c) =>
        [resultSize.w * c/(cols>1?cols-1:1), resultSize.h * r/(rows>1?rows-1:1)]));

  // 运行边缘检测并更新 pts
  const detectAndSet = async (rows, cols, imgData) => {
    const data = imgData || imgDataRef.current;
    if (!data) { setPts(uniformPts(rows, cols)); return; }
    setDetectProgress({ msg: '开始检测...', pct: 0 });
    try {
      // 使用新的拼接缝检测函数（暂时仍用 autoDetectBorder）
      // TODO: 后续替换为 detectStitchSeams
      await new Promise(r => setTimeout(r, 10)); // 让 UI 有机会渲染进度
      setDetectProgress({ msg: '分析图像边缘...', pct: 50 });
      await new Promise(r => setTimeout(r, 10));
      const result = autoDetectBorder(data, rows, cols, resultSize.w, resultSize.h);
      setDetectProgress({ msg: '生成网格...', pct: 90 });
      await new Promise(r => setTimeout(r, 10));
      setPts(result);
      setDetectProgress({ msg: '完成', pct: 100 });
      setTimeout(() => setDetectProgress(null), 500);
    } catch (e) {
      console.error('检测失败:', e);
      setDetectProgress(null);
      setPts(uniformPts(rows, cols));
    }
  };

  const onImgLoad = () => {
    const rect = imgRef.current.getBoundingClientRect();
    setDispW(rect.width); setDispH(rect.height);
    // 降采样到最长边 800px，加速扫描
    const scale = Math.min(1, 800 / Math.max(resultSize.w, resultSize.h));
    const dw = Math.round(resultSize.w * scale), dh = Math.round(resultSize.h * scale);
    const cvs = document.createElement('canvas'); cvs.width = dw; cvs.height = dh;
    cvs.getContext('2d').drawImage(imgRef.current, 0, 0, dw, dh);
    const imgData = cvs.getContext('2d').getImageData(0, 0, dw, dh);
    imgDataRef.current = imgData;

    // 计算边缘数据（供吸附使用）
    const gray = new Uint8Array(dw * dh);
    for (let i = 0; i < dw * dh; i++) {
      const idx = i * 4;
      gray[i] = Math.round(imgData.data[idx] * 0.299 +
                           imgData.data[idx+1] * 0.587 +
                           imgData.data[idx+2] * 0.114);
    }
    const edge = sobel(gray, dw, dh);
    setImgEdgeData({ edge, width: dw, height: dh, scale });

    detectAndSet(gridRows, gridCols, imgData);
  };

  const sx = dispW/resultSize.w, sy = dispH/resultSize.h;

  // 网格约束：防止网格线交叉
  const fixGridCrossings = (pts) => {
    const rows = pts.length;
    const cols = pts[0].length;
    const result = pts.map(row => row.map(p => [...p]));

    // 简化策略：确保相邻点的单调性
    for (let r = 0; r < rows; r++) {
      for (let c = 1; c < cols; c++) {
        const prev = result[r][c - 1];
        const curr = result[r][c];
        if (curr[0] < prev[0]) curr[0] = prev[0] + 1;
      }
    }

    for (let c = 0; c < cols; c++) {
      for (let r = 1; r < rows; r++) {
        const prev = result[r - 1][c];
        const curr = result[r][c];
        if (curr[1] < prev[1]) curr[1] = prev[1] + 1;
      }
    }

    return result;
  };

  const onMouseMove = (e) => {
    if (!dragging||!imgRef.current) return;
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      const r=imgRef.current.getBoundingClientRect();
      const sx2=r.width/resultSize.w, sy2=r.height/resultSize.h;
      let x=Math.max(0,Math.min(resultSize.w,(e.clientX-r.left)/sx2));
      let y=Math.max(0,Math.min(resultSize.h,(e.clientY-r.top)/sy2));

      // 吸附到强边缘（Shift 键禁用）
      if (snapEnabled && imgEdgeData && !e.shiftKey) {
        const snapped = snapToEdge(x, y, imgEdgeData);
        if (snapped) {
          x = snapped.x;
          y = snapped.y;
        }
      }

      setPts(prev => {
        const newPts = prev.map((row,ri) =>
          row.map((p,ci) => ri===dragging.r && ci===dragging.c ? [x,y] : p)
        );
        return constrainGrid ? fixGridCrossings(newPts) : newPts;
      });
    });
  };

  const applyWarp = async () => {
    if (!pts) return;
    setApplying(true);
    await new Promise(r=>setTimeout(r,20));
    const img=new Image(); img.src=resultUrl;
    await new Promise(r=>img.onload=r);
    const sc=document.createElement('canvas');
    sc.width=resultSize.w; sc.height=resultSize.h;
    sc.getContext('2d').drawImage(img,0,0);
    const srcData=sc.getContext('2d').getImageData(0,0,resultSize.w,resultSize.h);

    let outData;
    try {
      // 尝试使用 OpenCV.js 透视变换
      const resultData = await applyPerspectiveMesh(srcData, pts, gridRows, gridCols);
      outData = resultData.data;
    } catch (e) {
      console.warn('OpenCV.js 透视变换失败，使用降级方案:', e);
      // 降级到原双线性插值
      outData = applyMeshWarp(srcData, pts, gridRows, gridCols, resultSize.w, resultSize.h);
    }

    const dc=document.createElement('canvas');
    dc.width=resultSize.w; dc.height=resultSize.h;
    dc.getContext('2d').putImageData(new ImageData(outData,dc.width,dc.height),0,0);
    onComplete(dc.toDataURL('image/jpeg',0.92));
    setApplying(false);
  };

  // 点击添加控制点（在空白处点击）
  const onCanvasClick = (e) => {
    if (!imgRef.current || dragging) return;
    const r = imgRef.current.getBoundingClientRect();
    const sx2 = r.width / resultSize.w, sy2 = r.height / resultSize.h;
    const x = Math.max(0, Math.min(resultSize.w, (e.clientX - r.left) / sx2));
    const y = Math.max(0, Math.min(resultSize.h, (e.clientY - r.top) / sy2));

    // 简化版：只更新最近的控制点（不动态增加行列）
    // 动态增加行列需要重新计算整个网格，这里暂不实现
    if (!pts) return;

    // 找到最近的控制点并移动它
    let bestDist = Infinity;
    let bestR = -1, bestC = -1;
    pts.forEach((row, r) => row.forEach((p, c) => {
      const dist = Math.hypot(p[0] - x, p[1] - y);
      if (dist < bestDist) {
        bestDist = dist;
        bestR = r;
        bestC = c;
      }
    }));

    if (bestDist < 50) {
      // 如果点击位置附近有点，移动它
      setPts(prev => prev.map((row, r) =>
        row.map((p, c) => r === bestR && c === bestC ? [x, y] : p)
      ));
    }
  };

  // 双击删除控制点（简化版：不做实现）
  // 动态删除行列需要重新计算网格，暂时不实现

  // 清理 RAF
  React.useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);


  return (
    <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,.92)',zIndex:9999,
      display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center'}}
      onMouseMove={onMouseMove} onMouseUp={()=>setDragging(null)}>

      {/* 进度显示 */}
      {detectProgress && (
        <div style={{
          position:'absolute', top:10, left:'50%', transform:'translateX(-50%)',
          background:'var(--bg3)', padding:'8px 16px', borderRadius:6,
          display:'flex', alignItems:'center', gap:10, zIndex:10000
        }}>
          <span style={{ fontSize:11, color:'var(--fg2)' }}>
            {detectProgress.msg}
          </span>
          <div style={{ width:100, height:4, background:'var(--bg4)', borderRadius:2 }}>
            <div style={{
              width:detectProgress.pct+'%', height:'100%',
              background:'var(--gold)', borderRadius:2, transition:'width 0.2s'
            }}/>
          </div>
        </div>
      )}

      <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:10,
        color:'var(--fg)',fontSize:12,flexWrap:'wrap',justifyContent:'center'}}>
        <span style={{color:'var(--fg2)'}}>拖动顶点对齐网格，按 Shift 禁用吸附，点击展平</span>
        <span style={{color:'var(--fg3)'}}>行</span>
        <input type="number" min={2} max={10} value={gridRows}
          onChange={e=>{const v=Math.max(2,Math.min(10,+e.target.value||2));setGridRows(v);detectAndSet(v,gridCols);}}
          style={{width:40,fontSize:11,padding:'2px 4px'}}/>
        <span style={{color:'var(--fg3)'}}>列</span>
        <input type="number" min={2} max={10} value={gridCols}
          onChange={e=>{const v=Math.max(2,Math.min(10,+e.target.value||2));setGridCols(v);detectAndSet(gridRows,v);}}
          style={{width:40,fontSize:11,padding:'2px 4px'}}/>
        <button className="btn btn-s" style={{fontSize:10,padding:'3px 8px'}}
          onClick={()=>detectAndSet(gridRows,gridCols)}>重置贴边</button>
        <label style={{display:'inline-flex',alignItems:'center',gap:5,fontSize:11,color:'var(--fg2)'}}>
          <input type="checkbox" checked={snapEnabled}
            onChange={e=>setSnapEnabled(e.target.checked)} />
          拖拽吸附
        </label>
        <label style={{display:'inline-flex',alignItems:'center',gap:5,fontSize:11,color:'var(--fg2)'}}>
          <input type="checkbox" checked={constrainGrid}
            onChange={e=>setConstrainGrid(e.target.checked)} />
          网格不交叉
        </label>
      </div>
      <div style={{position:'relative',lineHeight:0,userSelect:'none'}} onClick={onCanvasClick}>
        <img ref={imgRef} src={resultUrl} onLoad={onImgLoad}
          style={{maxWidth:'88vw',maxHeight:'72vh',display:'block',pointerEvents:'none'}}/>
        {pts && dispW>0 && (()=>{
          const rows=pts.length, cols=pts[0].length;
          const lines=[], circles=[];
          pts.forEach((row,r)=>row.forEach((p,c)=>{
            const dx=p[0]*sx, dy=p[1]*sy;
            if (c<cols-1){const p2=pts[r][c+1];lines.push(<line key={`h${r}${c}`} x1={dx} y1={dy} x2={p2[0]*sx} y2={p2[1]*sy} stroke="rgba(255,80,80,.8)" strokeWidth="1.5"/>);}
            if (r<rows-1){const p2=pts[r+1][c];lines.push(<line key={`v${r}${c}`} x1={dx} y1={dy} x2={p2[0]*sx} y2={p2[1]*sy} stroke="rgba(255,80,80,.8)" strokeWidth="1.5"/>);}
            const edge=r===0||r===rows-1||c===0||c===cols-1;
            circles.push(<circle key={`d${r}${c}`} cx={dx} cy={dy} r={edge?8:6}
              fill={edge?'rgba(255,80,80,.9)':'rgba(201,168,108,.9)'} stroke="white" strokeWidth="1.5"
              style={{cursor:'grab'}} onMouseDown={e=>{e.preventDefault();setDragging({r,c});}}/>);
          }));
          return <svg style={{position:'absolute',top:0,left:0,width:'100%',height:'100%',overflow:'visible'}}>{lines}{circles}</svg>;
        })()}
      </div>
      <div style={{display:'flex',gap:12,marginTop:14}}>
        <button className="btn btn-s" onClick={onCancel}>取消</button>
        <button className="btn btn-p" onClick={applyWarp} disabled={applying||!pts}
          style={{background:'var(--gold)',color:'#1a180e',fontWeight:700,minWidth:90}}>
          {applying ? '展平中…' : '▶ 网格展平'}
        </button>
      </div>
    </div>
  );
}


// ══════════════════════════════════════════════════════════════
//  StitchPanel — 图片拼接 React 组件
// ══════════════════════════════════════════════════════════════
function StitchPanel({ addRef }) {
  const [images,    setImages]    = useState([]);
  const [stitching, setStitching] = useState(false);
  const [progress,  setProgress]  = useState({msg:'', pct:0});
  const [resultUrl, setResultUrl] = useState(null);
  const [resultSize,setResultSize]= useState(null);
  const [err,       setErr]       = useState('');
  const [meshEditing,  setMeshEditing]   = useState(false);
  const workerRef  = useRef(null);
  const dragIndex  = useRef(null);
  const dropRef    = useRef(null);

  // 暴露 addFromUrl 给云图库使用
  useEffect(() => {
    if (!addRef) return;
    addRef.current = async (url, name) => {
      try {
        const resp = await fetch(url);
        const blob = await resp.blob();
        const reader = new FileReader();
        reader.onload = ev => setImages(prev => prev.length >= 10 ? prev : [...prev, {url: ev.target.result, name: name || 'cloud.jpg'}]);
        reader.readAsDataURL(blob);
      } catch(e) { console.warn('addFromUrl failed', e); }
    };
  }, [addRef]);

  /* ── 文件处理 ── */
  const addImages = useCallback((files) => {
    const arr = Array.from(files).filter(f => /\.(jpe?g|png|webp|bmp|tiff?)$/i.test(f.name));
    if (!arr.length) return;
    arr.forEach(f => {
      const reader = new FileReader();
      reader.onload = ev => setImages(prev => prev.length >= 10 ? prev : [...prev, {url: ev.target.result, name: f.name}]);
      reader.readAsDataURL(f);
    });
  }, []);

  const removeImage = (i) => setImages(prev => prev.filter((_, idx) => idx !== i));

  const handleReset = () => {
    if (workerRef.current) { workerRef.current.terminate(); workerRef.current = null; }
    setImages([]); setResultUrl(null); setResultSize(null);
    setErr(''); setStitching(false); setProgress({msg:'', pct:0});
  };

  /* ── 拖动排序 ── */
  const handleDragStart = (i) => { dragIndex.current = i; };
  const handleDragOver  = (e, i) => {
    e.preventDefault();
    const from = dragIndex.current;
    if (from === null || from === i) return;
    setImages(prev => {
      const a = [...prev]; const [item] = a.splice(from, 1); a.splice(i, 0, item);
      dragIndex.current = i; return a;
    });
  };
  const handleDrop = (e) => { e.preventDefault(); dragIndex.current = null; };

  /* ── 区域拖拽上传 ── */
  const onZoneDragOver = (e) => { e.preventDefault(); if(dropRef.current) dropRef.current.style.borderColor='var(--gold)'; };
  const onZoneDragLeave= ()  => { if(dropRef.current) dropRef.current.style.borderColor='var(--border2)'; };
  const onZoneDrop     = (e) => { e.preventDefault(); if(dropRef.current) dropRef.current.style.borderColor='var(--border2)'; addImages(e.dataTransfer.files); };

  /* ── 拼接主流程 ── */
  const handleStitch = useCallback(async () => {
    if (images.length < 2) { setErr('请至少上传 2 张图片'); return; }
    setErr(''); setResultUrl(null); setResultSize(null);
    setStitching(true); setProgress({msg:'准备中…', pct:1});

    let imgDatas = [];
    try {
      imgDatas = await Promise.all(images.map(im => new Promise((res, rej) => {
        const img = new Image();
        img.onload = () => {
          const cv2 = document.createElement('canvas');
          cv2.width = img.naturalWidth; cv2.height = img.naturalHeight;
          cv2.getContext('2d').drawImage(img, 0, 0);
          const id = cv2.getContext('2d').getImageData(0, 0, cv2.width, cv2.height);
          res({data: id.data.buffer, width: cv2.width, height: cv2.height});
        };
        img.onerror = rej; img.src = im.url;
      })));
    } catch(ex) { setErr('图片解码失败：' + ex.message); setStitching(false); return; }

    if (workerRef.current) { workerRef.current.terminate(); }
    const w = createStitchWorker();
    workerRef.current = w;

    w.onmessage = (e) => {
      const d = e.data;
      if (d.type === 'progress') { setProgress({msg: d.msg, pct: d.pct}); return; }
      if (d.type === 'done') {
        const arr = new Uint8ClampedArray(d.data);
        const cv2 = document.createElement('canvas');
        cv2.width = d.width; cv2.height = d.height;
        cv2.getContext('2d').putImageData(new ImageData(arr, d.width, d.height), 0, 0);
        setResultUrl(cv2.toDataURL('image/jpeg', 0.92));
        setResultSize({w: d.width, h: d.height});
        setStitching(false); setProgress({msg:'', pct:0}); return;
      }
      if (d.type === 'error') {
        setErr('拼接失败：' + (d.msg || '未知错误'));
        setStitching(false); setProgress({msg:'', pct:0});
      }
    };
    w.onerror = (e) => { setErr('Worker 错误：' + e.message); setStitching(false); setProgress({msg:'', pct:0}); };

    w.postMessage({type: 'init', urls: OPENCV_CDN_URLS});
    w.postMessage({type: 'stitch', imgs: imgDatas.map(d => ({data: new Uint8ClampedArray(d.data), width: d.width, height: d.height}))});
    setProgress({msg:'正在加载 OpenCV.js（首次约 9MB）…', pct:3});
  }, [images]);

  const handleDownload = () => {
    if (!resultUrl) return;
    const a = document.createElement('a'); a.href = resultUrl;
    a.download = 'panorama_' + Date.now() + '.jpg'; a.click();
  };

  /* ── 渲染 ── */
  return (
    <div style={{flex:1, display:'flex', overflow:'hidden', minHeight:0}}>

      {/* 网格展平编辑器遮罩 */}
      {meshEditing && resultUrl && resultSize && (
        <MeshEditor
          resultUrl={resultUrl}
          resultSize={resultSize}
          onComplete={(url) => { setResultUrl(url); setMeshEditing(false); }}
          onCancel={() => setMeshEditing(false)}
        />
      )}

      {/* 左侧面板 */}
      <div style={{width:260, borderRight:'1px solid var(--border)', display:'flex',
        flexDirection:'column', background:'var(--bg2)', flexShrink:0, overflow:'hidden'}}>

        <div style={{padding:'10px 14px', borderBottom:'1px solid var(--border)',
          fontSize:11, color:'var(--fg3)', letterSpacing:2}}>上传图片</div>

        {/* 大拖拽区 */}
        <label ref={dropRef}
          onDragOver={onZoneDragOver} onDragLeave={onZoneDragLeave} onDrop={onZoneDrop}
          style={{margin:'12px 10px', borderRadius:8, border:'2px dashed var(--border2)',
            minHeight:140, display:'flex', flexDirection:'column', alignItems:'center',
            justifyContent:'center', gap:8, cursor:'pointer', transition:'border-color .2s',
            background:'var(--bg3)', color:'var(--fg3)', textAlign:'center', padding:'16px 12px'}}>
          <Icon name="upload" size={28}/>
          <div style={{fontSize:12, fontWeight:500, color:'var(--fg2)'}}>点击选择 / 拖拽到此</div>
          <div style={{fontSize:10, color:'var(--fg3)', lineHeight:1.5}}>
            JPG · PNG · WEBP · BMP<br/>最多 10 张，建议 30-50% 重叠
          </div>
          <input type="file" multiple accept=".jpg,.jpeg,.png,.webp,.bmp,.tiff"
            style={{display:'none'}} onChange={e => addImages(e.target.files)}/>
        </label>

        <div style={{padding:'4px 12px 8px', display:'flex', alignItems:'center', justifyContent:'space-between'}}>
          <span style={{fontSize:11, color:'var(--fg3)'}}>已选 {images.length} / 10 张</span>
          {images.length > 0 && (
            <button onClick={() => setImages([])} style={{background:'none', color:'var(--fg3)',
              fontSize:11, padding:'2px 6px', border:'1px solid var(--border2)', borderRadius:3, cursor:'pointer'}}>
              清空
            </button>
          )}
        </div>

        {/* 缩略图列表 */}
        <div style={{flex:1, overflowY:'auto', padding:'0 10px 8px'}}>
          {images.length === 0 ? (
            <div style={{fontSize:10, color:'var(--fg3)', textAlign:'center', paddingTop:8, lineHeight:1.6}}>
              上传后在此显示<br/>可拖动调整拼接顺序
            </div>
          ) : (
            images.map((im, i) => (
              <div key={i} draggable
                onDragStart={() => handleDragStart(i)}
                onDragOver={e => handleDragOver(e, i)}
                onDrop={handleDrop}
                style={{display:'flex', alignItems:'center', gap:8, padding:'5px 6px',
                  borderRadius:5, marginBottom:4, cursor:'grab', border:'1px solid var(--border)',
                  background:'var(--bg3)', userSelect:'none'}}>
                <div style={{width:44, height:34, borderRadius:3, overflow:'hidden', flexShrink:0,
                  position:'relative', border:'1px solid var(--border2)'}}>
                  <img src={im.url} alt={im.name}
                    style={{width:'100%', height:'100%', objectFit:'cover', pointerEvents:'none'}}/>
                  <div style={{position:'absolute', bottom:0, left:0, right:0, textAlign:'center',
                    background:'rgba(0,0,0,.55)', color:'var(--gold)', fontSize:8, lineHeight:'14px'}}>
                    {i + 1}
                  </div>
                </div>
                <div style={{flex:1, minWidth:0}}>
                  <div style={{fontSize:10, color:'var(--fg2)', overflow:'hidden',
                    textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{im.name}</div>
                  <div style={{fontSize:9, color:'var(--fg3)'}}>拖动可排序</div>
                </div>
                <button onClick={() => removeImage(i)}
                  style={{background:'none', color:'var(--fg3)', padding:'2px 4px',
                    fontSize:14, cursor:'pointer', flexShrink:0, lineHeight:1, border:'none'}}>×</button>
              </div>
            ))
          )}
        </div>

        {/* 错误 */}
        {err && (
          <div style={{margin:'0 10px 8px', padding:'6px 10px', borderRadius:4,
            background:'rgba(196,90,90,.15)', border:'1px solid var(--red)',
            fontSize:11, color:'var(--red)', lineHeight:1.4}}>
            {err}
            <button onClick={() => setErr('')} style={{float:'right', background:'none',
              color:'var(--red)', border:'none', cursor:'pointer', fontSize:12}}>×</button>
          </div>
        )}

        {/* 进度条（小） */}
        {stitching && (
          <div style={{padding:'8px 12px', borderTop:'1px solid var(--border)'}}>
            <div style={{display:'flex', justifyContent:'space-between', fontSize:10,
              color:'var(--cyan)', marginBottom:4}}>
              <span style={{overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', flex:1,
                fontSize:9}}>{progress.msg}</span>
              <span style={{marginLeft:4, flexShrink:0}}>{progress.pct}%</span>
            </div>
            <div style={{height:4, background:'var(--bg4)', borderRadius:2, overflow:'hidden'}}>
              <div style={{height:'100%', background:'var(--gold)', width: progress.pct + '%',
                transition:'width .4s ease', boxShadow:'0 0 6px var(--gold)'}}/>
            </div>
          </div>
        )}

        {/* 操作按钮 */}
        <div style={{padding:'10px 10px', borderTop:'1px solid var(--border)', display:'flex', flexDirection:'column', gap:6}}>
          <button className="btn btn-p" style={{width:'100%', fontSize:13}}
            onClick={handleStitch}
            disabled={stitching || images.length < 2}>
            {stitching ? <><Icon name="refresh" size={13}/> 计算中…</> : '▶ 开始拼接'}
          </button>
          {(resultUrl || images.length > 0) && !stitching && (
            <button className="btn btn-s" style={{width:'100%', fontSize:12}}
              onClick={handleReset}>↺ 重新开始</button>
          )}
          {resultUrl && !stitching && (
            <button className="btn btn-s" style={{width:'100%', fontSize:12,
              display:'inline-flex', alignItems:'center', justifyContent:'center', gap:5}}
              onClick={handleDownload}>
              <Icon name="download" size={12}/> 下载全景图
            </button>
          )}
        </div>

        <div style={{padding:'8px 12px', borderTop:'1px solid var(--border)',
          fontSize:9, color:'var(--fg3)', lineHeight:1.6}}>
          首次加载 OpenCV.js ~9MB，之后缓存<br/>全程本地计算，图片不离开设备
        </div>
      </div>

      {/* 右侧内容区 */}
      <div style={{flex:1, overflow:'auto', background:'var(--bg)', display:'flex',
        flexDirection:'column', alignItems:'center',
        justifyContent: resultUrl || stitching ? 'flex-start' : 'center',
        padding:'32px 24px'}}>

        {/* 空状态 */}
        {!resultUrl && !stitching && (
          <div style={{textAlign:'center', maxWidth:500}}>
            <div style={{marginBottom:16}}><Icon name="image" size={56}/></div>
            <div style={{fontSize:18, color:'var(--gold2)', marginBottom:8, fontFamily:'var(--serif)'}}>
              图片拼接 · 全景合成
            </div>
            <div style={{fontSize:12, color:'var(--fg3)', marginBottom:24, lineHeight:2}}>
              将多张不同角度拍摄的照片<br/>
              自动对齐合成为高分辨率全景图<br/>
              <span style={{color:'var(--green)'}}>相邻图片建议有 30% ~ 50% 重叠区域</span>
            </div>
            <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:10, textAlign:'left'}}>
              {[
                ['AKAZE 特征检测','旋转+尺度不变，特征点覆盖全图'],
                ['RANSAC 2.5px','严格剔除误匹配，减少重影'],
                ['中心锚点链式变换','以中间图为基准，两侧误差不累积'],
                ['自动白平衡校准','逐通道均值比校准，消除色差'],
                ['距离变换羽化融合','拼缝处权重渐变，无锯齿色块'],
                ['全程浏览器计算','不上传服务器，数据不离开设备'],
              ].map(([t,d]) => (
                <div key={t} style={{background:'var(--bg2)', borderRadius:6, padding:'10px 12px',
                  border:'1px solid var(--border)'}}>
                  <div style={{fontWeight:600, color:'var(--gold)', fontSize:11, marginBottom:3}}>{t}</div>
                  <div style={{color:'var(--fg3)', fontSize:10, lineHeight:1.5}}>{d}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 进度（大） */}
        {stitching && (
          <div style={{width:'100%', maxWidth:520, textAlign:'center'}}>
            <div style={{marginBottom:20}}><Icon name="refresh" size={44}/></div>
            <div style={{fontSize:14, color:'var(--fg)', marginBottom:8}}>{progress.msg || '处理中…'}</div>
            <div style={{height:8, background:'var(--bg3)', borderRadius:4, overflow:'hidden', marginBottom:8}}>
              <div style={{height:'100%', background:'var(--gold)', width: progress.pct + '%',
                transition:'width .5s ease', boxShadow:'0 0 12px var(--gold)'}}/>
            </div>
            <div style={{fontSize:11, color:'var(--fg3)', marginBottom:4}}>{progress.pct}% 完成</div>
            <div style={{fontSize:10, color:'var(--fg3)'}}>
              首次加载 OpenCV.js (~9MB)，之后浏览器缓存，无需重复下载
            </div>
          </div>
        )}

        {/* 结果 */}
        {resultUrl && !stitching && (
          <div style={{width:'100%'}}>
            <div style={{display:'flex', alignItems:'center', justifyContent:'space-between',
              marginBottom:14, flexWrap:'wrap', gap:8}}>
              <span style={{color:'var(--green)', display:'inline-flex', alignItems:'center',
                gap:5, fontSize:13}}>
                <Icon name="check" size={14}/> 拼接完成 · {resultSize?.w} × {resultSize?.h} px
              </span>
              <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
                <button className="btn btn-s btn-sm" onClick={handleReset}
                  style={{display:'inline-flex', alignItems:'center', gap:5}}>
                  ↺ 重新拼接
                </button>
                <button className="btn btn-s btn-sm" onClick={()=>setMeshEditing(true)}
                  style={{display:'inline-flex', alignItems:'center', gap:5,
                    border:'1px solid var(--gold)', color:'var(--gold)'}}>
                  ⊞ 网格展平
                </button>
                <button className="btn btn-p btn-sm" onClick={handleDownload}
                  style={{display:'inline-flex', alignItems:'center', gap:5}}>
                  <Icon name="download" size={12}/> 下载 JPEG
                </button>
              </div>
            </div>
            <div style={{border:'1px solid var(--border2)', borderRadius:8, overflow:'hidden',
              background:'#111', textAlign:'center'}}>
              <img src={resultUrl} alt="panorama"
                style={{maxWidth:'100%', maxHeight:'75vh', objectFit:'contain',
                  display:'block', margin:'0 auto'}}/>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}



// ── ScanEnhanceApp React 组件 ─────────────────────────────────
function ScanEnhanceApp({user, onLogout, onUpdateUser}) {
  // 本地页面数组：[{num, origDataUrl, procDataUrl}]
  const [pages, setPages]         = useState([]);
  const [curIdx, setCurIdx]       = useState(0);
  const [fileName, setFileName]   = useState('');
  const [enabledOps, setEnabledOps] = useState({});
  const [opParams, setOpParams]   = useState({});
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress]   = useState('');
  const [err, setErr]             = useState('');
  const [splitPos, setSplitPos]   = useState(50);
  const [dragging, setDragging]   = useState(false);
  const [sbOpen, setSbOpen]       = useState(false);
  const [loadingFile, setLoadingFile] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [mode, setMode] = useState('enhance'); // 'enhance' | 'stitch' | 'cloud'
  // 从云图库「送入拼接」时存储待添加图片
  const stitchAddRef = useRef(null); // 回调引用
  const sliderRef = useRef(null);
  const workerRef = useRef(null);

  // 初始化默认参数
  useEffect(() => {
    const defaults = {};
    SCAN_OPS.forEach(op => { const p={}; op.params.forEach(pm=>{p[pm.name]=pm.default;}); defaults[op.key]=p; });
    setOpParams(defaults);
  }, []);

  const view    = pages.length > 0 ? 'editor' : 'home';
  const curPage = pages[curIdx] || null;

  // ── 加载文件（本地，不上传服务器） ───────────────────────────
  const handleFile = useCallback(async (file) => {
    if (!file) return;
    setErr(''); setLoadingFile(true); setPages([]); setProcForAll([]);
    try {
      const ext = file.name.split('.').pop().toLowerCase();
      setFileName(file.name);
      if (ext === 'pdf') {
        const lib = await loadPdfjsLib();
        const ab  = await file.arrayBuffer();
        setProgress('正在加载 PDF…');
        const pdfDoc = await lib.getDocument({data: ab}).promise;
        const newPages = [];
        for (let i = 1; i <= pdfDoc.numPages; i++) {
          setProgress(`正在渲染第 ${i} / ${pdfDoc.numPages} 页…`);
          const page = await pdfDoc.getPage(i);
          const vp   = page.getViewport({scale: 2.0});
          const cv   = document.createElement('canvas');
          cv.width = vp.width; cv.height = vp.height;
          await page.render({canvasContext: cv.getContext('2d'), viewport: vp}).promise;
          newPages.push({num: i, origDataUrl: cv.toDataURL('image/jpeg', 0.92), procDataUrl: null});
        }
        setPages(newPages); setCurIdx(0);
      } else {
        setProgress('正在读取图像…');
        const dataUrl = await new Promise((res, rej) => {
          const r = new FileReader();
          r.onload = e => res(e.target.result); r.onerror = rej;
          r.readAsDataURL(file);
        });
        setPages([{num: 1, origDataUrl: dataUrl, procDataUrl: null}]);
        setCurIdx(0);
      }
    } catch(ex) { setErr('文件加载失败：' + ex.message); }
    setLoadingFile(false); setProgress('');
  }, []);

  // ── 接收相机拍照结果 ─────────────────────────────────────────
  const handleCameraCapture = useCallback((dataUrl) => {
    setShowCamera(false);
    setErr(''); setPages([]); setLoadingFile(false);
    setFileName('拍照_' + new Date().toISOString().slice(0,19).replace(/[:T]/g,'-') + '.jpg');
    setPages([{num: 1, origDataUrl: dataUrl, procDataUrl: null}]);
    setCurIdx(0);
  }, []);

  // 用于清空已处理结果（辅助）
  const setProcForAll = (_) => {};

  // ── 开始处理（Web Worker） ──────────────────────────────────
  const handleProcess = useCallback(async () => {
    if (!curPage || processing) return;
    const activeOps = {};
    SCAN_OPS.forEach(op => { if (enabledOps[op.key]) activeOps[op.key] = true; });
    if (!Object.keys(activeOps).length) { setErr('请至少勾选一个处理操作'); return; }
    setErr(''); setProcessing(true); setProgress('准备图像数据…');
    if (workerRef.current) { workerRef.current.terminate(); workerRef.current = null; }
    try {
      const img = new Image();
      img.src = curPage.origDataUrl;
      await new Promise((res, rej) => { img.onload = res; img.onerror = rej; });
      const cv = document.createElement('canvas');
      cv.width = img.width; cv.height = img.height;
      cv.getContext('2d').drawImage(img, 0, 0);
      const id = cv.getContext('2d').getImageData(0, 0, img.width, img.height);
      setProgress('启动处理线程…');
      const worker = createScanWorker();
      workerRef.current = worker;
      worker.onmessage = (e) => {
        if (e.data.status === 'progress') { setProgress(e.data.msg); return; }
        if (e.data.status === 'ok') {
          const {data, width, height} = e.data;
          const rc = document.createElement('canvas');
          rc.width = width; rc.height = height;
          rc.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(data), width, height), 0, 0);
          const procDataUrl = rc.toDataURL('image/jpeg', 0.92);
          const idx = curIdx;
          setPages(prev => prev.map((p, i) => i === idx ? {...p, procDataUrl} : p));
          setSplitPos(50);
        } else { setErr('处理失败：' + (e.data.error || '未知错误')); }
        worker.terminate(); workerRef.current = null;
        setProcessing(false); setProgress('');
      };
      worker.onerror = (e) => {
        setErr('Worker 错误：' + e.message);
        worker.terminate(); workerRef.current = null;
        setProcessing(false); setProgress('');
      };
      worker.postMessage(
        {imageData:{data:id.data,width:id.width,height:id.height}, enabledOps:activeOps, opParams},
        [id.data.buffer]
      );
    } catch(ex) { setErr('处理出错：' + ex.message); setProcessing(false); setProgress(''); }
  }, [curPage, curIdx, processing, enabledOps, opParams]);

  // ── 下载当前页 ──────────────────────────────────────────────
  const handleDownload = useCallback(() => {
    if (!curPage?.procDataUrl) return;
    const a = document.createElement('a');
    a.href = curPage.procDataUrl;
    a.download = (fileName.replace(/\.[^.]+$/, '') || 'scan') + `_enhanced_p${curPage.num}.jpg`;
    a.click();
  }, [curPage, fileName]);

  // 下载全部已处理页
  const handleDownloadAll = useCallback(() => {
    pages.forEach((p, i) => {
      if (!p.procDataUrl) return;
      setTimeout(() => {
        const a = document.createElement('a');
        a.href = p.procDataUrl;
        a.download = (fileName.replace(/\.[^.]+$/, '') || 'scan') + `_enhanced_p${p.num}.jpg`;
        a.click();
      }, i * 120);
    });
  }, [pages, fileName]);

  // ── 分割线拖动 ──────────────────────────────────────────────
  useEffect(() => {
    if (!dragging) return;
    const move = e => {
      const rect = sliderRef.current?.getBoundingClientRect();
      if (!rect) return;
      setSplitPos(Math.max(2, Math.min(98, (e.clientX - rect.left) / rect.width * 100)));
    };
    const up = () => setDragging(false);
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
    return () => { window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up); };
  }, [dragging]);

  const toggleOp = k => setEnabledOps(p => ({...p, [k]: !p[k]}));
  const setParam = (opKey, name, val) => setOpParams(p => ({...p, [opKey]: {...(p[opKey]||{}), [name]: val}}));

  const processedCount = pages.filter(p => p.procDataUrl).length;

  // ── 渲染 ────────────────────────────────────────────────────
  return (
    <div className="app">
      {/* ── 侧边栏 ── */}
      <div className={`sb${sbOpen?' open':''}`} style={{width:220}}>
        <div className="sb-hd">
          <h1>扫描增强</h1>
          <p style={{fontSize:10,color:'var(--green)',marginTop:4}}>● 浏览器端处理 · 零服务器占用</p>
        </div>
        <div className="sb-nav">
          {mode === 'stitch' ? (
            <div className="ns">
              <div className="ns-t">图片拼接</div>
              <div className="ni on"><i><Icon name="image" size={12}/></i> 上传并拼接</div>
              <div style={{padding:'8px 8px 4px',fontSize:10,color:'var(--fg3)',lineHeight:1.8}}>
                <div style={{color:'var(--gold)',fontWeight:500,marginBottom:4}}>使用建议</div>
                <div>・相邻图片重叠 30–50%</div>
                <div>・光线尽量一致</div>
                <div>・避免拍摄运动物体</div>
                <div>・建议不超过 5 张</div>
              </div>
            </div>
          ) : mode === 'cloud' ? (
            <div className="ns">
              <div className="ns-t">云端图库</div>
              <div className="ni on"><i><Icon name="upload" size={12}/></i> 上传 &amp; 管理</div>
              <div style={{padding:'8px 8px 4px',fontSize:10,color:'var(--fg3)',lineHeight:1.8}}>
                <div style={{color:'var(--gold)',fontWeight:500,marginBottom:4}}>说明</div>
                <div>・支持 JPG PNG WEBP 等</div>
                <div>・单文件最大 50 MB</div>
                <div>・最多 200 张记录</div>
                <div>・点击「→ 送入拼接」</div>
              </div>
            </div>
          ) : (
            <>
              <div className="ns">
                <div className="ns-t">WORKSPACE</div>
                <div className={`ni${view==='home'?' on':''}`} onClick={()=>{ if(view==='editor'){ setPages([]); setCurIdx(0); } }}>
                  <i><Icon name="upload" size={12} /></i> 打开文件
                </div>
                {/* 显眼拼接入口 */}
                <div className="ni" onClick={()=>setMode('stitch')}
                  style={{background:'rgba(201,168,108,.10)',border:'1px solid var(--gold-dim)',
                    borderRadius:4,margin:'4px 8px',padding:'6px 8px',cursor:'pointer',
                    display:'flex',alignItems:'center',gap:7}}>
                  <i style={{color:'var(--gold)'}}><Icon name="image" size={13}/></i>
                  <div>
                    <div style={{fontSize:11,fontWeight:600,color:'var(--gold)'}}>图片拼接</div>
                    <div style={{fontSize:9,color:'var(--fg3)',marginTop:1}}>全景 · 多段合成</div>
                  </div>
                </div>
                {/* 云图库入口 */}
                <div className="ni" onClick={()=>setMode('cloud')}
                  style={{margin:'4px 8px',padding:'5px 8px',cursor:'pointer',
                    display:'flex',alignItems:'center',gap:7}}>
                  <i style={{color:'var(--fg2)'}}><Icon name="upload" size={12}/></i>
                  <div style={{fontSize:11,color:'var(--fg2)'}}>云端图库</div>
                </div>
                {curPage && (
                  <div className="ni on">
                    <i><Icon name="file" size={12} /></i>
                    <span style={{overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',fontSize:11}}>{fileName || '当前文件'}</span>
                  </div>
                )}
              </div>
              {pages.length > 1 && (
                <div className="ns">
                  <div className="ns-t">PDF 页面 ({pages.length}页)</div>
                  <div style={{maxHeight:180,overflowY:'auto'}}>
                    {pages.map((p, i) => (
                      <div key={i} style={{display:'flex',alignItems:'center',gap:6,padding:'4px 8px',borderRadius:4,cursor:'pointer',
                        background: curIdx===i ? 'var(--bg4)':'transparent'}} onClick={()=>setCurIdx(i)}>
                        <span style={{fontSize:11,color:curIdx===i?'var(--gold2)':'var(--fg2)',flex:1}}>第 {p.num} 页</span>
                        {p.procDataUrl && <Icon name="check" size={10} color="var(--green)" />}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
        <div style={{padding:'10px 14px',borderTop:'1px solid var(--border)',fontSize:10,color:'var(--fg3)',lineHeight:1.5}}>
          所有图像处理算法<br/>运行在您的浏览器中<br/>不会上传到服务器
        </div>
      </div>

      {/* ── 主区域 ── */}
      <div className="main">
        {/* 顶栏 */}
        <div className="top">
          <button onClick={()=>setSbOpen(o=>!o)} style={{background:'none',color:'var(--fg3)',padding:'0 4px',marginRight:4}}><Icon name="menu" size={18} /></button>
          <span className="top-t">
            {mode==='stitch' ? '图片拼接 · 全景合成' : mode==='cloud' ? '云端图库 · 上传与管理' : (view==='home' ? '扫描增强 · 浏览器端图像处理' : `${fileName} · 第 ${curPage?.num} 页`)}
          </span>
          {/* Tab 切换器 */}
          <div style={{display:'flex',gap:3,marginRight:6,flexShrink:0}}>
            {[{k:'enhance',l:'增强'},{k:'stitch',l:'拼接'},{k:'cloud',l:'云图库'}].map(({k,l})=>(
              <button key={k} onClick={()=>setMode(k)}
                style={{padding:'3px 10px',borderRadius:3,fontSize:11,cursor:'pointer',
                  background: mode===k ? 'var(--gold)' : 'var(--bg3)',
                  color: mode===k ? '#1a180e' : 'var(--fg2)',
                  border: mode===k ? 'none' : '1px solid var(--border2)',
                  fontWeight: mode===k ? 600 : 400}}>{l}</button>
            ))}
          </div>
          {view==='editor' && mode==='enhance' && (
            <>
              {curPage?.procDataUrl && (
                <button className="btn btn-s btn-sm" onClick={handleDownload} style={{display:'inline-flex',alignItems:'center',gap:5}}>
                  <Icon name="download" size={12}/> 下载
                </button>
              )}
              {processedCount > 1 && (
                <button className="btn btn-s btn-sm" onClick={handleDownloadAll} style={{display:'inline-flex',alignItems:'center',gap:5}}>
                  <Icon name="download" size={12}/> 全部({processedCount})
                </button>
              )}
              <button className="btn btn-s btn-sm" onClick={()=>setShowCamera(true)}
                style={{display:'inline-flex',alignItems:'center',gap:5}}>
                <Icon name="scan" size={12}/> 拍照
              </button>
              <label className="btn btn-p btn-sm" style={{cursor:loadingFile?'wait':'pointer'}}>
                {loadingFile ? '加载中…' : '+ 换文件'}
                <input type="file" style={{display:'none'}} accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff,.webp"
                  onChange={e=>handleFile(e.target.files?.[0])} disabled={loadingFile}/>
              </label>
            </>
          )}
          <button onClick={onLogout} style={{background:'none',color:'var(--fg3)',fontSize:12}}>退出</button>
        </div>

        {err && (
          <div style={{background:'rgba(196,90,90,.15)',border:'1px solid var(--red)',
            borderRadius:4,padding:'8px 14px',margin:'10px 16px',fontSize:12,color:'var(--red)'}}>
            {err} <button onClick={()=>setErr('')} style={{background:'none',color:'var(--red)',float:'right'}}><Icon name="x" size={11}/></button>
          </div>
        )}

        {/* ── 拼接面板 ── */}
        {mode === 'stitch' && <StitchPanel addRef={stitchAddRef}/>}

        {/* ── 云图库面板 ── */}
        {mode === 'cloud' && (
          <CloudUploadPanel onSendToStitch={(url, name) => {
            setMode('stitch');
            // 用 setTimeout 等 StitchPanel 挂载后调用其 addFromUrl
            setTimeout(() => { if (stitchAddRef.current) stitchAddRef.current(url, name); }, 100);
          }}/>
        )}

        {/* ── 首页上传区 ── */}
        {view === 'home' && mode === 'enhance' && (
          <div className="ct" style={{maxWidth:680,margin:'0 auto',paddingTop:32}}>
            <div style={{textAlign:'center',marginBottom:32}}>
              <div style={{marginBottom:12}}><Icon name="scan" size={48}/></div>
              <h2 style={{fontFamily:'var(--serif)',fontSize:22,color:'var(--gold2)',marginBottom:8}}>扫描文档增强工作台</h2>
              <p style={{color:'var(--fg3)',fontSize:13,marginBottom:8}}>上传扫描图片或 PDF，所有处理算法运行在您的浏览器中</p>
              <div style={{display:'inline-flex',gap:8,flexWrap:'wrap',justifyContent:'center',fontSize:11,color:'var(--fg3)'}}>
                {['曲面平整','透视校正','自动纠偏','去除阴影','CLAHE增强','自适应二值化','锐化/降噪'].map(t=>(
                  <span key={t} style={{background:'var(--bg3)',border:'1px solid var(--border2)',borderRadius:10,padding:'2px 8px'}}>{t}</span>
                ))}
              </div>
            </div>

            {/* 上传区 */}
            <label style={{display:'block',border:'2px dashed var(--border2)',borderRadius:8,
              padding:'48px 20px',textAlign:'center',cursor:loadingFile?'wait':'pointer',
              transition:'border-color .2s',background:'var(--bg2)'}}
              onDragOver={e=>{e.preventDefault();e.currentTarget.style.borderColor='var(--gold)'}}
              onDragLeave={e=>{e.currentTarget.style.borderColor='var(--border2)'}}
              onDrop={e=>{e.preventDefault();e.currentTarget.style.borderColor='var(--border2)';const f=e.dataTransfer.files[0];if(f)handleFile(f);}}>
              <input type="file" style={{display:'none'}} accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff,.webp"
                onChange={e=>handleFile(e.target.files?.[0])} disabled={loadingFile}/>
              {loadingFile
                ? <><div style={{marginBottom:10}}><Icon name="refresh" size={32}/></div><div style={{color:'var(--fg2)',fontSize:14}}>{progress || '加载中…'}</div></>
                : <><div style={{marginBottom:10}}><Icon name="upload" size={32}/></div>
                    <div style={{color:'var(--fg)',fontWeight:500,marginBottom:6}}>点击上传或拖拽文件到这里</div>
                    <div style={{color:'var(--fg3)',fontSize:12}}>支持 PDF · PNG · JPG · BMP · TIFF · WEBP</div>
                    <div style={{color:'var(--fg3)',fontSize:11,marginTop:8}}>文件不会上传到服务器，完全本地处理</div></>
              }
            </label>

            {/* 相机拍照入口 */}
            <div style={{marginTop:12,display:'flex',justifyContent:'center'}}>
              <button className="btn btn-s" onClick={e=>{e.preventDefault();setShowCamera(true);}}
                style={{display:'inline-flex',alignItems:'center',gap:8,padding:'10px 24px',fontSize:13,
                  borderColor:'var(--gold-dim)',color:'var(--gold)'}}>
                <Icon name="scan" size={15}/> 使用相机拍照
              </button>
            </div>

            <div style={{marginTop:24,padding:'16px',background:'var(--bg2)',borderRadius:8,border:'1px solid var(--border)'}}>
              <div style={{fontSize:11,color:'var(--fg3)',letterSpacing:1,marginBottom:10}}>技术说明</div>
              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:8,fontSize:11,color:'var(--fg2)'}}>
                {[
                  ['曲面平整化','逐列扫描边缘 + 多项式拟合 + 双线性重映射'],
                  ['CLAHE 对比度','分块直方图均衡化 + 双线性插值合并'],
                  ['自适应二值化','积分图 O(1) 局部均值/Sauvola 阈值'],
                  ['去除阴影','形态膨胀估计背景 + 通道逐像素归一化'],
                  ['透视校正','Sobel 边缘 + DLT 单应矩阵 + 双线性重采样'],
                  ['自动纠偏','投影剖面方差打分 + 最优角度旋转'],
                ].map(([t,d])=>(
                  <div key={t} style={{background:'var(--bg3)',borderRadius:4,padding:'8px 10px'}}>
                    <div style={{fontWeight:500,color:'var(--gold)',marginBottom:3}}>{t}</div>
                    <div style={{color:'var(--fg3)',lineHeight:1.4}}>{d}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── 编辑器视图 ── */}
        {view === 'editor' && mode === 'enhance' && curPage && (
          <div style={{flex:1,display:'flex',overflow:'hidden',minHeight:0}}>
            {/* 左侧操作面板 */}
            <div style={{width:268,borderRight:'1px solid var(--border)',display:'flex',flexDirection:'column',
              background:'var(--bg2)',flexShrink:0,overflow:'hidden'}}>
              <div style={{padding:'10px 14px',borderBottom:'1px solid var(--border)',fontSize:11,color:'var(--fg3)',letterSpacing:2}}>处理操作</div>
              <div style={{flex:1,overflowY:'auto',padding:'8px 10px'}}>
                {SCAN_OPS.map(op => {
                  const active = !!enabledOps[op.key];
                  return (
                    <div key={op.key} style={{marginBottom:5,borderRadius:6,overflow:'hidden',
                      border:`1px solid ${active?'var(--gold-dim)':'var(--border)'}`,
                      background: active?'rgba(201,168,108,.07)':'var(--bg3)'}}>
                      <div style={{display:'flex',alignItems:'center',gap:8,padding:'7px 10px',cursor:'pointer'}}
                        onClick={() => toggleOp(op.key)}>
                        <input type="checkbox" checked={active} readOnly
                          style={{accentColor:'var(--gold)',flexShrink:0,pointerEvents:'none'}}/>
                        <span style={{flexShrink:0}}><Icon name={op.icon} size={13}/></span>
                        <div style={{flex:1,minWidth:0}}>
                          <div style={{fontSize:12,fontWeight:500,color:active?'var(--gold2)':'var(--fg)'}}>{op.label}</div>
                          <div style={{fontSize:9,color:'var(--fg3)',marginTop:1,lineHeight:1.35,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{op.desc}</div>
                        </div>
                      </div>
                      {active && op.params.length > 0 && (
                        <div style={{borderTop:'1px solid var(--border)',padding:'8px 10px',background:'var(--bg4)'}}>
                          {op.params.map(pm => (
                            <div key={pm.name} style={{marginBottom:7}}>
                              <div style={{display:'flex',justifyContent:'space-between',marginBottom:3}}>
                                <span style={{fontSize:10,color:'var(--fg3)'}}>{pm.label}</span>
                                <span style={{fontSize:10,fontFamily:'var(--mono)',color:'var(--gold)'}}>{opParams[op.key]?.[pm.name]??pm.default}</span>
                              </div>
                              {pm.type==='range' ? (
                                <input type="range" min={pm.min} max={pm.max} step={pm.step}
                                  value={opParams[op.key]?.[pm.name]??pm.default}
                                  onChange={e=>setParam(op.key,pm.name,parseFloat(e.target.value))}
                                  style={{width:'100%',height:3,accentColor:'var(--gold)',background:'none',border:'none',padding:0}}/>
                              ) : pm.type==='select' ? (
                                <select value={opParams[op.key]?.[pm.name]??pm.default}
                                  onChange={e=>setParam(op.key,pm.name,e.target.value)}
                                  style={{width:'100%',fontSize:11,padding:'3px 6px'}}>
                                  {pm.options.map(o=><option key={o.v} value={o.v}>{o.label}</option>)}
                                </select>
                              ) : null}
                              {pm.hint && <div style={{fontSize:9,color:'var(--fg3)',marginTop:2,lineHeight:1.3}}>{pm.hint}</div>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* 处理按钮 */}
              <div style={{padding:'10px 10px',borderTop:'1px solid var(--border)'}}>
                {progress && processing && (
                  <div style={{fontSize:10,color:'var(--cyan)',marginBottom:6,textAlign:'center',
                    padding:'4px 8px',background:'var(--bg4)',borderRadius:4,lineHeight:1.4}}>
                    {progress}
                  </div>
                )}
                <button className="btn btn-p" style={{width:'100%',fontSize:13}}
                  onClick={handleProcess} disabled={processing}>
                  {processing ? <><Icon name="refresh" size={13}/> 处理中…</> : '▶ 在浏览器中处理'}
                </button>
              </div>

              {/* 多页选择 */}
              {pages.length > 1 && (
                <div style={{padding:'8px 10px',borderTop:'1px solid var(--border)',display:'flex',gap:4,flexWrap:'wrap'}}>
                  {pages.map((p, i) => (
                    <button key={i} className={`btn btn-sm${curIdx===i?' btn-p':' btn-s'}`}
                      style={{position:'relative'}} onClick={()=>setCurIdx(i)}>
                      {p.num}
                      {p.procDataUrl && <span style={{position:'absolute',top:-3,right:-3,width:6,height:6,borderRadius:'50%',background:'var(--green)'}}/>}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 右侧前后对比区 */}
            <div style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden',background:'var(--bg)'}}>
              <div style={{padding:'7px 14px',borderBottom:'1px solid var(--border)',
                display:'flex',alignItems:'center',gap:12,background:'var(--bg2)',fontSize:12}}>
                <span style={{color:'var(--fg3)'}}>拖动分割线对比原始 / 处理后效果</span>
                {curPage.procDataUrl && (
                  <span style={{color:'var(--green)',marginLeft:'auto',display:'inline-flex',alignItems:'center',gap:4}}>
                    <Icon name="check" size={11}/> 处理完成（浏览器端）
                  </span>
                )}
              </div>
              <div ref={sliderRef} style={{flex:1,position:'relative',overflow:'hidden',userSelect:'none'}}>
                {/* 原始图 */}
                <div style={{position:'absolute',inset:0,display:'flex',alignItems:'center',justifyContent:'center',background:'#111',overflow:'hidden'}}>
                  {curPage.origDataUrl
                    ? <img src={curPage.origDataUrl} alt="original" style={{maxHeight:'100%',maxWidth:'100%',objectFit:'contain'}}/>
                    : <div style={{color:'var(--fg3)'}}>无图片</div>}
                </div>
                {/* 处理后图（左侧裁剪） */}
                {curPage.procDataUrl && (
                  <div style={{position:'absolute',inset:0,clipPath:`inset(0 ${100-splitPos}% 0 0)`,
                    display:'flex',alignItems:'center',justifyContent:'center',background:'#111',overflow:'hidden'}}>
                    <img src={curPage.procDataUrl} alt="processed" style={{maxHeight:'100%',maxWidth:'100%',objectFit:'contain'}}/>
                  </div>
                )}
                {/* 标签 */}
                {curPage.procDataUrl && (<>
                  <div style={{position:'absolute',top:10,left:12,background:'rgba(94,184,122,.9)',color:'#000',
                    fontSize:10,padding:'2px 8px',borderRadius:3,pointerEvents:'none',display:splitPos>10?'block':'none'}}>处理后</div>
                  <div style={{position:'absolute',top:10,right:12,background:'rgba(0,0,0,.55)',color:'var(--fg2)',
                    fontSize:10,padding:'2px 8px',borderRadius:3,pointerEvents:'none',display:splitPos<90?'block':'none'}}>原始</div>
                  {/* 分割线 */}
                  <div style={{position:'absolute',top:0,bottom:0,left:`${splitPos}%`,width:2,
                    background:'var(--gold)',cursor:'ew-resize',transform:'translateX(-50%)'}}
                    onMouseDown={e=>{e.preventDefault();setDragging(true);}}>
                    <div style={{position:'absolute',top:'50%',left:'50%',transform:'translate(-50%,-50%)',
                      width:26,height:26,borderRadius:'50%',background:'var(--gold)',
                      display:'flex',alignItems:'center',justifyContent:'center',
                      fontSize:13,color:'#000',boxShadow:'0 2px 8px rgba(0,0,0,.5)'}}>⇔</div>
                  </div>
                </>)}
                {!curPage.procDataUrl && !processing && (
                  <div style={{position:'absolute',bottom:20,left:'50%',transform:'translateX(-50%)',
                    background:'rgba(0,0,0,.65)',color:'var(--fg2)',fontSize:12,padding:'8px 18px',
                    borderRadius:20,pointerEvents:'none',whiteSpace:'nowrap'}}>
                    勾选操作 → 点击「在浏览器中处理」
                  </div>
                )}
                {processing && (
                  <div style={{position:'absolute',inset:0,background:'rgba(0,0,0,.55)',
                    display:'flex',alignItems:'center',justifyContent:'center',flexDirection:'column',gap:14}}>
                    <div><Icon name="settings" size={36}/></div>
                    <div style={{color:'var(--fg)',fontSize:15,fontWeight:500}}>浏览器端处理中…</div>
                    <div style={{color:'var(--cyan)',fontSize:12,maxWidth:320,textAlign:'center'}}>{progress}</div>
                    <div style={{color:'var(--fg3)',fontSize:11}}>服务器 CPU 占用：0%</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── CameraCapture 弹层 ── */}
      {showCamera && (
        <CameraCapture
          onCapture={handleCameraCapture}
          onClose={() => setShowCamera(false)}
        />
      )}
    </div>
  );
}

{% endverbatim %}
{% verbatim %}
// ── AI 题库 ──────────────────────────────────────────────────────────────────

function QBMd({content}) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (!ref.current || !content) return;
    ref.current.innerHTML = window.marked ? window.marked.parse(content) : content.replace(/\n/g,'<br>');
    if (window.MathJax && window.MathJax.typesetPromise) {
      window.MathJax.typesetPromise([ref.current]).catch(()=>{});
    }
  }, [content]);
  return <div ref={ref} style={{lineHeight:1.7, fontSize:14}} className="md-body" />;
}

function QBModelBadge({model}) {
  const isVision = model === 'glm-4v-flash';
  return (
    <span style={{
      display:'inline-flex', alignItems:'center', gap:4, padding:'2px 7px',
      borderRadius:10, fontSize:11,
      background: isVision ? 'rgba(154,106,196,0.18)' : 'rgba(90,138,196,0.18)',
      color: isVision ? 'var(--purple)' : 'var(--blue)',
      border: `1px solid ${isVision ? 'rgba(154,106,196,0.35)' : 'rgba(90,138,196,0.35)'}`,
    }}>
      <Icon name={isVision ? 'eye' : 'chat'} size={12} />
      <span>{isVision ? 'GLM-4V' : 'GLM-4.7'}</span>
    </span>
  );
}

function QuestionBankApp({user, onLogout, onUpdateUser}) {
  const token = localStorage.getItem('mf_token');
  const [view, setView] = React.useState('list'); // list | edit | shared | shared-detail
  const [questions, setQuestions] = React.useState([]);
  const [currentQ, setCurrentQ] = React.useState(null);
  const [sharedList, setSharedList] = React.useState([]);
  const [currentShared, setCurrentShared] = React.useState(null);
  const [sbOpen, setSbOpen] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [sharedSearch, setSharedSearch] = React.useState('');
  const [sharedSubject, setSharedSubject] = React.useState('');

  const headers = React.useMemo(() => ({
    'Content-Type': 'application/json',
    ...(token ? {'Authorization': `Token ${token}`} : {}),
  }), [token]);

  const authFetch = React.useCallback(async (url, opts = {}) => {
    const r = await fetch(url, {...opts, headers: {...headers, ...(opts.headers||{})}});
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }, [headers]);

  const loadQuestions = React.useCallback(async () => {
    if (!token) return;
    try {
      const data = await authFetch('/api/qbank/questions/');
      setQuestions(data);
    } catch {}
  }, [authFetch, token]);

  const loadShared = React.useCallback(async (search='', subject='') => {
    try {
      const params = new URLSearchParams();
      if (search) params.set('q', search);
      if (subject) params.set('subject', subject);
      const r = await fetch(`/api/qbank/shared/?${params}`, {headers});
      if (!r.ok) return;
      setSharedList(await r.json());
    } catch {}
  }, [headers]);

  React.useEffect(() => {
    if (view === 'list') loadQuestions();
    if (view === 'shared') loadShared(sharedSearch, sharedSubject);
  }, [view, loadQuestions, loadShared, sharedSearch, sharedSubject]);

  const openNew = () => {
    setCurrentQ({
      id: null, title: '', content: '', model_used: 'glm-4.7-flash',
      tags: '', subject: '', has_image: false, image_data_url: '',
      original_image: '', image_type: 'jpeg',
      messages: [], final_answer_content: '',
      standard_answer_md: '', standard_answer_image: '', is_published: false,
    });
    setView('edit');
  };

  const openQuestion = async (q) => {
    setLoading(true);
    try {
      const data = await authFetch(`/api/qbank/questions/${q.id}/`);
      setCurrentQ(data);
      setView('edit');
    } catch (e) { showAlert('加载失败: ' + e.message, '错误'); }
    setLoading(false);
  };

  const openSharedDetail = async (sq) => {
    setLoading(true);
    try {
      const data = await authFetch(`/api/qbank/shared/${sq.id}/`);
      setCurrentShared(data);
      setView('shared-detail');
    } catch (e) { showAlert('加载失败: ' + e.message, '错误'); }
    setLoading(false);
  };

  const deleteQuestion = async (q) => {
    const confirmed = await showConfirm(`确认删除「${q.title}」？`);
    if (!confirmed) return;
    try {
      await fetch(`/api/qbank/questions/${q.id}/`, {method:'DELETE', headers});
      loadQuestions();
    } catch {}
  };

  return (
    <div className="qb-minimal" style={{display:'flex', height:'100vh', overflow:'hidden', fontFamily:'var(--sans)'}}>
      {/* 侧边栏 */}
      <div className={`sb${sbOpen?' open':''}`} style={{position:'relative',zIndex:10}}>
        <div className="sb-hd">
          <h1>AI 题库</h1>
          <p style={{fontSize:10,color:'var(--fg3)',marginTop:3,letterSpacing:2}}>QUESTION BANK</p>
        </div>
        <div className="sb-nav">
          <div className="ns">
            <div className="ns-t">功能</div>
            {[
              {v:'list', label:'我的题目', icon:'note'},
              {v:'shared', label:'共享题库', icon:'share-2'},
            ].map(item => (
              <div key={item.v}
                className={`ni${view===item.v||(!['shared','shared-detail'].includes(view)&&item.v==='list'&&view==='list')?' on':''}`}
                onClick={() => { setView(item.v); setSbOpen(false); }}>
                <span style={{display:'inline-flex',alignItems:'center'}}><Icon name={item.icon} size={13} /></span>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
          {view === 'edit' && currentQ && (
            <div className="ns">
              <div className="ns-t">当前题目</div>
              <div className="ni on" style={{fontSize:12,wordBreak:'break-word',whiteSpace:'normal',lineHeight:1.4}}>
                {currentQ.title || '新题目'}
              </div>
            </div>
          )}
        </div>
        <div style={{padding:'10px 14px', borderTop:'1px solid var(--border)'}}>
          <div style={{fontSize:11, color:'var(--fg3)', marginBottom:6}}>{user?.email || '访客'}</div>
          <div style={{display:'flex', gap:6}}>
            <button onClick={() => window.location.hash='#/'} style={{flex:1,background:'var(--bg3)',color:'var(--fg2)',padding:'5px 0',borderRadius:'var(--r)',fontSize:11}}>← MineAI 首页</button>
            <button onClick={onLogout} style={{flex:1,background:'var(--bg3)',color:'var(--fg2)',padding:'5px 0',borderRadius:'var(--r)',fontSize:11}}>退出</button>
          </div>
        </div>
      </div>

      {/* 主内容 */}
      <div style={{flex:1, display:'flex', flexDirection:'column', overflow:'hidden', minWidth:0}}>
        {/* 顶栏 */}
        <div style={{height:46,borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',padding:'0 16px',gap:10,background:'var(--bg2)',flexShrink:0}}>
          <button style={{background:'transparent',border:'none',color:'var(--fg3)',cursor:'pointer',padding:'4px',display:'flex',alignItems:'center'}} onClick={()=>setSbOpen(o=>!o)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          </button>
          <span style={{fontSize:14,fontWeight:500,color:'var(--fg)'}}>
            {view==='list'?'我的题目':view==='edit'?(currentQ?.id?`编辑: ${currentQ.title||'题目'}` :'新建题目'):view==='shared'?'共享题库':'题目详情'}
          </span>
          {view === 'edit' && currentQ?.id && (
            <button onClick={()=>setView('list')} style={{background:'transparent',color:'var(--fg3)',fontSize:12,marginLeft:8}}>← 返回列表</button>
          )}
          {view === 'shared-detail' && (
            <button onClick={()=>setView('shared')} style={{background:'transparent',color:'var(--fg3)',fontSize:12,marginLeft:8}}>← 返回题库</button>
          )}
          {view === 'list' && (
            <button className="btn btn-p btn-sm" style={{marginLeft:'auto'}} onClick={openNew}>+ 新建题目</button>
          )}
        </div>

        {/* 内容区 */}
        <div style={{flex:1,overflow:'auto',minHeight:0}}>
          {loading && <div style={{textAlign:'center',padding:40,color:'var(--fg3)'}}>加载中…</div>}
          {!loading && view === 'list' && (
            <QBMyQuestions questions={questions} onOpen={openQuestion} onDelete={deleteQuestion} onNew={openNew} />
          )}
          {!loading && view === 'edit' && currentQ && (
            <QBEditView
              question={currentQ}
              onSaved={(q) => { setCurrentQ(q); }}
              onBack={() => { loadQuestions(); setView('list'); }}
              token={token}
              headers={headers}
              authFetch={authFetch}
              user={user}
            />
          )}
          {!loading && view === 'shared' && (
            <QBSharedList
              list={sharedList}
              search={sharedSearch}
              subject={sharedSubject}
              onSearchChange={setSharedSearch}
              onSubjectChange={setSharedSubject}
              onSearch={()=>loadShared(sharedSearch,sharedSubject)}
              onOpen={openSharedDetail}
              user={user}
              headers={headers}
            />
          )}
          {!loading && view === 'shared-detail' && currentShared && (
            <QBSharedDetail
              shared={currentShared}
              onBack={() => setView('shared')}
              token={token}
              headers={headers}
              authFetch={authFetch}
              user={user}
              onReload={async () => {
                try { const d = await authFetch(`/api/qbank/shared/${currentShared.id}/`); setCurrentShared(d); } catch {}
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ── 我的题目列表 ──────────────────────────────────────────────────────────────

function QBMyQuestions({questions, onOpen, onDelete, onNew}) {
  if (questions.length === 0) {
    return (
      <div style={{display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',height:'100%',gap:16,color:'var(--fg3)'}}>
        <div style={{display:'inline-flex',alignItems:'center',justifyContent:'center',width:48,height:48,borderRadius:12,border:'1px solid var(--border2)',background:'var(--bg3)'}}><Icon name="note" size={22}/></div>
        <div style={{fontSize:16,color:'var(--fg2)'}}>还没有题目</div>
        <div style={{fontSize:13}}>上传题目图片，用 OCR 或视觉模型识别，然后让 AI 解答</div>
        <button className="btn btn-p" style={{marginTop:8}} onClick={onNew}>新建题目</button>
      </div>
    );
  }
  return (
    <div style={{padding:'20px',display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:14}}>
      {questions.map(q => (
        <div key={q.id} style={{background:'var(--bg2)',borderRadius:8,border:'1px solid var(--border)',padding:'14px',cursor:'pointer',transition:'border .15s'}}
          onMouseEnter={e=>e.currentTarget.style.borderColor='var(--gold-dim)'}
          onMouseLeave={e=>e.currentTarget.style.borderColor='var(--border)'}>
          <div style={{display:'flex',gap:8,alignItems:'flex-start',marginBottom:8}}>
            <div style={{flex:1,minWidth:0}} onClick={()=>onOpen(q)}>
              <div style={{fontWeight:500,color:'var(--fg)',marginBottom:4,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{q.title || '未命名题目'}</div>
              <div style={{fontSize:12,color:'var(--fg3)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{q.content || '(无文字内容)'}</div>
            </div>
            <button onClick={e=>{e.stopPropagation();onDelete(q);}}
              style={{background:'transparent',color:'var(--fg3)',fontSize:16,padding:'0 2px',lineHeight:1,flexShrink:0}}>×</button>
          </div>
          <div style={{display:'flex',gap:6,flexWrap:'wrap',alignItems:'center'}} onClick={()=>onOpen(q)}>
            <QBModelBadge model={q.model_used} />
            {q.subject && <span style={{fontSize:11,color:'var(--fg3)',padding:'1px 6px',borderRadius:8,background:'var(--bg4)'}}>{q.subject}</span>}
            {q.is_published && <span style={{fontSize:11,color:'var(--green)',padding:'1px 6px',borderRadius:8,background:'rgba(94,184,122,0.12)'}}>已发布</span>}
            {q.has_final_answer && <span style={{fontSize:11,color:'var(--gold)',padding:'1px 6px',borderRadius:8,background:'rgba(201,168,108,0.12)'}}>有答案</span>}
            {q.has_image && <span style={{fontSize:11,color:'var(--cyan)',padding:'1px 6px',borderRadius:8,background:'rgba(90,196,180,0.12)'}}>有图片</span>}
          </div>
          <div style={{fontSize:11,color:'var(--fg3)',marginTop:8,cursor:'pointer'}} onClick={()=>onOpen(q)}>
            {new Date(q.created_at).toLocaleDateString('zh-CN')}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── 题目编辑视图 ──────────────────────────────────────────────────────────────

function QBEditView({question, onSaved, onBack, token, headers, authFetch, user}) {
  const [q, setQ] = React.useState(question);
  const [tab, setTab] = React.useState('question'); // question | chat | answer | standard | publish
  const [ocrLoading, setOcrLoading] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [model, setModel] = React.useState(question.model_used || 'glm-4.7-flash');
  const [msgs, setMsgs] = React.useState(question.messages || []);
  const [chatInput, setChatInput] = React.useState('');
  const [streaming, setStreaming] = React.useState(false);
  const [streamText, setStreamText] = React.useState('');
  const [finalAnswer, setFinalAnswer] = React.useState(question.final_answer_content || '');
  const [editingFinal, setEditingFinal] = React.useState(false);
  const [stdMd, setStdMd] = React.useState(question.standard_answer_md || '');
  const [stdImage, setStdImage] = React.useState('');
  const [stdImageType, setStdImageType] = React.useState('jpeg');
  const [stdPreview, setStdPreview] = React.useState(question.standard_answer_image || '');
  const [publishing, setPublishing] = React.useState(false);
  const chatEndRef = React.useRef(null);

  React.useEffect(() => {
    chatEndRef.current?.scrollIntoView({behavior:'smooth'});
  }, [msgs, streamText]);

  // 处理图片上传（题目图片）
  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (ev) => {
      const dataUrl = ev.target.result;
      const [meta, b64] = dataUrl.split(',');
      const imgType = meta.match(/image\/([^;]+)/)?.[1] || 'jpeg';
      setQ(prev => ({...prev, image_data_url: dataUrl, original_image: b64, image_type: imgType, has_image: true}));
    };
    reader.readAsDataURL(file);
  };

  // OCR 识别
  const runOCR = async () => {
    if (!q.original_image) return;
    setOcrLoading(true);
    try {
      const resp = await fetch('/api/qbank/ocr/', {
        method: 'POST',
        headers,
        body: JSON.stringify({image_b64: q.original_image, image_type: q.image_type}),
      });
      const data = await resp.json();
      if (data.error) throw new Error(data.error);
      setQ(prev => ({...prev, content: data.text || ''}));
    } catch (e) { showAlert('OCR 失败: ' + e.message, '错误'); }
    setOcrLoading(false);
  };

  // 保存题目（新建或更新）
  const saveQuestion = async () => {
    setSaving(true);
    try {
      let saved;
      if (!q.id) {
        saved = await authFetch('/api/qbank/questions/', {
          method: 'POST',
          body: JSON.stringify({
            title: q.title || q.content.slice(0,60) || '新题目',
            content: q.content,
            original_image: q.original_image,
            image_type: q.image_type,
            model_used: model,
            tags: q.tags,
            subject: q.subject,
          }),
        });
      } else {
        saved = await authFetch(`/api/qbank/questions/${q.id}/`, {
          method: 'PUT',
          body: JSON.stringify({
            title: q.title || q.content.slice(0,60) || '新题目',
            content: q.content,
            original_image: q.original_image,
            image_type: q.image_type,
            model_used: model,
            tags: q.tags,
            subject: q.subject,
          }),
        });
      }
      setQ(prev => ({...prev, ...saved, image_data_url: prev.image_data_url}));
      onSaved({...saved, image_data_url: q.image_data_url});
      return saved;
    } catch (e) { showAlert('保存失败: ' + e.message, '错误'); return null; }
    finally { setSaving(false); }
  };

  // 切换模型
  const handleModelChange = (newModel) => {
    setModel(newModel);
    setQ(prev => ({...prev, model_used: newModel}));
  };

  // 发送消息 (SSE)
  const sendMessage = async () => {
    if (!chatInput.trim() || streaming) return;
    let qid = q.id;
    if (!qid) {
      const saved = await saveQuestion();
      if (!saved) return;
      qid = saved.id;
    }
    const userMsg = chatInput.trim();
    setChatInput('');
    setMsgs(prev => [...prev, {role:'user', content:userMsg, model_used:model}]);
    setStreaming(true);
    setStreamText('');

    const isVision = model === 'glm-4v-flash';
    const includeImage = isVision && q.has_image && msgs.length === 0;

    try {
      const resp = await fetch(`/api/qbank/questions/${qid}/chat-stream/`, {
        method: 'POST',
        headers,
        body: JSON.stringify({message: userMsg, model, include_image: includeImage}),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const reader = resp.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      let full = '';
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        buf += dec.decode(value, {stream:true});
        const lines = buf.split('\n');
        buf = lines.pop();
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const ev = JSON.parse(line.slice(6));
            if (ev.content) { full += ev.content; setStreamText(full); }
            if (ev.done) {
              setMsgs(prev => [...prev, {role:'assistant', content:full, model_used:model}]);
              setStreamText('');
            }
          } catch {}
        }
      }
    } catch (e) {
      setMsgs(prev => [...prev, {role:'assistant', content:`错误: ${e.message}`, model_used:model}]);
    }
    setStreaming(false);
    setStreamText('');
  };

  // 保存最终答案
  const saveFinal = async () => {
    let qid = q.id;
    if (!qid) { const s = await saveQuestion(); if (!s) return; qid = s.id; }
    try {
      await authFetch(`/api/qbank/questions/${qid}/final/`, {
        method:'POST', body:JSON.stringify({content: finalAnswer}),
      });
      setEditingFinal(false);
      setQ(prev => ({...prev, has_final_answer: true, final_answer_content: finalAnswer}));
    } catch (e) { showAlert('保存失败: ' + e.message, '错误'); }
  };

  // 将 AI 回答复制到最终答案编辑器
  const importFromChat = (content) => {
    setFinalAnswer(content);
    setEditingFinal(true);
    setTab('answer');
  };

  // 处理标准答案图片
  const handleStdImage = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      const dataUrl = ev.target.result;
      const [meta, b64] = dataUrl.split(',');
      const imgType = meta.match(/image\/([^;]+)/)?.[1] || 'jpeg';
      setStdImage(b64);
      setStdImageType(imgType);
      setStdPreview(dataUrl);
    };
    reader.readAsDataURL(file);
  };

  // 保存标准答案
  const saveStandard = async () => {
    let qid = q.id;
    if (!qid) { const s = await saveQuestion(); if (!s) return; qid = s.id; }
    try {
      await authFetch(`/api/qbank/questions/${qid}/standard/`, {
        method:'POST',
        body: JSON.stringify({content_md: stdMd, image: stdImage, image_type: stdImageType}),
      });
      setQ(prev => ({...prev, has_standard_answer: true}));
      showAlert('标准答案已保存', '保存成功');
    } catch (e) { showAlert('保存失败: ' + e.message, '错误'); }
  };

  // 发布
  const publish = async () => {
    let qid = q.id;
    if (!qid) { const s = await saveQuestion(); if (!s) return; qid = s.id; }
    setPublishing(true);
    try {
      await authFetch(`/api/qbank/questions/${qid}/publish/`, {method:'POST', body:JSON.stringify({})});
      setQ(prev => ({...prev, is_published: true}));
      showAlert('发布成功！题目已出现在共享题库中。', '发布成功');
    } catch (e) { showAlert('发布失败: ' + e.message, '错误'); }
    setPublishing(false);
  };

  // 取消发布
  const unpublish = async () => {
    if (!q.id) return;
    const confirmed = await showConfirm('确认取消发布？');
    if (!confirmed) return;
    try {
      await fetch(`/api/qbank/questions/${q.id}/publish/`, {method:'DELETE', headers});
      setQ(prev => ({...prev, is_published: false}));
    } catch (e) { showAlert('操作失败: ' + e.message, '错误'); }
  };

  const tabStyle = (t) => ({
    padding:'7px 14px', fontSize:13, cursor:'pointer', borderRadius:0,
    background:'transparent', border:'none',
    borderBottom: tab===t ? '2px solid var(--gold)' : '2px solid transparent',
    color: tab===t ? 'var(--gold)' : 'var(--fg3)',
    transition:'all .15s',
  });

  return (
    <div style={{display:'flex',flexDirection:'column',height:'100%'}}>
      {/* Tab 导航 */}
      <div style={{display:'flex',borderBottom:'1px solid var(--border)',background:'var(--bg2)',flexShrink:0,paddingLeft:8}}>
        <button style={tabStyle('question')} onClick={()=>setTab('question')}><span className="with-ic"><Icon name="scan" size={12}/>题目</span></button>
        <button style={tabStyle('chat')} onClick={()=>setTab('chat')}><span className="with-ic"><Icon name="chat" size={12}/>AI 对话</span></button>
        <button style={tabStyle('answer')} onClick={()=>setTab('answer')}><span className="with-ic"><Icon name="pen" size={12}/>最终答案</span></button>
        <button style={tabStyle('standard')} onClick={()=>setTab('standard')}><span className="with-ic"><Icon name="clipboard" size={12}/>标准答案</span></button>
        <button style={tabStyle('publish')} onClick={()=>setTab('publish')}><span className="with-ic"><Icon name="share-2" size={12}/>发布</span></button>
        <button className="btn btn-p btn-sm" style={{marginLeft:'auto',marginRight:8,marginTop:4,marginBottom:4}} onClick={saveQuestion} disabled={saving}>
          {saving ? '保存中…' : '保存'}
        </button>
      </div>

      {/* Tab 内容 */}
      <div style={{flex:1,overflow:'auto',padding:20}}>

        {/* ── 题目面板 ─────────────────────────────────────────── */}
        {tab === 'question' && (
          <div style={{maxWidth:800,margin:'0 auto',display:'flex',flexDirection:'column',gap:16}}>
            <div style={{display:'flex',gap:12,alignItems:'center',flexWrap:'wrap'}}>
              <label style={{fontSize:13,color:'var(--fg2)'}}>模型选择：</label>
              <button onClick={()=>handleModelChange('glm-4.7-flash')}
                style={{padding:'5px 12px',borderRadius:20,border:`1px solid ${model==='glm-4.7-flash'?'var(--blue)':'var(--border2)'}`,
                  background:model==='glm-4.7-flash'?'rgba(90,138,196,0.15)':'transparent',
                  color:model==='glm-4.7-flash'?'var(--blue)':'var(--fg3)',fontSize:12,cursor:'pointer'}}>
                <span className="with-ic"><Icon name="chat" size={12}/>GLM-4.7（文字题）</span>
              </button>
              <button onClick={()=>handleModelChange('glm-4v-flash')}
                style={{padding:'5px 12px',borderRadius:20,border:`1px solid ${model==='glm-4v-flash'?'var(--purple)':'var(--border2)'}`,
                  background:model==='glm-4v-flash'?'rgba(154,106,196,0.15)':'transparent',
                  color:model==='glm-4v-flash'?'var(--purple)':'var(--fg3)',fontSize:12,cursor:'pointer'}}>
                <span className="with-ic"><Icon name="eye" size={12}/>GLM-4V（几何/图形题）</span>
              </button>
            </div>

            <div style={{display:'flex',gap:12,flexWrap:'wrap'}}>
              <div style={{flex:'1 1 140px'}}>
                <div style={{fontSize:12,color:'var(--fg3)',marginBottom:4}}>科目/标签</div>
                <input value={q.subject} onChange={e=>setQ(p=>({...p,subject:e.target.value}))} placeholder="如：数学、物理…" style={{width:'100%'}} />
              </div>
              <div style={{flex:'2 1 200px'}}>
                <div style={{fontSize:12,color:'var(--fg3)',marginBottom:4}}>题目标题</div>
                <input value={q.title} onChange={e=>setQ(p=>({...p,title:e.target.value}))} placeholder="题目标题（可选，留空自动截取）" style={{width:'100%'}} />
              </div>
            </div>

            {/* 图片上传区 */}
            <div style={{border:'1px dashed var(--border2)',borderRadius:8,padding:16,textAlign:'center',background:'var(--bg3)'}}>
              {q.image_data_url ? (
                <div>
                  <img src={q.image_data_url} alt="题目图片" style={{maxWidth:'100%',maxHeight:320,borderRadius:6,marginBottom:10}} />
                  <div style={{display:'flex',gap:8,justifyContent:'center',flexWrap:'wrap'}}>
                    {model !== 'glm-4v-flash' && (
                      <button className="btn btn-p btn-sm" onClick={runOCR} disabled={ocrLoading}>
                        {ocrLoading ? '识别中…' : <span className="with-ic"><Icon name="search" size={12}/>OCR 识别文字</span>}
                      </button>
                    )}
                    <label className="btn btn-s btn-sm" style={{cursor:'pointer',display:'inline-flex',alignItems:'center',gap:4}}>
                      <span className="with-ic"><Icon name="refresh" size={12}/>换图片</span>
                      <input type="file" accept="image/*" style={{display:'none'}} onChange={handleImageUpload} />
                    </label>
                    <button className="btn btn-sm" style={{background:'var(--bg5)',color:'var(--fg3)'}}
                      onClick={()=>setQ(p=>({...p,image_data_url:'',original_image:'',has_image:false}))}>
                      <span className="with-ic"><Icon name="x" size={12}/>移除</span>
                    </button>
                  </div>
                </div>
              ) : (
                <label style={{cursor:'pointer',display:'flex',flexDirection:'column',alignItems:'center',gap:8,padding:12}}>
                  <div style={{display:'inline-flex',alignItems:'center',justifyContent:'center',width:42,height:42,borderRadius:10,border:'1px solid var(--border2)',background:'var(--bg2)'}}><Icon name="scan" size={18}/></div>
                  <div style={{fontSize:14,color:'var(--fg2)'}}>点击上传题目图片</div>
                  <div style={{fontSize:12,color:'var(--fg3)'}}>支持 JPG / PNG，上传后可 OCR 识别文字或直接用视觉模型解题</div>
                  <input type="file" accept="image/*" style={{display:'none'}} onChange={handleImageUpload} />
                </label>
              )}
            </div>

            {/* 题目文字内容 */}
            <div>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:6}}>
                <span style={{fontSize:12,color:'var(--fg3)'}}>
                  题目文字内容
                  {model !== 'glm-4v-flash' && <span style={{marginLeft:6,color:'var(--fg3)',fontSize:11}}>（OCR识别后可在此编辑）</span>}
                  {model === 'glm-4v-flash' && <span style={{marginLeft:6,color:'var(--purple)',fontSize:11}}>（视觉模型将直接读取图片，文字可选填）</span>}
                </span>
              </div>
              <textarea value={q.content} onChange={e=>setQ(p=>({...p,content:e.target.value}))}
                placeholder={model === 'glm-4v-flash' ? '可选：用文字补充描述题目…' : '在此粘贴或编辑题目文字…'}
                style={{width:'100%',minHeight:140,fontFamily:'var(--mono)',fontSize:13}} />
            </div>

            <div style={{display:'flex',justifyContent:'flex-end',gap:8}}>
              <button className="btn btn-p" onClick={()=>{ saveQuestion().then(()=>setTab('chat')); }}>
                保存并去 AI 对话 →
              </button>
            </div>
          </div>
        )}

        {/* ── AI 对话面板 ──────────────────────────────────────── */}
        {tab === 'chat' && (
          <div style={{display:'flex',flexDirection:'column',height:'calc(100vh - 140px)',maxWidth:800,margin:'0 auto'}}>
            {/* 模型切换提示 */}
            <div style={{display:'flex',gap:8,alignItems:'center',marginBottom:12,padding:'8px 12px',background:'var(--bg3)',borderRadius:8,flexShrink:0}}>
              <span style={{fontSize:12,color:'var(--fg3)',marginRight:4}}>当前模型：</span>
              <button onClick={()=>handleModelChange('glm-4.7-flash')}
                style={{padding:'3px 10px',borderRadius:14,border:`1px solid ${model==='glm-4.7-flash'?'var(--blue)':'var(--border2)'}`,
                  background:model==='glm-4.7-flash'?'rgba(90,138,196,0.15)':'transparent',
                  color:model==='glm-4.7-flash'?'var(--blue)':'var(--fg3)',fontSize:11,cursor:'pointer'}}>
                <span className="with-ic"><Icon name="chat" size={11}/>GLM-4.7</span>
              </button>
              <button onClick={()=>handleModelChange('glm-4v-flash')}
                style={{padding:'3px 10px',borderRadius:14,border:`1px solid ${model==='glm-4v-flash'?'var(--purple)':'var(--border2)'}`,
                  background:model==='glm-4v-flash'?'rgba(154,106,196,0.15)':'transparent',
                  color:model==='glm-4v-flash'?'var(--purple)':'var(--fg3)',fontSize:11,cursor:'pointer'}}>
                <span className="with-ic"><Icon name="eye" size={11}/>GLM-4V</span>
              </button>
              <span style={{fontSize:11,color:'var(--fg3)',marginLeft:4}}>切换模型不会清空对话历史</span>
              {msgs.length > 0 && (
                <button style={{marginLeft:'auto',background:'transparent',color:'var(--fg3)',fontSize:12,cursor:'pointer',border:'1px solid var(--border2)',borderRadius:4,padding:'2px 8px'}}
                  onClick={async ()=>{ const confirmed = await showConfirm('确认清空对话历史？'); if(confirmed) setMsgs([]); }}>
                  清空对话
                </button>
              )}
            </div>

            {/* 消息列表 */}
            <div style={{flex:1,overflow:'auto',display:'flex',flexDirection:'column',gap:12,paddingBottom:8}}>
              {msgs.length === 0 && !streaming && (
                <div style={{textAlign:'center',color:'var(--fg3)',padding:30}}>
                  <div style={{marginBottom:8}}><Icon name="bot" size={20}/></div>
                  <div style={{fontSize:14,marginBottom:4}}>向 AI 提问</div>
                  <div style={{fontSize:12}}>描述你的问题，或让 AI 解答题目图片中的内容</div>
                  {q.content && (
                    <button className="btn btn-p btn-sm" style={{marginTop:12}} onClick={()=>setChatInput(`请解答以下题目：\n\n${q.content}`)}>
                      一键发送题目内容
                    </button>
                  )}
                  {model === 'glm-4v-flash' && q.has_image && (
                    <button className="btn btn-sm" style={{marginTop:8,marginLeft:8,background:'rgba(154,106,196,0.15)',color:'var(--purple)',border:'1px solid var(--purple)'}}
                      onClick={()=>setChatInput('请解答这道题，请给出详细解题步骤。')}>
                      让 GLM-4V 直接看图解题
                    </button>
                  )}
                </div>
              )}
              {msgs.map((m, i) => (
                <div key={i} style={{display:'flex',flexDirection:'column',alignItems:m.role==='user'?'flex-end':'flex-start'}}>
                  <div style={{fontSize:11,color:'var(--fg3)',marginBottom:3,display:'flex',alignItems:'center',gap:6}}>
                    <span>{m.role==='user'?'你':'AI'}</span>
                    {m.model_used && <QBModelBadge model={m.model_used} />}
                  </div>
                  <div style={{
                    maxWidth:'80%', padding:'10px 14px', borderRadius:8,
                    background: m.role==='user' ? 'var(--bg4)' : 'var(--bg3)',
                    border: '1px solid var(--border)',
                    position:'relative',
                  }}>
                    {m.role === 'assistant' ? <QBMd content={m.content} /> : <span style={{fontSize:13,whiteSpace:'pre-wrap'}}>{m.content}</span>}
                    {m.role === 'assistant' && (
                      <button onClick={()=>importFromChat(m.content)}
                        style={{marginTop:8,background:'transparent',color:'var(--gold)',fontSize:11,cursor:'pointer',
                          border:'1px solid var(--gold-dim)',borderRadius:4,padding:'2px 8px',display:'block'}}>
                        → 用作最终答案
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {streaming && streamText && (
                <div style={{display:'flex',flexDirection:'column',alignItems:'flex-start'}}>
                  <div style={{fontSize:11,color:'var(--fg3)',marginBottom:3,display:'flex',alignItems:'center',gap:6}}>
                    <span>AI</span><QBModelBadge model={model} />
                  </div>
                  <div style={{maxWidth:'80%',padding:'10px 14px',borderRadius:8,background:'var(--bg3)',border:'1px solid var(--border)'}}>
                    <QBMd content={streamText} />
                    <span style={{animation:'blink 1s infinite'}}>▌</span>
                  </div>
                </div>
              )}
              {streaming && !streamText && <div style={{color:'var(--fg3)',fontSize:12,textAlign:'center'}}>AI 思考中…</div>}
              <div ref={chatEndRef} />
            </div>

            {/* 输入框 */}
            <div style={{display:'flex',gap:8,marginTop:8,flexShrink:0}}>
              <textarea value={chatInput} onChange={e=>setChatInput(e.target.value)}
                onKeyDown={e=>{ if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();} }}
                placeholder="输入消息… (Enter 发送, Shift+Enter 换行)"
                style={{flex:1,minHeight:60,maxHeight:120,resize:'vertical',fontFamily:'var(--sans)',fontSize:13}} />
              <button className="btn btn-p" style={{alignSelf:'flex-end'}} onClick={sendMessage} disabled={streaming||!chatInput.trim()}>
                {streaming ? '…' : '发送'}
              </button>
            </div>
          </div>
        )}

        {/* ── 最终答案面板 ────────────────────────────────────── */}
        {tab === 'answer' && (
          <div style={{maxWidth:800,margin:'0 auto',display:'flex',flexDirection:'column',gap:16}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
              <h3 style={{fontSize:16,color:'var(--fg)'}}>最终答案（Markdown）</h3>
              <div style={{display:'flex',gap:8}}>
                {!editingFinal && finalAnswer && (
                  <button className="btn btn-s btn-sm" onClick={()=>setEditingFinal(true)}>编辑</button>
                )}
                {editingFinal && (
                  <button className="btn btn-p btn-sm" onClick={saveFinal}>保存答案</button>
                )}
              </div>
            </div>
            {editingFinal || !finalAnswer ? (
              <div>
                <textarea value={finalAnswer} onChange={e=>setFinalAnswer(e.target.value)}
                  placeholder="在此编写最终答案（支持 Markdown 和 LaTeX 数学公式）"
                  style={{width:'100%',minHeight:300,fontFamily:'var(--mono)',fontSize:13}} />
                {!editingFinal && (
                  <div style={{marginTop:8,display:'flex',gap:8}}>
                    <button className="btn btn-p btn-sm" onClick={()=>{setEditingFinal(true);}} disabled={!finalAnswer.trim()}>
                      保存为最终答案
                    </button>
                  </div>
                )}
                {editingFinal && (
                  <div style={{marginTop:8,display:'flex',gap:8}}>
                    <button className="btn btn-p btn-sm" onClick={saveFinal}>保存</button>
                    <button className="btn btn-s btn-sm" onClick={()=>setEditingFinal(false)}>取消</button>
                  </div>
                )}
              </div>
            ) : (
              <div style={{background:'var(--bg2)',borderRadius:8,border:'1px solid var(--border)',padding:20}}>
                <QBMd content={finalAnswer} />
              </div>
            )}
            {!finalAnswer && msgs.length === 0 && (
              <div style={{color:'var(--fg3)',fontSize:13,textAlign:'center',padding:20}}>
                先在「AI 对话」标签页与 AI 交流，然后点击「→ 用作最终答案」将 AI 回答引入到此处进行编辑和完善。
              </div>
            )}
          </div>
        )}

        {/* ── 标准答案面板 ────────────────────────────────────── */}
        {tab === 'standard' && (
          <div style={{maxWidth:800,margin:'0 auto',display:'flex',flexDirection:'column',gap:16}}>
            <h3 style={{fontSize:16,color:'var(--fg)'}}>标准答案（可选）</h3>
            <div style={{fontSize:13,color:'var(--fg3)'}}>上传官方标准答案，支持图片或 Markdown 文字，发布后其他用户可查看。</div>

            <div>
              <div style={{fontSize:12,color:'var(--fg3)',marginBottom:6}}>文字标准答案（Markdown）</div>
              <textarea value={stdMd} onChange={e=>setStdMd(e.target.value)}
                placeholder="在此粘贴标准答案文字，支持 Markdown 和 LaTeX…"
                style={{width:'100%',minHeight:160,fontFamily:'var(--mono)',fontSize:13}} />
            </div>

            <div style={{border:'1px dashed var(--border2)',borderRadius:8,padding:16,background:'var(--bg3)'}}>
              <div style={{fontSize:12,color:'var(--fg3)',marginBottom:8}}>标准答案图片（可选）</div>
              {stdPreview ? (
                <div>
                  <img src={stdPreview} alt="标准答案" style={{maxWidth:'100%',maxHeight:300,borderRadius:6,marginBottom:8}} />
                  <div style={{display:'flex',gap:8}}>
                    <label className="btn btn-s btn-sm" style={{cursor:'pointer'}}>
                      换图片
                      <input type="file" accept="image/*" style={{display:'none'}} onChange={handleStdImage} />
                    </label>
                    <button className="btn btn-sm" style={{background:'var(--bg5)',color:'var(--fg3)'}}
                      onClick={()=>{ setStdImage(''); setStdPreview(''); }}>移除</button>
                  </div>
                </div>
              ) : (
                <label style={{cursor:'pointer',display:'flex',flexDirection:'column',alignItems:'center',gap:6,padding:12}}>
                  <div style={{fontSize:28}}>🖼</div>
                  <div style={{fontSize:13,color:'var(--fg2)'}}>点击上传标准答案图片</div>
                  <input type="file" accept="image/*" style={{display:'none'}} onChange={handleStdImage} />
                </label>
              )}
            </div>

            <button className="btn btn-p btn-sm" style={{width:'fit-content'}} onClick={saveStandard}>
              保存标准答案
            </button>
          </div>
        )}

        {/* ── 发布面板 ─────────────────────────────────────────── */}
        {tab === 'publish' && (
          <div style={{maxWidth:600,margin:'0 auto',display:'flex',flexDirection:'column',gap:16,alignItems:'center',textAlign:'center',paddingTop:20}}>
            <div style={{display:'inline-flex',alignItems:'center',justifyContent:'center',width:56,height:56,borderRadius:16,border:'1px solid var(--border2)',background:'var(--bg3)'}}><Icon name="share-2" size={24}/></div>
            <h3 style={{fontSize:18,color:'var(--fg)'}}>发布到共享题库</h3>
            <div style={{fontSize:13,color:'var(--fg3)',maxWidth:400,lineHeight:1.8}}>
              发布后，所有用户可以查看题目内容、AI 解答和标准答案。
              其他用户可以点赞、收藏和评论。
            </div>
            <div style={{display:'flex',gap:12,flexWrap:'wrap',justifyContent:'center'}}>
              {[
                {label:'题目内容', ok: !!q.content || !!q.original_image},
                {label:'最终答案', ok: !!finalAnswer || q.has_final_answer},
                {label:'标准答案', ok: q.has_standard_answer || !!stdMd},
              ].map(item => (
                <div key={item.label} style={{padding:'6px 14px',borderRadius:20,fontSize:12,
                  background:item.ok?'rgba(94,184,122,0.12)':'var(--bg3)',
                  color:item.ok?'var(--green)':'var(--fg3)',
                  border:`1px solid ${item.ok?'rgba(94,184,122,0.3)':'var(--border2)'}`}}>
                  {item.ok ? '✓' : '○'} {item.label}
                </div>
              ))}
            </div>
            {!q.id && <div style={{color:'var(--orange)',fontSize:13}}>请先保存题目</div>}
            {q.is_published ? (
              <div style={{display:'flex',flexDirection:'column',gap:12,alignItems:'center'}}>
                <div style={{color:'var(--green)',fontSize:14}}>✓ 已发布到共享题库</div>
                <div style={{display:'flex',gap:8}}>
                  <button className="btn btn-p btn-sm" onClick={publish} disabled={publishing}>更新发布</button>
                  <button className="btn btn-sm" style={{background:'rgba(196,90,90,0.15)',color:'var(--red)',border:'1px solid var(--red)'}}
                    onClick={unpublish}>取消发布</button>
                </div>
              </div>
            ) : (
              <button className="btn btn-p" onClick={publish} disabled={publishing || !q.id} style={{padding:'10px 28px'}}>
                {publishing ? '发布中…' : '发布到共享题库'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── 共享题库列表 ──────────────────────────────────────────────────────────────

function QBSharedList({list, search, subject, onSearchChange, onSubjectChange, onSearch, onOpen, user, headers}) {
  return (
    <div style={{padding:20}}>
      <div style={{display:'flex',gap:10,marginBottom:20,flexWrap:'wrap',alignItems:'center'}}>
        <input value={search} onChange={e=>onSearchChange(e.target.value)}
          onKeyDown={e=>e.key==='Enter'&&onSearch()}
          placeholder="搜索题目…" style={{flex:'1 1 200px',maxWidth:300}} />
        <input value={subject} onChange={e=>onSubjectChange(e.target.value)}
          onKeyDown={e=>e.key==='Enter'&&onSearch()}
          placeholder="科目筛选…" style={{flex:'1 1 120px',maxWidth:160}} />
        <button className="btn btn-p btn-sm" onClick={onSearch}>搜索</button>
        <span style={{fontSize:12,color:'var(--fg3)',marginLeft:'auto'}}>{list.length} 道题</span>
      </div>
      {list.length === 0 && (
        <div style={{textAlign:'center',padding:40,color:'var(--fg3)'}}>
          <div style={{display:'inline-flex',alignItems:'center',justifyContent:'center',width:46,height:46,borderRadius:12,border:'1px solid var(--border2)',background:'var(--bg3)',marginBottom:8}}><Icon name="share-2" size={18}/></div>
          <div>共享题库暂无内容</div>
        </div>
      )}
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(300px,1fr))',gap:14}}>
        {list.map(sq => (
          <div key={sq.id} onClick={()=>onOpen(sq)}
            style={{background:'var(--bg2)',borderRadius:8,border:'1px solid var(--border)',padding:14,cursor:'pointer',transition:'border .15s'}}
            onMouseEnter={e=>e.currentTarget.style.borderColor='var(--gold-dim)'}
            onMouseLeave={e=>e.currentTarget.style.borderColor='var(--border)'}>
            <div style={{fontWeight:500,marginBottom:6,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',color:'var(--fg)'}}>
              {sq.title || '无标题'}
            </div>
            <div style={{fontSize:12,color:'var(--fg3)',marginBottom:8,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
              {sq.content || '(无文字预览)'}
            </div>
            {sq.subject && <span style={{fontSize:11,color:'var(--fg3)',padding:'1px 6px',borderRadius:8,background:'var(--bg4)',marginRight:4}}>{sq.subject}</span>}
            <div style={{display:'flex',gap:10,marginTop:8,fontSize:12,color:'var(--fg3)',alignItems:'center'}}>
              <span className="with-ic"><Icon name="check" size={11}/> {sq.like_count}</span>
              <span className="with-ic"><Icon name="star" size={11}/> {sq.favorite_count}</span>
              <span className="with-ic"><Icon name="chat" size={11}/> {sq.comment_count}</span>
              <span style={{marginLeft:'auto'}}>{sq.author}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── 共享题目详情 ──────────────────────────────────────────────────────────────

function QBSharedDetail({shared, onBack, token, headers, authFetch, user, onReload}) {
  const [comment, setComment] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);
  const [liked, setLiked] = React.useState(shared.liked);
  const [favorited, setFavorited] = React.useState(shared.favorited);
  const [likeCount, setLikeCount] = React.useState(shared.like_count);
  const [favCount, setFavCount] = React.useState(shared.favorite_count);
  const [comments, setComments] = React.useState(shared.comments || []);
  const [activeSection, setActiveSection] = React.useState('question'); // question | answer | standard

  const toggleLike = async () => {
    if (!user) { showAlert('请先登录', '提示'); return; }
    try {
      const d = await authFetch(`/api/qbank/shared/${shared.id}/like/`, {method:'POST', body:JSON.stringify({})});
      setLiked(d.liked);
      setLikeCount(d.count);
    } catch {}
  };

  const toggleFav = async () => {
    if (!user) { showAlert('请先登录', '提示'); return; }
    try {
      const d = await authFetch(`/api/qbank/shared/${shared.id}/favorite/`, {method:'POST', body:JSON.stringify({})});
      setFavorited(d.favorited);
      setFavCount(d.count);
    } catch {}
  };

  const postComment = async () => {
    if (!user) { showAlert('请先登录', '提示'); return; }
    if (!comment.trim()) return;
    setSubmitting(true);
    try {
      const c = await authFetch(`/api/qbank/shared/${shared.id}/comment/`, {method:'POST', body:JSON.stringify({content:comment})});
      setComments(prev => [...prev, c]);
      setComment('');
    } catch (e) { showAlert('评论失败: ' + e.message, '错误'); }
    setSubmitting(false);
  };

  const sectionStyle = (s) => ({
    padding:'6px 14px', fontSize:13, cursor:'pointer',
    borderRadius:0, background:'transparent', border:'none',
    borderBottom: activeSection===s ? '2px solid var(--gold)' : '2px solid transparent',
    color: activeSection===s ? 'var(--gold)' : 'var(--fg3)',
  });

  return (
    <div style={{maxWidth:860,margin:'0 auto',padding:'20px 20px 40px'}}>
      {/* 标题栏 */}
      <div style={{marginBottom:16}}>
        <h2 style={{fontSize:18,color:'var(--fg)',marginBottom:6}}>{shared.title || '无标题'}</h2>
        <div style={{display:'flex',gap:10,alignItems:'center',flexWrap:'wrap'}}>
          {shared.subject && <span style={{fontSize:12,color:'var(--fg3)',padding:'2px 8px',borderRadius:8,background:'var(--bg4)'}}>{shared.subject}</span>}
          <QBModelBadge model={shared.model_used} />
          <span style={{fontSize:12,color:'var(--fg3)'}}>作者：{shared.author}</span>
          <span style={{fontSize:12,color:'var(--fg3)'}} className="with-ic"><Icon name="eye" size={12}/> {shared.view_count} 次浏览</span>
          {/* 互动按钮 */}
          <div style={{marginLeft:'auto',display:'flex',gap:8}}>
            <button onClick={toggleLike}
              style={{padding:'5px 12px',borderRadius:20,border:`1px solid ${liked?'var(--red)':'var(--border2)'}`,
                background:liked?'rgba(196,90,90,0.15)':'transparent',
                color:liked?'var(--red)':'var(--fg3)',fontSize:12,cursor:'pointer'}}>
              <span className="with-ic"><Icon name="check" size={11}/> {likeCount}</span>
            </button>
            <button onClick={toggleFav}
              style={{padding:'5px 12px',borderRadius:20,border:`1px solid ${favorited?'var(--gold)':'var(--border2)'}`,
                background:favorited?'rgba(201,168,108,0.15)':'transparent',
                color:favorited?'var(--gold)':'var(--fg3)',fontSize:12,cursor:'pointer'}}>
              <span className="with-ic"><Icon name="star" size={11}/> {favCount}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 内容区域 */}
      <div style={{borderBottom:'1px solid var(--border)',marginBottom:16,display:'flex'}}>
        <button style={sectionStyle('question')} onClick={()=>setActiveSection('question')}><span className="with-ic"><Icon name="note" size={12}/>题目</span></button>
        {shared.final_answer && <button style={sectionStyle('answer')} onClick={()=>setActiveSection('answer')}><span className="with-ic"><Icon name="pen" size={12}/>AI 解答</span></button>}
        {(shared.standard_answer_md || shared.standard_answer_image) && <button style={sectionStyle('standard')} onClick={()=>setActiveSection('standard')}><span className="with-ic"><Icon name="clipboard" size={12}/>标准答案</span></button>}
        <button style={sectionStyle('comments')} onClick={()=>setActiveSection('comments')}><span className="with-ic"><Icon name="chat" size={12}/>评论 ({comments.length})</span></button>
      </div>

      {activeSection === 'question' && (
        <div>
          {shared.has_image && shared.image_data_url && (
            <img src={shared.image_data_url} alt="题目图片" style={{maxWidth:'100%',maxHeight:400,borderRadius:8,marginBottom:14,display:'block'}} />
          )}
          {shared.content ? (
            <div style={{background:'var(--bg2)',border:'1px solid var(--border)',borderRadius:8,padding:16}}>
              <QBMd content={shared.content} />
            </div>
          ) : <div style={{color:'var(--fg3)',fontSize:13}}>（仅图片题目）</div>}
        </div>
      )}

      {activeSection === 'answer' && shared.final_answer && (
        <div style={{background:'var(--bg2)',border:'1px solid var(--border)',borderRadius:8,padding:16}}>
          <QBMd content={shared.final_answer} />
        </div>
      )}

      {activeSection === 'standard' && (
        <div style={{display:'flex',flexDirection:'column',gap:14}}>
          {shared.standard_answer_image && (
            <img src={shared.standard_answer_image} alt="标准答案" style={{maxWidth:'100%',maxHeight:500,borderRadius:8,display:'block'}} />
          )}
          {shared.standard_answer_md && (
            <div style={{background:'var(--bg2)',border:'1px solid var(--border)',borderRadius:8,padding:16}}>
              <QBMd content={shared.standard_answer_md} />
            </div>
          )}
        </div>
      )}

      {activeSection === 'comments' && (
        <div>
          {/* 评论列表 */}
          <div style={{display:'flex',flexDirection:'column',gap:10,marginBottom:16}}>
            {comments.length === 0 && <div style={{color:'var(--fg3)',fontSize:13,textAlign:'center',padding:16}}>暂无评论</div>}
            {comments.map(c => (
              <div key={c.id} style={{background:'var(--bg2)',border:'1px solid var(--border)',borderRadius:8,padding:'10px 14px'}}>
                <div style={{display:'flex',gap:10,marginBottom:4,alignItems:'center'}}>
                  <span style={{fontSize:12,color:'var(--gold)'}}>{c.user}</span>
                  <span style={{fontSize:11,color:'var(--fg3)'}}>{new Date(c.created_at).toLocaleString('zh-CN')}</span>
                </div>
                <div style={{fontSize:13,color:'var(--fg)',lineHeight:1.6}}>{c.content}</div>
              </div>
            ))}
          </div>
          {/* 评论输入 */}
          {user ? (
            <div style={{display:'flex',gap:8}}>
              <textarea value={comment} onChange={e=>setComment(e.target.value)}
                onKeyDown={e=>{ if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();postComment();} }}
                placeholder="写下你的评论…" style={{flex:1,minHeight:72,fontFamily:'var(--sans)'}} />
              <button className="btn btn-p" style={{alignSelf:'flex-end'}} onClick={postComment} disabled={submitting||!comment.trim()}>
                {submitting ? '…' : '发送'}
              </button>
            </div>
          ) : (
            <div style={{textAlign:'center',color:'var(--fg3)',fontSize:13}}>
              <a href="#/login" style={{color:'var(--gold)'}}>登录</a> 后可以评论
            </div>
          )}
        </div>
      )}
    </div>
  );
}

{% endverbatim %}
{% verbatim %}
// ── 文档阅读器应用组件 ────────────────────────────────────────
// 支持 PDF/MD 文档阅读，GLM-OCR 解析，可视化分段，LLM 对话

function DocReaderApp({user, onLogout, onUpdateUser}) {
  const [v, setV] = useState('documents'); // documents, reader, chat
  const [documents, setDocuments] = useState([]);
  const [currentDoc, setCurrentDoc] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pdfDoc, setPdfDoc] = useState(null);
  const [pageScale, setPageScale] = useState(1.5);
  const [ocrResults, setOcrResults] = useState({});
  const [selectedSegments, setSelectedSegments] = useState([]);
  const [chatSessions, setChatSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [instructionType, setInstructionType] = useState('custom');
  const [userMessage, setUserMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [cacheUsage, setCacheUsage] = useState({used: 0, quota: 200 * 1024 * 1024, percentage: 0});
  const [parseProgress, setParseProgress] = useState({current: 0, total: 0, status: ''});
  const [sbOpen, setSbOpen] = useState(false);
  const [pdfLoaded, setPdfLoaded] = useState(!!window.pdfjsLib);
  const [dragActive, setDragActive] = useState(false);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef(null);

  const token = localStorage.getItem('mf_token');

  // 动态加载 PDF.js
  useEffect(() => {
    if (window.pdfjsLib) return;
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
    s.onload = () => {
      window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
      setPdfLoaded(true);
    };
    document.head.appendChild(s);
  }, []);

  // 加载文档列表
  useEffect(() => {
    if (!user) return;
    fetch('/api/reader/documents/', {
      headers: {'Authorization': `Token ${token}`}
    })
    .then(r => r.json())
    .then(data => setDocuments(data.documents || []))
    .catch(console.error);
  }, [user]);

  // 加载缓存配额
  const loadCacheQuota = () => {
    fetch('/api/reader/cache/quota/', {
      headers: {'Authorization': `Token ${token}`}
    })
    .then(r => r.json())
    .then(data => setCacheUsage(data.cache_usage))
    .catch(console.error);
  };

  useEffect(() => {
    loadCacheQuota();
    const interval = setInterval(loadCacheQuota, 30000);
    return () => clearInterval(interval);
  }, []);

  // 当进入阅读模式、翻页或currentDoc更新（包含新的pages状态）时，检查当前页是否已解析但未加载详细结果
  useEffect(() => {
    if (v === 'reader' && currentDoc && currentDoc.id && !String(currentDoc.id).startsWith('local-')) {
      const pageInfo = currentDoc.pages?.find(p => p.page_num === currentPage);
      if (pageInfo && pageInfo.ocr_status === 'done') {
        const existingData = ocrResults[currentPage];
        if (!existingData || existingData.layout_details === undefined) {
          fetch(`/api/reader/documents/${currentDoc.id}/pages/${currentPage}/`, {
            headers: {'Authorization': `Token ${token}`}
          })
          .then(r => r.json())
          .then(data => {
            if (data.ocr_status === 'done' && data.layout_details) {
              setOcrResults(prev => ({...prev, [currentPage]: data}));
            }
          })
          .catch(console.error);
        }
      }
    }
  }, [v, currentDoc, currentPage, ocrResults, token]);

  const createDocumentProject = async ({name, fileType, totalPages, fileSize}) => {
    const res = await fetch('/api/reader/documents/', {
      method: 'POST',
      headers: {
        'Authorization': `Token ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: name,
        file_type: fileType,
        total_pages: totalPages,
        file_size: fileSize,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || '创建文档失败');
    }
    return data;
  };

  // 加载本地 PDF 文档，支持自动创建项目
  const loadLocalPDF = async (file, existingDoc = null, shouldCreate = true) => {
    if (!pdfLoaded) {
      showAlert('PDF.js 加载中，请稍候...', '提示');
      return;
    }
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
      showAlert('请导入 PDF 文件', '提示');
      return;
    }

    try {
      setImporting(true);
      const fileBuffer = await file.arrayBuffer();
      const loadingTask = window.pdfjsLib.getDocument({data: fileBuffer});
      const pdf = await loadingTask.promise;

      let serverDoc = existingDoc;
      if (!serverDoc && shouldCreate) {
        try {
          serverDoc = await createDocumentProject({
            name: file.name.replace(/\.pdf$/i, ''),
            fileType: 'pdf',
            totalPages: pdf.numPages,
            fileSize: file.size,
          });
          setDocuments(prev => [serverDoc, ...prev.filter(d => d.id !== serverDoc.id)]);
        } catch (createErr) {
          console.warn('自动创建文档项目失败，将使用本地阅读模式:', createErr);
          showAlert('已进入本地阅读模式（自动创建文档失败，可稍后重试）', '提示');
        }
      }

      const localDoc = {
        ...(serverDoc || {}),
        id: (serverDoc && serverDoc.id) || `local-${Date.now()}`,
        name: (serverDoc && serverDoc.name) || file.name,
        file_type: 'pdf',
        total_pages: (serverDoc && serverDoc.total_pages) || pdf.numPages,
        file_size: (serverDoc && serverDoc.file_size) || file.size,
        file: file,
      };

      setCurrentDoc(localDoc);
      setV('reader');
      setSelectedSegments([]);
      setOcrResults({});
      setPdfDoc(pdf);
      setCurrentPage(1);
    } catch (err) {
      console.error('PDF加载失败:', err);
      showAlert(`PDF加载失败: ${err.message}`, '错误');
    } finally {
      setImporting(false);
    }
  };

  const openExistingDocument = async (doc) => {
    if (doc.file_type !== 'pdf') {
      showAlert('当前仅支持 PDF 阅读', '提示');
      return;
    }
    const picker = document.createElement('input');
    picker.type = 'file';
    picker.accept = '.pdf';
    picker.onchange = async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      await loadLocalPDF(file, doc, false);
    };
    picker.click();
  };

  const handlePickedFile = async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    await loadLocalPDF(file, null, true);
    e.target.value = '';
  };

  const handleDropImport = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (!file) return;
    await loadLocalPDF(file, null, true);
  };

  // 渲染当前页面为图片
  const renderPageToImage = async (pageNum) => {
    if (!pdfDoc) return null;
    const page = await pdfDoc.getPage(pageNum);
    const viewport = page.getViewport({scale: 2.0});
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    await page.render({canvasContext: context, viewport: viewport}).promise;
    return canvas.toDataURL('image/png');
  };

  // 上传页面到服务器缓存
  const uploadPage = async (pageNum) => {
    const canUseServer = currentDoc && currentDoc.id && !String(currentDoc.id).startsWith('local-');
    if (!canUseServer) {
      throw new Error('当前文档未创建服务端项目，无法上传页面');
    }
    const dataUrl = await renderPageToImage(pageNum);
    const base64 = dataUrl.split(',')[1];
    const page = await pdfDoc.getPage(pageNum);
    const originViewport = page.getViewport({scale: 1});

    const res = await fetch(`/api/reader/documents/${currentDoc.id}/pages/upload/`, {
      method: 'POST',
      headers: {
        'Authorization': `Token ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        page_num: pageNum,
        image_b64: base64,
        page_width: Math.round(originViewport.width),
        page_height: Math.round(originViewport.height),
      }),
    });
    return res.json();
  };

  // 解析单个页面
  const parsePage = async (pageNum) => {
    const canUseServer = currentDoc && currentDoc.id && !String(currentDoc.id).startsWith('local-');
    if (!canUseServer) {
      showAlert('当前文档仅本地阅读，无法解析。请重新导入并自动创建文档项目。', '提示');
      return null;
    }
    setParseProgress({current: pageNum, total: pageNum, status: `正在解析第 ${pageNum} 页...`});
    const res = await fetch(`/api/reader/documents/${currentDoc.id}/pages/${pageNum}/parse/`, {
      method: 'POST',
      headers: {'Authorization': `Token ${token}`},
    });
    const data = await res.json();
    if (data.ocr_status === 'done') {
      setOcrResults(prev => ({...prev, [pageNum]: data}));
    }
    setParseProgress({current: 0, total: 0, status: ''});
    return data;
  };

  // 批量解析
  const batchParse = async (pageNumbers) => {
    const canUseServer = currentDoc && currentDoc.id && !String(currentDoc.id).startsWith('local-');
    if (!canUseServer) {
      showAlert('当前文档仅本地阅读，无法批量解析。请重新导入并自动创建文档项目。', '提示');
      return;
    }

    // Upload un-cached pages first
    for (let i = 0; i < pageNumbers.length; i++) {
      const pageNum = pageNumbers[i];
      // Check if page already has image cached on server
      const pageInfo = currentDoc.pages?.find(p => p.page_num === pageNum);
      if (!pageInfo || !pageInfo.has_image) {
        setParseProgress({current: i+1, total: pageNumbers.length, status: `缓存第 ${pageNum} 页图片...`});
        try {
          await uploadPage(pageNum);
        } catch (e) {
          showAlert(`缓存第 ${pageNum} 页失败: ${e.message}`, '错误');
          setParseProgress({current: 0, total: 0, status: ''});
          return;
        }
      }
    }

    setParseProgress({current: 0, total: pageNumbers.length, status: '准备解析...'});

    const res = await fetch(`/api/reader/documents/${currentDoc.id}/parse/batch/`, {
      method: 'POST',
      headers: {
        'Authorization': `Token ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({page_numbers: pageNumbers}),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'progress') {
            setParseProgress({current: data.page_num, total: pageNumbers.length, status: `解析第 ${data.page_num} 页...`});
          } else if (data.type === 'success') {
            setOcrResults(prev => ({...prev, [data.page_num]: {...data, ocr_status: 'done'}}));
          } else if (data.type === 'error') {
            showAlert(`第 ${data.page_num} 页解析失败: ${data.message}`, '错误');
            setOcrResults(prev => ({...prev, [data.page_num]: {ocr_status: 'error', error_msg: data.message}}));
          } else if (data.type === 'done') {
            setParseProgress({current: 0, total: 0, status: `完成！成功 ${data.completed}，失败 ${data.failed}`});

            // Reload document details to update server state
            if (currentDoc && currentDoc.id && !String(currentDoc.id).startsWith('local-')) {
              fetch(`/api/reader/documents/${currentDoc.id}/`, {
                headers: {'Authorization': `Token ${token}`},
              }).then(res => res.json()).then(data => {
                if (data.id) {
                  setCurrentDoc(data);
                }
              }).catch(e => console.error(e));
            }
          }
        }
      }
    }
  };

  // 格式化文件大小
  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  };

  // 发送消息到AI
  const sendMessage = async () => {
    const canUseServer = currentDoc && currentDoc.id && !String(currentDoc.id).startsWith('local-');
    if (!canUseServer) {
      showAlert('当前文档仅本地阅读，AI对话需先创建服务端文档项目。', '提示');
      return;
    }
    if (loading) return;
    if (selectedSegments.length === 0 && instructionType === 'custom') {
      showAlert('请先选择文本或输入自定义消息', '提示');
      return;
    }

    let content = userMessage;
    if (instructionType === 'translate') {
      content = '请将以下文本翻译成中文：';
    } else if (instructionType === 'summarize') {
      content = '请总结以下文本的要点：';
    } else if (instructionType === 'explain') {
      content = '请详细讲解以下文本的内容，包括背景和含义：';
    }

    // 添加用户消息
    const userMsg = {
      role: 'user',
      content: content,
      selected_texts: selectedSegments,
      instruction_type: instructionType,
    };
    setChatMessages(prev => [...prev, userMsg]);
    setUserMessage('');
    setLoading(true);

    try {
      const response = await fetch(`/api/reader/documents/${currentDoc.id}/chats/${currentSession?.id || 'new'}/stream/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: content,
          selected_texts: selectedSegments,
          instruction_type: instructionType,
        }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';

      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            if (data.content) {
              assistantMessage += data.content;
              setStreamingContent(assistantMessage);
            }
            if (data.done) {
              setChatMessages(prev => [...prev, {
                role: 'assistant',
                content: assistantMessage,
              }]);
              setStreamingContent('');
            }
            if (data.error) {
              showAlert('错误: ' + data.error, '错误');
              setLoading(false);
              return;
            }
          }
        }
      }
    } catch (err) {
      console.error('发送消息失败:', err);
      showAlert('发送失败: ' + err.message, '错误');
    } finally {
      setLoading(false);
    }
  };

  // 文档列表视图
  if (v === 'documents' && !currentDoc) {
    return (
      <div className="app" style={{height:'100vh'}}>
        <aside className={'sb' + (sbOpen ? ' open' : '')} style={{padding:'1rem'}}>
          <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'1.5rem'}}>
            <h2 style={{margin:0, fontSize:'1.2rem', color:'var(--gold)', fontFamily:'var(--serif)'}} className="with-ic"><Icon name="file-text" size={16}/> 文档阅读器</h2>
            <button className="btn btn-s" onClick={() => setSbOpen(!sbOpen)} style={{padding:'0.3rem 0.6rem', fontSize:'1.2rem'}}>
              <Icon name={sbOpen ? 'x' : 'menu'} size={14}/>
            </button>
          </div>

          <div style={{marginBottom:'1rem'}}>
            <button className="btn btn-p" style={{width:'100%'}} onClick={() => fileInputRef.current && fileInputRef.current.click()}>
              + 导入 PDF
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              style={{display:'none'}}
              onChange={handlePickedFile}
            />
          </div>

          <div style={{marginBottom:'1rem'}}>
            <button className="btn" style={{width:'100%', background:'var(--bg3)', color:'var(--fg)'}} onClick={() => showAlert('云盘选择功能即将上线', '提示')}>
              <span className="with-ic"><Icon name="cloud-drive" size={13}/> 从云盘选择</span>
            </button>
          </div>

          <div style={{borderTop:'1px solid var(--border)', paddingTop:'1rem', marginBottom:'1rem'}}>
            <div style={{fontSize:'0.8rem', color:'var(--fg3)', marginBottom:'0.5rem'}}>缓存使用量</div>
            <div style={{fontSize:'1.5rem', fontWeight:'bold', color:'var(--gold)'}}>
              {formatSize(cacheUsage.used)} / {formatSize(cacheUsage.quota)}
            </div>
            <div style={{fontSize:'0.8rem', color:cacheUsage.percentage > 90 ? 'var(--danger)' : 'var(--fg3)'}}>
              {cacheUsage.percentage}% 已使用
            </div>
            {cacheUsage.percentage > 90 && (
              <div style={{fontSize:'0.7rem', color:'var(--danger)', marginTop:'0.3rem'}}>
                <span className="with-ic"><Icon name="alert" size={11}/> 缓存空间不足</span>
              </div>
            )}
          </div>
        </aside>

        <main style={{flex:1, padding:'2rem', overflow:'auto'}}>
          <h1 style={{marginTop:0, marginBottom:'0.5rem'}}>我的文档</h1>
          <p style={{marginTop:0, color:'var(--fg3)', marginBottom:'1.2rem'}}>拖入 PDF 立即阅读，系统会自动创建文档项目。</p>

          <section
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={(e) => { e.preventDefault(); setDragActive(false); }}
            onDrop={handleDropImport}
            onClick={() => fileInputRef.current && fileInputRef.current.click()}
            style={{
              marginBottom:'1.5rem',
              padding:'1.3rem',
              borderRadius:'14px',
              border: dragActive ? '2px solid var(--gold)' : '2px dashed var(--border2)',
              background: dragActive ? 'color-mix(in srgb, var(--gold) 14%, var(--bg2))' : 'var(--bg2)',
              cursor:'pointer',
              transition:'all .18s ease',
              boxShadow:'0 10px 28px rgba(0,0,0,0.08)',
            }}
          >
            <div style={{fontWeight:700, marginBottom:'0.3rem'}}><span className="with-ic"><Icon name="upload" size={15}/> 拖拽 PDF 到这里</span></div>
            <div style={{fontSize:'0.85rem', color:'var(--fg3)'}}>
              支持“拖入即阅读”，自动创建文档；也可点击此处选择文件
            </div>
            {importing && <div style={{fontSize:'0.8rem', color:'var(--gold)', marginTop:'0.6rem'}}>正在导入中...</div>}
          </section>

          {documents.length === 0 ? (
            <div style={{textAlign:'center', padding:'3rem', color:'var(--fg3)'}}>
              <div style={{marginBottom:'1rem'}}><Icon name="file-text" size={34}/></div>
              <p>还没有文档，拖入一个 PDF 开始阅读吧</p>
            </div>
          ) : (
            <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(250px, 1fr))', gap:'1rem'}}>
              {documents.map(doc => (
              <div key={doc.id} style={{
                  background:'var(--bg2)',
                  border:'1px solid var(--border)',
                  borderRadius:'8px',
                  padding:'1rem',
                  cursor:'pointer',
                  transition:'all 0.2s',
                }} onClick={() => openExistingDocument(doc)} onMouseEnter={(e) => e.currentTarget.style.borderColor='var(--gold)'} onMouseLeave={(e) => e.currentTarget.style.borderColor='var(--border)'}>
                  <div style={{marginBottom:'0.5rem',display:'inline-flex',alignItems:'center',justifyContent:'center',width:34,height:34,borderRadius:8,background:'var(--bg3)',border:'1px solid var(--border)'}}>
                    <Icon name={doc.file_type === 'pdf' ? 'book' : doc.file_type === 'md' ? 'note' : 'file'} size={16}/>
                  </div>
                  <div style={{fontWeight:'bold', marginBottom:'0.5rem', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>
                    {doc.name}
                  </div>
                  <div style={{fontSize:'0.8rem', color:'var(--fg3)'}}>
                    {doc.file_type.toUpperCase()} · {doc.total_pages}页
                  </div>
                  <div style={{fontSize:'0.7rem', color:'var(--fg3)', marginTop:'0.3rem'}}>
                    缓存: {doc.cached_pages}/{doc.total_pages}页 ({formatSize(doc.cache_size)})
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    );
  }

  // 阅读器视图
  if (v === 'reader' && currentDoc) {
    const canUseServerFeatures = currentDoc.id && !String(currentDoc.id).startsWith('local-');
    const ocrData = ocrResults[currentPage];
    const layoutDetails = ocrData?.layout_details || [];

    return (
      <div className="app" style={{height:'100vh'}}>
        {/* 左侧边栏 - 页面导航 */}
        <aside className={'sb' + (sbOpen ? ' open' : '')} style={{padding:'1rem', width:'250px'}}>
          <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'1rem'}}>
            <button className="btn" onClick={() => {setCurrentDoc(null); setV('documents');}} style={{padding:'0.3rem 0.6rem'}}>
              ← 返回
            </button>
            <button className="btn btn-s" onClick={() => setSbOpen(!sbOpen)} style={{padding:'0.3rem 0.6rem', fontSize:'1.2rem'}}>
              <Icon name={sbOpen ? 'x' : 'menu'} size={14}/>
            </button>
          </div>

          <h3 style={{marginBottom:'1rem', fontSize:'1rem', color:'var(--gold)'}}>{currentDoc.name}</h3>

          <div style={{marginBottom:'1rem'}}>
            <button className="btn btn-p" style={{width:'100%', marginBottom:'0.5rem'}} disabled={!canUseServerFeatures} onClick={async () => {
              if (parseProgress.total > 0) return;
              await batchParse([currentPage]);
            }}>
              {parseProgress.total > 0 ? '解析中...' : '解析当前页'}
            </button>
            <button className="btn" style={{width:'100%'}} disabled={!canUseServerFeatures} onClick={async () => {
              if (parseProgress.total > 0) return;
              const pageNums = [];
              for (let i = 1; i <= currentDoc.total_pages; i++) {
                if (!ocrResults[i]) pageNums.push(i);
              }
              if (pageNums.length === 0) {
                showAlert('所有页面已解析', '提示');
                return;
              }
              const confirmed = await showConfirm(`将解析 ${pageNums.length} 个页面，继续？`);
              if (!confirmed) return;
              await batchParse(pageNums);
            }}>
              {parseProgress.total > 0 ? `解析中 ${parseProgress.current}/${parseProgress.total}` : '批量解析全部'}
            </button>
          </div>

          {parseProgress.status && (
            <div style={{padding:'0.5rem', background:'var(--bg3)', borderRadius:'4px', fontSize:'0.8rem', marginBottom:'1rem'}}>
              {parseProgress.status}
            </div>
          )}

          <div style={{borderTop:'1px solid var(--border)', paddingTop:'1rem'}}>
            <div style={{fontSize:'0.8rem', color:'var(--fg3)', marginBottom:'0.5rem'}}>页面导航</div>
            <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, 1fr)', gap:'0.3rem', maxHeight:'60vh', overflow:'auto'}}>
              {Array.from({length: currentDoc.total_pages}, (_, i) => i + 1).map(pageNum => (
                <button
                  key={pageNum}
                  className="btn"
                  style={{
                    padding:'0.4rem',
                    fontSize:'0.8rem',
                    background: pageNum === currentPage ? 'var(--gold)' : ocrResults[pageNum] ? 'var(--bg3)' : 'var(--bg4)',
                    color: pageNum === currentPage ? '#000' : 'var(--fg)',
                  }}
                  onClick={() => setCurrentPage(pageNum)}
                >
                  {pageNum}
                  {ocrResults[pageNum] && '✓'}
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* 中间 - PDF查看器 + OCR结果 */}
        <main style={{flex:1, display:'flex', flexDirection:'column', padding:'1rem', overflow:'hidden'}}>
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'1rem', background:'var(--bg2)', border:'1px solid var(--border)', borderRadius:'12px', padding:'0.7rem 1rem'}}>
            <div>
              <button className="btn" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage <= 1}>
                ← 上一页
              </button>
              <span style={{margin:'0 1rem'}}>
                第 {currentPage} / {currentDoc.total_pages} 页
              </span>
              <button className="btn" onClick={() => setCurrentPage(Math.min(currentDoc.total_pages, currentPage + 1))} disabled={currentPage >= currentDoc.total_pages}>
                下一页 →
              </button>
            </div>
            <button className="btn" onClick={() => setV('chat')} disabled={!canUseServerFeatures}>
              <span className="with-ic"><Icon name="chat" size={13}/> AI 对话 →</span>
            </button>
          </div>
          {!canUseServerFeatures && (
            <div style={{marginBottom:'1rem', background:'var(--bg2)', border:'1px solid var(--border)', borderRadius:'10px', padding:'0.7rem 0.9rem', color:'var(--fg3)', fontSize:'0.85rem'}}>
              当前为本地临时阅读，OCR 解析和 AI 对话不可用。通过“导入 PDF”创建项目后可启用这些能力。
            </div>
          )}

          <div style={{flex:1, display:'flex', gap:'1rem', overflow:'hidden'}}>
            {/* PDF查看器 */}
            <div style={{flex:1, background:'var(--bg2)', borderRadius:'8px', padding:'1rem', overflow:'auto'}}>
              {currentDoc.file_type === 'pdf' ? (
                <div style={{display:'flex', justifyContent:'center'}}>
                  <canvas
                    ref={async (canvas) => {
                      if (!canvas || !pdfDoc) return;
                      const page = await pdfDoc.getPage(currentPage);
                      const viewport = page.getViewport({scale: pageScale});
                      canvas.height = viewport.height;
                      canvas.width = viewport.width;
                      const context = canvas.getContext('2d');
                      await page.render({canvasContext: context, viewport: viewport}).promise;
                    }}
                    style={{maxWidth:'100%', boxShadow:'0 2px 8px rgba(0,0,0,0.1)'}}
                  />
                </div>
              ) : (
                <div style={{padding:'1rem', whiteSpace:'pre-wrap', fontFamily:'monospace'}}>
                  {/* MD/TXT内容 */}
                </div>
              )}
            </div>

            {/* OCR结果 - 可视化分段 */}
            <div style={{width:'350px', background:'var(--bg2)', borderRadius:'8px', padding:'1rem', overflow:'auto'}}>
              <h4 style={{margin:'0 0 1rem 0', color:'var(--gold)'}}>解析结果</h4>

              {!ocrData ? (
                <div style={{color:'var(--fg3)', fontSize:'0.9rem'}}>
                  {parseProgress.status || '点击"解析当前页"开始解析'}
                </div>
              ) : (
                <div>
                  <div style={{marginBottom:'1rem'}}>
                    <button className="btn btn-p" style={{fontSize:'0.8rem', padding:'0.3rem 0.6rem'}} onClick={() => {
                      const allTexts = layoutDetails.map((seg, i) => seg.content || '');
                      setSelectedSegments(allTexts);
                    }}>
                      全选
                    </button>
                    <button className="btn" style={{fontSize:'0.8rem', padding:'0.3rem 0.6rem', marginLeft:'0.5rem'}} onClick={() => setSelectedSegments([])}>
                      清空
                    </button>
                    <span style={{fontSize:'0.8rem', color:'var(--fg3)', marginLeft:'0.5rem'}}>
                      已选 {selectedSegments.length} 段
                    </span>
                  </div>

                  {layoutDetails.map((segment, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding:'0.5rem',
                        marginBottom:'0.5rem',
                        background: selectedSegments.includes(segment.content) ? 'var(--gold)' : 'var(--bg3)',
                        color: selectedSegments.includes(segment.content) ? '#000' : 'var(--fg)',
                        borderRadius:'4px',
                        cursor:'pointer',
                        fontSize:'0.85rem',
                        border: selectedSegments.includes(segment.content) ? '2px solid var(--gold)' : '1px solid var(--border)',
                      }}
                      onClick={() => {
                        if (selectedSegments.includes(segment.content)) {
                          setSelectedSegments(prev => prev.filter(s => s !== segment.content));
                        } else {
                          setSelectedSegments(prev => [...prev, segment.content]);
                        }
                      }}
                    >
                      <div style={{fontSize:'0.7rem', color:'var(--fg3)', marginBottom:'0.2rem'}}>
                        <span className="with-ic">
                          <Icon name={segment.label === 'text' ? 'note' : segment.label === 'image' ? 'image' : 'grid'} size={11}/>
                          <span>索引 {segment.index}</span>
                        </span>
                      </div>
                      <div style={{maxHeight:'100px', overflow:'hidden'}}>
                        {(segment.content || '').substring(0, 200)}
                        {(segment.content || '').length > 200 && '...'}
                      </div>
                    </div>
                  ))}

                  {selectedSegments.length > 0 && (
                    <button
                      className="btn btn-p"
                      style={{width:'100%', marginTop:'1rem'}}
                      disabled={!canUseServerFeatures}
                      onClick={() => setV('chat')}
                    >
                      发送到 AI 对话 →
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    );
  }

  // AI 对话视图
  if (v === 'chat' && currentDoc) {
    return (
      <div className="app" style={{height:'100vh'}}>
        {/* 左侧 - 选中文本预览 */}
        <aside style={{width:'300px', background:'var(--bg2)', padding:'1rem', borderRight:'1px solid var(--border)'}}>
          <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'1rem'}}>
            <h3 style={{margin:0, fontSize:'1rem', color:'var(--gold)'}}>选中的文本</h3>
            <button className="btn" onClick={() => setV('reader')} style={{padding:'0.3rem 0.6rem'}}>
              ← 返回
            </button>
          </div>

          <div style={{maxHeight:'60vh', overflow:'auto', fontSize:'0.9rem'}}>
            {selectedSegments.length === 0 ? (
              <div style={{color:'var(--fg3)'}}>未选择任何文本</div>
            ) : (
              selectedSegments.map((text, idx) => (
                <div key={idx} style={{
                  padding:'0.5rem',
                  marginBottom:'0.5rem',
                  background:'var(--bg3)',
                  borderRadius:'4px',
                  fontSize:'0.85rem'
                }}>
                  {text.substring(0, 200)}
                  {text.length > 200 && '...'}
                </div>
              ))
            )}
          </div>

          <div style={{marginTop:'1rem', borderTop:'1px solid var(--border)', paddingTop:'1rem'}}>
            <div style={{fontSize:'0.8rem', color:'var(--fg3)', marginBottom:'0.5rem'}}>预设指令</div>
            <select
              value={instructionType}
              onChange={(e) => setInstructionType(e.target.value)}
              style={{width:'100%', padding:'0.5rem', background:'var(--bg3)', border:'1px solid var(--border)', color:'var(--fg)', borderRadius:'4px'}}
            >
              <option value="custom">自定义对话</option>
              <option value="translate">翻译（中文）</option>
              <option value="summarize">总结内容</option>
              <option value="explain">详细讲解</option>
            </select>
          </div>
        </aside>

        {/* 右侧 - 对话区域 */}
        <main style={{flex:1, display:'flex', flexDirection:'column', padding:'1rem'}}>
          <h3 style={{margin:'0 0 1rem 0'}}>AI 对话助手</h3>

          <div style={{flex:1, overflow:'auto', marginBottom:'1rem', padding:'1rem', background:'var(--bg2)', borderRadius:'8px'}}>
            {chatMessages.length === 0 && !streamingContent ? (
              <div style={{textAlign:'center', color:'var(--fg3)', marginTop:'2rem'}}>
                <div style={{marginBottom:'1rem'}}><Icon name="chat" size={26}/></div>
                <p>选择文本后开始对话</p>
                <p style={{fontSize:'0.9rem'}}>支持翻译、总结、讲解等功能</p>
              </div>
            ) : (
              <>
                {chatMessages.map((msg, idx) => (
                  <div key={idx} style={{
                    marginBottom:'1rem',
                    padding:'0.8rem',
                    borderRadius:'8px',
                    background: msg.role === 'user' ? 'var(--bg3)' : 'var(--bg4)',
                  }}>
                    <div style={{fontSize:'0.8rem', color:'var(--fg3)', marginBottom:'0.3rem'}}>
                      <span className="with-ic"><Icon name={msg.role === 'user' ? 'user' : 'bot'} size={11}/> {msg.role === 'user' ? '你' : '助手'}</span>
                    </div>
                    <div style={{whiteSpace:'pre-wrap'}}>{msg.content}</div>
                  </div>
                ))}
                {streamingContent && (
                  <div style={{
                    padding:'0.8rem',
                    borderRadius:'8px',
                    background:'var(--bg4)',
                  }}>
                    <div style={{fontSize:'0.8rem', color:'var(--fg3)', marginBottom:'0.3rem'}} className="with-ic"><Icon name="bot" size={11}/> 助手</div>
                    <div style={{whiteSpace:'pre-wrap'}}>
                      {streamingContent}
                      <span style={{animation:'blink 1s infinite'}}>▌</span>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          <div style={{display:'flex', gap:'0.5rem'}}>
            <input
              type="text"
              value={userMessage}
              onChange={(e) => setUserMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder={instructionType === 'custom' ? '输入你的问题...' : '点击发送开始处理'}
              disabled={loading}
              style={{
                flex:1,
                padding:'0.8rem',
                background:'var(--bg3)',
                border:'1px solid var(--border)',
                color:'var(--fg)',
                borderRadius:'8px',
                fontSize:'1rem',
              }}
            />
            <button
              className="btn btn-p"
              onClick={sendMessage}
              disabled={loading || (selectedSegments.length === 0 && instructionType !== 'custom')}
            >
              {loading ? '...' : '发送'}
            </button>
          </div>
        </main>
      </div>
    );
  }

  return null;
}

ReactDOM.createRoot(document.getElementById('root')).render(<Root/>);
{% endverbatim %}
{% verbatim %}
// ── 极简扁平图标组件 ─────────────────────────────────────────────────
const BIcon=({name,size=16,color='#fff'})=>{
  const icons={
    people:<svg viewBox="0 0 24 24" fill={color}><circle cx="12" cy="7" r="4"/><path d="M4 20v-3a4 4 0 014-4h8a4 4 0 014 4v3"/></svg>,
    gold:<svg viewBox="0 0 24 24" fill={color}><circle cx="12" cy="12" r="10" fill="none" stroke={color} strokeWidth="2"/><circle cx="12" cy="12" r="3"/></svg>,
    logs:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><rect x="3" y="8" width="18" height="8" rx="1"/><line x1="8" y1="8" x2="8" y2="16"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="16" y1="8" x2="16" y2="16"/></svg>,
    stone:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M4 12l4-8 8 2 4 6-4 8-8-2-4-6z"/></svg>,
    firewood:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M12 2v20M8 18c0-3 2-5 4-8M16 18c0-3-2-5-4-8"/><path d="M10 14a4 4 0 004 4"/></svg>,
    food:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M12 2a10 10 0 000 20 10 10 0 000-20zm0 0v20"/></svg>,
    build:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M3 21h18M5 21V7l8-4 8 4v14M8 21v-6a2 2 0 012-2h4a2 2 0 012 2v6"/></svg>,
    market:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M3 3h18v18H3z"/><path d="M9 3v18M15 3v18"/></svg>,
    ai:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="8" strokeDasharray="4 2"/><circle cx="12" cy="12" r="11" strokeDasharray="2 3"/></svg>,
    save:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/></svg>,
    raw:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9h6M9 15h6"/></svg>,
    crafted:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 12h6M12 9v6"/></svg>,
    housing:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M3 21h18M5 21V7l8-4 8 4v14"/></svg>,
    resource:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M2 12l4-8 8 2 4 6-4 8-8-2-4-6z"/></svg>,
    storage:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M4 10h16v10H4zM4 6h16M4 14h16"/></svg>,
    service:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>,
    hunger:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M12 2a10 10 0 000 20 10 10 0 000-20zm0 0v20"/></svg>,
    thirst:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M12 2L6 22h12L12 2z"/></svg>,
    warmth:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M12 2v20M8 18c0-3 2-5 4-8M16 18c0-3-2-5-4-8"/><path d="M10 14a4 4 0 004 4"/></svg>,
    health:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>,
    trade:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M7 16V4M7 4L3 8M7 4L11 8M17 8v12M17 20l-4-4M17 20l4-4"/></svg>,
    trophy:<svg viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2"><path d="M6 9H4.5a2.5 2.5 0 010-5H6"/><path d="M18 9h1.5a2.5 2.5 0 000-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0012 0V2Z"/></svg>,
  };
  return <span style={{display:'inline-flex',alignItems:'center',justifyContent:'center',width:size,height:size}}>{icons[name]||null}</span>;
};

// ── HUD ──────────────────────────────────────────────────────────────
function BanishedHUD({state,speed,onSetSpeed,onToggleRes,syncStatus}){
  if(!state?.time)return null;
  const {time,resources,population}=state;
  const SZH={spring:'春',summer:'夏',autumn:'秋',winter:'冬'};
  const SC={spring:'#3eb87a',summer:'#c9a86c',autumn:'#d49a5a',winter:'#9ab4d4'};
  const food=FOOD_KEYS.reduce((a,k)=>a+(resources[k]||0),0);
  return(
    <div style={{position:'absolute',top:0,left:0,right:0,display:'flex',alignItems:'center',gap:12,padding:'8px 14px',background:'linear-gradient(135deg,rgba(58,184,122,0.15) 0%,rgba(8,8,11,0.92) 100%)',backdropFilter:'blur(8px)',borderBottom:'1px solid rgba(58,184,122,0.2)',boxShadow:'0 2px 20px rgba(0,0,0,0.4)',zIndex:10,fontSize:13,flexWrap:'wrap'}}>
      <button className="btn btn-s btn-sm" onClick={onToggleRes} style={{padding:'4px 8px',borderRadius:'6px',background:'rgba(58,184,122,0.2)',border:'1px solid rgba(58,184,122,0.3)'}}><Icon name="menu" size={14}/></button>
      <span style={{color:SC[time.season],fontWeight:700,fontSize:14,textShadow:'0 0 10px '+SC[time.season]}}>{SZH[time.season]}</span>
      <span style={{color:'rgba(255,255,255,0.7)',fontWeight:500}}>第{time.year}年</span>
      <div style={{display:'flex',gap:12,marginLeft:8,marginRight:8}}>
        <span style={{display:'flex',alignItems:'center',gap:4,color:'rgba(255,255,255,0.9)',fontWeight:600}}><BIcon name="people" size={14} color="rgba(255,255,255,0.9)"/>{population.total}</span>
        <span style={{display:'flex',alignItems:'center',gap:4,color:'#ffd700',fontWeight:600,filter:'drop-shadow(0 0 6px rgba(255,215,0,0.5))'}}><BIcon name="gold" size={14}/>{resources.gold||0}</span>
        <span style={{display:'flex',alignItems:'center',gap:4,color:'rgba(255,255,255,0.85)'}}><BIcon name="logs" size={14}/>{resources.logs||0}</span>
        <span style={{display:'flex',alignItems:'center',gap:4,color:'rgba(255,255,255,0.85)'}}><BIcon name="stone" size={14}/>{resources.stone||0}</span>
        <span style={{display:'flex',alignItems:'center',gap:4,color:'#ff8c42',fontWeight:500}}><BIcon name="firewood" size={14}/>{resources.firewood||0}</span>
        <span style={{display:'flex',alignItems:'center',gap:4,color:'#3eb87a',fontWeight:500}}><BIcon name="food" size={14}/>{Math.floor(food)}</span>
      </div>
      <div style={{display:'flex',gap:6,marginLeft:'auto'}}>
        {[1,5,10].map(s=>(
          <button key={s} className={`btn btn-sm ${speed===s?'btn-p':'btn-s'}`} onClick={()=>onSetSpeed(s)} style={{padding:'4px 12px',fontSize:12,borderRadius:'6px',fontWeight:600,transition:'all 0.2s',background:speed===s?'linear-gradient(135deg,#3eb87a,#2d9a62)':'rgba(255,255,255,0.08)',border:speed===s?'none':'1px solid rgba(255,255,255,0.15)',color:speed===s?'#fff':'rgba(255,255,255,0.8)',boxShadow:speed===s?'0 2px 12px rgba(58,184,122,0.4)':'none'}}>{s}x</button>
        ))}
      </div>
      {syncStatus&&<span style={{fontSize:11,padding:'3px 8px',borderRadius:'4px',background:syncStatus.ok?'rgba(58,184,122,0.2)':'rgba(196,90,90,0.2)',color:syncStatus.ok?'#3eb87a':'#c45a5a',marginLeft:8,fontWeight:500}}>{syncStatus.ok?'✓ 已同步':syncStatus.msg}</span>}
    </div>
  );
}

// ── ResourcePanel ────────────────────────────────────────────────────
function BanishedResourcePanel({state,open,onClose}){
  if(!state?.resources)return null;
  const res=state.resources;
  const groups=[
    {label:'原材料',keys:['logs','stone','iron','coal'],color:'#5ac480',icon:'raw'},
    {label:'加工品',keys:['firewood','iron_tools','steel_tools'],color:'#c9a86c',icon:'crafted'},
    {label:'食物',keys:FOOD_KEYS,color:'#3eb87a',icon:'food'},
    {label:'手工品',keys:['wool','leather','herbs','hide_coat','wool_coat','warm_coat'],color:'#d49a5a',icon:'crafted'},
    {label:'货币',keys:['gold'],color:'#ffd700',icon:'gold'},
  ];
  return(
    <div style={{position:'absolute',left:open?0:'-220px',top:52,bottom:0,width:200,background:'linear-gradient(180deg,rgba(15,20,18,0.98) 0%,rgba(8,12,10,0.98) 100%)',borderRight:'1px solid rgba(58,184,122,0.2)',overflowY:'auto',transition:'left 0.25s cubic-bezier(0.4,0,0.2,1)',zIndex:9,padding:'12px',boxShadow:'2px 0 20px rgba(0,0,0,0.5)'}}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12,paddingBottom:8,borderBottom:'1px solid rgba(58,184,122,0.2)'}}>
        <span style={{fontWeight:700,fontSize:14,color:'#5ac480'}}>资源</span>
        <button className="btn btn-s btn-sm" onClick={onClose} style={{padding:'4px 6px',borderRadius:'6px',background:'rgba(255,255,255,0.06)'}}><Icon name="x" size={13}/></button>
      </div>
      {groups.map(g=>(
        <div key={g.label} style={{marginBottom:14}}>
          <div style={{fontSize:11,color:g.color,fontWeight:600,marginBottom:6,display:'flex',alignItems:'center',gap:4}}><BIcon name={g.icon} size={12} color={g.color}/>{g.label}</div>
          {g.keys.filter(k=>(res[k]||0)>0||k==='gold').map(k=>(
            <div key={k} style={{display:'flex',justifyContent:'space-between',alignItems:'center',fontSize:13,marginBottom:4,padding:'4px 6px',borderRadius:'4px',background:'rgba(255,255,255,0.02)',transition:'background 0.2s'}} onMouseEnter={e=>e.currentTarget.style.background='rgba(255,255,255,0.06)'} onMouseLeave={e=>e.currentTarget.style.background='rgba(255,255,255,0.02)'}>
              <span style={{color:'rgba(255,255,255,0.9)'}}>{RESOURCE_LABELS[k]||k}</span>
              <span style={{color:k==='gold'?'#ffd700':k==='food'?'#3eb87a':k==='firewood'?'#ff8c42':'rgba(255,255,255,0.95)',fontWeight:600}}>{Math.floor(res[k]||0)}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ── BuildPanel ───────────────────────────────────────────────────────
function BanishedBuildPanel({state,buildMode,onSetBuild,onCancel}){
  const [cat,setCat]=React.useState('housing');
  const res=state?.resources||{};
  const canAfford=cost=>Object.entries(cost).every(([r,a])=>(res[r]||0)>=a);
  const catColors={housing:'#5ac480',resource:'#c9a86c',food:'#3eb87a',storage:'#9ab4d4',trade:'#d49a5a',service:'#5a8ac4'};
  return(
    <div style={{position:'absolute',right:0,bottom:48,width:230,background:'linear-gradient(180deg,rgba(15,20,18,0.98) 0%,rgba(8,12,10,0.98) 100%)',borderLeft:'1px solid rgba(58,184,122,0.2)',borderTop:'1px solid rgba(58,184,122,0.2)',borderTopLeftRadius:'12px',zIndex:9,maxHeight:'65vh',overflowY:'auto',boxShadow:'-2px 0 20px rgba(0,0,0,0.5)'}}>
      <div style={{padding:'8px',borderBottom:'1px solid rgba(58,184,122,0.15)',display:'flex',gap:5,flexWrap:'wrap',background:'rgba(58,184,122,0.05)',position:'sticky',top:0'}}>
        {Object.entries(B_CATS).map(([k,v])=>(
          <button key={k} className={`btn btn-sm ${cat===k?'btn-p':'btn-s'}`} onClick={()=>setCat(k)} style={{fontSize:11,padding:'4px 8px',borderRadius:'6px',fontWeight:600,background:cat===k?catColors[k]||'#5ac480':'rgba(255,255,255,0.06)',border:cat===k?'none':'1px solid rgba(255,255,255,0.1)',color:cat===k?'#fff':'rgba(255,255,255,0.7)',transition:'all 0.2s',display:'flex',alignItems:'center',gap:4}}><BIcon name={k} size={12} color={cat===k?'#fff':'rgba(255,255,255,0.7)'}/>{v.name}</button>
        ))}
        {buildMode&&<button className="btn btn-d btn-sm" onClick={onCancel} style={{fontSize:11,padding:'4px 8px',borderRadius:'6px',fontWeight:600,marginLeft:'auto',background:'rgba(196,90,90,0.2)',border:'1px solid rgba(196,90,90,0.3)',color:'#c45a5a'}}>取消</button>}
      </div>
      <div style={{padding:8}}>
        {Object.entries(BUILDINGS_DATA).filter(([,b])=>b.cat===cat).map(([type,b])=>{
          const ok=canAfford(b.cost);
          const selected=buildMode===type;
          return(
            <div key={type} onClick={()=>ok&&onSetBuild(type)} style={{padding:'10px',marginBottom:6,borderRadius:'8px',border:`1.5px solid ${selected?(catColors[cat]||'#5ac480'):'rgba(255,255,255,0.1)'}`,cursor:ok?'pointer':'not-allowed',opacity:ok?1:0.45,background:selected?`${(catColors[cat]||'#5ac480')}20`:'rgba(255,255,255,0.03)',transition:'all 0.2s',boxShadow:selected?`0 0 15px ${(catColors[cat]||'#5ac480')}40`:'none'}} onMouseEnter={e=>{if(ok&&!selected)e.currentTarget.style.background='rgba(255,255,255,0.06)';e.currentTarget.style.transform='translateX(-2px)';}} onMouseLeave={e=>{if(ok&&!selected)e.currentTarget.style.background='rgba(255,255,255,0.03)';e.currentTarget.style.transform='translateX(0)';}}>
              <div style={{fontWeight:600,fontSize:13,marginBottom:4,color:selected?(catColors[cat]||'#5ac480'):'rgba(255,255,255,0.95)'}}>{b.name}</div>
              <div style={{fontSize:11,color:ok?'rgba(255,255,255,0.6)':'rgba(196,90,90,0.8)',marginBottom:3}}>{Object.entries(b.cost).map(([r,a])=>`${RESOURCE_LABELS[r]||r}:${a}`).join(' ')||'免费'}</div>
              {b.workers>0&&<div style={{fontSize:10,color:'rgba(255,255,255,0.5)',display:'flex',alignItems:'center',gap:4}}>工人: {b.workers}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── InfoPanel ────────────────────────────────────────────────────────
function BanishedInfoPanel({selBuilding,selVillager,onClose}){
  if(!selBuilding&&!selVillager)return null;
  const Bar=({val,max,color,label,icon})=>(
    <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:8}}>
      <span style={{fontSize:11,width:36,color:'rgba(255,255,255,0.7)',fontWeight:500,display:'flex',alignItems:'center',gap:4}}><BIcon name={icon} size={12} color="rgba(255,255,255,0.7)"/>{label}</span>
      <div style={{height:8,background:'rgba(255,255,255,0.08)',borderRadius:4,flex:1,overflow:'hidden',boxShadow:'inset 0 1px 3px rgba(0,0,0,0.3)'}}>
        <div style={{height:'100%',width:`${Math.max(0,Math.min(100,(val/max)*100))}%`,background:`linear-gradient(90deg,${color},${color}dd)`,borderRadius:4,transition:'width 0.3s',boxShadow:`0 0 10px ${color}40`}}/>
      </div>
      <span style={{fontSize:11,width:28,textAlign:'right',fontWeight:600,color:color}}>{Math.floor(val||0)}</span>
    </div>
  );
  if(selVillager){
    const v=selVillager;
    return(
      <div style={{position:'absolute',bottom:48,left:0,width:250,background:'linear-gradient(135deg,rgba(15,20,18,0.98) 0%,rgba(8,12,10,0.98) 100%)',border:'1px solid rgba(58,184,122,0.25)',borderRadius:'12px',padding:14,zIndex:9,boxShadow:'0 4px 24px rgba(0,0,0,0.5)',backdropFilter:'blur(8px)'}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:10,paddingBottom:8,borderBottom:'1px solid rgba(58,184,122,0.15)'}}>
          <div>
            <span style={{fontWeight:700,fontSize:15,color:'rgba(255,255,255,0.95)'}}>{v.name}</span>
            <span style={{fontSize:13,color:'rgba(255,255,255,0.6)',marginLeft:6}}>({v.age}岁)</span>
          </div>
          <button className="btn btn-s btn-sm" onClick={onClose} style={{padding:'4px 6px',borderRadius:'6px',background:'rgba(255,255,255,0.06)'}}><Icon name="x" size={13}/></button>
        </div>
        <div style={{display:'inline-block',fontSize:11,padding:'3px 8px',borderRadius:'4px',background:`${VILLAGER_COLORS[v.state]||'#888'}20`,color:VILLAGER_COLORS[v.state]||'rgba(255,255,255,0.7)',fontWeight:600,marginBottom:10,border:`1px solid ${VILLAGER_COLORS[v.state]||'#888'}40`}}>{v.state}</div>
        <div style={{marginTop:10}}>
          <Bar val={v.hunger||0} max={100} color="#e88a1a" label="饱食" icon="hunger"/>
          <Bar val={v.thirst||0} max={100} color="#5ad4e8" label="水分" icon="thirst"/>
          <Bar val={v.warmth||0} max={100} color="#9ab4d4" label="保暖" icon="warmth"/>
          <Bar val={v.health||100} max={100} color="#3eb87a" label="健康" icon="health"/>
        </div>
        {v.educated&&<div style={{marginTop:8,fontSize:11,padding:'6px 10px',background:'rgba(90,138,196,0.15)',borderRadius:'6px',color:'#5a8ac4',fontWeight:600,display:'flex',alignItems:'center',gap:6,border:'1px solid rgba(90,138,196,0.3)'}}>受教育 · 效率×2</div>}
      </div>
    );
  }
  const b=selBuilding,bd=BUILDINGS_DATA[b.type];
  return(
    <div style={{position:'absolute',bottom:48,left:0,width:250,background:'linear-gradient(135deg,rgba(15,20,18,0.98) 0%,rgba(8,12,10,0.98) 100%)',border:'1px solid rgba(58,184,122,0.25)',borderRadius:'12px',padding:14,zIndex:9,boxShadow:'0 4px 24px rgba(0,0,0,0.5)',backdropFilter:'blur(8px)'}}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:10,paddingBottom:8,borderBottom:'1px solid rgba(58,184,122,0.15)'}}>
        <span style={{fontWeight:700,fontSize:15,color:'#5ac480'}}>{bd?.name||b.type}</span>
        <button className="btn btn-s btn-sm" onClick={onClose} style={{padding:'4px 6px',borderRadius:'6px',background:'rgba(255,255,255,0.06)'}}><Icon name="x" size={13}/></button>
      </div>
      {!b.built&&(
        <div style={{marginBottom:10}}>
          <div style={{display:'flex',justifyContent:'space-between',fontSize:11,color:'rgba(255,255,255,0.6)',marginBottom:4}}>建造进度</div>
          <div style={{height:10,background:'rgba(255,255,255,0.08)',borderRadius:5,overflow:'hidden'}}>
            <div style={{height:'100%',width:`${(b.progress||0)*100}%`,background:'linear-gradient(90deg,#5ac480,#3eb87a)',borderRadius:5,transition:'width 0.3s',boxShadow:'0 0 10px rgba(58,184,122,0.4)'}}/>
          </div>
          <div style={{fontSize:10,color:'rgba(255,255,255,0.5)',marginTop:2,textAlign:'right'}}>{Math.floor((b.progress||0)*100)}%</div>
        </div>
      )}
      {b.built&&b.workers_max>0&&(
        <div style={{fontSize:12,color:'rgba(255,255,255,0.85)',marginBottom:8,padding:'6px 10px',background:'rgba(58,184,122,0.1)',borderRadius:'6px',display:'flex',alignItems:'center',gap:8}}>
          <span>工人: <strong style={{color:'#5ac480'}}>{b.workers_assigned}</strong> / {b.workers_max}</span>
        </div>
      )}
      {b.type==='well'&&(
        <div style={{fontSize:12,color:'#5ad4e8',marginBottom:8,padding:'6px 10px',background:'rgba(90,212,232,0.1)',borderRadius:'6px',display:'flex',alignItems:'center',gap:8}}>
          <span>水量: <strong>{Math.floor(b.water_storage||0)}</strong> / 200</span>
        </div>
      )}
      <div style={{fontSize:11,color:'rgba(255,255,255,0.5)',padding:'6px 10px',background:'rgba(255,255,255,0.03)',borderRadius:'6px',display:'flex',alignItems:'center',gap:6}}>
        <span>({b.x}, {b.y}) · {b.w}×{b.h}</span>
      </div>
    </div>
  );
}

// ── MarketPanel ──────────────────────────────────────────────────────
function BanishedMarketPanel({onClose}){
  const [res,setRes]=React.useState('logs');
  const [summary,setSummary]=React.useState(null);
  const [hist,setHist]=React.useState([]);
  const [ot,setOt]=React.useState('buy');
  const [amt,setAmt]=React.useState('');
  const [price,setPrice]=React.useState('');
  const [msg,setMsg]=React.useState('');
  const load=async()=>{
    try{
      const[s,h]=await Promise.all([F(`/api/banished/market/`),F(`/api/banished/market/history/${res}/`)]);
      setSummary((s.summary||{})[res]||s);setHist(h.history||[]);
    }catch{}
  };
  React.useEffect(()=>{load();},[res]);
  const place=async()=>{
    if(!amt||!price)return;
    setMsg('');
    try{await P(`/api/banished/market/order/`,{resource:res,order_type:ot,amount:parseInt(amt),price:parseInt(price)});setMsg('✓ 挂单成功');setAmt('');setPrice('');load();}
    catch(e){setMsg('✗ '+e.message);}
  };
  return(
    <div style={{position:'absolute',top:'8%',left:'50%',transform:'translateX(-50%)',width:'min(500px,94vw)',maxHeight:'82vh',background:'linear-gradient(135deg,rgba(15,20,18,0.98) 0%,rgba(8,12,10,0.98) 100%)',border:'1px solid rgba(201,168,108,0.3)',borderRadius:16,overflow:'hidden',zIndex:20,display:'flex',flexDirection:'column',boxShadow:'0 8px 32px rgba(0,0,0,0.6)',backdropFilter:'blur(12px)'}}>
      <div style={{padding:'14px 18px',borderBottom:'1px solid rgba(201,168,108,0.2)',display:'flex',justifyContent:'space-between',alignItems:'center',background:'linear-gradient(90deg,rgba(201,168,108,0.1),transparent)'}}>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <span style={{fontWeight:700,fontSize:16,color:'#c9a86c'}}>全球交易市场</span>
        </div>
        <button className="btn btn-s btn-sm" onClick={onClose} style={{padding:'5px 8px',borderRadius:'6px',background:'rgba(255,255,255,0.06)'}}><Icon name="x" size={15}/></button>
      </div>
      <div style={{flex:1,overflowY:'auto',padding:14}}>
        <div style={{display:'flex',gap:6,marginBottom:12,flexWrap:'wrap'}}>
          {['logs','stone','iron','coal','firewood','wheat','fish'].map(r=>(
            <button key={r} className={`btn btn-sm ${res===r?'btn-p':'btn-s'}`} onClick={()=>setRes(r)} style={{fontSize:11,padding:'4px 10px',borderRadius:'6px',fontWeight:600,background:res===r?'linear-gradient(135deg,#c9a86c,#b89760)':'rgba(255,255,255,0.06)',border:res===r?'none':'1px solid rgba(255,255,255,0.1)',color:res===r?'#fff':'rgba(255,255,255,0.7)'}}>{RESOURCE_LABELS[r]||r}</button>
          ))}
        </div>
        {summary&&(
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10,marginBottom:12}}>
            <div style={{background:'linear-gradient(135deg,rgba(196,90,90,0.12),rgba(196,90,90,0.05))',border:'1px solid rgba(196,90,90,0.25)',borderRadius:10,padding:12}}>
              <div style={{fontSize:11,color:'#c45a5a',fontWeight:600,marginBottom:6,display:'flex',alignItems:'center',gap:6}}>卖单 (最低5)</div>
              {(summary.sell_orders||[]).slice(0,5).map((o,i)=>(
                <div key={i} style={{display:'flex',justifyContent:'space-between',fontSize:12,marginBottom:3,padding:'4px 6px',background:'rgba(255,255,255,0.03)',borderRadius:4}}>
                  <span style={{color:'rgba(255,255,255,0.9)'}}>{o.amount}</span><span style={{color:'#c45a5a',fontWeight:600}}>{o.price}💰</span>
                </div>
              ))}
              {!(summary.sell_orders?.length)&&<div style={{fontSize:11,color:'rgba(255,255,255,0.4)',textAlign:'center',padding:8}}>暂无卖单</div>}
            </div>
            <div style={{background:'linear-gradient(135deg,rgba(58,184,122,0.12),rgba(58,184,122,0.05))',border:'1px solid rgba(58,184,122,0.25)',borderRadius:10,padding:12}}>
              <div style={{fontSize:11,color:'#3eb87a',fontWeight:600,marginBottom:6,display:'flex',alignItems:'center',gap:6}}>买单 (最高5)</div>
              {(summary.buy_orders||[]).slice(0,5).map((o,i)=>(
                <div key={i} style={{display:'flex',justifyContent:'space-between',fontSize:12,marginBottom:3,padding:'4px 6px',background:'rgba(255,255,255,0.03)',borderRadius:4}}>
                  <span style={{color:'#3eb87a',fontWeight:600}}>{o.price}💰</span><span style={{color:'rgba(255,255,255,0.9)'}}>{o.amount}</span>
                </div>
              ))}
              {!(summary.buy_orders?.length)&&<div style={{fontSize:11,color:'rgba(255,255,255,0.4)',textAlign:'center',padding:8}}>暂无买单</div>}
            </div>
          </div>
        )}
        {summary?.last_price&&<div style={{textAlign:'center',fontSize:14,padding:10,background:'linear-gradient(90deg,transparent,rgba(201,168,108,0.15),transparent)',borderRadius:8,marginBottom:12,color:'#ffd700',fontWeight:700}}>最新成交: {summary.last_price}</div>}
        {hist.length>0&&(
          <div style={{marginBottom:12}}>
            <div style={{fontSize:11,color:'rgba(255,255,255,0.6)',marginBottom:6,fontWeight:500}}>成交历史 ({hist.length}笔)</div>
            <div style={{display:'flex',alignItems:'flex-end',gap:1.5,height:44,padding:'8px',background:'rgba(255,255,255,0.02)',borderRadius:8}}>
              {hist.slice(-30).map((h,i)=>{
                const mx=Math.max(...hist.map(x=>x.price)),mn=Math.min(...hist.map(x=>x.price));
                const n=mx>mn?(h.price-mn)/(mx-mn):0.5;
                return<div key={i} style={{flex:1,height:`${Math.max(4,n*36)}px`,background:`linear-gradient(180deg,#c9a86c,#a88750)`,opacity:0.75,borderRadius:2,transition:'all 0.2s'}} title={`${h.price}💰`} onMouseEnter={e=>{e.currentTarget.style.opacity='1';e.currentTarget.style.height=`${Math.max(6,n*38)}px`;}} onMouseLeave={e=>{e.currentTarget.style.opacity='0.75';e.currentTarget.style.height=`${Math.max(4,n*36)}px`;}}/>;
              })}
            </div>
          </div>
        )}
        <div style={{borderTop:'1px solid rgba(201,168,108,0.15)',paddingTop:12}}>
          <div style={{display:'flex',gap:8,marginBottom:10}}>
            <button className={`btn btn-sm ${ot==='buy'?'btn-p':'btn-s'}`} onClick={()=>setOt('buy')} style={{flex:1,padding:'8px',fontSize:13,borderRadius:'8px',fontWeight:600,background:ot==='buy'?'linear-gradient(135deg,#3eb87a,#2d9a62)':'rgba(255,255,255,0.06)',border:ot==='buy'?'none':'1px solid rgba(255,255,255,0.1)',color:ot==='buy'?'#fff':'rgba(255,255,255,0.7)'}}>买入</button>
            <button className={`btn btn-sm ${ot==='sell'?'btn-d':'btn-s'}`} onClick={()=>setOt('sell')} style={{flex:1,padding:'8px',fontSize:13,borderRadius:'8px',fontWeight:600,background:ot==='sell'?'linear-gradient(135deg,#c45a5a,#a33d3d)':'rgba(255,255,255,0.06)',border:ot==='sell'?'none':'1px solid rgba(255,255,255,0.1)',color:ot==='sell'?'#fff':'rgba(255,255,255,0.7)'}}>卖出</button>
          </div>
          <div style={{display:'flex',gap:10,marginBottom:10}}>
            <div className="fg" style={{flex:1}}><label style={{fontSize:11,color:'rgba(255,255,255,0.6)',marginBottom:4,display:'block'}}>数量</label><input type="number" value={amt} onChange={e=>setAmt(e.target.value)} placeholder="0" style={{fontSize:13,padding:'8px',borderRadius:'6px'}}/></div>
            <div className="fg" style={{flex:1}}><label style={{fontSize:11,color:'rgba(255,255,255,0.6)',marginBottom:4,display:'block'}}>单价</label><input type="number" value={price} onChange={e=>setPrice(e.target.value)} placeholder="0" style={{fontSize:13,padding:'8px',borderRadius:'6px'}}/></div>
          </div>
          <button className="btn btn-p" style={{width:'100%',fontSize:13,padding:'10px',borderRadius:'8px',fontWeight:600,background:'linear-gradient(135deg,#c9a86c,#b89760)',border:'none'}} onClick={place}>挂单</button>
          {msg&&<div style={{fontSize:12,padding:'8px',borderRadius:'6px',textAlign:'center',marginTop:8,background:msg.includes('成功')?'rgba(58,184,122,0.15)':'rgba(196,90,90,0.15)',color:msg.includes('成功')?'#3eb87a':'#c45a5a',fontWeight:500}}>{msg}</div>}
        </div>
      </div>
    </div>
  );
}

// ── AIPanel ──────────────────────────────────────────────────────────
function BanishedAIPanel({token,gameState,onClose}){
  const [active,setActive]=React.useState(false);
  const [perms,setPerms]=React.useState({build:false,assign:false,trade:false});
  const [log,setLog]=React.useState('');
  const [streaming,setStreaming]=React.useState(false);
  const toggle=async()=>{try{const r=await P(`/api/banished/ai/toggle/`,{});setActive(r.is_ai_active);}catch{}};
  const savePerms=async(p)=>{try{await P(`/api/banished/ai/permissions/`,p);setPerms(p);}catch{}};
  const run=async()=>{
    setStreaming(true);setLog('');
    try{
      for await(const chunk of streamSSE(`/api/banished/ai/action/`,{state:gameState,permissions:perms},token)){
        if(chunk.type==='reasoning')setLog(l=>l+chunk.text);
        if(chunk.type==='action')setLog(l=>l+'\n[动作] '+JSON.stringify(chunk.action));
        if(chunk.done)break;
      }
    }catch(e){setLog(l=>l+'\n错误:'+e.message);}
    setStreaming(false);
  };
  return(
    <div style={{position:'absolute',top:'8%',right:0,width:'min(320px,94vw)',maxHeight:'82vh',background:'linear-gradient(135deg,rgba(15,20,18,0.98) 0%,rgba(8,12,10,0.98) 100%)',border:'1px solid rgba(90,138,196,0.3)',borderRadius:'16px 0 0 16px',overflow:'hidden',zIndex:20,display:'flex',flexDirection:'column',boxShadow:'-4px 0 24px rgba(0,0,0,0.5)',backdropFilter:'blur(12px)'}}>
      <div style={{padding:'14px 18px',borderBottom:'1px solid rgba(90,138,196,0.2)',display:'flex',justifyContent:'space-between',alignItems:'center',background:'linear-gradient(90deg,rgba(90,138,196,0.15),transparent)'}}>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <span style={{fontWeight:700,fontSize:16,color:'#5a8ac4'}}>AI 协同</span>
        </div>
        <button className="btn btn-s btn-sm" onClick={onClose} style={{padding:'5px 8px',borderRadius:'6px',background:'rgba(255,255,255,0.06)'}}><Icon name="x" size={15}/></button>
      </div>
      <div style={{flex:1,overflowY:'auto',padding:14}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:14,padding:'10px 12px',background:'rgba(90,138,196,0.1)',borderRadius:8,border:'1px solid rgba(90,138,196,0.2)'}}>
          <span style={{fontSize:13,color:'rgba(255,255,255,0.9)'}}>运行状态</span>
          <button className={`btn btn-sm ${active?'btn-p':'btn-s'}`} onClick={toggle} style={{padding:'5px 12px',fontSize:11,borderRadius:'6px',fontWeight:600,background:active?'linear-gradient(135deg,#5a8ac4,#4a7ab4)':'rgba(255,255,255,0.06)',border:active?'none':'1px solid rgba(255,255,255,0.1)',color:active?'#fff':'rgba(255,255,255,0.7)'}}>{active?'● 运行中':'○ 已停止'}</button>
        </div>
        <div style={{marginBottom:14}}>
          <div style={{fontSize:11,color:'rgba(255,255,255,0.6)',marginBottom:8,fontWeight:500,textTransform:'uppercase',letterSpacing:'0.5px'}}>权限设置</div>
          {[['build','建筑规划'],['assign','工人分配'],['trade','市场交易']].map(([k,lbl])=>(
            <div key={k} style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8,padding:'8px 10px',background:'rgba(255,255,255,0.03)',borderRadius:6,transition:'background 0.2s'}} onMouseEnter={e=>e.currentTarget.style.background='rgba(255,255,255,0.06)'} onMouseLeave={e=>e.currentTarget.style.background='rgba(255,255,255,0.03)'}>
              <span style={{fontSize:12,color:'rgba(255,255,255,0.9)'}}>{lbl}</span>
              <button className={`btn btn-sm ${perms[k]?'btn-p':'btn-s'}`} onClick={()=>savePerms({...perms,[k]:!perms[k]})} style={{fontSize:10,padding:'4px 10px',borderRadius:'5px',fontWeight:600,background:perms[k]?'linear-gradient(135deg,#5a8ac4,#4a7ab4)':'rgba(255,255,255,0.06)',border:perms[k]?'none':'1px solid rgba(255,255,255,0.1)',color:perms[k]?'#fff':'rgba(255,255,255,0.7)'}}>{perms[k]?'✓ 允许':'✗ 禁止'}</button>
            </div>
          ))}
        </div>
        <button className="btn btn-p" style={{width:'100%',marginBottom:10,padding:'10px',fontSize:13,borderRadius:'8px',fontWeight:600,background:'linear-gradient(135deg,#5a8ac4,#4a7ab4)',border:'none'}} onClick={run} disabled={streaming}>{streaming?'思考中...':'AI决策一次'}</button>
        {log&&<div style={{background:'linear-gradient(135deg,rgba(90,138,196,0.08),rgba(90,138,196,0.03))',border:'1px solid rgba(90,138,196,0.2)',borderRadius:10,padding:12,fontSize:11,color:'rgba(255,255,255,0.85)',whiteSpace:'pre-wrap',lineHeight:1.7,maxHeight:200,overflowY:'auto',fontFamily:'monospace'}}>{log}{streaming&&<span style={{animation:'blink 1s infinite',color:'#5a8ac4'}}>▌</span>}</div>}
      </div>
    </div>
  );
}

// ── SavePanel ────────────────────────────────────────────────────────
function BanishedSavePanel({currentState,onLoad,onClose}){
  const [saves,setSaves]=React.useState([]);
  const [busy,setBusy]=React.useState(false);
  const [msg,setMsg]=React.useState('');
  const load=async()=>{try{const d=await F(`/api/banished/saves/`);setSaves(d.saves||[]);}catch{}};
  React.useEffect(()=>{load();},[]);
  const save=async slot=>{setBusy(true);try{await P(`/api/banished/saves/${slot}/`,{name:`存档${slot}-第${currentState?.time?.year||1}年`});setMsg(`✓ 存档${slot}成功`);load();}catch(e){setMsg('✗ '+e.message);}setBusy(false);};
  const loadSlot=async slot=>{setBusy(true);try{const d=await P(`/api/banished/saves/${slot}/load/`,{});onLoad(d.state);onClose();}catch(e){setMsg('✗ '+e.message);}setBusy(false);};
  return(
    <div style={{position:'absolute',top:'8%',left:'50%',transform:'translateX(-50%)',width:'min(400px,94vw)',background:'linear-gradient(135deg,rgba(15,20,18,0.98) 0%,rgba(8,12,10,0.98) 100%)',border:'1px solid rgba(201,168,108,0.3)',borderRadius:16,overflow:'hidden',zIndex:20,boxShadow:'0 8px 32px rgba(0,0,0,0.6)',backdropFilter:'blur(12px)'}}>
      <div style={{padding:'14px 18px',borderBottom:'1px solid rgba(201,168,108,0.2)',display:'flex',justifyContent:'space-between',alignItems:'center',background:'linear-gradient(90deg,rgba(201,168,108,0.1),transparent)'}}>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <span style={{fontWeight:700,fontSize:16,color:'#c9a86c'}}>云存档</span>
        </div>
        <button className="btn btn-s btn-sm" onClick={onClose} style={{padding:'5px 8px',borderRadius:'6px',background:'rgba(255,255,255,0.06)'}}><Icon name="x" size={15}/></button>
      </div>
      <div style={{padding:14}}>
        {[1,2,3].map(slot=>{
          const sv=saves.find(s=>s.slot===slot);
          return(
            <div key={slot} style={{display:'flex',alignItems:'center',gap:10,padding:12,background:'linear-gradient(135deg,rgba(201,168,108,0.08),rgba(201,168,108,0.03))',border:'1px solid rgba(201,168,108,0.2)',borderRadius:10,marginBottom:10,transition:'all 0.2s'}} onMouseEnter={e=>e.currentTarget.style.background='linear-gradient(135deg,rgba(201,168,108,0.12),rgba(201,168,108,0.06))'} onMouseLeave={e=>e.currentTarget.style.background='linear-gradient(135deg,rgba(201,168,108,0.08),rgba(201,168,108,0.03))'}>
              <div style={{flex:1}}>
                <div style={{fontSize:14,fontWeight:600,color:'#c9a86c',marginBottom:2}}>存档 {slot}</div>
                {sv?<div style={{fontSize:12,color:'rgba(255,255,255,0.6)'}}>{sv.name} · 第{sv.year}年 · {sv.population}人</div>:<div style={{fontSize:12,color:'rgba(255,255,255,0.4)'}}>空插槽</div>}
              </div>
              <div style={{display:'flex',gap:6}}>
                <button className="btn btn-p btn-sm" onClick={()=>save(slot)} disabled={busy} style={{padding:'6px 12px',fontSize:12,borderRadius:'6px',fontWeight:600,background:'linear-gradient(135deg,#c9a86c,#b89760)',border:'none'}}>保存</button>
                {sv&&<button className="btn btn-s btn-sm" onClick={()=>loadSlot(slot)} disabled={busy} style={{padding:'6px 12px',fontSize:12,borderRadius:'6px',fontWeight:600,background:'rgba(255,255,255,0.06)',border:'1px solid rgba(255,255,255,0.1)'}}>读取</button>}
              </div>
            </div>
          );
        })}
        {msg&&<div style={{textAlign:'center',fontSize:12,padding:8,borderRadius:'6px',background:msg.includes('成功')?'rgba(58,184,122,0.15)':'rgba(196,90,90,0.15)',color:msg.includes('成功')?'#3eb87a':'#c45a5a',fontWeight:500,marginTop:6}}>{msg}</div>}
      </div>
    </div>
  );
}

// ── Leaderboard ──────────────────────────────────────────────────────
function BanishedLeaderboard({onClose}){
  const [board,setBoard]=React.useState([]);
  React.useEffect(()=>{F(`/api/banished/leaderboard/`).then(d=>setBoard(d.leaderboard||[])).catch(()=>{});},[]);
  const rankColors=['#ffd700','#c0c0c0','#cd7f32'];
  return(
    <div style={{position:'absolute',top:'8%',left:'50%',transform:'translateX(-50%)',width:'min(400px,94vw)',background:'linear-gradient(135deg,rgba(15,20,18,0.98) 0%,rgba(8,12,10,0.98) 100%)',border:'1px solid rgba(201,168,108,0.3)',borderRadius:16,overflow:'hidden',zIndex:20,boxShadow:'0 8px 32px rgba(0,0,0,0.6)',backdropFilter:'blur(12px)'}}>
      <div style={{padding:'14px 18px',borderBottom:'1px solid rgba(201,168,108,0.2)',display:'flex',justifyContent:'space-between',alignItems:'center',background:'linear-gradient(90deg,rgba(201,168,108,0.1),transparent)'}}>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <span style={{fontWeight:700,fontSize:16,color:'#c9a86c'}}>排行榜</span>
        </div>
        <button className="btn btn-s btn-sm" onClick={onClose} style={{padding:'5px 8px',borderRadius:'6px',background:'rgba(255,255,255,0.06)'}}><Icon name="x" size={15}/></button>
      </div>
      <div style={{padding:12,maxHeight:'60vh',overflowY:'auto'}}>
        {!board.length&&<div style={{textAlign:'center',color:'rgba(255,255,255,0.4)',padding:24,fontSize:13}}>暂无数据</div>}
        {board.map((e,i)=>(
          <div key={i} style={{display:'flex',alignItems:'center',gap:12,padding:i<3?'12px':'10px',borderRadius:10,background:i<3?`linear-gradient(135deg,${rankColors[i]}15,${rankColors[i]}05)`:'transparent',border:i<3?`1px solid ${rankColors[i]}30`:'none',marginBottom:6,transition:'all 0.2s'}} onMouseEnter={e=>{if(i>=3)e.currentTarget.style.background='rgba(255,255,255,0.04)';}} onMouseLeave={e=>{if(i>=3)e.currentTarget.style.background='transparent';}}>
            <span style={{width:28,textAlign:'center',fontSize:i<3?18:14,fontWeight:i<3?800:700,color:i<3?rankColors[i]:'rgba(255,255,255,0.5)'}}>{i<3?`${i+1}`:`#${i+1}`}</span>
            <span style={{flex:1,fontSize:14,color:'rgba(255,255,255,0.95)',fontWeight:500}}>{e.username}</span>
            <div style={{textAlign:'right'}}>
              <div style={{color:'#ffd700',fontSize:15,fontWeight:700}}>{e.score}分</div>
              <div style={{color:'rgba(255,255,255,0.5)',fontSize:11}}>人口{e.population} · 第{e.year}年</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Lobby ────────────────────────────────────────────────────────────
function BanishedLobby({onNewGame,onLoadGame,onBack}){
  const [saves,setSaves]=React.useState([]);
  const [showBoard,setShowBoard]=React.useState(false);
  const [busy,setBusy]=React.useState(false);
  React.useEffect(()=>{F(`/api/banished/saves/`).then(d=>setSaves(d.saves||[])).catch(()=>{});},[]);
  const cont=async()=>{
    setBusy(true);
    try{const d=await F(`/api/banished/game/`);if(d.state&&Object.keys(d.state).length>2)onLoadGame(d.state);else onNewGame();}
    catch{onNewGame();}
    setBusy(false);
  };
  const loadSlot=async slot=>{
    setBusy(true);
    try{const d=await P(`/api/banished/saves/${slot}/load/`,{});onLoadGame(d.state);}
    catch(e){alert(e.message);}
    setBusy(false);
  };
  return(
    <div style={{height:'100vh',display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',background:'radial-gradient(ellipse at top,rgba(58,184,122,0.12) 0%,rgba(8,8,11,0.98) 60%,#050507 100%)',gap:20,padding:24,position:'relative',overflow:'hidden'}}>
      {/* 背景装饰 */}
      <div style={{position:'absolute',top:0,left:0,right:0,bottom:0,opacity:0.03,backgroundImage:'repeating-linear-gradient(45deg,transparent,transparent 35px,rgba(58,184,122,0.4) 35px,rgba(58,184,122,0.4) 70px)',pointerEvents:'none'}}/>
      <div style={{position:'absolute',top:-100,left:-100,width:400,height:400,background:'radial-gradient(circle,rgba(58,184,122,0.1),transparent 70%)',filter:'blur(60px)',pointerEvents:'none'}}/>
      <div style={{position:'absolute',bottom:-150,right:-150,width:500,height:500,background:'radial-gradient(circle,rgba(201,168,108,0.08),transparent 70%)',filter:'blur(80px)',pointerEvents:'none'}}/>
      {showBoard&&<BanishedLeaderboard onClose={()=>setShowBoard(false)}/>}
      <div style={{position:'relative',zIndex:1,textAlign:'center'}}>
        <h1 style={{fontFamily:'var(--serif)',fontSize:42,color:'#5ac480',margin:'0 0 12px',fontWeight:700,textShadow:'0 0 40px rgba(58,184,122,0.5)',letterSpacing:'2px'}}>放逐之城</h1>
        <p style={{color:'rgba(255,255,255,0.65)',fontSize:14,textAlign:'center',maxWidth:400,lineHeight:1.8,margin:'0 0 24px',fontWeight:400}}>在蛮荒之地建立并繁荣你的城市。<br/>合理分配资源，养活村民，抵御严冬。</p>
        <div style={{display:'flex',flexDirection:'column',gap:12,width:'min(300px,90vw)',margin:'0 auto'}}>
          <button className="btn btn-p" onClick={cont} disabled={busy} style={{padding:'14px 20px',fontSize:16,borderRadius:'12px',fontWeight:600,background:'linear-gradient(135deg,#5ac480,#3eb87a)',border:'none',boxShadow:'0 4px 20px rgba(58,184,122,0.4)',transition:'all 0.3s'}} onMouseEnter={e=>{e.currentTarget.style.transform='translateY(-2px)';e.currentTarget.style.boxShadow='0 6px 28px rgba(58,184,122,0.6)';}} onMouseLeave={e=>{e.currentTarget.style.transform='translateY(0)';e.currentTarget.style.boxShadow='0 4px 20px rgba(58,184,122,0.4)';}}>{busy?'加载中...':'继续游戏'}</button>
          <button className="btn btn-s" onClick={onNewGame} style={{padding:'14px 20px',fontSize:16,borderRadius:'12px',fontWeight:600,background:'rgba(255,255,255,0.06)',border:'1px solid rgba(255,255,255,0.1)',color:'rgba(255,255,255,0.9)',transition:'all 0.3s'}} onMouseEnter={e=>{e.currentTarget.style.background='rgba(255,255,255,0.1)';e.currentTarget.style.transform='translateY(-2px)';}} onMouseLeave={e=>{e.currentTarget.style.background='rgba(255,255,255,0.06)';e.currentTarget.style.transform='translateY(0)';}}>新游戏</button>
        </div>
        {saves.length>0&&(
          <div style={{marginTop:20,width:'min(300px,90vw)',marginLeft:'auto',marginRight:'auto'}}>
            <div style={{fontSize:12,color:'rgba(255,255,255,0.5)',marginBottom:8,textAlign:'center',fontWeight:500,letterSpacing:'1px'}}>云存档</div>
            {saves.map(s=>(
              <button key={s.slot} className="btn btn-s" style={{width:'100%',marginBottom:8,padding:'10px 14px',fontSize:13,display:'flex',justifyContent:'space-between',alignItems:'center',borderRadius:'8px',background:'linear-gradient(135deg,rgba(201,168,108,0.1),rgba(201,168,108,0.05))',border:'1px solid rgba(201,168,108,0.2)',transition:'all 0.2s'}} onClick={()=>loadSlot(s.slot)} disabled={busy} onMouseEnter={e=>{e.currentTarget.style.background='linear-gradient(135deg,rgba(201,168,108,0.15),rgba(201,168,108,0.08))';e.currentTarget.style.transform='translateX(4px)';}} onMouseLeave={e=>{e.currentTarget.style.background='linear-gradient(135deg,rgba(201,168,108,0.1),rgba(201,168,108,0.05))';e.currentTarget.style.transform='translateX(0)';}}>
                <span style={{color:'rgba(255,255,255,0.9)'}}>{s.name||`存档${s.slot}`}</span>
                <span style={{color:'rgba(255,255,255,0.5)',fontSize:12}}>第{s.year}年 · {s.population}人</span>
              </button>
            ))}
          </div>
        )}
        <div style={{display:'flex',gap:12,marginTop:20}}>
          <button className="btn btn-s btn-sm" onClick={()=>setShowBoard(true)} style={{padding:'8px 16px',fontSize:13,borderRadius:'8px',fontWeight:600,background:'rgba(255,255,215,0.08)',border:'1px solid rgba(255,215,0,0.2)',color:'#ffd700',transition:'all 0.2s'}} onMouseEnter={e=>{e.currentTarget.style.background='rgba(255,215,0,0.15)';}} onMouseLeave={e=>{e.currentTarget.style.background='rgba(255,215,0,0.08)';}}>🏆 排行榜</button>
          <button className="btn btn-s btn-sm" onClick={onBack} style={{padding:'8px 16px',fontSize:13,borderRadius:'8px',fontWeight:600,background:'rgba(255,255,255,0.06)',border:'1px solid rgba(255,255,255,0.1)',color:'rgba(255,255,255,0.7)',transition:'all 0.2s'}} onMouseEnter={e=>{e.currentTarget.style.background='rgba(255,255,255,0.1)';}} onMouseLeave={e=>{e.currentTarget.style.background='rgba(255,255,255,0.06)';}}>← 返回主页</button>
        </div>
      </div>
    </div>
  );
}

// ── GameView ─────────────────────────────────────────────────────────
function BanishedGameView({initialState,token,onBack}){
  const canvasRef=React.useRef(null);
  const engineRef=React.useRef(null);
  const [gs,setGs]=React.useState(initialState);
  const [speed,setSpeed]=React.useState(initialState?.time?.speed||1);
  const [selBuilding,setSelBuilding]=React.useState(null);
  const [selVillager,setSelVillager]=React.useState(null);
  const [buildMode,setBuildMode]=React.useState(null);
  const [buildError,setBuildError]=React.useState(null);
  const [showRes,setShowRes]=React.useState(true);
  const [showBuild,setShowBuild]=React.useState(true);
  const [showMarket,setShowMarket]=React.useState(false);
  const [showAI,setShowAI]=React.useState(false);
  const [showSave,setShowSave]=React.useState(false);
  const [syncStatus,setSyncStatus]=React.useState(null);

  React.useEffect(()=>{
    const resize=()=>{if(canvasRef.current){canvasRef.current.width=window.innerWidth;canvasRef.current.height=window.innerHeight;}};
    resize();window.addEventListener('resize',resize);return()=>window.removeEventListener('resize',resize);
  },[]);

  React.useEffect(()=>{
    if(!canvasRef.current||!gs)return;
    const eng=new BanishedEngine(canvasRef.current,gs,upd=>{
      if(upd.state)setGs(s=>({...s,...upd.state}));
      if(upd.selectedBuilding!==undefined){setSelBuilding(upd.selectedBuilding);if(upd.selectedBuilding)setSelVillager(null);}
      if(upd.selectedVillager!==undefined){setSelVillager(upd.selectedVillager);if(upd.selectedVillager)setSelBuilding(null);}
      if(upd.buildError!==undefined)setBuildError(upd.buildError);
    });
    engineRef.current=eng;
    eng.start(async(newState,prev,elapsed)=>{
      setSyncStatus({ok:false,msg:'同步中...'});
      try{const r=await P(`/api/banished/game/sync/`,{state:newState,elapsed_seconds:elapsed});setSyncStatus({ok:true,msg:r.warnings?.length?`⚠ ${r.warnings[0]}`:'已同步'});}
      catch{setSyncStatus({ok:false,msg:'失败'});}
    });
    return()=>eng.destroy();
  },[]);

  const handleSpeed=s=>{setSpeed(s);if(engineRef.current)engineRef.current.setSpeed(s);};
  const handleBuild=type=>{setBuildMode(type);setBuildError(null);if(engineRef.current)engineRef.current.setBuildMode(type);};
  const handleCancelBuild=()=>{setBuildMode(null);if(engineRef.current)engineRef.current.cancelBuildMode();};
  const handleLoad=state=>{if(engineRef.current){engineRef.current.pause();engineRef.current.destroy();}setGs(state);};

  return(
    <div style={{position:'relative',width:'100vw',height:'100vh',overflow:'hidden',background:'linear-gradient(180deg,#050507 0%,#0a0a0f 100%)'}}>
      <canvas ref={canvasRef} style={{position:'absolute',top:0,left:0,cursor:buildMode?'crosshair':'default'}}/>
      <BanishedHUD state={gs} speed={speed} onSetSpeed={handleSpeed} onToggleRes={()=>setShowRes(r=>!r)} syncStatus={syncStatus}/>
      <BanishedResourcePanel state={gs} open={showRes} onClose={()=>setShowRes(false)}/>
      {showBuild&&<BanishedBuildPanel state={gs} buildMode={buildMode} onSetBuild={handleBuild} onCancel={handleCancelBuild}/>}
      <BanishedInfoPanel selBuilding={selBuilding} selVillager={selVillager} onClose={()=>{setSelBuilding(null);setSelVillager(null);}}/>
      {showMarket&&<BanishedMarketPanel onClose={()=>setShowMarket(false)}/>}
      {showAI&&<BanishedAIPanel token={token} gameState={gs} onClose={()=>setShowAI(false)}/>}
      {showSave&&<BanishedSavePanel currentState={gs} onLoad={handleLoad} onClose={()=>setShowSave(false)}/>}
      {buildError&&(
        <div style={{position:'absolute',bottom:60,left:'50%',transform:'translateX(-50%)',background:'linear-gradient(135deg,rgba(196,90,90,0.95),rgba(180,70,70,0.95))',padding:'8px 16px',borderRadius:10,fontSize:13,zIndex:30,cursor:'pointer',fontWeight:600,boxShadow:'0 4px 20px rgba(196,90,90,0.5)',border:'1px solid rgba(196,90,90,0.5)',display:'flex',alignItems:'center',gap:6}} onClick={()=>setBuildError(null)}>⚠️ {buildError}</div>
      )}
      <div style={{position:'absolute',bottom:0,left:'50%',transform:'translateX(-50%)',display:'flex',gap:8,padding:'8px 14px',background:'linear-gradient(180deg,rgba(8,8,11,0.95) 0%,rgba(15,15,20,0.98) 100%)',borderTop:'1px solid rgba(58,184,122,0.25)',borderRadius:'14px 14px 0 0',zIndex:10,backdropFilter:'blur(12px)',boxShadow:'0 -4px 20px rgba(0,0,0,0.4)'}}>
        <button className={`btn btn-sm ${showBuild?'btn-p':'btn-s'}`} onClick={()=>setShowBuild(b=>!b)} style={{padding:'6px 12px',fontSize:12,borderRadius:'8px',fontWeight:600,background:showBuild?'linear-gradient(135deg,#5ac480,#3eb87a)':'rgba(255,255,255,0.06)',border:showBuild?'none':'1px solid rgba(255,255,255,0.12)',color:showBuild?'#fff':'rgba(255,255,255,0.8)',display:'flex',alignItems:'center',gap:4}}><BIcon name="build" size={14} color={showBuild?'#fff':'rgba(255,255,255,0.8)'}/>建造</button>
        <button className={`btn btn-sm ${showMarket?'btn-p':'btn-s'}`} onClick={()=>setShowMarket(m=>!m)} style={{padding:'6px 12px',fontSize:12,borderRadius:'8px',fontWeight:600,background:showMarket?'linear-gradient(135deg,#c9a86c,#b89760)':'rgba(255,255,255,0.06)',border:showMarket?'none':'1px solid rgba(255,255,255,0.12)',color:showMarket?'#fff':'rgba(255,255,255,0.8)',display:'flex',alignItems:'center',gap:4}}><BIcon name="market" size={14} color={showMarket?'#fff':'rgba(255,255,255,0.8)'}/>市场</button>
        <button className={`btn btn-sm ${showAI?'btn-p':'btn-s'}`} onClick={()=>setShowAI(a=>!a)} style={{padding:'6px 12px',fontSize:12,borderRadius:'8px',fontWeight:600,background:showAI?'linear-gradient(135deg,#5a8ac4,#4a7ab4)':'rgba(255,255,255,0.06)',border:showAI?'none':'1px solid rgba(255,255,255,0.12)',color:showAI?'#fff':'rgba(255,255,255,0.8)',display:'flex',alignItems:'center',gap:4}}><BIcon name="ai" size={14} color={showAI?'#fff':'rgba(255,255,255,0.8)'}/>AI</button>
        <button className={`btn btn-sm ${showSave?'btn-p':'btn-s'}`} onClick={()=>setShowSave(s=>!s)} style={{padding:'6px 12px',fontSize:12,borderRadius:'8px',fontWeight:600,background:showSave?'linear-gradient(135deg,#d49a5a,#c4884a)':'rgba(255,255,255,0.06)',border:showSave?'none':'1px solid rgba(255,255,255,0.12)',color:showSave?'#fff':'rgba(255,255,255,0.8)',display:'flex',alignItems:'center',gap:4}}><BIcon name="save" size={14} color={showSave?'#fff':'rgba(255,255,255,0.8)'}/>存档</button>
        <button className="btn btn-s btn-sm" onClick={onBack} style={{padding:'6px 12px',fontSize:12,borderRadius:'8px',fontWeight:600,background:'rgba(255,255,255,0.06)',border:'1px solid rgba(255,255,255,0.12)',color:'rgba(255,255,255,0.7)'}}>返回</button>
      </div>
    </div>
  );
}

// ── BanishedApp ──────────────────────────────────────────────────────
function BanishedApp({user,onLogout,onUpdateUser}){
  const token=localStorage.getItem('mf_token');
  const [view,setView]=React.useState('lobby');
  const [gs,setGs]=React.useState(null);
  const [starting,setStarting]=React.useState(false);
  const newGame=async()=>{
    setStarting(true);
    try{const d=await P(`/api/banished/game/new/`,{});setGs(d.state);setView('game');}
    catch(e){alert('创建游戏失败:'+e.message);}
    setStarting(false);
  };
  const loadGame=state=>{setGs(state);setView('game');};
  if(starting)return(
    <div style={{height:'100vh',display:'flex',alignItems:'center',justifyContent:'center',flexDirection:'column',gap:12}}>
      <div style={{color:'var(--gold)',fontSize:16}}>正在生成世界…</div>
      <div style={{color:'var(--fg3)',fontSize:12}}>地形生成中，请稍候</div>
    </div>
  );
  if(view==='lobby'||!gs)return<BanishedLobby onNewGame={newGame} onLoadGame={loadGame} onBack={()=>window.location.hash='#/'}/>;
  return<BanishedGameView initialState={gs} token={token} onBack={()=>setView('lobby')}/>;
}
{% endverbatim %}
{% verbatim %}
function ChatApp({user, onLogout, onUpdateUser}) {
  const [conversations, setConversations] = useState([]);
  const [activeConv, setActiveConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [inputMsg, setInputMsg] = useState('');
  const [generating, setGenerating] = useState(false);
  const [awaitingFirstChunk, setAwaitingFirstChunk] = useState(false);
  const [selectedModel, setSelectedModel] = useState('glm-4.7-flash');
  const chatEndRef = useRef(null);

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    if (activeConv) {
      loadMessages(activeConv.id);
      setSelectedModel(activeConv.model_name || 'glm-4.7-flash');
    } else {
      setMessages([]);
    }
  }, [activeConv]);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
    // Render markdown math if needed
    if (window.MathJax && window.MathJax.typesetPromise) {
      window.MathJax.typesetPromise().catch(err => console.error(err));
    }
  }, [messages, generating]);

  const loadConversations = async () => {
    try {
      const data = await F(`${API}/chat/conversations/`);
      setConversations(data);
      if (data.length > 0 && !activeConv) {
        setActiveConv(data[0]);
      }
    } catch (e) {
      showAlert('无法加载会话列表: ' + e.message);
    }
    setLoadingList(false);
  };

  const loadMessages = async (id) => {
    try {
      const data = await F(`${API}/chat/conversations/${id}/`);
      setMessages(data.messages || []);
    } catch (e) {
      showAlert('无法加载消息: ' + e.message);
      setActiveConv(null);
    }
  };

  const createNewChat = async () => {
    try {
      const newConv = await P(`${API}/chat/conversations/`, { title: 'New Chat', model_name: selectedModel });
      setConversations([newConv, ...conversations]);
      setActiveConv(newConv);
    } catch (e) {
      showAlert('无法创建新会话: ' + e.message);
    }
  };

  const deleteConversation = async (id, e) => {
    e.stopPropagation();
    const ok = await showConfirm('确定要删除此会话吗？');
    if (!ok) return;
    try {
      await F(`${API}/chat/conversations/${id}/`, { method: 'DELETE' });
      setConversations(conversations.filter(c => c.id !== id));
      if (activeConv && activeConv.id === id) {
        setActiveConv(null);
      }
    } catch (err) {
      showAlert('删除失败: ' + err.message);
    }
  };

  const sendMessage = async () => {
    if (!inputMsg.trim() || generating) return;
    const msgText = inputMsg.trim();
    setInputMsg('');
    
    let conv = activeConv;
    if (!conv) {
      try {
        conv = await P(`${API}/chat/conversations/`, { title: msgText.substring(0, 20), model_name: selectedModel });
        setConversations([conv, ...conversations]);
        setActiveConv(conv);
      } catch (err) {
        showAlert('无法创建会话: ' + err.message);
        return;
      }
    }

    const newMessage = {id: 'client-'+Date.now(), role: 'user', content: msgText};
    setMessages(prev => [...prev, newMessage]);
    setGenerating(true);
    setAwaitingFirstChunk(true);
    const assistantId = 'ast-'+Date.now();
    let assistantMsg = { id: assistantId, role: 'assistant', content: '', thinking: true };
    setMessages(prev => [...prev, assistantMsg]);

    const token = localStorage.getItem('mf_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Token ${token}`;
    
    try {
      const response = await fetch(`${API}/chat/conversations/${conv.id}/chat/`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ content: msgText, model_name: selectedModel })
      });
      
      if (!response.ok) {
        throw new Error(await response.text());
      }
      if (!response.body) {
        throw new Error('未收到响应流');
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      let buf = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop(); // keep the last partial line
        
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const dataStr = line.slice(6).trim();
          if (!dataStr) continue;
          try {
            const data = JSON.parse(dataStr);
            if (data.type === 'chunk') {
               if (awaitingFirstChunk) setAwaitingFirstChunk(false);
               assistantMsg.content += data.text;
               setMessages(prev => prev.map(m => m.id === assistantMsg.id ? {...assistantMsg, thinking:false} : m));
            } else if (data.type === 'done') {
               // Load conversations silently to get title update if it was a new chat
               setAwaitingFirstChunk(false);
               setMessages(prev => prev.map(m => m.id === assistantMsg.id ? {...assistantMsg, thinking:false} : m));
               loadConversations();
            } else if (data.type === 'error') {
               setAwaitingFirstChunk(false);
               showAlert('回复出错: ' + data.text);
            }
          } catch(err) {
            console.error('JSON parse error:', err);
          }
        }
      }
    } catch(err) {
      setAwaitingFirstChunk(false);
      showAlert('发送失败: ' + err.message);
      setMessages(prev => prev.map(m => m.id === assistantId ? {...m, thinking:false, content: m.content || '请求失败，请重试。'} : m));
    } finally {
      setGenerating(false);
      setAwaitingFirstChunk(false);
    }
  };
  
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const renderMarkdown = (text) => {
    if (!window.marked) return text;
    return {__html: window.marked.parse(text)};
  };

  return (
    <div className="dash-wrap">
      <nav className="dash-nav">
        <div style={{display:'flex',alignItems:'center',gap:12}}>
          <button className="btn btn-s" onClick={() => window.location.hash='#/'} style={{padding:6}} title="返回 MineAI 首页"><Icon name="home" size={16} /></button>
          <div className="dash-logo"><Icon name="chat" size={16} /> MineAI Chat</div>
        </div>
        <div className="dash-sw" style={{visibility:'hidden'}}></div>
        <div className="dash-right">
          <span style={{fontSize:12,color:'var(--fg3)'}}>{displayName(user)}</span>
          <button className="btn btn-s btn-sm" onClick={onLogout}>退出</button>
        </div>
      </nav>
      
      <div style={{display:'flex', height:'calc(100vh - 56px)'}}>
        
        {/* Sidebar */}
        <div style={{width:260, borderRight:'1px solid var(--border)', display:'flex', flexDirection:'column', background:'var(--bg2)'}}>
          <div style={{padding:16}}>
             <button className="btn btn-p" onClick={() => setActiveConv(null)} style={{width:'100%', display:'flex', alignItems:'center', justifyContent:'center', gap:8}}>
               <Icon name="pen" size={14} /> 新对话
             </button>
          </div>
          <div style={{flex:1, overflowY:'auto', padding:'0 12px 16px 12px'}}>
            <div style={{fontSize:11, color:'var(--fg3)', marginBottom:8, marginLeft:4, fontWeight:600}}>历史记录 (最多20条)</div>
            {loadingList ? <div style={{padding:12, fontSize:12, color:'var(--fg3)'}}>加载中...</div> :
             conversations.length === 0 ? <div style={{padding:12, fontSize:12, color:'var(--fg3)'}}>无历史记录</div> :
             conversations.map(c => (
              <div key={c.id} 
                   style={{
                     padding:'10px 12px', 
                     borderRadius:8, 
                     cursor:'pointer', 
                     marginBottom:4,
                     display:'flex',
                     alignItems:'center',
                     justifyContent:'space-between',
                     background: activeConv?.id === c.id ? 'var(--bg4)' : 'transparent',
                     color: activeConv?.id === c.id ? 'var(--fg)' : 'var(--fg2)'
                   }}
                   onClick={() => setActiveConv(c)}
                   className="conv-item">
                <div style={{overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap', fontSize:13, flex:1}}>
                  {c.title}
                </div>
                <button className="btn btn-s" 
                        onClick={(e) => deleteConversation(c.id, e)} 
                        style={{padding:4, color:'var(--red)', opacity: activeConv?.id === c.id ? 1 : 0.4}} 
                        title="删除">
                   <Icon name="trash" size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
        
        {/* Main Chat Area */}
        <div style={{flex:1, display:'flex', flexDirection:'column', background:'var(--bg)'}}>
          
          <div style={{padding:'12px 24px', borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', justifyContent:'space-between'}}>
            <div style={{fontSize:16, fontWeight:600}}>
              {activeConv ? activeConv.title : '新对话'}
            </div>
            <div>
              <select value={selectedModel} onChange={e => {
                if (!activeConv) setSelectedModel(e.target.value);
              }}
              disabled={!!activeConv}
              style={{
                background:'var(--bg3)', color:'var(--fg)', border:'1px solid var(--border)', 
                padding:'6px 12px', borderRadius:6, fontSize:13, outline:'none'
              }}>
                <option value="glm-4.7-flash">GLM-4.7 (智谱新一代模型)</option>
                <option value="glm-4.5-flash">GLM-4.5-Air (性价比模型)</option>
              </select>
            </div>
          </div>
          
          <div style={{flex:1, overflowY:'auto', padding:'24px 0'}}>
            <div style={{maxWidth:768, margin:'0 auto', padding:'0 24px'}}>
              {messages.length === 0 ? (
                <div style={{textAlign:'center', marginTop:100, color:'var(--fg3)'}}>
                  <Icon name="bot" size={48} style={{opacity:0.2, marginBottom:16}} />
                  <h3 style={{fontSize:20, fontWeight:500, color:'var(--fg)'}}>今天能帮您什么？</h3>
                  <p style={{marginTop:8}}>开始对话，体验大模型的强大能力</p>
                </div>
              ) : (
                messages.map((m, idx) => (
                  <div key={m.id || idx} style={{
                    display:'flex', 
                    gap:16, 
                    marginBottom:32,
                    justifyContent: m.role==='user'?'flex-end':'flex-start'
                  }}>
                    {m.role === 'assistant' && (
                      <div style={{width:32, height:32, borderRadius:'50%', background:'var(--gold)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, color:'#000'}}>
                        <Icon name="bot" size={18} />
                      </div>
                    )}
                    <div style={{
                      maxWidth: '85%',
                      minWidth: '50px',
                      background: m.role==='user' ? 'var(--bg3)' : 'transparent',
                      padding: m.role==='user' ? '12px 16px' : '6px 0',
                      borderRadius: 12,
                      fontSize: 15,
                      lineHeight: 1.6,
                      color: 'var(--fg)'
                    }}>
                      {m.role === 'user' ? (
                        <div style={{whiteSpace:'pre-wrap'}}>{m.content}</div>
                      ) : m.thinking && !m.content ? (
                        <div style={{display:'inline-flex', alignItems:'center', gap:10, color:'var(--fg2)', fontSize:14}}>
                          <div className="spinner" style={{width:14,height:14,borderWidth:2}}></div>
                          <span>AI 正在思考...</span>
                        </div>
                      ) : (
                        <div className="markdown-body" dangerouslySetInnerHTML={renderMarkdown(m.content)} />
                      )}
                    </div>
                    {m.role === 'user' && (
                      <div style={{width:32, height:32, borderRadius:'50%', background:'var(--bg4)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, border:'1px solid var(--border)'}}>
                        <Icon name="user" size={16} />
                      </div>
                    )}
                  </div>
                ))
              )}
              <div ref={chatEndRef} />
            </div>
          </div>
          
          <div style={{padding:'0 24px 24px'}}>
             <div style={{
               maxWidth: 768, margin: '0 auto', background:'var(--bg2)', 
               borderRadius: 16, border: '1px solid var(--border)', padding: '12px 16px',
               display: 'flex', flexDirection: 'column', position: 'relative'
             }}>
               <textarea 
                 value={inputMsg}
                 onChange={e => setInputMsg(e.target.value)}
                 onKeyDown={handleKeyDown}
                 placeholder={generating ? "等待回复中..." : "输入消息，Shift+Enter换行..."}
                 disabled={generating}
                 style={{
                   width: '100%', minHeight: 48, maxHeight: 200, background: 'transparent',
                   border: 'none', color: 'var(--fg)', fontSize: 15, resize: 'none',
                   outline: 'none', lineHeight: 1.5, paddingBottom: 32
                 }}
               />
               <button 
                 className={`btn ${generating ? 'btn-d' : 'btn-p'}`}
                 onClick={sendMessage}
                 disabled={!inputMsg.trim() || generating}
                 style={{
                   position: 'absolute', right: 12, bottom: 12, width: 32, height: 32,
                   padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                   borderRadius: '50%'
                 }}
                 title="发送消息"
               >
                 {generating ? <div className="spinner" style={{width:16,height:16,borderWidth:2}}></div> : <Icon name="rocket" size={16} />}
               </button>
             </div>
             <div style={{textAlign:'center', marginTop:8, fontSize:11, color:'var(--fg3)'}}>
               {generating ? (awaitingFirstChunk ? '消息已发送，AI 正在思考中...' : 'AI 正在生成回复...') : 'AI 会产生错误信息，请注意核实。'}
             </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
{% endverbatim %}

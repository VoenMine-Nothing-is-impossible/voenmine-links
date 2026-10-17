import { useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8096';

const PILLS = [
  ['expire', '⏳ Срок жизни'],
  ['paid', '💳 Платный доступ'],
  ['pass', '🔒 Пароль на ссылку'],
  ['tags', '🏷️ Метки'],
  ['preview', '👁️ Превью'],
  ['limit', '🔢 Лимит переходов'],
  ['slug', '✏️ Своё окончание'],
  ['qr', '📷 QR-код'],
  ['track', '📊 Трекеры'],
  ['where', '🧭 Куда ведёт'],
  ['webhook', '🔔 Вебхук на клик'],
];

export default function Home() {
  const [target, setTarget] = useState('');
  const [open, setOpen] = useState({ qr: true });
  const [f, setF] = useState({});
  const [out, setOut] = useState(null);
  const [err, setErr] = useState('');
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const toggle = (k) => setOpen((p) => ({ ...p, [k]: !p[k] }));

  async function shorten() {
    setErr(''); setOut(null);
    try {
      const body = {
        target_url: target,
        slug: (f.slug || '').toUpperCase() || null,
        fallback_url: f.fallback || null,
        password: f.pass || null,
        max_clicks: f.max ? parseInt(f.max) : null,
        show_preview: !!f.showPreview,
        og_title: f.ogTitle || null,
        og_description: f.ogDesc || null,
        og_image: f.ogImage || null,
        tags: (f.tags || '').split(',').map((s) => s.trim()).filter(Boolean),
        trackers: { ga: f.ga || null, fb: f.fb || null, ym: f.ym || null },
        webhook_url: f.webhook || null,
        price_amount: f.price ? parseFloat(f.price) : null,
      };
      if (f.expires) body.expires_at = new Date(f.expires).toISOString();
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : '';
      const r = await fetch(`${API}/api/links`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
        body: JSON.stringify(body),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || ('HTTP ' + r.status));
      setOut(j);
    } catch (e) { setErr(String(e.message || e)); }
  }

  return (
    <section className="hero">
      <h1>🔗 VoenMine Links</h1>
      <p className="sub">Свой сократитель ссылок для самостоятельного хостинга. Быстро. Приватно. По-своему.</p>
      <div className="shorten-box">
        <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Вставьте длинную ссылку…" />
        <button className="btn primary" onClick={shorten}>✂️ Сократить</button>
      </div>
      {out && (
        <div className="result">
          Готово: <a href={`${API}/${out.code}`} target="_blank" rel="noreferrer">{out.short_url}</a>
          <div className="muted small">/{out.code} → {out.target_url} (повтор тех же параметров вернёт этот же код)</div>
          {open.qr && (
            <div style={{ marginTop: 10 }}>
              <img src={`${API}/qr/${out.code}.png`} width="140" height="140" alt="QR" />
              <div><a href={`${API}/qr/${out.code}.png`} download>Скачать PNG</a> · <a href={`${API}/qr/${out.code}.svg`} download>SVG</a></div>
            </div>
          )}
        </div>
      )}
      {err && <div className="error">{err}</div>}
      <div className="pills">
        {PILLS.map(([k, label]) => (
          <button key={k} className={'pill' + (open[k] ? ' on' : '')} onClick={() => toggle(k)}>{label}</button>
        ))}
      </div>
      <div className="panes">
        {open.expire && <div className="pane"><label>Срок жизни</label><input type="datetime-local" onChange={(e) => set('expires', e.target.value)} /><div className="muted small">По истечении — страница «ссылка истекла».</div></div>}
        {open.paid && <div className="pane"><label>Платный доступ, ₽ (YooKassa)</label><input placeholder="например, 49" onChange={(e) => set('price', e.target.value)} /></div>}
        {open.pass && <div className="pane"><label>Пароль на ссылку</label><input type="password" placeholder="необязательно" onChange={(e) => set('pass', e.target.value)} /><div className="muted small">Хранится только хеш bcrypt.</div></div>}
        {open.tags && <div className="pane"><label>Метки (через запятую)</label><input placeholder="promo, blog, qr" onChange={(e) => set('tags', e.target.value)} /></div>}
        {open.preview && <div className="pane"><label><input type="checkbox" onChange={(e) => set('showPreview', e.target.checked)} /> Показывать превью перед редиректом</label><input placeholder="OG-заголовок" onChange={(e) => set('ogTitle', e.target.value)} /><input placeholder="OG-описание" onChange={(e) => set('ogDesc', e.target.value)} /><input placeholder="OG-картинка https://…" onChange={(e) => set('ogImage', e.target.value)} /></div>}
        {open.limit && <div className="pane"><label>Лимит переходов</label><input type="number" placeholder="например, 100" onChange={(e) => set('max', e.target.value)} /><div className="muted small">Счётчик атомарный (Redis INCR).</div></div>}
        {open.slug && <div className="pane"><label>Своё окончание (мин. 7 символов, A–Z и 0–9)</label><input placeholder="PROMO2026" maxLength={64} style={{ textTransform: 'uppercase' }} onChange={(e) => set('slug', e.target.value)} /><div className="muted small">api, admin, static… запрещены.</div></div>}
        {open.qr && <div className="pane"><label>QR-код</label><div className="muted small">Автогенерация: /qr/КОД.png и .svg — для скачивания.</div></div>}
        {open.track && <div className="pane"><label>Трекеры + резервный адрес</label><input placeholder="GA ID (G-…)" onChange={(e) => set('ga', e.target.value)} /><input placeholder="FB Pixel ID" onChange={(e) => set('fb', e.target.value)} /><input placeholder="Yandex Metrika ID" onChange={(e) => set('ym', e.target.value)} /><input placeholder="Резервный адрес https://…" onChange={(e) => set('fallback', e.target.value)} /></div>}
        {open.where && <div className="pane"><label>Куда ведёт</label><div className="muted small">Откройте {API}/КОД — превью/пароль/оплата покажут адрес до перехода.</div></div>}
        {open.webhook && <div className="pane"><label>Вебхук на клик</label><input placeholder="https://ваш-сервер/hook" onChange={(e) => set('webhook', e.target.value)} /><div className="muted small">POST: timestamp, IP/гео, UA, referrer. Ретраи ×5.</div></div>}
      </div>
      <div className="features">
        <div className="card"><b>⚡ Быстро</b><span>Кэш горячих ссылок в Redis</span></div>
        <div className="card"><b>🛡️ Приватно</b><span>Пароли — bcrypt, JWT, API-ключи</span></div>
        <div className="card"><b>📈 Аналитика</b><span>Гео, устройства, браузеры, referrer</span></div>
        <div className="card"><b>🐳 Self-hosted</b><span>Docker :8096 + Traefik + Postgres/Redis</span></div>
      </div>
    </section>
  );
}

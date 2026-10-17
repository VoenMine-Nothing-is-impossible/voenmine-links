import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8096';

export default function Dashboard() {
  const [links, setLinks] = useState([]);
  const [stats, setStats] = useState(null);
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('all');
  const [tag, setTag] = useState('');
  const router = useRouter();
  const tok = () => (typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '');

  async function load() {
    if (!tok()) { router.push('/login'); return; }
    const u = new URLSearchParams({ status });
    if (q) u.set('q', q);
    if (tag) u.set('tag', tag);
    const r = await fetch(`${API}/api/links?` + u, { headers: { Authorization: 'Bearer ' + tok() } });
    if (r.status === 401) { router.push('/login'); return; }
    setLinks(await r.json());
  }

  useEffect(() => { load(); }, []);

  async function showStats(code) {
    const r = await fetch(`${API}/api/links/${code}/stats`, { headers: { Authorization: 'Bearer ' + tok() } });
    setStats({ code, ...(await r.json()) });
    window.scrollTo(0, document.body.scrollHeight);
  }

  async function del(code) {
    if (!confirm('Удалить /' + code + '?')) return;
    await fetch(`${API}/api/links/${code}`, { method: 'DELETE', headers: { Authorization: 'Bearer ' + tok() } });
    load();
  }

  return (
    <section>
      <h2>Личный кабинет</h2>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '16px 0' }}>
        <input placeholder="Поиск…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">Все</option>
          <option value="active">Активные</option>
          <option value="expired">Истекшие</option>
          <option value="limited">Лимит исчерпан</option>
        </select>
        <input placeholder="Метка…" value={tag} onChange={(e) => setTag(e.target.value)} />
        <button className="btn small" onClick={load}>Обновить</button>
      </div>
      {links.map((l) => (
        <div key={l.code} className="link-card">
          <div><b>/{l.code}</b> <span className="muted">{l.is_active ? '🟢' : '🔴'} {l.clicks_count} кликов{l.max_clicks ? '/' + l.max_clicks : ''}</span></div>
          <div className="mono small">{l.target_url}</div>
          <div className="muted small">{l.short_url} {l.has_password ? '🔒' : ''} {l.is_paid ? '💳 ' + l.price_amount : ''} {(l.tags || []).map((t) => '#' + t).join(' ')}</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <a className="btn small" href={`${API}/qr/${l.code}.png`} target="_blank" rel="noreferrer">QR PNG</a>
            <button className="btn small" onClick={() => showStats(l.code)}>📊 Статистика</button>
            <button className="btn small danger" onClick={() => del(l.code)}>Удалить</button>
          </div>
        </div>
      ))}
      {stats && (
        <div className="pane">
          <h3>/{stats.code} — всего {stats.total}</h3>
          <p className="muted">По дням: {(stats.by_day || []).map((d) => d.date + ': ' + d.count).join(', ') || '—'}</p>
          <p className="muted">Браузеры: {JSON.stringify(stats.by_browser)}</p>
          <p className="muted">ОС: {JSON.stringify(stats.by_os)}</p>
          <p className="muted">Устройства: {JSON.stringify(stats.by_device)}</p>
          <p className="muted">Гео: {JSON.stringify(stats.by_country)}</p>
          <p className="muted">Источники: {JSON.stringify(stats.by_referrer)}</p>
        </div>
      )}
    </section>
  );
}

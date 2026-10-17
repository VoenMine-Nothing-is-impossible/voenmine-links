import { useState } from 'react';
import { useRouter } from 'next/router';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8096';

export default function Login() {
  const [u, setU] = useState('');
  const [p, setP] = useState('');
  const [err, setErr] = useState('');
  const router = useRouter();
  async function go() {
    setErr('');
    const r = await fetch(`${API}/api/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: u, password: p }) });
    const j = await r.json();
    if (r.ok) { localStorage.setItem('token', j.access_token); router.push('/dashboard'); }
    else setErr(j.detail || 'Ошибка');
  }
  return (
    <section className="gate">
      <h2>Вход</h2>
      <div className="form">
        <input placeholder="Логин" value={u} onChange={(e) => setU(e.target.value)} />
        <input type="password" placeholder="Пароль" value={p} onChange={(e) => setP(e.target.value)} />
        <button className="btn primary" onClick={go}>Войти</button>
        {err && <div className="error">{err}</div>}
      </div>
    </section>
  );
}

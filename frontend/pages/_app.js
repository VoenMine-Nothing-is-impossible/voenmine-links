import '../styles/globals.css';
import Link from 'next/link';

export default function App({ Component, pageProps }) {
  return (
    <>
      <header className="topbar">
        <Link className="logo" href="/">🔗 VoenMine <span>Links</span></Link>
        <nav className="nav">
          <Link href="/">Главная</Link>{' '}
          <Link href="/dashboard">Кабинет</Link>{' '}
          <Link href="/login">Войти</Link>
        </nav>
      </header>
      <main className="wrap">
        <Component {...pageProps} />
      </main>
      <footer className="footer">©2022 - 2026 VoenMine | Нет ничего невозможного!</footer>
    </>
  );
}

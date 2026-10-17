/* VoenMine Links — общий JS: auth-зона, создание ссылок, проверка «куда ведёт». */
(function () {
  const $ = (id) => document.getElementById(id);

  function token() { return localStorage.getItem('token') || ''; }
  function authHeaders(extra) {
    const h = Object.assign({'Content-Type': 'application/json'}, extra || {});
    if (token()) h['Authorization'] = 'Bearer ' + token();
    return h;
  }

  // шапка: вход/кабинет
  const area = $('auth-area');
  if (area) {
    if (token()) area.innerHTML = '<a href="/dashboard">Кабинет</a> <a href="#" id="logout">Выйти</a>';
    else area.innerHTML = '<a href="/login">Войти</a> <a href="/register">Регистрация</a>';
    const lo = $('logout');
    if (lo) lo.onclick = (e) => { e.preventDefault(); localStorage.removeItem('token'); location.reload(); };
  }

  const btn = $('btn-shorten');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    const err = $('error'), res = $('result');
    err.classList.add('hidden'); res.classList.add('hidden');
    const target = ($('target') || {}).value || '';
    if (!target) { err.textContent = 'Вставьте ссылку'; err.classList.remove('hidden'); return; }
    const tagsRaw = ($('f-tags') || {}).value || '';
    const body = {
      target_url: target,
      slug: (($('f-slug') || {}).value || '').trim().toUpperCase() || null,
      fallback_url: ($('f-fallback') || {}).value || null,
      password: ($('f-pass') || {}).value || null,
      max_clicks: parseInt((($('f-max') || {}).value || '')) || null,
      show_preview: !!($('f-show-preview') || {}).checked,
      og_title: ($('f-og-title') || {}).value || null,
      og_description: ($('f-og-desc') || {}).value || null,
      og_image: ($('f-og-image') || {}).value || null,
      tags: tagsRaw.split(',').map((s) => s.trim()).filter(Boolean),
      trackers: {ga: ($('f-ga') || {}).value || null, fb: ($('f-fb') || {}).value || null, ym: ($('f-ym') || {}).value || null},
      webhook_url: ($('f-webhook') || {}).value || null,
      price_amount: parseFloat((($('f-price') || {}).value || '')) || null,
    };
    const exp = ($('f-expires') || {}).value;
    if (exp) body.expires_at = new Date(exp).toISOString();
    btn.disabled = true; btn.textContent = 'Сокращаем…';
    try {
      const r = await fetch('/api/links', {method: 'POST', headers: authHeaders(), body: JSON.stringify(body)});
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.detail || ('HTTP ' + r.status));
      const wantQR = ($('f-qr') || {}).checked;
      res.innerHTML = 'Готово: <a href="/' + j.code + '" target="_blank">' + j.short_url + '</a>'
        + '<div class="muted small">/' + j.code + ' → ' + j.target_url + ' (повторное создание тех же параметров вернёт этот же код)</div>'
        + (wantQR ? '<div style="margin-top:10px"><img src="/qr/' + j.code + '.png" width="140" height="140" alt="QR"><div><a href="/qr/' + j.code + '.png" download>Скачать PNG</a> · <a href="/qr/' + j.code + '.svg" download>SVG</a></div></div>' : '');
      res.classList.remove('hidden');
    } catch (e) {
      err.textContent = 'Ошибка: ' + e.message;
      err.classList.remove('hidden');
    } finally { btn.disabled = false; btn.textContent = '✂️ Сократить'; }
  });

  const bc = $('btn-check');
  if (bc) bc.addEventListener('click', async () => {
    const code = (($('f-check') || {}).value || '').trim().toUpperCase();
    const out = $('check-out');
    if (!code) return;
    // публичной проверки нет — пробуем HEAD через редирект-страницу превью? Покажем ссылку.
    out.innerHTML = 'Откройте <a href="/' + code + '" target="_blank">/' + code + '</a> — сервис покажет превью/пароль/оплату либо сразу перенаправит. Целевой адрес виден на странице превью.';
  });
})();

/**
 * app-nav.js — Mostra link Admin na sidebar para usuários admin
 * Incluir após clerk-auth.js. Requer elemento #admin-link-wrap no nav.
 */
(async function () {
  const API_BASE = window.location.origin;
  const wrap = document.getElementById('admin-link-wrap');
  if (!wrap) return;

  const tryInject = () => {
    if (!window.authFetch || !window.ClerkAuth?.signedIn) return false;
    return true;
  };

  for (let i = 0; i < 50; i++) {
    if (tryInject()) break;
    await new Promise(r => setTimeout(r, 100));
  }

  try {
    const res = await authFetch(API_BASE + '/api/me');
    const me = await res.json();
    if (me.isAdmin) wrap.style.display = 'block';
    else wrap.remove();
  } catch (_) {
    wrap.remove();
  }
})();

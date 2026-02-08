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
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/93780d09-6b5a-42a9-b230-9dd7e72f883b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'app-nav.js:api/me',message:'app_nav_me_response',data:{status:res.status,ok:res.ok,contentType:res.headers.get('content-type')},hypothesisId:'H3',timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    const me = await res.json();
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/93780d09-6b5a-42a9-b230-9dd7e72f883b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'app-nav.js:me_parsed',message:'app_nav_me_parsed',data:{isAdmin:!!me.isAdmin},hypothesisId:'H3',timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    if (me.isAdmin) wrap.style.display = 'block';
    else wrap.remove();
  } catch (e) {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/93780d09-6b5a-42a9-b230-9dd7e72f883b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'app-nav.js:catch',message:'app_nav_catch',data:{error:String(e.message||e)},hypothesisId:'H3',timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    wrap.remove();
  }
})();

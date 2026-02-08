/**
 * Clerk Auth - inicialização e helper fetch autenticado
 * Para páginas protegidas: carrega Clerk, monta SignIn/UserButton e oferece authFetch.
 */
(function () {
  const API_BASE = window.location.origin;

  /** Parse JSON seguro: evita erro "Unexpected token" quando backend retorna HTML/500. */
  window.safeJson = async function (res) {
    const text = await res.text();
    if (!text || !text.trim()) return {};
    const ct = (res.headers.get('content-type') || '').toLowerCase();
    if (!ct.includes('application/json') && !/^\s*[{[]/.test(text)) {
      throw new Error('O servidor retornou uma resposta inválida. Verifique se o backend está funcionando.');
    }
    try {
      return JSON.parse(text);
    } catch (_) {
      throw new Error('O servidor retornou uma resposta inválida. Verifique se o backend está funcionando.');
    }
  };

  /** Envolve fetch para que res.json() lance erro amigável em respostas inválidas. */
  function wrapAuthFetch(fn) {
    return async function (url, opts) {
      const res = await fn(url, opts);
      const origJson = res.json.bind(res);
      res.json = async function () {
        try {
          return await origJson();
        } catch (e) {
          throw new Error('O servidor retornou uma resposta inválida. Verifique se o backend está funcionando.');
        }
      };
      return res;
    };
  }

  // Busca config do backend e inicializa Clerk
  async function initClerk() {
    const res = await fetch(`${API_BASE}/api/clerk-config`);
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/93780d09-6b5a-42a9-b230-9dd7e72f883b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'clerk-auth.js:clerk-config',message:'clerk_config_response',data:{status:res.status,ok:res.ok,contentType:res.headers.get('content-type')},hypothesisId:'H1',timestamp:Date.now()})}).catch(function(){});
    // #endregion
    const config = await window.safeJson(res);
    const pk = config.publishableKey?.trim();
    const frontendApi = config.frontendApi?.trim();

    if (!pk || !frontendApi) {
      console.warn('Clerk não configurado. Rodando sem autenticação.');
      window.ClerkAuth = {
        ready: true,
        signedIn: false,
        authFetch: wrapAuthFetch((url, opts) => fetch(url, opts)),
        getUserName: () => 'Visitante',
      };
      return;
    }

    return new Promise((resolve) => {
      const script = document.createElement('script');
      script.async = true;
      script.crossOrigin = 'anonymous';
      script.dataset.clerkPublishableKey = pk;
      script.src = `${frontendApi}/npm/@clerk/clerk-js@5/dist/clerk.browser.js`;
      script.type = 'text/javascript';
      script.onload = async () => {
        const dashboardUrl = `${API_BASE}/frontend/dashboard.html`;
        await Clerk.load({ signInFallbackRedirectUrl: dashboardUrl, signUpFallbackRedirectUrl: dashboardUrl });
        const signedIn = !!Clerk.user;
          window.ClerkAuth = {
            ready: true,
            signedIn,
            clerk: Clerk,
            authFetch: wrapAuthFetch(async (url, opts = {}) => {
              const token = Clerk.session ? await Clerk.session.getToken() : null;
              const headers = { ...opts.headers };
              if (token) headers['Authorization'] = `Bearer ${token}`;
              return fetch(url, { ...opts, headers });
            }),
            getUserName: () => (Clerk.user ? Clerk.user.firstName || Clerk.user.emailAddresses?.[0]?.emailAddress || 'Usuário' : ''),
          };
        resolve(window.ClerkAuth);
      };
      document.head.appendChild(script);
    });
  }

  // Inicializa e monta UI (SignIn ou UserButton)
  window.initClerkAuth = async function (opts = {}) {
    const { signInContainerId = 'clerk-signin', userButtonContainerId = 'clerk-user-button', appContentId = 'app-content' } = opts;

    const signInEl = document.getElementById(signInContainerId);
    const appContent = document.getElementById(appContentId);

    // Esconde o app até decidir: mostrar SignIn ou dashboard
    if (appContent) appContent.style.display = 'none';
    if (signInEl) {
      signInEl.style.display = 'flex';
      signInEl.innerHTML = '<p style="margin:auto;color:var(--gray);">Carregando…</p>';
    }

    try {
      await initClerk();
    } catch (err) {
      console.error('Clerk init error:', err);
      if (appContent) appContent.style.display = '';
      if (signInEl) { signInEl.style.display = 'none'; signInEl.innerHTML = ''; }
      window.ClerkAuth = { ready: true, signedIn: false, authFetch: wrapAuthFetch((u, o) => fetch(u, o)), getUserName: () => 'Visitante' };
      return;
    }

    const auth = window.ClerkAuth;
    if (!auth) return;

    const userButtonEl = document.getElementById(userButtonContainerId);

    if (auth.signedIn) {
      if (userButtonEl && auth.clerk) auth.clerk.mountUserButton(userButtonEl);
      if (appContent) appContent.style.display = '';
      if (signInEl) { signInEl.style.display = 'none'; signInEl.innerHTML = ''; }
      const userSpan = document.querySelector('.app-user');
      if (userSpan && auth.getUserName()) userSpan.textContent = `Olá, ${auth.getUserName()}`;
    } else if (auth.clerk) {
      signInEl.innerHTML = ''; // Remove "Carregando..."
      const dashboardUrl = `${API_BASE}/frontend/dashboard.html`;
      if (signInEl) auth.clerk.mountSignIn(signInEl, { signInFallbackRedirectUrl: dashboardUrl, signUpFallbackRedirectUrl: dashboardUrl });
      if (signInEl) signInEl.style.display = 'flex';
      if (appContent) appContent.style.display = 'none';
      if (userButtonEl) userButtonEl.style.display = 'none';
    } else {
      // Clerk não configurado — modo dev, mostra o app
      if (appContent) appContent.style.display = '';
      if (signInEl) { signInEl.style.display = 'none'; signInEl.innerHTML = ''; }
    }

    return auth;
  };

  // Helper global para fetch autenticado (com json() seguro)
  window.authFetch = function (url, opts) {
    if (window.ClerkAuth?.authFetch) return window.ClerkAuth.authFetch(url, opts);
    return wrapAuthFetch((u, o) => fetch(u, o))(url, opts);
  };
})();

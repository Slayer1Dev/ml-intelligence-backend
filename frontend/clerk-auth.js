/**
 * Clerk Auth - inicialização e helper fetch autenticado
 * Para páginas protegidas: carrega Clerk, monta SignIn/UserButton e oferece authFetch.
 */
(function () {
  const API_BASE = window.location.origin;

  // Busca config do backend e inicializa Clerk
  async function initClerk() {
    const res = await fetch(`${API_BASE}/api/clerk-config`);
    const config = await res.json();
    const pk = config.publishableKey?.trim();
    const frontendApi = config.frontendApi?.trim();

    if (!pk || !frontendApi) {
      console.warn('Clerk não configurado. Rodando sem autenticação.');
      window.ClerkAuth = {
        ready: true,
        signedIn: false,
        authFetch: (url, opts = {}) => fetch(url, opts),
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
            authFetch: async (url, opts = {}) => {
              const token = Clerk.session ? await Clerk.session.getToken() : null;
              const headers = { ...opts.headers };
              if (token) headers['Authorization'] = `Bearer ${token}`;
              return fetch(url, { ...opts, headers });
            },
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
      window.ClerkAuth = { ready: true, signedIn: false, authFetch: (u, o) => fetch(u, o), getUserName: () => 'Visitante' };
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

  // Helper global para fetch autenticado
  window.authFetch = function (url, opts) {
    if (window.ClerkAuth?.authFetch) return window.ClerkAuth.authFetch(url, opts);
    return fetch(url, opts);
  };
})();

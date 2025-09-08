(function () {
    if (!('pushState' in window.history)) return;

    const main = document.querySelector('main');
    if (!main) return;

    let isNavigating = false;

    // Set active class on nav links
    const updateActiveNav = (path) => {
        document.querySelectorAll('.header-nav a, .footer-right a').forEach((a) => {
            const isActive = a.getAttribute('href') === path;
            a.classList.toggle('is-active', isActive);
            a.setAttribute('aria-current', isActive ? 'page' : 'false');
        });
    };

    // Handle navigation to a new URL
    const navigate = async (url, replace) => {
        if (isNavigating) return;
        isNavigating = true;
        try {
            // Request the new page
            const res = await fetch(url);
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const text = await res.text();

            // Parse the response and extract <main> and <title>
            const parser = new DOMParser();
            const doc = parser.parseFromString(text, 'text/html');
            const newMain = doc.querySelector('main');
            const newTitle = doc.querySelector('title');

            // If we got valid content, swap it in
            if (!newMain) {
                window.location.assign(url);
                return;
            }

            // Apply body content and title
            main.innerHTML = newMain.innerHTML;
            // Re-initialize Lucide icons for newly injected content
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
            if (newTitle) document.title = newTitle.textContent;
            const path = new URL(url, window.location.origin).pathname;
            updateActiveNav(path);
            if (replace) history.replaceState({}, '', url); else history.pushState({}, '', url);
            window.scrollTo(0, 0); // A11Y: move focus to top on navigation
        } catch (err) {
            console.error('[SPA] navigate failed:', err);
            window.location.assign(url);
        } finally {
            isNavigating = false;
        }
    };

    // Intercept link clicks
    document.addEventListener('click', (e) => {
        const a = e.target.closest('a');
        if (!a) return;
        const href = a.getAttribute('href');
        if (!href) return;

        const url = new URL(href, window.location.origin);
        const isExternal = url.origin !== window.location.origin;
        const hasTarget = a.target && a.target !== '' && a.target !== '_self';
        const isDownload = a.hasAttribute('download');
        const isHashOnly = url.pathname === window.location.pathname && url.hash && url.hash !== '';
        const modified = e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0;

        if (isExternal || hasTarget || isDownload || isHashOnly || modified) return;

        e.preventDefault();
        navigate(url.pathname + url.search);
    });

    // Handle back/forward navigation
    window.addEventListener('popstate', () => {
        navigate(window.location.pathname + window.location.search, true);
    });

    updateActiveNav(window.location.pathname);
})();
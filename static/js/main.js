/* ═══════════════════════════════════════════════════════════════
   Imagine Inventory — Main JavaScript (v9)
   Comportements conservés + petites touches d'ergonomie :
   - fermeture auto des messages flash (5 s)
   - fermeture du menu mobile au clic sur un lien
   - défilement de la sidebar jusqu'à l'élément actif
   - ombre de la recherche collante au défilement
   ═══════════════════════════════════════════════════════════════ */

// Keep fixed sheets/modals inside the actually visible area when the iOS/Android
// on-screen keyboard opens or the browser chrome changes height.
(function syncVisualViewport() {
    const root = document.documentElement;
    const update = () => {
        const vv = window.visualViewport;
        const height = vv ? vv.height : window.innerHeight;
        const offsetTop = vv ? vv.offsetTop : 0;
        root.style.setProperty('--app-visible-height', Math.max(0, Math.round(height)) + 'px');
        root.style.setProperty('--app-visible-top', Math.max(0, Math.round(offsetTop)) + 'px');
    };
    update();
    window.addEventListener('resize', update, { passive: true });
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', update, { passive: true });
        window.visualViewport.addEventListener('scroll', update, { passive: true });
    }
})();

document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss flash messages after 5 seconds
    const flashes = document.querySelectorAll('.flash-message');
    flashes.forEach(f => {
        setTimeout(() => {
            f.style.opacity = '0';
            f.style.transform = 'translateX(24px)';
            f.style.transition = 'all 0.3s ease';
            setTimeout(() => f.remove(), 300);
        }, 5000);
    });

    // Sidebar close on mobile when clicking a nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const sb = document.getElementById('sidebar');
            if (!sb) return;
            sb.classList.remove('open');
            if (document.body.classList.contains('sb-open')) {
                const scrollY = parseInt(document.body.style.top || '0', 10) * -1;
                document.body.classList.remove('sb-open');
                document.body.style.top = '';
                document.body.style.position = '';
                if (!isNaN(scrollY)) window.scrollTo(0, scrollY);
            }
        });
    });

    // Faire défiler la sidebar jusqu'à l'entrée active (desktop + mobile)
    const active = document.querySelector('.sidebar-nav .nav-item.active');
    if (active) {
        try { active.scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
    }

    // Ombre portée de la barre de recherche collante quand on défile
    const search = document.querySelector('.search-section');
    if (search) {
        const onScroll = () => {
            search.style.boxShadow = window.scrollY > 24
                ? '0 10px 28px rgba(11,29,58,.14)'
                : '';
        };
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    if (sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !(e.target.closest && e.target.closest('.menu-toggle'))) {
        sidebar.classList.remove('open');
        if (document.body.classList.contains('sb-open')) {
            const scrollY = parseInt(document.body.style.top || '0', 10) * -1;
            document.body.classList.remove('sb-open');
            document.body.style.top = '';
            document.body.style.position = '';
            if (!isNaN(scrollY)) window.scrollTo(0, scrollY);
        }
    }
});

/* ═══════════════════════════════════════
   Imagine Inventory — Main JavaScript
   ═══════════════════════════════════════ */

// Auto-dismiss flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
    const flashes = document.querySelectorAll('.flash-message');
    flashes.forEach(f => {
        setTimeout(() => {
            f.style.opacity = '0';
            f.style.transform = 'translateX(100%)';
            f.style.transition = 'all 0.3s ease';
            setTimeout(() => f.remove(), 300);
        }, 5000);
    });

    // Sidebar close on mobile when clicking a nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            document.getElementById('sidebar')?.classList.remove('open');
        });
    });
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    if (sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !e.target.classList.contains('menu-toggle')) {
        sidebar.classList.remove('open');
    }
});

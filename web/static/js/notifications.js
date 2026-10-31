/**
 * ScholarPilot AI - Unified Notification Center Engine (Navbar Bell & Dropdown)
 * Zero Emojis Constraint: Strictly Lucide SVG icons.
 */

let currentDropdownCategory = 'all';

async function fetchNotificationUnreadCount() {
    try {
        const res = await fetch('/api/notifications/unread-count');
        if (!res.ok) return;
        const data = await res.json();
        const count = data.unread_count || 0;
        updateBadgeUI(count);
    } catch (e) {
        console.warn('Notification count check failed:', e);
    }
}

function updateBadgeUI(count) {
    const badges = document.querySelectorAll('#globalNotifBadge, #notifBadge');
    badges.forEach(badge => {
        if (!badge) return;
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.remove('hidden');
        } else {
            badge.textContent = '0';
            badge.classList.add('hidden');
        }
    });

    const pill = document.getElementById('dropdownUnreadPill');
    if (pill) {
        pill.textContent = count > 0 ? `${count} جديد` : 'لا تنبيهات جديدة';
    }
}

function toggleUnifiedNotifDropdown(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    const menu = document.getElementById('unifiedNotifDropdown') || document.getElementById('notificationsMenu');
    if (!menu) return;

    const isClosed = menu.classList.contains('hidden');
    // Close other open popovers if any
    document.querySelectorAll('.sp-dropdown-menu').forEach(el => el.classList.add('hidden'));

    if (isClosed) {
        menu.classList.remove('hidden');
        loadDropdownNotifs(currentDropdownCategory);
    } else {
        menu.classList.add('hidden');
    }
}

async function loadDropdownNotifs(category = 'all') {
    const list = document.getElementById('unifiedDropdownList') || document.getElementById('notificationsList');
    if (!list) return;

    list.innerHTML = `
        <div class="py-8 text-center text-slate-400 dark:text-slate-500">
            <i data-lucide="loader-2" class="w-5 h-5 mx-auto animate-spin mb-2 text-blue-500"></i>
            <p class="text-xs">جاري تحميل أحدث التنبيهات...</p>
        </div>
    `;
    if (window.lucide) lucide.createIcons();

    try {
        let url = '/api/notifications?limit=6';
        if (category && category !== 'all') {
            url += `&category=${encodeURIComponent(category)}`;
        }
        const res = await fetch(url);
        if (!res.ok) throw new Error('Network error');
        const data = await res.json();
        const items = data.notifications || [];

        if (items.length === 0) {
            list.innerHTML = `
                <div class="py-8 text-center text-slate-400 dark:text-slate-500">
                    <i data-lucide="check-circle" class="w-8 h-8 mx-auto mb-2 text-emerald-500/80"></i>
                    <p class="text-xs font-semibold text-slate-700 dark:text-slate-300">أنت على اطلاع بكل جديد</p>
                    <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">لا توجد تنبيهات حالية في هذا القسم.</p>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
            return;
        }

        list.innerHTML = items.map(n => renderDropdownItem(n)).join('');
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        list.innerHTML = `
            <div class="py-6 text-center text-rose-500 text-xs">
                <i data-lucide="alert-triangle" class="w-5 h-5 mx-auto mb-1 text-rose-500"></i>
                <p>تعذر تحميل التنبيهات حالياً.</p>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
    }
}

function renderDropdownItem(n) {
    const isUnread = !n.is_read;
    const cat = n.category || 'system';
    
    // Category visual config
    let catIcon = 'bell';
    let catColor = 'text-blue-500 bg-blue-50 dark:bg-blue-950/50 border-blue-200 dark:border-blue-900/60';
    let catLabel = 'تنبيه';

    if (cat === 'scholarship') {
        catIcon = 'graduation-cap';
        catColor = 'text-indigo-500 bg-indigo-50 dark:bg-indigo-950/50 border-indigo-200 dark:border-indigo-900/60';
        catLabel = 'منحة';
    } else if (cat === 'community') {
        catIcon = 'users';
        catColor = 'text-purple-500 bg-purple-50 dark:bg-purple-950/50 border-purple-200 dark:border-purple-900/60';
        catLabel = 'مجتمع';
    } else if (cat === 'news') {
        catIcon = 'newspaper';
        catColor = 'text-emerald-500 bg-emerald-50 dark:bg-emerald-950/50 border-emerald-200 dark:border-emerald-900/60';
        catLabel = 'أخبار';
    }

    const timeAgo = formatTimestampRelative(n.created_at);
    const linkUrl = n.action_url || n.link || '/notifications';

    return `
        <div class="p-2.5 rounded-xl transition ${isUnread ? 'bg-blue-50/60 dark:bg-blue-950/30' : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'} flex items-start gap-3 relative group" id="dropNotif_${n.id}">
            <div class="w-8 h-8 rounded-lg ${catColor} border flex items-center justify-center shrink-0 mt-0.5">
                <i data-lucide="${catIcon}" class="w-4 h-4"></i>
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between gap-1">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">${catLabel}</span>
                    <span class="text-[10px] text-slate-400">${timeAgo}</span>
                </div>
                <a href="${linkUrl}" class="block text-xs font-bold text-slate-900 dark:text-slate-100 hover:text-blue-600 dark:hover:text-blue-400 line-clamp-1 mt-0.5" onclick="quickMarkSingleRead('${n.id}', event)">
                    ${escapeHTML(n.title)}
                </a>
                <p class="text-[11px] text-slate-600 dark:text-slate-400 line-clamp-2 mt-0.5 leading-relaxed">
                    ${escapeHTML(n.message)}
                </p>
            </div>
            ${isUnread ? `
                <button type="button" onclick="quickMarkSingleRead('${n.id}', event)" class="p-1 rounded-md text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 opacity-0 group-hover:opacity-100 transition shrink-0" title="تحديد كمقروء">
                    <i data-lucide="check" class="w-3.5 h-3.5"></i>
                </button>
            ` : ''}
        </div>
    `;
}

function filterDropdownNotifs(cat, e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    currentDropdownCategory = cat;

    // Update active tab buttons
    document.querySelectorAll('.notif-tab-btn').forEach(btn => {
        if (btn.getAttribute('data-tab') === cat) {
            btn.className = 'notif-tab-btn flex-1 py-1 rounded-lg text-center transition bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm font-bold';
        } else {
            btn.className = 'notif-tab-btn flex-1 py-1 rounded-lg text-center transition hover:text-slate-900 dark:hover:text-white text-slate-500 dark:text-slate-400';
        }
    });

    loadDropdownNotifs(cat);
}

async function quickMarkAllRead(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    try {
        const res = await fetch('/api/notifications/read-all', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                category: currentDropdownCategory === 'all' ? null : currentDropdownCategory
            })
        });
        if (res.ok) {
            await fetchNotificationUnreadCount();
            loadDropdownNotifs(currentDropdownCategory);
        }
    } catch (err) {
        console.error('Failed to mark all read:', err);
    }
}

async function quickMarkSingleRead(id, e) {
    try {
        await fetch(`/api/notifications/${id}/read`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({})
        });
        await fetchNotificationUnreadCount();
        const row = document.getElementById(`dropNotif_${id}`);
        if (row) {
            row.classList.remove('bg-blue-50/60', 'dark:bg-blue-950/30');
            const checkBtn = row.querySelector('button');
            if (checkBtn) checkBtn.remove();
        }
    } catch (err) {
        console.error('Failed to mark read:', err);
    }
}

function formatTimestampRelative(isoStr) {
    if (!isoStr) return '';
    try {
        const d = new Date(isoStr);
        const now = new Date();
        const diffMs = now - d;
        const diffMins = Math.floor(diffMs / 60000);
        if (diffMins < 1) return 'الآن';
        if (diffMins < 60) return `منذ ${diffMins} دقيقة`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `منذ ${diffHours} ساعة`;
        const diffDays = Math.floor(diffHours / 24);
        if (diffDays < 7) return `منذ ${diffDays} يوم`;
        return d.toLocaleDateString('ar-EG', {month: 'short', day: 'numeric'});
    } catch (e) {
        return '';
    }
}

function escapeHTML(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Global click outside listener to close dropdown
document.addEventListener('click', (e) => {
    const root = document.getElementById('navNotificationRoot');
    const menu = document.getElementById('unifiedNotifDropdown') || document.getElementById('notificationsMenu');
    if (!menu || menu.classList.contains('hidden')) return;

    if (root && !root.contains(e.target)) {
        menu.classList.add('hidden');
    }
});

// Auto-initialize on load
document.addEventListener('DOMContentLoaded', () => {
    fetchNotificationUnreadCount();
    // Refresh unread count every 60 seconds
    setInterval(fetchNotificationUnreadCount, 60000);
});

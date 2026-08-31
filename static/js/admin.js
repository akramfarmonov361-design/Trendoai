// TrendoAI admin panel — umumiy skript (base_admin.html dan yuklanadi).
// Inline bloklardan yig'ildi (CSP: script-src 'self').

// CSRF tokeni base_admin.html dagi <meta name="csrf-token"> dan olinadi
function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// Real-time Card Search
function filterCards() {
    const q = (document.getElementById('crmSearch') ? document.getElementById('crmSearch').value : '').toLowerCase().trim();
    const cards = document.querySelectorAll('.crm-card');

    cards.forEach(card => {
        const text = card.getAttribute('data-search') || '';
        if (text.includes(q)) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}

// Universal Table Live Search & Category Filter
function filterTable(tableSelector, queryInputId, categoryFilter) {
    const qInput = document.getElementById(queryInputId);
    const q = qInput ? qInput.value.toLowerCase().trim() : '';
    const rows = document.querySelectorAll(tableSelector + ' tbody tr:not(.empty-state)');
    let visibleCount = 0;

    rows.forEach(row => {
        const rowText = (row.textContent || '').toLowerCase();
        const rowCat = (row.getAttribute('data-category') || '').toLowerCase();

        const matchesQuery = !q || rowText.includes(q);
        const matchesCat = !categoryFilter || categoryFilter === 'all' || rowCat === categoryFilter.toLowerCase();

        if (matchesQuery && matchesCat) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    const counter = document.getElementById('itemCount');
    if (counter) {
        counter.textContent = visibleCount;
    }
}

// CSRF: admin panel POST so'rovlari base_admin.html dagi meta tokenni yuboradi
function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// Status Update via AJAX
async function updateCrmStatus(type, id, status) {
    try {
        const res = await fetch('/api/admin/crm/update-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
            body: JSON.stringify({ type, id: parseInt(id), status })
        });
        const data = await res.json();
        if (data.success) {
            window.location.reload();
        } else {
            alert('Xatolik: ' + (data.error || 'Status yangilanmadi'));
        }
    } catch(e) {
        alert('Server bilan ulanishda xato: ' + e);
    }
}

// Follow-up Note Save via AJAX
async function saveNote(type, id, btnElement) {
    const textarea = btnElement.closest('.note-container').querySelector('.note-input');
    const note = textarea.value;
    const oldText = btnElement.innerText;
    btnElement.innerText = '...';

    try {
        const res = await fetch('/api/admin/crm/update-note', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
            body: JSON.stringify({ type, id: parseInt(id), note })
        });
        const data = await res.json();
        if (data.success) {
            btnElement.innerText = '✅ Saqlandi';
            setTimeout(() => { btnElement.innerText = oldText; }, 2000);
        } else {
            alert('Xato: ' + (data.error || 'Saqlanmadi'));
            btnElement.innerText = oldText;
        }
    } catch(e) {
        alert('Server bilan ulanishda xato: ' + e);
        btnElement.innerText = oldText;
    }
}

function setTopic(topic) {
        document.getElementById('topic').value = topic;
    }

function updateStatus(orderId, newStatus) {
    if(!newStatus) return;
    
    if(!confirm("Haqiqatdan ham statusni o'zgartirmoqchimisiz? Mijozga Telegram orqali xabar boradi!")) {
        return;
    }
    
    fetch('/api/bot-order-status', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken(),
        },
        body: JSON.stringify({
            order_id: orderId,
            status: newStatus
        })
    })
    .then(r => r.json())
    .then(data => {
        if(data.success) {
            window.location.reload();
        } else {
            alert('Xatolik yuz berdi: ' + data.error);
        }
    });
}

// ===== Inline handlerlar o'rniga listenerlar =====

// Tasdiqlash (avval onsubmit="return confirm(...)" yoki onclick="return confirm(...)")
document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
        if (!confirm(form.dataset.confirm)) e.preventDefault();
    });
});
document.querySelectorAll('button[data-confirm], a[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
        if (!confirm(el.dataset.confirm)) e.preventDefault();
    });
});

// Modal ochish/yopish (avval onclick="document.getElementById(...).style.display=...")
document.querySelectorAll('[data-modal-open]').forEach(function (el) {
    el.addEventListener('click', function () {
        const target = document.getElementById(el.dataset.modalOpen);
        if (target) target.style.display = 'block';
    });
});
document.querySelectorAll('[data-modal-hide]').forEach(function (el) {
    el.addEventListener('click', function () {
        const target = document.getElementById(el.dataset.modalHide);
        if (target) target.style.display = 'none';
    });
});

// Tanlov o'zgarganda formani yuborish (avval onchange="this.form.submit()")
document.querySelectorAll('[data-autosubmit]').forEach(function (el) {
    el.addEventListener('change', function () { if (el.form) el.form.submit(); });
});

// Chop etish (avval onclick="window.print()")
document.querySelectorAll('[data-print]').forEach(function (el) {
    el.addEventListener('click', function () { window.print(); });
});

// AI generatsiya: tayyor mavzu tanlash (avval onclick="setTopic('...')")
document.querySelectorAll('[data-topic]').forEach(function (btn) {
    btn.addEventListener('click', function () { setTopic(btn.dataset.topic); });
});

// Sahifani yangilash (avval onclick="window.location.reload()")
document.querySelectorAll('[data-reload]').forEach(function (el) {
    el.addEventListener('click', function () { window.location.reload(); });
});

// Kanban qidiruvi (avval onkeyup="filterCards()")
document.querySelectorAll('[data-filter-input]').forEach(function (el) {
    el.addEventListener('keyup', filterCards);
});

// Kanban: eslatma saqlash (avval onclick="saveNote('tur','id',this)")
document.querySelectorAll('[data-save-note]').forEach(function (btn) {
    btn.addEventListener('click', function () {
        saveNote(btn.dataset.itemType, btn.dataset.itemId, btn);
    });
});

// Kanban: status o'zgartirish (avval onchange="updateCrmStatus('tur','id',this.value)")
document.querySelectorAll('[data-crm-status]').forEach(function (sel) {
    sel.addEventListener('change', function () {
        updateCrmStatus(sel.dataset.itemType, sel.dataset.itemId, sel.value);
    });
});

// Bot buyurtma statusi (avval onchange="updateStatus('id', this.value)")
document.querySelectorAll('[data-order-status]').forEach(function (sel) {
    sel.addEventListener('change', function () {
        updateStatus(sel.dataset.orderId, sel.value);
    });
});

// Buyurtma tafsilotlari (avval onclick="alert('Manzil:...')")
document.querySelectorAll('[data-order-details]').forEach(function (btn) {
    btn.addEventListener('click', function () {
        alert('Manzil:\n' + (btn.dataset.address || '') +
              '\nIzoh: ' + (btn.dataset.note || '') +
              '\nMahsulotlar: ' + (btn.dataset.items || ''));
    });
});

// Jadval qidiruvi va toifalar filtrlari
document.querySelectorAll('[data-table-search]').forEach(function (input) {
    input.addEventListener('input', function () {
        const table = input.dataset.tableSearch;
        const activeFilterBtn = document.querySelector('[data-cat-filter].active');
        const cat = activeFilterBtn ? activeFilterBtn.dataset.catFilter : 'all';
        filterTable(table, input.id, cat);
    });
});

document.querySelectorAll('[data-cat-filter]').forEach(function (btn) {
    btn.addEventListener('click', function () {
        document.querySelectorAll('[data-cat-filter]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const inputId = btn.dataset.searchTarget || 'tableSearch';
        const table = btn.dataset.tableTarget || '.admin-table';
        filterTable(table, inputId, btn.dataset.catFilter);
    });
});

// Dashboard Analitika Grafiklari (Chart.js)
function initDashboardCharts() {
    const dataElem = document.getElementById('dashboard-chart-data');
    if (!dataElem) return;

    let chartData = {};
    try {
        chartData = JSON.parse(dataElem.textContent);
    } catch (e) {
        return;
    }

    const ordersCtx = document.getElementById('ordersTrendChart');
    if (ordersCtx && typeof Chart !== 'undefined') {
        new Chart(ordersCtx, {
            type: 'line',
            data: {
                labels: chartData.daysLabels || [],
                datasets: [{
                    label: 'Buyurtmalar soni',
                    data: chartData.ordersData || [],
                    borderColor: '#3B82F6',
                    backgroundColor: 'rgba(59, 130, 246, 0.15)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#3B82F6',
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1 } }
                }
            }
        });
    }

    const catCtx = document.getElementById('categoryPieChart');
    if (catCtx && typeof Chart !== 'undefined') {
        new Chart(catCtx, {
            type: 'doughnut',
            data: {
                labels: chartData.catLabels || [],
                datasets: [{
                    data: chartData.catValues || [],
                    backgroundColor: ['#10B981', '#3B82F6', '#8B5CF6'],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }
}

// Rasm yuklanganda Preview chiqarish
document.querySelectorAll('[data-image-preview]').forEach(function (fileInput) {
    fileInput.addEventListener('change', function (e) {
        const file = e.target.files[0];
        const previewTarget = document.querySelector(fileInput.dataset.imagePreview);
        if (!file || !previewTarget) return;

        const reader = new FileReader();
        reader.onload = function (event) {
            previewTarget.innerHTML = `<img src="${event.target.result}" alt="Preview" class="preview-thumb" style="max-height: 140px; border-radius: 8px; margin-top: 10px; border: 1px solid var(--border);">`;
        };
        reader.readAsDataURL(file);
    });
});

document.addEventListener('DOMContentLoaded', initDashboardCharts);

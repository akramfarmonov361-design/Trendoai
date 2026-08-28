// TrendoAI admin panel — umumiy skript (base_admin.html dan yuklanadi).
// Inline bloklardan yig'ildi (CSP: script-src 'self').

// CSRF tokeni base_admin.html dagi <meta name="csrf-token"> dan olinadi
function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// Real-time Card Search
function filterCards() {
    const q = document.getElementById('crmSearch').value.toLowerCase().trim();
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

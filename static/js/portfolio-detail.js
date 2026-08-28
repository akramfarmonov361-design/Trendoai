// TrendoAI — portfolio loyihasi sahifasi: galereya lightbox va rasm zaxirasi.
// Inline blokdan chiqarildi (CSP: script-src 'self').

function openLightbox(url) {
    const modal = document.getElementById('lightboxModal');
    const img = document.getElementById('lightboxImg');
    img.src = url;
    modal.style.display = 'flex';
}

// ===== Inline handlerlar o'rniga listenerlar =====

// Galereya rasmini bosish (avval onclick="openLightbox('...')")
document.querySelectorAll('[data-lightbox-src]').forEach(function (el) {
    el.addEventListener('click', function () { openLightbox(el.dataset.lightboxSrc); });
});

// Lightbox fonini bosish (avval onclick="this.style.display='none'")
const lightboxModal = document.getElementById('lightboxModal');
if (lightboxModal) {
    lightboxModal.addEventListener('click', function () {
        lightboxModal.style.display = 'none';
    });
}

// Rasm yuklanmasa zaxira rasm (avval onerror="this.src='...'").
// Xatolik listener biriktirilgunga qadar yuz bergan bo'lishi mumkin,
// shuning uchun tugallangan-lekin-bo'sh holat ham tekshiriladi.
document.querySelectorAll('[data-fallback-src]').forEach(function (img) {
    function swap() {
        if (img.src !== img.dataset.fallbackSrc) img.src = img.dataset.fallbackSrc;
    }
    if (img.complete && img.naturalWidth === 0) swap();
    else img.addEventListener('error', swap, { once: true });
});

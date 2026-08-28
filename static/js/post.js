// TrendoAI — maqola sahifasi: o'qish progressi va nusxalash tugmalari.
// Inline blokdan chiqarildi (CSP: script-src 'self').

    // Progress Bar Logic
    window.addEventListener('scroll', updateProgressBar);
    function updateProgressBar() {
        var winScroll = window.pageYOffset || document.documentElement.scrollTop;
        var height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        var scrolled = (winScroll / height) * 100;
        const progressBar = document.getElementById("reading-progress-bar");
        if (progressBar) progressBar.style.width = scrolled + "%";
    }

    // TOC Generation Logic
    document.addEventListener('DOMContentLoaded', function () {
        const articleBody = document.getElementById('article-body');
        const sidebarToc = document.getElementById('sidebar-toc-content');
        const mobileToc = document.getElementById('mobile-toc-content');
        const headings = articleBody.querySelectorAll('h2, h3');

        if (headings.length === 0) {
            document.getElementById('sidebar-toc-widget').style.display = 'none';
            document.querySelector('.mobile-toc-container').style.display = 'none';
            return;
        }

        const tocList = document.createElement('ul');
        headings.forEach((heading, index) => {
            const id = 'heading-' + index;
            heading.id = id;

            const li = document.createElement('li');
            li.className = 'toc-item ' + heading.tagName.toLowerCase();
            const a = document.createElement('a');
            a.href = '#' + id;
            a.textContent = heading.textContent;
            li.appendChild(a);
            tocList.appendChild(li);
        });

        if (sidebarToc) sidebarToc.appendChild(tocList.cloneNode(true));
        if (mobileToc) mobileToc.appendChild(tocList);
    });

    function copyLink() {
        navigator.clipboard.writeText(window.location.href);
        const btn = document.querySelector('.share-card.copy');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-check"></i> Nusxalandi!';
        setTimeout(() => { btn.innerHTML = originalText; }, 2000);
    }

    function copyImagePrompt() {
        const promptElement = document.getElementById('image-prompt-text');
        if (!promptElement) return;
        navigator.clipboard.writeText(promptElement.textContent.trim());
    }

// ===== Inline handlerlar o'rniga listenerlar =====

// Havolani nusxalash (avval onclick="copyLink()")
document.querySelectorAll('[data-copy-link]').forEach(function (btn) {
    btn.addEventListener('click', copyLink);
});

// Rasm promptini nusxalash (avval onclick="copyImagePrompt()")
document.querySelectorAll('[data-copy-prompt]').forEach(function (btn) {
    btn.addEventListener('click', copyImagePrompt);
});

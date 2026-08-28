// TrendoAI admin — portfolio formasi (meta tavsif hisoblagichi va AI generatsiya).
// Inline blokdan chiqarildi (CSP: script-src 'self').

// Character counter for meta description
    const metaDesc = document.getElementById('meta_description');
    const charCount = document.querySelector('.char-count');

    metaDesc.addEventListener('input', function () {
        charCount.textContent = this.value.length + '/160';
    });

    // Initialize on load
    charCount.textContent = metaDesc.value.length + '/160';

    // AI Generate functionality
    const aiBtn = document.getElementById('ai-generate-btn');
    const aiLoading = document.getElementById('ai-loading');

    aiBtn.addEventListener('click', async function () {
        const title = document.getElementById('title').value.trim();
        const category = document.getElementById('category').value;

        if (!title) {
            alert("Iltimos, avval 'Loyiha Nomi' kiriting!");
            document.getElementById('title').focus();
            return;
        }

        aiBtn.disabled = true;
        aiBtn.textContent = '⏳ Generatsiya...';
        aiLoading.style.display = 'block';

        try {
            const response = await fetch(`/admin/api/generate-portfolio?title=${encodeURIComponent(title)}&category=${category}`);
            const data = await response.json();

            if (data.error) {
                alert('AI xatosi: ' + data.error);
            } else {
                if (data.description) document.getElementById('description').value = data.description;
                if (data.technologies) document.getElementById('technologies').value = data.technologies;
                if (data.features) document.getElementById('features').value = data.features;
                if (data.details) document.getElementById('details').value = data.details;
                if (data.meta_description) {
                    document.getElementById('meta_description').value = data.meta_description;
                    charCount.textContent = data.meta_description.length + '/160';
                }
                if (data.meta_keywords) document.getElementById('meta_keywords').value = data.meta_keywords;
            }
        } catch (error) {
            alert('Xatolik yuz berdi: ' + error.message);
        } finally {
            aiBtn.disabled = false;
            aiBtn.textContent = '🤖 AI bilan yozish';
            aiLoading.style.display = 'none';
        }
    });

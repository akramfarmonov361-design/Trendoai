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
        const categoryElem = document.getElementById('category');
        const category = categoryElem ? categoryElem.value : 'web';

        if (!title) {
            alert("Iltimos, avval 'Loyiha Nomi' kiriting!");
            document.getElementById('title').focus();
            return;
        }

        aiBtn.disabled = true;
        aiBtn.textContent = '⏳ AI Yozmoqda...';
        if (aiLoading) aiLoading.style.display = 'block';

        try {
            const response = await fetch('/admin/portfolio/ai-generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': typeof csrfToken === 'function' ? csrfToken() : ''
                },
                body: JSON.stringify({ title, category })
            });
            const resData = await response.json();

            if (!resData.success || !resData.data) {
                alert('AI xatosi: ' + (resData.error || 'Ma\'lumot olinmadi'));
            } else {
                const data = resData.data;
                if (data.emoji && document.getElementById('emoji')) document.getElementById('emoji').value = data.emoji;
                if (data.description && document.getElementById('description')) document.getElementById('description').value = data.description;
                if (data.technologies && document.getElementById('technologies')) document.getElementById('technologies').value = data.technologies;
                if (data.features && document.getElementById('features')) document.getElementById('features').value = data.features;
                if (data.details && document.getElementById('details')) document.getElementById('details').value = data.details;
                if (data.problem && document.getElementById('problem')) document.getElementById('problem').value = data.problem;
                if (data.solution && document.getElementById('solution')) document.getElementById('solution').value = data.solution;
                if (data.result && document.getElementById('result')) document.getElementById('result').value = data.result;
                if (data.meta_description && document.getElementById('meta_description')) {
                    document.getElementById('meta_description').value = data.meta_description;
                    if (charCount) charCount.textContent = data.meta_description.length + '/160';
                }
                if (data.meta_keywords && document.getElementById('meta_keywords')) document.getElementById('meta_keywords').value = data.meta_keywords;
            }
        } catch (error) {
            alert('Xatolik yuz berdi: ' + error.message);
        } finally {
            aiBtn.disabled = false;
            aiBtn.textContent = '🤖 AI bilan yozish';
            if (aiLoading) aiLoading.style.display = 'none';
        }
    });

// TrendoAI admin — xizmat formasi (AI generatsiya).
// Inline blokdan chiqarildi (CSP: script-src 'self').

document.getElementById('ai-generate-btn').addEventListener('click', async function () {
        const title = document.getElementById('title').value.trim();
        if (!title) {
            alert('Avval "Xizmat nomi" maydonini to\'ldiring!');
            return;
        }

        const btn = this;
        const originalText = btn.innerHTML;
        btn.innerHTML = '⏳ Generatsiya qilinmoqda...';
        btn.disabled = true;

        try {
            const response = await fetch('/admin/services/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken(),
                },
                body: JSON.stringify({ title: title })
            });

            const data = await response.json();

            if (data.error) {
                alert('Xatolik: ' + data.error);
            } else {
                // Formani to'ldirish
                if (data.description) document.getElementById('description').value = data.description;
                if (data.full_description) document.getElementById('full_description').value = data.full_description;
                if (data.features) document.getElementById('features').value = JSON.stringify(data.features, null, 2);
                if (data.meta_desc) document.getElementById('meta_desc').value = data.meta_desc;
                if (data.icon) document.getElementById('icon').value = data.icon;
                if (data.slug && !document.getElementById('slug').value) {
                    document.getElementById('slug').value = data.slug;
                }

                alert('✅ AI muvaffaqiyatli generatsiya qildi! Matnlarni ko\'rib chiqing va zarur bo\'lsa tahrirlang.');
            }
        } catch (error) {
            alert('Xatolik: ' + error.message);
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

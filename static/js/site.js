// TrendoAI — sayt UI, service worker, push va PWA mantiqi.
// base.html ichidagi inline blokdan chiqarildi: inline skript CSP'da
// 'unsafe-inline' talab qilardi, nonce esa stale-while-revalidate
// keshi bilan mos kelmaydi (eski nonce butun sahifani buzardi).

// FontAwesome preload -> stylesheet (avval onload="" atributi edi).
// Hodisani kutmasdan bevosita almashtiramiz: preload keshni allaqachon
// isitgan, shuning uchun hodisani o'tkazib yuborish xavfi yo'q.
(function () {
    const fa = document.getElementById('fa-css');
    if (fa && fa.rel === 'preload') fa.rel = 'stylesheet';
})();

        document.querySelectorAll('a[target="_blank"]').forEach(link => {
            link.relList.add('noopener', 'noreferrer');
        });

        // Header scrolls normally with the page (no auto-hide)
        const header = document.querySelector('header');

        // ========== MOBILE HAMBURGER MENU ==========
        const mobileMenuToggle = document.getElementById('mobileMenuToggle');
        const mainNav = document.getElementById('mainNav');

        if (mobileMenuToggle && mainNav) {
            const syncMenuState = () => {
                const isOpen = mainNav.classList.contains('mobile-open');
                mobileMenuToggle.setAttribute('aria-expanded', String(isOpen));
            };

            mobileMenuToggle.addEventListener('click', function (e) {
                e.stopPropagation();
                mobileMenuToggle.classList.toggle('active');
                mainNav.classList.toggle('mobile-open');
                syncMenuState();
            });

            // Close menu when clicking a nav link
            mainNav.querySelectorAll('a').forEach(link => {
                link.addEventListener('click', function () {
                    mobileMenuToggle.classList.remove('active');
                    mainNav.classList.remove('mobile-open');
                    syncMenuState();
                });
            });

            // Close menu when clicking outside
            document.addEventListener('click', function (e) {
                if (!header.contains(e.target)) {
                    mobileMenuToggle.classList.remove('active');
                    mainNav.classList.remove('mobile-open');
                    syncMenuState();
                }
            });
        }

        // Telegram Popup Logic
        function showTgPopup() {
            document.getElementById('tg-popup').classList.add('active');
        }

        function closeTgPopup() {
            document.getElementById('tg-popup').classList.remove('active');
            localStorage.setItem('tg_popup_shown', 'true');
        }

        // Show popup after 1 minute if not already shown
        if (!localStorage.getItem('tg_popup_shown')) {
            setTimeout(showTgPopup, 60000); // 60 seconds = 1 minute
        }

        // Back to Top Button Logic
        const backToTopBtn = document.getElementById('back-to-top');

        window.addEventListener('scroll', function () {
            if (window.pageYOffset > 300) {
                backToTopBtn.classList.add('visible');
            } else {
                backToTopBtn.classList.remove('visible');
            }
        });

        backToTopBtn.addEventListener('click', function () {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });

        // Theme Toggle Logic
        const themeToggle = document.getElementById('themeToggle');
        const savedTheme = localStorage.getItem('theme') || 'dark';

        // Apply saved theme on load
        if (savedTheme === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
        }

        themeToggle.addEventListener('click', function () {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';

            document.documentElement.setAttribute('data-theme', newTheme === 'light' ? 'light' : '');
            localStorage.setItem('theme', newTheme);
        });


        // Service Worker & Push Notifications
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', async () => {
                try {
                    const registration = await navigator.serviceWorker.register('/sw.js');
                    console.log('SW registered:', registration);
                    const readyRegistration = await navigator.serviceWorker.ready;
                    initializeUI(readyRegistration);
                } catch (error) {
                    console.log('SW registration failed:', error);
                }
            });
        }

        function initializeUI(registration) {
            const notifyBtn = document.getElementById('notify-btn');
            if (!notifyBtn || !('PushManager' in window)) {
                return;
            }

            syncExistingSubscription(registration);

            if (Notification.permission === 'granted') {
                notifyBtn.style.display = 'none';
            } else if (Notification.permission !== 'denied') {
                notifyBtn.style.display = 'inline-block';
            }

            notifyBtn.addEventListener('click', async () => {
                const permission = await Notification.requestPermission();
                if (permission === 'granted') {
                    await subscribeUser(registration);
                    notifyBtn.style.display = 'none';
                }
            });
        }

        const VAPID_PUBLIC_KEY = document.body.dataset.vapidKey || '';

        function urlBase64ToUint8Array(base64String) {
            const padding = '='.repeat((4 - base64String.length % 4) % 4);
            const base64 = (base64String + padding)
                .replace(/\-/g, '+')
                .replace(/_/g, '/');
            const rawData = window.atob(base64);
            const outputArray = new Uint8Array(rawData.length);
            for (let i = 0; i < rawData.length; ++i) {
                outputArray[i] = rawData.charCodeAt(i);
            }
            return outputArray;
        }

        async function syncExistingSubscription(registration) {
            try {
                const existingSubscription = await registration.pushManager.getSubscription();
                if (existingSubscription) {
                    await sendSubscriptionToBackEnd(existingSubscription);
                    return existingSubscription;
                }

                if (Notification.permission === 'granted') {
                    return await subscribeUser(registration);
                }
            } catch (error) {
                console.error('Push subscription sync failed:', error);
            }
            return null;
        }

        async function subscribeUser(registration) {
            const subscribeOptions = {
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
            };

            try {
                const existingSubscription = await registration.pushManager.getSubscription();
                if (existingSubscription) {
                    await sendSubscriptionToBackEnd(existingSubscription);
                    return existingSubscription;
                }

                const pushSubscription = await registration.pushManager.subscribe(subscribeOptions);
                console.log('Received PushSubscription:', JSON.stringify(pushSubscription));
                await sendSubscriptionToBackEnd(pushSubscription);
                return pushSubscription;
            } catch (err) {
                console.log('Subscription failed: ', err);
                return null;
            }
        }

        function sendSubscriptionToBackEnd(subscription) {
            const payload = typeof subscription.toJSON === 'function'
                ? subscription.toJSON()
                : subscription;

            return fetch('/api/push/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error('Bad status code from server.');
                    }
                    return response.json();
                })
                .then(function (responseData) {
                    return responseData;
                })
                .catch(function (error) {
                    console.error('Error sending subscription to backend:', error);
                    throw error;
                });
        }
        // PWA Install Logic
        let deferredPrompt;
        const installBtn = document.getElementById('install-btn');

        window.addEventListener('beforeinstallprompt', (e) => {
            // Prevent Chrome 67 and earlier from automatically showing the prompt
            e.preventDefault();
            // Stash the event so it can be triggered later.
            deferredPrompt = e;
            // Update UI to notify the user they can add to home screen
            installBtn.style.display = 'inline-block';

            installBtn.addEventListener('click', (e) => {
                // Hide our user interface that shows our A2HS button
                installBtn.style.display = 'none';
                // Show the prompt
                deferredPrompt.prompt();
                // Wait for the user to respond to the prompt
                deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        console.log('User accepted the A2HS prompt');
                    } else {
                        console.log('User dismissed the A2HS prompt');
                    }
                    deferredPrompt = null;
                });
            });
        });

        window.addEventListener('appinstalled', (evt) => {
            console.log('a2hs installed');
            installBtn.style.display = 'none';
        });

    // Telegram popup yopish tugmalari (avval onclick="closeTgPopup()" edi)
    document.querySelectorAll('[data-tg-popup-close]').forEach(function (btn) {
        btn.addEventListener('click', closeTgPopup);
    });

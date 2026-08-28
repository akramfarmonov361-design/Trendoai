// TrendoAI — AI chatbot vidjeti va Live Voice mantiqi.
// base.html inline blokidan chiqarildi (CSP: script-src 'self').

                // ========== AI CHATBOT LOGIC ==========
        const chatbotToggle = document.getElementById('chatbotToggle');
        const chatbotWindow = document.getElementById('chatbotWindow');
        const chatbotClose = document.getElementById('chatbotClose');
        const chatbotMessages = document.getElementById('chatbotMessages');
        const chatbotInput = document.getElementById('chatbotInput');
        const chatbotSend = document.getElementById('chatbotSend');

        function setChatbotOpen(isOpen) {
            chatbotWindow.classList.toggle('active', isOpen);
            chatbotWindow.setAttribute('aria-hidden', String(!isOpen));
            chatbotToggle.setAttribute('aria-expanded', String(isOpen));
            document.body.classList.toggle('chatbot-open', isOpen && window.innerWidth <= 768);
            if (isOpen) {
                chatbotInput.focus();
            }
        }

        chatbotToggle.addEventListener('click', function () {
            setChatbotOpen(!chatbotWindow.classList.contains('active'));
        });

        chatbotClose.addEventListener('click', function () {
            setChatbotOpen(false);
        });

        window.addEventListener('resize', function () {
            if (window.innerWidth > 768) {
                document.body.classList.remove('chatbot-open');
            } else if (chatbotWindow.classList.contains('active')) {
                document.body.classList.add('chatbot-open');
            }
        });

        let chatHistory = [];

        async function sendChatMessage() {
            const message = chatbotInput.value.trim();
            if (!message) return;

            chatHistory.push({ role: 'user', content: message });

            chatbotInput.disabled = true;
            chatbotSend.disabled = true;

            const userDiv = document.createElement('div');
            userDiv.className = 'chat-message user';
            userDiv.textContent = message;
            chatbotMessages.appendChild(userDiv);

            chatbotInput.value = '';

            const typingDiv = document.createElement('div');
            typingDiv.className = 'chat-message bot typing';
            typingDiv.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
            chatbotMessages.appendChild(typingDiv);
            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message, messages: chatHistory })
                });

                const data = await response.json();
                if (data.reply) {
                    chatHistory.push({ role: 'assistant', content: data.reply });
                }

                // Fire Meta Pixel Lead event if contact was sent
                if (typeof fbq !== 'undefined' && /(\+?998[0-9\s\-]{9,13}|\b9[0-9]{8}\b|@[a-zA-Z0-9_]{4,})/.test(message)) {
                    try { fbq('track', 'Lead', { content_name: 'AI Chat Lead' }); } catch(e){}
                }

                typingDiv.remove();

                const botDiv = document.createElement('div');
                botDiv.className = 'chat-message bot';
                botDiv.textContent = data.reply || data.response || data.error || 'Xatolik yuz berdi';
                chatbotMessages.appendChild(botDiv);
            } catch (error) {
                typingDiv.remove();
                const errorDiv = document.createElement('div');
                errorDiv.className = 'chat-message bot';
                errorDiv.textContent = 'Tarmoq xatosi. Iltimos, qayta urinib ko\'ring.';
                chatbotMessages.appendChild(errorDiv);
            }

            chatbotInput.disabled = false;
            chatbotSend.disabled = false;
            chatbotInput.focus();
            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        }

        chatbotSend.addEventListener('click', sendChatMessage);

        chatbotInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        });

        // ========== VOICE RECORDING ==========
        const chatbotMic = document.getElementById('chatbotMic');
        let mediaRecorder = null;
        let audioChunks = [];
        let isRecording = false;

        chatbotMic.addEventListener('click', async function () {
            if (isRecording) {
                // Stop recording
                mediaRecorder.stop();
                chatbotMic.classList.remove('recording');
                chatbotMic.textContent = '🎤';
                isRecording = false;
            } else {
                // Start recording
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];

                    mediaRecorder.ondataavailable = (event) => {
                        audioChunks.push(event.data);
                    };

                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        stream.getTracks().forEach(track => track.stop());

                        // Send audio to server
                        await sendAudioMessage(audioBlob);
                    };

                    mediaRecorder.start();
                    chatbotMic.classList.add('recording');
                    chatbotMic.textContent = '⏹️';
                    isRecording = true;

                    // Add recording indicator
                    chatbotInput.placeholder = '🔴 Yozib olinmoqda...';
                } catch (error) {
                    alert('Mikrofonga ruxsat berilmadi. Iltimos, brauzer sozlamalarini tekshiring.');
                }
            }
        });

        async function sendAudioMessage(audioBlob) {
            chatbotInput.placeholder = 'Xabar yozing...';

            // Show user message
            const userDiv = document.createElement('div');
            userDiv.className = 'chat-message user';
            userDiv.textContent = '🎤 Ovozli xabar yuborildi';
            chatbotMessages.appendChild(userDiv);

            // Add typing indicator
            const typingDiv = document.createElement('div');
            typingDiv.className = 'chat-message bot typing';
            typingDiv.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
            chatbotMessages.appendChild(typingDiv);
            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

            try {
                // Convert to base64
                const reader = new FileReader();
                reader.readAsDataURL(audioBlob);

                reader.onloadend = async () => {
                    const base64Audio = reader.result.split(',')[1];

                    const response = await fetch('/api/chat/audio', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ audio: base64Audio })
                    });

                    const data = await response.json();
                    typingDiv.remove();

                    const botDiv = document.createElement('div');
                    botDiv.className = 'chat-message bot';
                    botDiv.textContent = data.response || data.error || 'Xatolik yuz berdi';
                    chatbotMessages.appendChild(botDiv);
                    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

                    // Ovozli javobni ijro etish
                    if (data.audio_base64) {
                        try {
                            const audio = new Audio("data:audio/wav;base64," + data.audio_base64);
                            audio.play().catch(e => console.log("Audio play error:", e));
                        } catch (e) {
                            console.log("Audio creation error:", e);
                        }
                    }
                };
            } catch (error) {
                typingDiv.remove();
                const errorDiv = document.createElement('div');
                errorDiv.className = 'chat-message bot';
                errorDiv.textContent = 'Audio yuborishda xatolik.';
                chatbotMessages.appendChild(errorDiv);
            }
        }

        // ========== LIVE VOICE CALL MANAGER ==========
        const chatbotCallStart = document.getElementById('chatbotCallStart');
        const chatbotCallOverlay = document.getElementById('chatbotCallOverlay');
        const callStatusText = document.getElementById('callStatusText');
        const callStatusDot = document.getElementById('callStatusDot');
        const callVoiceWave = document.getElementById('callVoiceWave');
        const callMuteBtn = document.getElementById('callMuteBtn');
        const callEndBtn = document.getElementById('callEndBtn');

        let isCallActive = false;
        let isCallMuted = false;
        let callStream = null;
        let callMediaRecorder = null;
        let callAudioChunks = [];
        let silenceTimer = null;
        let currentAudioOutput = null;

        function updateCallStatus(status, text, isSpeaking = false) {
            if (callStatusText) callStatusText.textContent = text;
            if (callStatusDot) {
                if (status === 'listening') callStatusDot.textContent = '🟢';
                else if (status === 'speaking') callStatusDot.textContent = '🔊';
                else if (status === 'connecting') callStatusDot.textContent = '🟡';
                else if (status === 'muted') callStatusDot.textContent = '🔇';
                else callStatusDot.textContent = '🔴';
            }
            if (callVoiceWave) {
                callVoiceWave.classList.toggle('speaking', isSpeaking);
            }
        }

        async function startLiveCall() {
            try {
                chatbotCallOverlay.classList.add('active');
                isCallActive = true;
                isCallMuted = false;
                if (callMuteBtn) {
                    callMuteBtn.classList.remove('muted');
                    callMuteBtn.textContent = '🎤';
                }

                updateCallStatus('connecting', 'Ulanmoqda...');

                callStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                updateCallStatus('listening', 'Sizni eshitmoqdamiz...');

                startListeningCycle();
            } catch (err) {
                alert('Mikrofonga ruxsat berilmadi yoki xatolik yuz berdi: ' + (err.message || err));
                endLiveCall();
            }
        }

        let vadAudioContext = null;
        let vadAnalyser = null;
        let vadCheckInterval = null;
        let speechDetected = false;
        let silenceStartTime = null;

        function startListeningCycle() {
            if (!isCallActive || isCallMuted) return;

            callAudioChunks = [];
            speechDetected = false;
            silenceStartTime = null;

            try {
                callMediaRecorder = new MediaRecorder(callStream, { mimeType: 'audio/webm;codecs=opus' });
            } catch (e) {
                try { callMediaRecorder = new MediaRecorder(callStream); } catch(err){ return; }
            }

            callMediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    callAudioChunks.push(event.data);
                }
            };

            callMediaRecorder.onstop = async () => {
                stopVAD();
                if (!isCallActive || callAudioChunks.length === 0) return;
                const audioBlob = new Blob(callAudioChunks, { type: 'audio/webm' });
                await sendCallAudioChunk(audioBlob);
            };

            callMediaRecorder.start(100);
            updateCallStatus('listening', 'Sizni eshitmoqdaman...');

            setupVAD();

            clearTimeout(silenceTimer);
            silenceTimer = setTimeout(() => {
                if (callMediaRecorder && callMediaRecorder.state === 'recording') {
                    callMediaRecorder.stop();
                }
            }, 6000);
        }

        function setupVAD() {
            try {
                if (!vadAudioContext) {
                    vadAudioContext = new (window.AudioContext || window.webkitAudioContext)();
                }
                if (vadAudioContext.state === 'suspended') {
                    vadAudioContext.resume();
                }
                const source = vadAudioContext.createMediaStreamSource(callStream);
                vadAnalyser = vadAudioContext.createAnalyser();
                vadAnalyser.fftSize = 512;
                source.connect(vadAnalyser);

                const dataArray = new Uint8Array(vadAnalyser.frequencyBinCount);

                clearInterval(vadCheckInterval);
                vadCheckInterval = setInterval(() => {
                    if (!callMediaRecorder || callMediaRecorder.state !== 'recording') {
                        clearInterval(vadCheckInterval);
                        return;
                    }
                    vadAnalyser.getByteFrequencyData(dataArray);
                    let sum = 0;
                    for (let i = 0; i < dataArray.length; i++) {
                        sum += dataArray[i];
                    }
                    const averageVolume = sum / dataArray.length;

                    if (averageVolume > 14) {
                        if (!speechDetected) {
                            speechDetected = true;
                            updateCallStatus('listening', '🎙️ Siz gapirmoqdasiz...', true);
                        }
                        silenceStartTime = null;
                    } else if (speechDetected) {
                        if (!silenceStartTime) {
                            silenceStartTime = Date.now();
                        } else if (Date.now() - silenceStartTime > 1100) {
                            clearInterval(vadCheckInterval);
                            if (callMediaRecorder && callMediaRecorder.state === 'recording') {
                                callMediaRecorder.stop();
                            }
                        }
                    }
                }, 100);
            } catch(e) {
                console.log("VAD error:", e);
            }
        }

        function stopVAD() {
            if (vadCheckInterval) clearInterval(vadCheckInterval);
        }

        async function sendCallAudioChunk(audioBlob) {
            if (!isCallActive) return;

            updateCallStatus('speaking', 'AI o\'ylamoqda...', true);

            try {
                const reader = new FileReader();
                reader.readAsDataURL(audioBlob);

                reader.onloadend = async () => {
                    const base64Audio = reader.result.split(',')[1];

                    const response = await fetch('/api/chat/audio', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ audio: base64Audio })
                    });

                    const data = await response.json();
                    if (!isCallActive) return;

                    const replyText = data.response || data.reply || '';
                    if (replyText) {
                        const botDiv = document.createElement('div');
                        botDiv.className = 'chat-message bot';
                        botDiv.textContent = '🎙️ AI (Live): ' + replyText;
                        chatbotMessages.appendChild(botDiv);
                        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
                    }

                    if (data.audio_base64) {
                        updateCallStatus('speaking', 'AI gapirmoqda...', true);
                        currentAudioOutput = new Audio("data:audio/wav;base64," + data.audio_base64);

                        currentAudioOutput.onended = () => {
                            if (isCallActive && !isCallMuted) {
                                startListeningCycle();
                            }
                        };

                        currentAudioOutput.onerror = () => {
                            if (isCallActive && !isCallMuted) {
                                startListeningCycle();
                            }
                        };

                        await currentAudioOutput.play().catch(e => {
                            console.log("Audio play error:", e);
                            if (isCallActive && !isCallMuted) startListeningCycle();
                        });
                    } else {
                        if (isCallActive && !isCallMuted) startListeningCycle();
                    }
                };
            } catch (err) {
                console.error("Call audio error:", err);
                if (isCallActive && !isCallMuted) setTimeout(startListeningCycle, 1000);
            }
        }

        function toggleCallMute() {
            isCallMuted = !isCallMuted;
            if (isCallMuted) {
                if (callMuteBtn) {
                    callMuteBtn.classList.add('muted');
                    callMuteBtn.textContent = '🔇';
                }
                updateCallStatus('muted', 'Mikrofon o\'chirilgan');
                if (callMediaRecorder && callMediaRecorder.state === 'recording') {
                    callMediaRecorder.stop();
                }
                clearTimeout(silenceTimer);
            } else {
                if (callMuteBtn) {
                    callMuteBtn.classList.remove('muted');
                    callMuteBtn.textContent = '🎤';
                }
                startListeningCycle();
            }
        }

        function endLiveCall() {
            isCallActive = false;
            stopVAD();
            clearTimeout(silenceTimer);

            if (currentAudioOutput) {
                currentAudioOutput.pause();
                currentAudioOutput = null;
            }

            if (callMediaRecorder && callMediaRecorder.state !== 'inactive') {
                try { callMediaRecorder.stop(); } catch(e){}
            }

            if (callStream) {
                callStream.getTracks().forEach(track => track.stop());
                callStream = null;
            }

            if (chatbotCallOverlay) {
                chatbotCallOverlay.classList.remove('active');
            }

            const sysDiv = document.createElement('div');
            sysDiv.className = 'chat-message bot';
            sysDiv.textContent = '📞 Ovozli qo\'ng\'iroq yakunlandi.';
            chatbotMessages.appendChild(sysDiv);
            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        }

        if (chatbotCallStart) {
            chatbotCallStart.addEventListener('click', () => {
                if (!chatbotWindow.classList.contains('active')) {
                    setChatbotOpen(true);
                }
                startLiveCall();
            });
        }

        if (callMuteBtn) callMuteBtn.addEventListener('click', toggleCallMute);
        if (callEndBtn) callEndBtn.addEventListener('click', endLiveCall);

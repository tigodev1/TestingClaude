// AI Tools - Pollinations AI Integration

// Global variables
let chatHistory = [];
let currentImageURL = '';

// ============= IMAGE GENERATION =============

function setPrompt(prompt) {
    document.getElementById('imagePrompt').value = prompt;
}

async function generateImage() {
    const prompt = document.getElementById('imagePrompt').value;
    const model = document.getElementById('imageModel').value;
    const width = document.getElementById('imageWidth').value;
    const height = document.getElementById('imageHeight').value;
    const seed = document.getElementById('imageSeed').value;
    const enhance = document.getElementById('imageEnhance').checked;

    if (!prompt.trim()) {
        showToast('Please enter a prompt', 'error');
        return;
    }

    showToast('Generating image...', 'info');

    try {
        const params = new URLSearchParams({
            prompt: prompt,
            model: model,
            width: width,
            height: height,
            enhance: enhance
        });

        if (seed) {
            params.append('seed', seed);
        }

        const response = await fetch(`/api/ai/generate-image?${params.toString()}`);
        const data = await response.json();

        if (response.ok) {
            currentImageURL = data.url;
            document.getElementById('generatedImage').src = currentImageURL;
            document.getElementById('imageResultCard').style.display = 'block';
            document.getElementById('downloadImageBtn').style.display = 'inline-block';
            document.getElementById('copyImageBtn').style.display = 'inline-block';

            // Show metadata
            document.getElementById('imageMetadata').innerHTML = `
                <strong>Model:</strong> ${model} |
                <strong>Size:</strong> ${width}×${height} |
                <strong>Seed:</strong> ${seed || 'Random'}
            `;

            showToast('Image generated successfully!', 'success');

            // Scroll to result
            document.getElementById('imageResultCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            showToast('Error: ' + (data.error || 'Failed to generate image'), 'error');
        }
    } catch (error) {
        showToast('Error generating image: ' + error.message, 'error');
        console.error('Image generation error:', error);
    }
}

function downloadGeneratedImage() {
    if (!currentImageURL) {
        showToast('No image to download', 'error');
        return;
    }

    const link = document.createElement('a');
    link.href = currentImageURL;
    link.download = 'generated-image-' + Date.now() + '.png';
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Download started!', 'success');
}

function copyImageURL() {
    if (!currentImageURL) {
        showToast('No image URL to copy', 'error');
        return;
    }

    navigator.clipboard.writeText(currentImageURL).then(() => {
        showToast('Image URL copied to clipboard!', 'success');
    }).catch(err => {
        showToast('Failed to copy URL', 'error');
    });
}

// ============= CHATBOT =============

function clearChat() {
    chatHistory = [];
    document.getElementById('chatMessages').innerHTML = '<div class="text-center text-muted" style="padding:40px 0;">Start a conversation...</div>';
    showToast('Chat cleared', 'success');
}

function addMessageToChat(role, content, isError = false) {
    const messagesDiv = document.getElementById('chatMessages');

    // Remove placeholder if exists
    const placeholder = messagesDiv.querySelector('.text-center');
    if (placeholder) {
        messagesDiv.innerHTML = '';
    }

    const messageDiv = document.createElement('div');
    messageDiv.style.cssText = `
        margin-bottom: 16px;
        padding: 12px 16px;
        border-radius: 8px;
        ${role === 'user' ? 'background: var(--accent); color: white; margin-left: 20%;' : 'background: var(--bg-secondary); margin-right: 20%;'}
        ${isError ? 'background: var(--danger); color: white;' : ''}
    `;

    const header = document.createElement('div');
    header.style.cssText = 'font-weight: bold; margin-bottom: 8px; opacity: 0.8;';
    header.textContent = role === 'user' ? '👤 You' : role === 'error' ? '⚠️ Error' : '🤖 AI';

    const contentDiv = document.createElement('div');
    contentDiv.style.cssText = 'white-space: pre-wrap; word-wrap: break-word;';
    contentDiv.textContent = content;

    messageDiv.appendChild(header);
    messageDiv.appendChild(contentDiv);
    messagesDiv.appendChild(messageDiv);

    // Scroll to bottom
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message) {
        showToast('Please enter a message', 'error');
        return;
    }

    const model = document.getElementById('chatModel').value;
    const temperature = parseFloat(document.getElementById('chatTemperature').value);
    const maxTokens = parseInt(document.getElementById('chatMaxTokens').value);
    const systemPrompt = document.getElementById('chatSystem').value;

    // Add user message to chat
    addMessageToChat('user', message);
    chatHistory.push({ role: 'user', content: message });

    // Clear input
    input.value = '';

    try {
        const response = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                messages: chatHistory,
                model: model,
                temperature: temperature,
                max_tokens: maxTokens,
                system: systemPrompt || undefined
            })
        });

        const data = await response.json();

        if (response.ok) {
            const aiMessage = data.response;
            addMessageToChat('assistant', aiMessage);
            chatHistory.push({ role: 'assistant', content: aiMessage });
        } else {
            addMessageToChat('error', data.error || 'Failed to get response', true);
        }
    } catch (error) {
        addMessageToChat('error', 'Error: ' + error.message, true);
        console.error('Chat error:', error);
    }
}

// ============= VISION AI =============

let visionImageBase64 = null;

function setVisionPrompt(prompt) {
    document.getElementById('visionPrompt').value = prompt;
}

function handleVisionImageUpload() {
    const fileInput = document.getElementById('visionImageFile');
    const file = fileInput.files[0];

    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        visionImageBase64 = e.target.result;
        document.getElementById('visionPreviewImg').src = visionImageBase64;
        document.getElementById('visionPreview').style.display = 'block';
        document.getElementById('visionImageURL').value = ''; // Clear URL field
        showToast('Image loaded successfully', 'success');
    };
    reader.readAsDataURL(file);
}

async function analyzeImage() {
    const imageURL = document.getElementById('visionImageURL').value;
    const prompt = document.getElementById('visionPrompt').value;

    if (!imageURL && !visionImageBase64) {
        showToast('Please provide an image URL or upload an image', 'error');
        return;
    }

    if (!prompt.trim()) {
        showToast('Please enter a question or prompt', 'error');
        return;
    }

    showToast('Analyzing image...', 'info');

    try {
        const response = await fetch('/api/ai/vision', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                image_url: imageURL || visionImageBase64,
                prompt: prompt
            })
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('visionResult').textContent = data.analysis;
            document.getElementById('visionResultCard').style.display = 'block';
            showToast('Analysis complete!', 'success');

            // Scroll to result
            document.getElementById('visionResultCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            showToast('Error: ' + (data.error || 'Failed to analyze image'), 'error');
        }
    } catch (error) {
        showToast('Error analyzing image: ' + error.message, 'error');
        console.error('Vision AI error:', error);
    }
}

// ============= TEXT-TO-SPEECH =============

let currentAudioURL = null;

function setTTSText(text) {
    document.getElementById('ttsText').value = text;
}

async function generateSpeech() {
    const text = document.getElementById('ttsText').value;
    const voice = document.getElementById('ttsVoice').value;
    const speed = parseFloat(document.getElementById('ttsSpeed').value);

    if (!text.trim()) {
        showToast('Please enter text to convert to speech', 'error');
        return;
    }

    showToast('Generating speech...', 'info');

    try {
        const response = await fetch('/api/ai/text-to-speech', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                voice: voice,
                speed: speed
            })
        });

        const data = await response.json();

        if (response.ok) {
            currentAudioURL = data.audio_url;
            const audioElement = document.getElementById('ttsAudio');
            audioElement.src = currentAudioURL;
            document.getElementById('ttsResultCard').style.display = 'block';
            audioElement.play();
            showToast('Speech generated successfully!', 'success');

            // Scroll to result
            document.getElementById('ttsResultCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            showToast('Error: ' + (data.error || 'Failed to generate speech'), 'error');
        }
    } catch (error) {
        showToast('Error generating speech: ' + error.message, 'error');
        console.error('Text-to-speech error:', error);
    }
}

function downloadAudio() {
    if (!currentAudioURL) {
        showToast('No audio to download', 'error');
        return;
    }

    const link = document.createElement('a');
    link.href = currentAudioURL;
    link.download = 'speech-' + Date.now() + '.mp3';
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Download started!', 'success');
}

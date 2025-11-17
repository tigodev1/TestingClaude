// AI Tools - Pollinations AI Integration with History

// Global variables
let chatHistory = [];
let currentImageURL = '';
let currentChatId = null;

// ============= IMAGE GENERATION =============

function setPrompt(prompt) {
    document.getElementById('imagePrompt').value = prompt;
}

async function loadImageGallery() {
    try {
        const response = await fetch('/api/ai/get-images');
        const data = await response.json();

        const gallery = document.getElementById('imageGallery');
        if (!gallery) return;

        if (data.images && data.images.length > 0) {
            gallery.innerHTML = data.images.map(img => `
                <div class="image-gallery-item" style="position:relative; cursor:pointer; overflow:hidden; border-radius:8px; background:var(--bg-surface);">
                    <img src="${img.url}"
                         onclick="viewImage('${img.url}', '${img.prompt.replace(/'/g, "\\'")}', '${img.seed}')"
                         style="width:100%; height:200px; object-fit:cover; display:block;"
                         alt="${img.prompt}">
                    <div style="padding:8px; font-size:11px;">
                        <div style="font-weight:bold; margin-bottom:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${img.prompt}">${img.prompt}</div>
                        <div style="color:var(--text-secondary); display:flex; justify-content:space-between;">
                            <span>Seed: ${img.seed}</span>
                            <button onclick="event.stopPropagation(); deleteImage(${img.id})" class="btn btn-sm btn-danger" style="padding:2px 6px; font-size:10px;"><i class="fas fa-trash"></i></button>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            gallery.innerHTML = '<div class="text-center text-muted" style="grid-column:1/-1; padding:40px 0;">No images generated yet</div>';
        }
    } catch (error) {
        console.error('Error loading image gallery:', error);
    }
}

function viewImage(url, prompt, seed) {
    document.getElementById('imagePrompt').value = prompt;
    document.getElementById('imageSeed').value = seed;
    document.getElementById('generatedImage').src = url;
    document.getElementById('imageResultCard').style.display = 'block';
    currentImageURL = url;
    document.getElementById('downloadImageBtn').style.display = 'inline-block';
    document.getElementById('copyImageBtn').style.display = 'inline-block';
    showToast('Image loaded from gallery', 'success');
}

async function deleteImage(imageId) {
    if (!confirm('Delete this image?')) return;

    try {
        await fetch(`/api/ai/delete-image/${imageId}`, { method: 'DELETE' });
        showToast('Image deleted', 'success');
        loadImageGallery();
    } catch (error) {
        showToast('Error deleting image', 'error');
    }
}

async function generateImage() {
    const prompt = document.getElementById('imagePrompt').value;
    const model = document.getElementById('imageModel').value;
    const width = document.getElementById('imageWidth').value;
    const height = document.getElementById('imageHeight').value;
    const seed = document.getElementById('imageSeed').value || '42069';

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
            seed: seed
        });

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
                <strong>Seed:</strong> ${seed}
            `;

            // Save to history
            await fetch('/api/ai/save-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: prompt,
                    url: currentImageURL,
                    model: model,
                    width: parseInt(width),
                    height: parseInt(height),
                    seed: seed
                })
            });

            showToast('Image generated successfully!', 'success');
            loadImageGallery();

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

async function loadChatHistory() {
    try {
        const response = await fetch('/api/ai/get-chats');
        const data = await response.json();

        const sidebar = document.getElementById('chatHistorySidebar');
        if (!sidebar) return;

        if (data.chats && data.chats.length > 0) {
            sidebar.innerHTML = data.chats.map(chat => `
                <div class="chat-history-item" onclick="loadSavedChat(${chat.id})" style="padding:12px; margin-bottom:8px; background:var(--bg-surface); border-radius:8px; cursor:pointer; border-left:3px solid var(--accent);">
                    <div style="font-weight:bold; margin-bottom:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${chat.name}</div>
                    <div style="font-size:11px; color:var(--text-secondary); display:flex; justify-content:space-between; align-items:center;">
                        <span><i class="fas fa-robot"></i> ${chat.model}</span>
                        <span>${new Date(chat.created_at).toLocaleDateString()}</span>
                    </div>
                </div>
            `).join('');
        } else {
            sidebar.innerHTML = '<div class="text-center text-muted" style="padding:20px;">No saved chats</div>';
        }
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

async function loadSavedChat(chatId) {
    try {
        const response = await fetch(`/api/ai/load-chat/${chatId}`);
        const data = await response.json();

        if (data.success) {
            chatHistory = data.messages;
            currentChatId = chatId;
            document.getElementById('chatModel').value = data.model;

            // Redraw messages
            const messagesDiv = document.getElementById('chatMessages');
            messagesDiv.innerHTML = '';
            chatHistory.forEach(msg => {
                addMessageToChat(msg.role, msg.content);
            });

            showToast(`Loaded: ${data.name}`, 'success');
        }
    } catch (error) {
        showToast('Error loading chat', 'error');
    }
}

async function saveCurrentChat() {
    if (chatHistory.length === 0) {
        showToast('No messages to save', 'error');
        return;
    }

    const name = prompt('Enter a name for this chat:', `Chat ${new Date().toLocaleDateString()}`);
    if (!name) return;

    try {
        const response = await fetch('/api/ai/save-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                messages: chatHistory,
                model: document.getElementById('chatModel').value
            })
        });

        const data = await response.json();
        if (data.success) {
            currentChatId = data.id;
            showToast('Chat saved successfully!', 'success');
            loadChatHistory();
        }
    } catch (error) {
        showToast('Error saving chat', 'error');
    }
}

function clearChat() {
    if (chatHistory.length > 0 && !confirm('Clear current chat? Unsaved messages will be lost.')) {
        return;
    }

    chatHistory = [];
    currentChatId = null;
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
        padding: 16px;
        border-radius: 12px;
        ${role === 'user'
            ? 'background: #2a2a2a; color: white; margin-left: 15%; border: 1px solid #444; box-shadow: 0 2px 8px rgba(0,0,0,0.3);'
            : 'background: var(--bg-surface); margin-right: 15%; border: 1px solid var(--border); box-shadow: 0 2px 8px rgba(0,0,0,0.1);'}
        ${isError ? 'background: #dc3545; color: white; margin: 0; border: 1px solid #c82333;' : ''}
    `;

    const header = document.createElement('div');
    header.style.cssText = 'font-weight: bold; margin-bottom: 8px; opacity: 0.9; font-size: 13px;';
    header.innerHTML = role === 'user' ? '<i class="fas fa-user-circle"></i> You' : role === 'error' ? '<i class="fas fa-exclamation-triangle"></i> Error' : '<i class="fas fa-robot"></i> AI Assistant';

    const contentDiv = document.createElement('div');
    contentDiv.style.cssText = 'white-space: pre-wrap; word-wrap: break-word; line-height: 1.6;';
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

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Load image gallery if on image gen page
    if (document.getElementById('imageGallery')) {
        loadImageGallery();
    }

    // Load chat history if on chatbot page
    if (document.getElementById('chatHistorySidebar')) {
        loadChatHistory();
    }
});

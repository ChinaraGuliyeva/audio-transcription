const UPLOAD_API_URL = "/upload";
const STATUS_API_URL = "/status"
const POLL_INTERVAL_MS = 3000;


const form = document.getElementById('uploadForm');
const fileInput = document.getElementById('audioFile');
const submitBtn = document.getElementById('submitBtn');
const submitBtnText = document.getElementById('submitBtnText');
const submitSpinner = document.getElementById('submitSpinner');
const resultBox = document.getElementById('resultBox');

const errorModalEl = document.getElementById('errorModal');
const errorModal = new bootstrap.Modal(errorModalEl);
const errorModalText = document.getElementById('errorModalText');

let pollTimer = null;

function showError(message) {
    errorModalText.textContent = message || 'Something went wrong.';
    errorModal.show();
    setSubmitting(false);
}

function setSubmitting(isSubmitting) {
    submitBtn.disabled = isSubmitting;
    submitBtnText.classList.toggle('d-none', isSubmitting);
    submitSpinner.classList.toggle('d-none', !isSubmitting);
}

function showProcessingMessage(text) {
    resultBox.classList.remove('d-none');
    resultBox.innerHTML = `<span class="blinking">${text}</span>`;
}

function showFinalResult(text) {
    resultBox.classList.remove('d-none');
    resultBox.innerHTML = `<span>${text}</span>`;
}

function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

async function pollStatus(taskId) {
    stopPolling();

    pollTimer = setInterval(async () => {
        try {
            const url = `${STATUS_API_URL}/${encodeURIComponent(taskId)}`;
            const response = await fetch(url, { method: 'GET' });

            if (!response.ok) {
                stopPolling();
                setSubmitting(false);
                showError(`Server error while checking status (code ${response.status}).`);
                return;
            }

            const data = await response.json();

            if (data.status === 'completed') {
                stopPolling();
                setSubmitting(false);
                showFinalResult(data.result ?? '');
            } else if (data.status === 'error' || data.status === 'failed') {
                stopPolling();
                setSubmitting(false);
                showError(data.message || 'Processing ended with an error.');
            }

        } catch (err) {
            stopPolling();
            setSubmitting(false);
            showError('Unable to contact the server while checking status.');
        }
    }, POLL_INTERVAL_MS);
}

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const file = fileInput.files[0];
    if (!file) {
        showError('Select an audio file.');
        return;
    }

    if (!file.type.startsWith('audio/') && !file.type.startsWith('video/')) {
        showError('Only audio and video files can be uploaded.');
        return;
    }

    setSubmitting(true);
    resultBox.classList.add('d-none');
    resultBox.innerHTML = '';

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(UPLOAD_API_URL, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            setSubmitting(false);
            showError(`File upload error (code ${response.status}).`);
            return;
        }

        const data = await response.json();

        if (!data.task_id) {
            setSubmitting(false);
            showError('Server error');
            return;
        }

        showProcessingMessage(data.message || 'Processing is running in the background');
        pollStatus(data.task_id);

    } catch (err) {
        setSubmitting(false);
        showError('Could not connect the server while downloading file.');
    }
});
const API_BASE = `${window.location.origin}/api`;

let currentTaskType = null;
let currentTask = null;
let mediaRecorder = null;
let recordedChunks = [];
let recordedBlob = null;
let recordingStartTime = null;
let recordingTimerInterval = null;

const mainContent = document.getElementById('main-content');
const taskSection = document.getElementById('task-section');
const resultSection = document.getElementById('result-section');
const loading = document.getElementById('loading');
const resultTaskTypeEl = document.getElementById('result-task-type');
const taskTitle = document.getElementById('task-title');
const instructions = document.getElementById('instructions');
const taskTextContent = document.getElementById('task-text-content');
const checkBtn = document.getElementById('check-btn');
const newTaskBtn = document.getElementById('new-task-btn');
const backBtn = document.getElementById('back-btn');
const scoreElement = document.getElementById('score');
const maxScoreElement = document.getElementById('max-score');
const feedbackText = document.getElementById('feedback-text');
const criteriaElement = document.getElementById('criteria');
const startRecordBtn = document.getElementById('start-record-btn');
const stopRecordBtn = document.getElementById('stop-record-btn');
const playRecordBtn = document.getElementById('play-record-btn');
const clearRecordBtn = document.getElementById('clear-record-btn');
const audioPreview = document.getElementById('audio-preview');
const recordingStatus = document.getElementById('recording-status');
const recordingTimer = document.getElementById('recording-timer');

const taskTypeNames = {
    reading: 'Чтение текста',
    retelling: 'Пересказ текста',
    monologue: 'Монолог'
};

document.querySelectorAll('.task-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const taskType = btn.dataset.type;
        loadTask(taskType);
    });
});

startRecordBtn.addEventListener('click', startRecording);
stopRecordBtn.addEventListener('click', stopRecording);
playRecordBtn.addEventListener('click', playRecording);
clearRecordBtn.addEventListener('click', clearRecording);
checkBtn.addEventListener('click', checkAnswer);
newTaskBtn.addEventListener('click', () => {
    if (currentTaskType) {
        loadTask(currentTaskType);
    }
});
backBtn.addEventListener('click', () => {
    resultSection.classList.add('hidden');
    taskSection.classList.remove('hidden');
});

async function loadTask(taskType) {
    currentTaskType = taskType;
    taskSection.classList.remove('hidden');
    resultSection.classList.add('hidden');
    resetRecording();
    
    try {
        const response = await fetch(`${API_BASE}/task/${taskType}`);
        if (!response.ok) {
            throw new Error('Ошибка загрузки задания');
        }
        
        currentTask = await response.json();
        displayTask(currentTask);
        mainContent.classList.add('task-selected');
    } catch (error) {
        alert('Ошибка при загрузке задания: ' + error.message);
        console.error(error);
    }
}

function displayTask(task) {
    taskTitle.textContent = taskTypeNames[task.task_type];
    instructions.textContent = task.instructions;
    
    if (task.task_type === 'reading' || task.task_type === 'retelling') {
        taskTextContent.innerHTML = `<p>${task.content.replace(/\n/g, '<br>')}</p>`;
    } else {
        taskTextContent.innerHTML = `<p><strong>Тема:</strong> ${task.content}</p>`;
    }
}

async function checkAnswer() {
    if (!currentTask) {
        alert('Сначала загрузите задание');
        return;
    }

    if (!recordedBlob) {
        alert('Пожалуйста, запишите ваш ответ, прежде чем отправлять его на проверку.');
        return;
    }
    
    loading.classList.remove('hidden');
    taskSection.classList.add('hidden');
    resultSection.classList.add('hidden');
    
    try {
        const formData = new FormData();
        formData.append('task_type', currentTask.task_type);
        if (currentTask.task_id !== undefined && currentTask.task_id !== null) {
            formData.append('task_id', String(currentTask.task_id));
        }
        const fileName = 'answer.webm';
        formData.append('audio', recordedBlob, fileName);

        const response = await fetch(`${API_BASE}/check-audio`, {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            throw new Error('Ошибка при проверке ответа');
        }
        
        const result = await response.json();
        displayResult(result);
    } catch (error) {
        alert('Ошибка при проверке ответа: ' + error.message);
        console.error(error);
        taskSection.classList.remove('hidden');
    } finally {
        loading.classList.add('hidden');
    }
}

function displayResult(result) {
    resultTaskTypeEl.textContent = taskTypeNames[currentTask.task_type] || currentTask.task_type;
    scoreElement.textContent = result.score;
    maxScoreElement.textContent = `из ${result.max_score}`;
    feedbackText.textContent = result.feedback;
    
    if (result.criteria && Object.keys(result.criteria).length > 0) {
        let criteriaHtml = '<h3>Критерии оценки:</h3><ul>';
        for (const [key, value] of Object.entries(result.criteria)) {
            if (key !== 'note') {
                criteriaHtml += `<li><strong>${key}:</strong> ${value}</li>`;
            }
        }
        criteriaHtml += '</ul>';
        criteriaElement.innerHTML = criteriaHtml;
    } else {
        criteriaElement.innerHTML = '';
    }
    
    resultSection.classList.remove('hidden');
}

function updateRecordingUI(state) {
    if (state === 'idle') {
        startRecordBtn.disabled = false;
        stopRecordBtn.disabled = true;
        playRecordBtn.disabled = !recordedBlob;
        clearRecordBtn.disabled = !recordedBlob;
        checkBtn.disabled = !recordedBlob;
        recordingStatus.textContent = 'Нажмите «Начать запись» и произнесите ответ.';
        recordingTimer.textContent = '00:00';
    } else if (state === 'recording') {
        startRecordBtn.disabled = true;
        stopRecordBtn.disabled = false;
        playRecordBtn.disabled = true;
        clearRecordBtn.disabled = true;
        checkBtn.disabled = true;
        recordingStatus.textContent = 'Идёт запись... Говорите в микрофон.';
    } else if (state === 'recorded') {
        startRecordBtn.disabled = false;
        stopRecordBtn.disabled = true;
        playRecordBtn.disabled = !recordedBlob;
        clearRecordBtn.disabled = !recordedBlob;
        checkBtn.disabled = !recordedBlob;
        recordingStatus.textContent = 'Запись готова. Вы можете прослушать её или отправить на проверку.';
    }
}

function formatTime(seconds) {
    const m = String(Math.floor(seconds / 60)).padStart(2, '0');
    const s = String(Math.floor(seconds % 60)).padStart(2, '0');
    return `${m}:${s}`;
}

function startTimer() {
    recordingStartTime = Date.now();
    recordingTimerInterval = setInterval(() => {
        const elapsedSec = (Date.now() - recordingStartTime) / 1000;
        recordingTimer.textContent = formatTime(elapsedSec);
    }, 500);
}

function stopTimer() {
    if (recordingTimerInterval) {
        clearInterval(recordingTimerInterval);
        recordingTimerInterval = null;
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recordedChunks = [];

        let options = {};
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
            options.mimeType = 'audio/webm;codecs=opus';
        }

        mediaRecorder = new MediaRecorder(stream, options);

        mediaRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            const blob = new Blob(recordedChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
            recordedBlob = blob;
            const url = URL.createObjectURL(blob);
            audioPreview.src = url;
            audioPreview.classList.remove('hidden');
            stopTimer();
            updateRecordingUI('recorded');

            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        startTimer();
        updateRecordingUI('recording');
    } catch (error) {
        console.error('Не удалось получить доступ к микрофону:', error);
        alert('Не удалось получить доступ к микрофону. Проверьте разрешения в браузере.');
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }
}

function playRecording() {
    if (audioPreview && recordedBlob) {
        audioPreview.play().catch((err) => {
            console.error('Ошибка при воспроизведении записи:', err);
        });
    }
}

function clearRecording() {
    recordedBlob = null;
    recordedChunks = [];
    if (audioPreview.src) {
        URL.revokeObjectURL(audioPreview.src);
    }
    audioPreview.src = '';
    audioPreview.classList.add('hidden');
    recordingTimer.textContent = '00:00';
    updateRecordingUI('idle');
}

function resetRecording() {
    clearRecording();
}

window.addEventListener('load', async () => {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();

        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/cd98caeb-34f0-4c65-ad20-ad54c2d79475', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: `log_${Date.now()}`,
                timestamp: Date.now(),
                location: 'script.js:155',
                message: 'health_check_success',
                data: { ai_available: !!data.ai_available, apiBase: API_BASE },
                runId: 'fix1',
                hypothesisId: 'H2',
            }),
        }).catch(() => {});
        // #endregion agent log

        if (!data.ai_available) {
            console.warn('ИИ проверка недоступна. Установите GEMINI_API_KEY в конфигурации (backend/conf.env) для полной функциональности.');
        }
    } catch (error) {
        console.error('Не удалось подключиться к API:', error);

        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/cd98caeb-34f0-4c65-ad20-ad54c2d79475', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: `log_${Date.now()}`,
                timestamp: Date.now(),
                location: 'script.js:165',
                message: 'health_check_error',
                data: { error: String(error), apiBase: API_BASE },
                runId: 'fix1',
                hypothesisId: 'H2',
            }),
        }).catch(() => {});
        // #endregion agent log

        alert('Не удалось подключиться к серверу. Убедитесь, что бэкенд запущен на http://127.0.0.1:8000');
    }
});


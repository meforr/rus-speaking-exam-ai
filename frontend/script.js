const API_BASE = 'http://127.0.0.1:8000/api';

let currentTaskType = null;
let currentTask = null;

// Элементы DOM
const taskSection = document.getElementById('task-section');
const resultSection = document.getElementById('result-section');
const loading = document.getElementById('loading');
const taskTitle = document.getElementById('task-title');
const instructions = document.getElementById('instructions');
const taskTextContent = document.getElementById('task-text-content');
const studentAnswer = document.getElementById('student-answer');
const checkBtn = document.getElementById('check-btn');
const newTaskBtn = document.getElementById('new-task-btn');
const backBtn = document.getElementById('back-btn');
const scoreElement = document.getElementById('score');
const maxScoreElement = document.getElementById('max-score');
const feedbackText = document.getElementById('feedback-text');
const criteriaElement = document.getElementById('criteria');

// Названия типов заданий
const taskTypeNames = {
    reading: 'Чтение текста',
    retelling: 'Пересказ текста',
    monologue: 'Монолог'
};

// Обработчики событий
document.querySelectorAll('.task-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const taskType = btn.dataset.type;
        loadTask(taskType);
    });
});

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

// Функции
async function loadTask(taskType) {
    currentTaskType = taskType;
    taskSection.classList.remove('hidden');
    resultSection.classList.add('hidden');
    studentAnswer.value = '';
    
    try {
        const response = await fetch(`${API_BASE}/task/${taskType}`);
        if (!response.ok) {
            throw new Error('Ошибка загрузки задания');
        }
        
        currentTask = await response.json();
        displayTask(currentTask);
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
    const answer = studentAnswer.value.trim();
    
    if (!answer) {
        alert('Пожалуйста, введите ваш ответ');
        return;
    }
    
    if (!currentTask) {
        alert('Сначала загрузите задание');
        return;
    }
    
    loading.classList.remove('hidden');
    taskSection.classList.add('hidden');
    resultSection.classList.add('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                task_type: currentTask.task_type,
                student_answer: answer,
                task_id: currentTask.task_id
            })
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
    scoreElement.textContent = result.score;
    maxScoreElement.textContent = `из ${result.max_score}`;
    feedbackText.textContent = result.feedback;
    
    // Отображение критериев
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

// Проверка доступности API при загрузке
window.addEventListener('load', async () => {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        if (!data.ai_available) {
            console.warn('⚠️ ИИ проверка недоступна. Установите OPENAI_API_KEY для полной функциональности.');
        }
    } catch (error) {
        console.error('Не удалось подключиться к API:', error);
        alert('⚠️ Не удалось подключиться к серверу. Убедитесь, что бэкенд запущен на http://127.0.0.1:8000');
    }
});


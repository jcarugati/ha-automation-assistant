/**
 * Automation Assistant Frontend
 */

// DOM Elements
const promptInput = document.getElementById('promptInput');
const generateBtn = document.getElementById('generateBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const errorMessage = document.getElementById('errorMessage');
const resultSection = document.getElementById('resultSection');
const explanation = document.getElementById('explanation');
const yamlOutput = document.getElementById('yamlOutput').querySelector('code');
const copyBtn = document.getElementById('copyBtn');
const validateBtn = document.getElementById('validateBtn');
const validationResult = document.getElementById('validationResult');
const showContextBtn = document.getElementById('showContextBtn');
const contextSummary = document.getElementById('contextSummary');
const contextModal = document.getElementById('contextModal');
const contextDetails = document.getElementById('contextDetails');
const closeModalBtn = document.getElementById('closeModalBtn');

// State
let currentYaml = '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadContextSummary();
    setupEventListeners();
});

function setupEventListeners() {
    generateBtn.addEventListener('click', generateAutomation);
    copyBtn.addEventListener('click', copyYaml);
    validateBtn.addEventListener('click', validateYaml);
    showContextBtn.addEventListener('click', showContext);
    closeModalBtn.addEventListener('click', hideContext);
    contextModal.addEventListener('click', (e) => {
        if (e.target === contextModal) hideContext();
    });

    // Allow Ctrl+Enter to generate
    promptInput.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            generateAutomation();
        }
    });
}

async function loadContextSummary() {
    try {
        const response = await fetch('/api/context');
        if (response.ok) {
            const data = await response.json();
            contextSummary.textContent =
                `${data.entity_count} entities | ${data.device_count} devices | ${data.area_count} areas`;
        }
    } catch (error) {
        console.error('Failed to load context summary:', error);
    }
}

async function generateAutomation() {
    const prompt = promptInput.value.trim();
    if (!prompt) {
        showError('Please enter an automation description.');
        return;
    }

    hideError();
    hideResult();
    showLoading();
    generateBtn.disabled = true;

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to generate automation');
        }

        if (!data.success) {
            throw new Error(data.error || 'Generation failed');
        }

        displayResult(data);

    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
        generateBtn.disabled = false;
    }
}

function displayResult(data) {
    // Extract explanation (everything before the YAML block)
    const response = data.response;
    let explanationText = response;

    // Try to split at the YAML block
    const yamlMatch = response.match(/```yaml[\s\S]*?```/);
    if (yamlMatch) {
        const yamlIndex = response.indexOf(yamlMatch[0]);
        explanationText = response.substring(0, yamlIndex).trim();

        // Also get any text after the YAML block
        const afterYaml = response.substring(yamlIndex + yamlMatch[0].length).trim();
        if (afterYaml) {
            explanationText += '\n\n' + afterYaml;
        }
    }

    explanation.textContent = explanationText;

    // Display YAML
    currentYaml = data.yaml_content || 'No YAML extracted';
    yamlOutput.textContent = currentYaml;

    resultSection.classList.remove('hidden');
    hideValidation();
}

async function validateYaml() {
    if (!currentYaml) return;

    try {
        const response = await fetch('/api/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ yaml_content: currentYaml }),
        });

        const data = await response.json();
        showValidation(data);

    } catch (error) {
        showValidation({ valid: false, errors: [error.message] });
    }
}

function showValidation(result) {
    validationResult.classList.remove('hidden', 'valid', 'invalid');

    if (result.valid) {
        validationResult.classList.add('valid');
        validationResult.textContent = 'Valid automation YAML';
    } else {
        validationResult.classList.add('invalid');
        validationResult.innerHTML = '<strong>Validation errors:</strong><br>' +
            result.errors.map(e => '- ' + e).join('<br>');
    }
}

function hideValidation() {
    validationResult.classList.add('hidden');
}

function copyYaml() {
    if (!currentYaml) return;

    navigator.clipboard.writeText(currentYaml).then(() => {
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        setTimeout(() => {
            copyBtn.textContent = originalText;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        showError('Failed to copy to clipboard');
    });
}

async function showContext() {
    try {
        const response = await fetch('/api/context');
        if (response.ok) {
            const data = await response.json();
            displayContextModal(data);
        }
    } catch (error) {
        showError('Failed to load context: ' + error.message);
    }
}

function displayContextModal(data) {
    contextDetails.innerHTML = `
        <div class="context-item">
            <h4>Entities</h4>
            <div class="value">${data.entity_count}</div>
        </div>
        <div class="context-item">
            <h4>Devices</h4>
            <div class="value">${data.device_count}</div>
        </div>
        <div class="context-item">
            <h4>Areas</h4>
            <div class="value">${data.area_count}</div>
        </div>
        <div class="context-item">
            <h4>Services</h4>
            <div class="value">${data.service_count}</div>
        </div>
        <div class="context-item">
            <h4>Domains</h4>
            <div class="domains">
                ${data.domains.map(d => `<span class="domain-tag">${d}</span>`).join('')}
            </div>
        </div>
    `;
    contextModal.classList.remove('hidden');
}

function hideContext() {
    contextModal.classList.add('hidden');
}

function showLoading() {
    loadingIndicator.classList.remove('hidden');
}

function hideLoading() {
    loadingIndicator.classList.add('hidden');
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
}

function hideError() {
    errorMessage.classList.add('hidden');
}

function hideResult() {
    resultSection.classList.add('hidden');
}

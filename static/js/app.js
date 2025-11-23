/**
 * Brazilian Roulette Assistant - Frontend Application
 * Arquitetura modular com gerenciamento de estado centralizado.
 * @version 4.0.0
 */

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

const AppState = {
    bankroll: 0,
    strategies: {},
    warmupNumbers: [],
    initialized: false,
    currentScreen: 'setup'
};

// ============================================================================
// CONSTANTS
// ============================================================================

const RED_NUMBERS = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]);

const NOMENCLATURE = {
    'R': 'vermelho', 'B': 'preto',
    'D1': '1a duzia', 'D2': '2a duzia', 'D3': '3a duzia',
    'C1': '1a coluna', 'C2': '2a coluna', 'C3': '3a coluna',
    'PAR': 'par', 'IMPAR': 'impar',
    'BAIXO': 'baixo (1-18)', 'ALTO': 'alto (19-36)'
};

const STRATEGY_NAMES = {
    'COR': 'Cor',
    'PAR_IMPAR': 'Par/Impar',
    'ALTO_BAIXO': 'Alto/Baixo',
    'DUZIA': 'Duzias',
    'COLUNA': 'Colunas',
    'FRIO': 'Numeros Frios'
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Formata valor para moeda brasileira.
 * @param {number} value - Valor a ser formatado
 * @returns {string} Valor formatado
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

/**
 * Retorna a cor de um numero da roleta.
 * @param {string|number} num - Numero da roleta
 * @returns {string} 'red', 'black' ou 'green'
 */
function getNumberColor(num) {
    const n = parseInt(num);
    if (num === '0' || num === '00' || n === 0) return 'green';
    return RED_NUMBERS.has(n) ? 'red' : 'black';
}

/**
 * Valida se um numero da roleta e valido.
 * @param {string|number} num - Numero a validar
 * @returns {boolean} Se e valido
 */
function isValidRouletteNumber(num) {
    if (num === '00') return true;
    const n = parseInt(num);
    return !isNaN(n) && n >= 0 && n <= 36;
}

// ============================================================================
// UI UTILITIES
// ============================================================================

/**
 * Exibe o overlay de carregamento.
 */
function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('active');
        overlay.setAttribute('aria-hidden', 'false');
    }
}

/**
 * Esconde o overlay de carregamento.
 */
function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('active');
        overlay.setAttribute('aria-hidden', 'true');
    }
}

/**
 * Exibe uma notificacao toast.
 * @param {string} message - Mensagem a exibir
 * @param {string} type - Tipo: 'success', 'error', 'warning'
 */
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

/**
 * Troca para uma tela especifica.
 * @param {string} screenId - ID da tela
 */
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });

    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.classList.add('active');
        AppState.currentScreen = screenId.replace('Screen', '');

        // Focus management for accessibility
        const firstFocusable = targetScreen.querySelector('input, button, select, textarea');
        if (firstFocusable) {
            setTimeout(() => firstFocusable.focus(), 100);
        }
    }
}

/**
 * Abre o modal de confirmacao.
 */
function openModal() {
    const modal = document.getElementById('confirmModal');
    if (modal) {
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
    }
}

/**
 * Fecha o modal de confirmacao.
 */
function closeModal() {
    const modal = document.getElementById('confirmModal');
    if (modal) {
        modal.classList.remove('active');
        modal.setAttribute('aria-hidden', 'true');
    }
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Realiza uma requisicao para a API.
 * @param {string} endpoint - Endpoint da API
 * @param {object} options - Opcoes do fetch
 * @returns {Promise<object>} Resposta da API
 */
async function apiRequest(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };

    const finalOptions = { ...defaultOptions, ...options };

    try {
        const response = await fetch(endpoint, finalOptions);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Erro na requisicao');
        }

        return data;
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}

// ============================================================================
// SETUP SCREEN
// ============================================================================

/**
 * Processa o formulario de setup e avanca para warmup.
 * @param {Event} event - Evento do formulario
 */
async function goToWarmup(event) {
    if (event) event.preventDefault();

    const bankrollInput = document.getElementById('bankroll');
    const bankroll = parseFloat(bankrollInput.value);

    // Validacao
    if (!bankroll || bankroll <= 0) {
        showToast('Por favor, insira uma banca valida', 'error');
        bankrollInput.focus();
        return;
    }

    // Coleta estrategias selecionadas
    const strategies = {};
    document.querySelectorAll('.strategy-checkbox input[type="checkbox"]').forEach(checkbox => {
        strategies[checkbox.value] = checkbox.checked;
    });

    // Verifica se pelo menos uma estrategia foi selecionada
    const hasActiveStrategy = Object.values(strategies).some(v => v === true);
    if (!hasActiveStrategy) {
        showToast('Selecione pelo menos uma estrategia', 'error');
        return;
    }

    // Salva no estado
    AppState.bankroll = bankroll;
    AppState.strategies = strategies;

    // Inicializa backend
    showLoading();

    try {
        const data = await apiRequest('/api/initialize', {
            method: 'POST',
            body: JSON.stringify({
                bankroll: bankroll,
                strategies: strategies
            })
        });

        hideLoading();

        if (data.success) {
            showScreen('warmupScreen');
            showToast('Configuracao salva com sucesso!');
        } else {
            showToast(data.error || 'Erro ao inicializar', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('Erro ao conectar com o servidor', 'error');
    }
}

// ============================================================================
// WARMUP SCREEN
// ============================================================================

/**
 * Adiciona um numero ao warmup.
 * @param {Event} event - Evento do formulario
 */
function addWarmupNumber(event) {
    if (event) event.preventDefault();

    const input = document.getElementById('warmupInput');
    const num = input.value.trim();

    if (num === '') return;

    if (!isValidRouletteNumber(num)) {
        showToast('Numero invalido! Use 0-36', 'error');
        input.value = '';
        input.focus();
        return;
    }

    if (AppState.warmupNumbers.length >= 12) {
        showToast('Maximo de 12 numeros atingido', 'warning');
        return;
    }

    AppState.warmupNumbers.push(num);
    updateWarmupDisplay();

    input.value = '';
    input.focus();

    if (AppState.warmupNumbers.length === 12) {
        document.getElementById('startGameBtn').disabled = false;
        showToast('12 numeros inseridos! Pronto para comecar', 'success');
    }
}

/**
 * Limpa todos os numeros do warmup.
 */
function clearWarmup() {
    AppState.warmupNumbers = [];
    updateWarmupDisplay();
    document.getElementById('startGameBtn').disabled = true;
    document.getElementById('warmupInput').focus();
}

/**
 * Atualiza a exibicao do warmup.
 */
function updateWarmupDisplay() {
    const container = document.getElementById('warmupNumbers');
    const count = AppState.warmupNumbers.length;

    // Atualiza barra de progresso
    const progressBar = document.getElementById('warmupProgressBar');
    const progressPercent = (count / 12) * 100;
    progressBar.style.width = `${progressPercent}%`;

    // Atualiza contador
    document.getElementById('warmupCount').textContent = count;

    // Atualiza ARIA
    const progressContainer = document.querySelector('.warmup-progress');
    if (progressContainer) {
        progressContainer.setAttribute('aria-valuenow', count);
    }

    // Atualiza display de numeros
    if (count === 0) {
        container.innerHTML = '<p class="warmup-empty">Nenhum numero adicionado</p>';
    } else {
        container.innerHTML = AppState.warmupNumbers.map((num, index) => {
            const color = getNumberColor(num);
            return `<div class="warmup-number-tag ${color}" title="Numero ${index + 1}">
                ${num}
                <button type="button" class="remove-number" onclick="removeWarmupNumber(${index})" aria-label="Remover numero ${num}">x</button>
            </div>`;
        }).join('');
    }
}

/**
 * Remove um numero do warmup.
 * @param {number} index - Indice do numero
 */
function removeWarmupNumber(index) {
    AppState.warmupNumbers.splice(index, 1);
    updateWarmupDisplay();
    document.getElementById('startGameBtn').disabled = AppState.warmupNumbers.length !== 12;
}

/**
 * Inicia o jogo apos o warmup.
 */
async function startGame() {
    if (AppState.warmupNumbers.length !== 12) {
        showToast('Insira exatamente 12 numeros', 'error');
        return;
    }

    showLoading();

    try {
        const data = await apiRequest('/api/warmup', {
            method: 'POST',
            body: JSON.stringify({
                numbers: AppState.warmupNumbers
            })
        });

        hideLoading();

        if (data.success) {
            AppState.initialized = true;
            showScreen('gameScreen');
            updateStats();
            showToast('Sistema iniciado com sucesso!');
        } else {
            showToast(data.error || 'Erro ao aquecer sistema', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('Erro ao conectar com o servidor', 'error');
    }
}

// ============================================================================
// GAME SCREEN
// ============================================================================

/**
 * Processa um novo spin da roleta.
 * @param {Event} event - Evento do formulario
 */
async function processSpin(event) {
    if (event) event.preventDefault();

    const input = document.getElementById('numberInput');
    const num = input.value.trim();

    if (num === '') return;

    if (!isValidRouletteNumber(num)) {
        showToast('Numero invalido! Use 0-36', 'error');
        input.value = '';
        input.focus();
        return;
    }

    showLoading();

    try {
        const data = await apiRequest('/api/spin', {
            method: 'POST',
            body: JSON.stringify({ number: num })
        });

        hideLoading();

        if (data.success) {
            updateGameDisplay(data);
            input.value = '';
            input.focus();
        } else {
            showToast(data.error || 'Erro ao processar numero', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('Erro ao conectar com o servidor', 'error');
    }
}

/**
 * Atualiza toda a exibicao do jogo.
 * @param {object} data - Dados retornados pela API
 */
function updateGameDisplay(data) {
    // Atualiza estatisticas
    updateBankrollDisplay(data.bankroll, data.profit_loss);
    document.getElementById('totalSpins').textContent = data.history.length;

    // Atualiza ultimo numero
    updateLastNumber(data.number, data.color);

    // Atualiza acao recomendada
    updateAction(data);

    // Atualiza sinais ativos
    updateSignals(data.signals);

    // Atualiza historico
    updateHistory(data.history);

    // Atualiza numeros quentes/frios
    updateHotCold(data.hot_numbers, data.cold_numbers);
}

/**
 * Atualiza a exibicao da banca.
 * @param {number} bankroll - Banca atual
 * @param {number} profitLoss - Lucro/Prejuizo
 */
function updateBankrollDisplay(bankroll, profitLoss) {
    const bankrollEl = document.getElementById('currentBankroll');
    const plEl = document.getElementById('profitLoss');

    bankrollEl.textContent = formatCurrency(bankroll);

    plEl.textContent = formatCurrency(Math.abs(profitLoss));
    plEl.className = 'stat-value';

    if (profitLoss > 0) {
        plEl.classList.add('positive');
        plEl.textContent = '+' + plEl.textContent;
    } else if (profitLoss < 0) {
        plEl.classList.add('negative');
        plEl.textContent = '-' + plEl.textContent;
    }
}

/**
 * Atualiza o ultimo numero exibido.
 * @param {string} number - Numero
 * @param {string} color - Cor (R, B, G)
 */
function updateLastNumber(number, color) {
    const container = document.getElementById('lastNumber');
    const colorClass = color === 'R' ? 'red' : (color === 'B' ? 'black' : 'green');

    container.innerHTML = `
        <p class="last-number-label">Ultimo numero:</p>
        <div class="number-badge ${colorClass}">${number}</div>
    `;
}

/**
 * Atualiza a acao recomendada.
 * @param {object} data - Dados do spin
 */
function updateAction(data) {
    const actionContent = document.getElementById('actionContent');

    if (data.signals && data.signals.length > 0) {
        const instructions = data.signals.map(signal => {
            const term = NOMENCLATURE[signal.target] || signal.target;
            const amount = formatCurrency(signal.amount);

            if (signal.strategy === 'DUZIA' || signal.strategy === 'COLUNA') {
                return `${amount} na ${term}`;
            } else if (signal.strategy === 'FRIO') {
                return `${amount} no numero ${signal.target}`;
            } else {
                return `${amount} no ${term}`;
            }
        });

        const finalText = instructions.join(' e ');
        actionContent.innerHTML = `<p class="action-instruction">${finalText}</p>`;
    } else {
        actionContent.innerHTML = '<p class="waiting-signal">Aguarde Sinal...</p>';
    }
}

/**
 * Atualiza os sinais ativos.
 * @param {Array} signals - Lista de sinais
 */
function updateSignals(signals) {
    const container = document.getElementById('signalsContent');

    if (!signals || signals.length === 0) {
        container.innerHTML = '<p class="no-signals">Nenhum sinal ativo</p>';
        return;
    }

    container.innerHTML = signals.map(signal => {
        const strategyName = STRATEGY_NAMES[signal.strategy] || signal.strategy;
        const term = NOMENCLATURE[signal.target] || signal.target;

        return `
            <div class="signal-item">
                <div class="signal-strategy">${strategyName}</div>
                <div class="signal-details">
                    Aposta: ${formatCurrency(signal.amount)} em ${term}
                    ${signal.losses > 0 ? ` - Perdas: ${signal.losses}` : ''}
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Atualiza o historico de numeros.
 * @param {Array} history - Lista de numeros
 */
function updateHistory(history) {
    const container = document.getElementById('historyContent');

    if (!history || history.length === 0) {
        container.innerHTML = '<p class="no-history">Nenhum historico ainda</p>';
        return;
    }

    // Mostra os ultimos 20, mais recente primeiro
    const recent = history.slice(-20).reverse();

    container.innerHTML = recent.map(num => {
        const color = getNumberColor(num);
        return `<div class="history-number ${color}">${num}</div>`;
    }).join('');
}

/**
 * Atualiza os numeros quentes e frios.
 * @param {Array} hotNumbers - Numeros quentes
 * @param {Array} coldNumbers - Numeros frios
 */
function updateHotCold(hotNumbers, coldNumbers) {
    const hotContainer = document.getElementById('hotNumbers');
    const coldContainer = document.getElementById('coldNumbers');

    if (hotNumbers && hotNumbers.length > 0) {
        hotContainer.innerHTML = hotNumbers.map(num =>
            `<span class="number-tag hot">${num}</span>`
        ).join('');
    } else {
        hotContainer.innerHTML = '<span class="number-tag hot">-</span>';
    }

    if (coldNumbers && coldNumbers.length > 0) {
        coldContainer.innerHTML = coldNumbers.map(num =>
            `<span class="number-tag cold">${num}</span>`
        ).join('');
    } else {
        coldContainer.innerHTML = '<span class="number-tag cold">-</span>';
    }
}

/**
 * Atualiza as estatisticas.
 */
async function updateStats() {
    try {
        const data = await apiRequest('/api/stats');

        if (data.success) {
            updateBankrollDisplay(data.bankroll, data.profit_loss);
            document.getElementById('totalSpins').textContent = data.total_spins;
            updateHotCold(data.hot_numbers, data.cold_numbers);
            updateHistory(data.history);
        }
    } catch (error) {
        console.error('Erro ao buscar estatisticas:', error);
    }
}

// ============================================================================
// RESET FUNCTIONS
// ============================================================================

/**
 * Exibe confirmacao de reset.
 */
function confirmReset() {
    openModal();
}

/**
 * Executa o reset da sessao.
 */
async function executeReset() {
    closeModal();
    showLoading();

    try {
        const data = await apiRequest('/api/reset', {
            method: 'POST'
        });

        hideLoading();

        if (data.success) {
            // Reseta estado local
            AppState.bankroll = 0;
            AppState.strategies = {};
            AppState.warmupNumbers = [];
            AppState.initialized = false;

            // Volta para tela inicial
            showScreen('setupScreen');
            showToast('Sessao encerrada com sucesso');
        } else {
            showToast(data.error || 'Erro ao resetar', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('Erro ao conectar com o servidor', 'error');
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Inicializa display do warmup
    updateWarmupDisplay();

    // Focus inicial
    setTimeout(() => {
        const bankrollInput = document.getElementById('bankroll');
        if (bankrollInput) bankrollInput.focus();
    }, 300);
});

// ============================================================================
// GLOBAL EXPORTS
// ============================================================================

window.goToWarmup = goToWarmup;
window.addWarmupNumber = addWarmupNumber;
window.clearWarmup = clearWarmup;
window.removeWarmupNumber = removeWarmupNumber;
window.startGame = startGame;
window.processSpin = processSpin;
window.confirmReset = confirmReset;
window.executeReset = executeReset;
window.closeModal = closeModal;

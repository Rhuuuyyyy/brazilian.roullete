// ========================================
// Brazilian Roulette Assistant - Frontend
// ========================================

// State Management
const state = {
    bankroll: 0,
    strategies: {},
    warmupNumbers: [],
    initialized: false
};

// Utility Functions
function showLoading() {
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function getNumberColor(num) {
    const redNumbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
    if (num === '0' || num === '00') return 'green';
    return redNumbers.includes(parseInt(num)) ? 'red' : 'black';
}

// Setup Functions
function goToWarmup() {
    const bankrollInput = document.getElementById('bankroll');
    const bankroll = parseFloat(bankrollInput.value);

    if (!bankroll || bankroll <= 0) {
        showToast('Por favor, insira uma banca válida', 'error');
        bankrollInput.focus();
        return;
    }

    // Get selected strategies
    const strategies = {};
    document.querySelectorAll('.strategy-checkbox input[type="checkbox"]').forEach(checkbox => {
        strategies[checkbox.value] = checkbox.checked;
    });

    // Check if at least one strategy is selected
    const hasActiveStrategy = Object.values(strategies).some(v => v === true);
    if (!hasActiveStrategy) {
        showToast('Selecione pelo menos uma estratégia', 'error');
        return;
    }

    // Save to state
    state.bankroll = bankroll;
    state.strategies = strategies;

    // Initialize backend
    showLoading();
    fetch('/api/initialize', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            bankroll: bankroll,
            strategies: strategies
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showScreen('warmupScreen');
            showToast('Configuração salva com sucesso!');
            // Focus on warmup input
            setTimeout(() => {
                document.getElementById('warmupInput').focus();
            }, 300);
        } else {
            showToast(data.error || 'Erro ao inicializar', 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        showToast('Erro ao conectar com o servidor', 'error');
    });
}

// Warmup Functions
function addWarmupNumber() {
    const input = document.getElementById('warmupInput');
    const num = input.value.trim();

    if (num === '') return;

    const numInt = parseInt(num);
    if (isNaN(numInt) || numInt < 0 || numInt > 36) {
        showToast('Número inválido! Use 0-36', 'error');
        input.value = '';
        input.focus();
        return;
    }

    if (state.warmupNumbers.length >= 12) {
        showToast('Máximo de 12 números atingido', 'error');
        return;
    }

    state.warmupNumbers.push(num);
    updateWarmupDisplay();

    input.value = '';
    input.focus();

    if (state.warmupNumbers.length === 12) {
        document.getElementById('startGameBtn').disabled = false;
        showToast('12 números inseridos! Pronto para começar', 'success');
    }
}

function updateWarmupDisplay() {
    const container = document.getElementById('warmupNumbers');
    const count = state.warmupNumbers.length;

    // Update progress bar
    const progressBar = document.getElementById('warmupProgressBar');
    progressBar.style.width = `${(count / 12) * 100}%`;

    // Update count
    document.getElementById('warmupCount').textContent = count;

    // Update numbers display
    container.innerHTML = state.warmupNumbers.map((num, index) => {
        const color = getNumberColor(num);
        return `<div class="warmup-number-tag" style="order: ${12 - index}">
            ${num}
        </div>`;
    }).join('');
}

function startGame() {
    if (state.warmupNumbers.length !== 12) {
        showToast('Insira exatamente 12 números', 'error');
        return;
    }

    showLoading();
    fetch('/api/warmup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            numbers: state.warmupNumbers
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            state.initialized = true;
            showScreen('gameScreen');
            updateStats();
            showToast('Sistema iniciado com sucesso!');
            // Focus on number input
            setTimeout(() => {
                document.getElementById('numberInput').focus();
            }, 300);
        } else {
            showToast(data.error || 'Erro ao aquecer sistema', 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        showToast('Erro ao conectar com o servidor', 'error');
    });
}

// Game Functions
function processSpin() {
    const input = document.getElementById('numberInput');
    const num = input.value.trim();

    if (num === '') return;

    const numInt = parseInt(num);
    if (isNaN(numInt) || numInt < 0 || numInt > 36) {
        showToast('Número inválido! Use 0-36', 'error');
        input.value = '';
        input.focus();
        return;
    }

    showLoading();
    fetch('/api/spin', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            number: num
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            updateGameDisplay(data);
            input.value = '';
            input.focus();
        } else {
            showToast(data.error || 'Erro ao processar número', 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        showToast('Erro ao conectar com o servidor', 'error');
    });
}

function updateGameDisplay(data) {
    // Update stats
    const currentBankroll = document.getElementById('currentBankroll');
    const profitLoss = document.getElementById('profitLoss');
    const totalSpins = document.getElementById('totalSpins');

    currentBankroll.textContent = formatCurrency(data.bankroll);

    const pl = data.profit_loss;
    profitLoss.textContent = formatCurrency(Math.abs(pl));
    profitLoss.className = 'stat-value';
    if (pl > 0) {
        profitLoss.classList.add('positive');
        profitLoss.textContent = '+' + profitLoss.textContent;
    } else if (pl < 0) {
        profitLoss.classList.add('negative');
        profitLoss.textContent = '-' + profitLoss.textContent;
    }

    totalSpins.textContent = data.history.length;

    // Update last number
    const lastNumber = document.getElementById('lastNumber');
    const color = getNumberColor(data.number);
    lastNumber.innerHTML = `
        <p style="margin-bottom: 8px; color: var(--text-secondary);">Último número:</p>
        <div class="number-badge ${color}">${data.number}</div>
    `;

    // Update action
    updateAction(data);

    // Update signals
    updateSignals(data.signals);

    // Update history
    updateHistory(data.history);

    // Update hot/cold numbers
    updateHotCold(data.hot_numbers, data.cold_numbers);
}

function updateAction(data) {
    const actionContent = document.getElementById('actionContent');

    if (data.signals && data.signals.length > 0) {
        const instructions = [];

        data.signals.forEach(signal => {
            const nomenclature = {
                'R': 'vermelho', 'B': 'preto',
                'D1': '1ª dúzia', 'D2': '2ª dúzia', 'D3': '3ª dúzia',
                'C1': '1ª coluna', 'C2': '2ª coluna', 'C3': '3ª coluna',
                'PAR': 'par', 'IMPAR': 'ímpar',
                'BAIXO': 'baixo (1-18)', 'ALTO': 'alto (19-36)'
            };

            const term = nomenclature[signal.target] || signal.target;
            const amount = formatCurrency(signal.amount);

            if (signal.strategy === 'DUZIA' || signal.strategy === 'COLUNA') {
                instructions.push(`${amount} na ${term}`);
            } else if (signal.strategy === 'FRIO') {
                instructions.push(`${amount} no número ${signal.target}`);
            } else {
                instructions.push(`${amount} no ${term}`);
            }
        });

        const finalText = instructions.join(' e ');
        actionContent.innerHTML = `<p class="action-instruction">💰 ${finalText}</p>`;
    } else {
        actionContent.innerHTML = '<p class="waiting-signal">Aguarde Sinal...</p>';
    }
}

function updateSignals(signals) {
    const signalsContent = document.getElementById('signalsContent');

    if (!signals || signals.length === 0) {
        signalsContent.innerHTML = '<p class="no-signals">Nenhum sinal ativo</p>';
        return;
    }

    signalsContent.innerHTML = signals.map(signal => {
        const strategyNames = {
            'COR': 'Cor',
            'PAR_IMPAR': 'Par/Ímpar',
            'ALTO_BAIXO': 'Alto/Baixo',
            'DUZIA': 'Dúzias',
            'COLUNA': 'Colunas',
            'FRIO': 'Números Frios'
        };

        return `
            <div class="signal-item">
                <div class="signal-strategy">${strategyNames[signal.strategy] || signal.strategy}</div>
                <div class="signal-details">
                    Aposta: ${formatCurrency(signal.amount)} em ${signal.target}
                    ${signal.losses > 0 ? ` • Perdas: ${signal.losses}` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function updateHistory(history) {
    const historyContent = document.getElementById('historyContent');

    if (!history || history.length === 0) {
        historyContent.innerHTML = '<p class="no-history">Nenhum histórico ainda</p>';
        return;
    }

    // Show last 20 numbers, most recent first
    const recent = history.slice(-20).reverse();

    historyContent.innerHTML = recent.map(num => {
        const color = getNumberColor(num);
        return `<div class="history-number ${color}">${num}</div>`;
    }).join('');
}

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

function updateStats() {
    fetch('/api/stats')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('currentBankroll').textContent = formatCurrency(data.bankroll);

            const pl = data.profit_loss;
            const profitLoss = document.getElementById('profitLoss');
            profitLoss.textContent = formatCurrency(Math.abs(pl));
            profitLoss.className = 'stat-value';
            if (pl > 0) {
                profitLoss.classList.add('positive');
                profitLoss.textContent = '+' + profitLoss.textContent;
            } else if (pl < 0) {
                profitLoss.classList.add('negative');
                profitLoss.textContent = '-' + profitLoss.textContent;
            }

            document.getElementById('totalSpins').textContent = data.total_spins;
        }
    })
    .catch(error => {
        console.error('Error fetching stats:', error);
    });
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Allow Enter key on inputs
    document.getElementById('bankroll')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            goToWarmup();
        }
    });

    document.getElementById('warmupInput')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            addWarmupNumber();
        }
    });

    document.getElementById('numberInput')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            processSpin();
        }
    });

    // Auto-focus on first input
    setTimeout(() => {
        document.getElementById('bankroll')?.focus();
    }, 500);
});

// Make functions globally available
window.goToWarmup = goToWarmup;
window.addWarmupNumber = addWarmupNumber;
window.startGame = startGame;
window.processSpin = processSpin;

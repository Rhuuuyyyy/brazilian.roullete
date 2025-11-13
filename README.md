# 🎰 Brazilian Roulette Assistant v3.0 Professional

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Professional](https://img.shields.io/badge/code%20style-professional-brightgreen.svg)](https://github.com/psf/black)

A sophisticated roulette betting strategy system that analyzes spin patterns and applies multiple betting strategies including Martingale progression, sequence analysis, and cold number tracking.

## 📋 Features

### Core Functionality
- **Multiple Betting Strategies**: 6 different strategy types
  - 🔴 **Color** (Red/Black)
  - ⚖️ **Even/Odd** (Par/Ímpar)
  - 📊 **High/Low** (Alto/Baixo 1-18/19-36)
  - 📦 **Dozens** (1ª, 2ª, 3ª Dúzia)
  - 📋 **Columns** (1ª, 2ª, 3ª Coluna)
  - 🧊 **Cold Numbers** (Números Frios)

### Professional Features
- ✅ **Object-Oriented Architecture**: Clean, maintainable code with SOLID principles
- ✅ **Type Safety**: Complete type hints for better IDE support and error prevention
- ✅ **Error Handling**: Custom exceptions and robust error management
- ✅ **Configuration**: External JSON configuration file
- ✅ **Logging**: Professional logging system with multiple levels
- ✅ **Rich UI**: Beautiful console interface with colors and tables
- ✅ **Testing**: Comprehensive unit tests included
- ✅ **Documentation**: Full docstrings and inline documentation

### Advanced Strategies
- **Martingale Progression**: Configurable multiplier (default 2x)
- **La Partage Rule**: European roulette advantage - lose only 50% on zero for 1:1 bets
- **Sequence Detection**: Automatically detects betting patterns
- **Cold Number Tracking**: Identifies numbers with longest delays
- **Signal Strength Analysis**: Measures confidence of betting signals
- **Bankroll Management**: Sophisticated money management system

## 🚀 Installation

### Requirements
- Python 3.8 or higher
- pip (Python package installer)

### Quick Start

1. **Clone the repository**:
```bash
git clone <repository-url>
cd brazilian.roullete
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Run the assistant**:
```bash
python roulette_assistant.py
```

## ⚙️ Configuration

Configuration is stored in `config.json`:

```json
{
  "initial_bet": 0.5,
  "martingale_factor": 2.0,
  "max_consecutive_losses": 4,
  "la_partage_enabled": true,
  "min_sequence_simple": 3,
  "min_sequence_dozen": 2,
  "min_cold_number_delay": 37,
  "roulette_type": "EUROPEAN",
  "warmup_spins": 12
}
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `initial_bet` | float | 0.5 | Initial bet amount in R$ |
| `martingale_factor` | float | 2.0 | Multiplier for Martingale progression |
| `max_consecutive_losses` | int | 4 | Maximum consecutive losses before reset |
| `la_partage_enabled` | bool | true | Enable La Partage rule for European roulette |
| `min_sequence_simple` | int | 3 | Minimum sequence for 1:1 bets |
| `min_sequence_dozen` | int | 2 | Minimum sequence for 2:1 bets |
| `min_cold_number_delay` | int | 37 | Minimum spins before betting on cold number |
| `roulette_type` | string | "EUROPEAN" | Roulette type: "EUROPEAN" or "AMERICAN" |
| `warmup_spins` | int | 12 | Number of initial spins for system warmup |

## 📖 Usage Guide

### Starting the Assistant

```bash
python roulette_assistant.py
```

### Interactive Setup

1. **Enter Initial Bankroll**:
```
Qual o valor da sua banca inicial? R$ 100
```

2. **Select Active Strategies**:
```
Ativar estratégia COR? (S/N): S
Ativar estratégia PAR_IMPAR? (S/N): S
...
```

3. **Warmup Phase** (12 spins):
```
Digite o 1º resultado (mais recente): 17
Digite o 2º resultado: 23
...
```

4. **Live Session**:
```
Próximo número: 5
```

### Understanding Output

```
➡️ CAIU: 5 (VERMELHO, ÍMPAR) | Banca: R$ 98.50
────────────────────────────────────────
💰 SINAL (COR): Sequência de 3x PRETO detectada. Apostar em VERMELHO.
✅ VITÓRIA (COR)! Ganhos: R$ 1.00. RESET.
🎯 AÇÃO: R$ 0.50 no vermelho
────────────────────────────────────────
Banca Inicial:  R$ 100.00
Banca Atual:    R$ 99.00
Resultado:      -R$ 1.00
ROI:            -1.00%
```

### Output Symbols

- ➡️ **CAIU**: The number that just came up
- 💰 **SINAL**: New betting signal detected
- ✅ **VITÓRIA**: Winning bet
- ❌ **DERROTA**: Losing bet
- 🟡 **LA PARTAGE**: Zero hit with half-loss rule
- 🚨 **ALERTA**: Max losses reached, strategy reset
- 🎯 **AÇÃO**: Recommended betting action

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python test_roulette_assistant.py

# With pytest (recommended)
pip install pytest
pytest test_roulette_assistant.py -v

# Run specific test
pytest test_roulette_assistant.py::TestRouletteNumber -v
```

### Test Coverage

- ✅ RouletteNumber parsing and validation
- ✅ BankManager operations
- ✅ Configuration loading and validation
- ✅ Strategy initialization and state management
- ✅ Sequence detection algorithms
- ✅ Martingale progression
- ✅ Integration tests

## 🏗️ Architecture

### Class Diagram

```
RouletteAssistant
├── AssistantConfig
├── BankManager
└── Strategies
    ├── SimpleSequenceStrategy (Color, Even/Odd, High/Low)
    ├── DozenColumnStrategy (Dozens, Columns)
    └── ColdNumberStrategy (Single Numbers)
```

### Key Components

#### 1. **RouletteNumber** (Dataclass)
Represents a roulette number with all its properties:
- Value, Color, Parity, Height, Dozen, Column

#### 2. **BankManager**
Manages bankroll and betting limits:
- Track wins/losses
- Calculate ROI
- Prevent over-betting

#### 3. **Strategy** (Abstract Base Class)
Base class for all betting strategies:
- `analyze()`: Process new number
- `_handle_bet_outcome()`: Manage wins/losses
- `_calculate_signal_strength()`: Signal confidence

#### 4. **RouletteAssistant**
Main orchestrator:
- Coordinate all strategies
- Manage user interaction
- Display results

## 📊 Betting Strategies Explained

### 1. Simple Sequence (1:1 Bets)
**Applies to**: Color, Even/Odd, High/Low
**Payout**: 2:1

Detects sequences of the same outcome (e.g., 3 consecutive reds) and signals to bet on the opposite.

**Example**:
```
Spins: R, R, R → Signal: Bet on BLACK
```

### 2. Dozen/Column Delay (2:1 Bets)
**Applies to**: Dozens (1-12, 13-24, 25-36), Columns
**Payout**: 3:1

Identifies which dozen/column hasn't appeared in recent spins.

**Example**:
```
Recent: D1, D2, D1, D2 → Signal: Bet on D3
```

### 3. Cold Number (35:1 Bet)
**Applies to**: Single numbers
**Payout**: 36:1

Tracks numbers with longest delay and bets when delay exceeds threshold.

**Example**:
```
Number 17: 45 spins without appearing → Signal: Bet on 17
```

### La Partage Rule
When zero hits on 1:1 bets (Color, Even/Odd, High/Low):
- **Without La Partage**: Full bet loss
- **With La Partage**: Only 50% loss, bet maintains value

## 📈 Risk Management

### Martingale Progression
After each loss, bet amount is multiplied by the Martingale factor:

```
Loss 1: R$ 0.50
Loss 2: R$ 1.00
Loss 3: R$ 2.00
Loss 4: R$ 4.00
Loss 5: RESET (max losses reached)
```

### Safety Limits
- Maximum consecutive losses before reset
- Bankroll validation before each bet
- Configurable bet limits

## 🎯 Best Practices

### Recommended Settings for Beginners
```json
{
  "initial_bet": 0.50,
  "martingale_factor": 2.0,
  "max_consecutive_losses": 3,
  "la_partage_enabled": true,
  "min_sequence_simple": 4,
  "min_sequence_dozen": 3
}
```

### Recommended Settings for Advanced Users
```json
{
  "initial_bet": 1.00,
  "martingale_factor": 2.0,
  "max_consecutive_losses": 4,
  "la_partage_enabled": true,
  "min_sequence_simple": 3,
  "min_sequence_dozen": 2
}
```

### Tips
- Start with a small percentage of your bankroll (1-2%)
- Enable La Partage for European roulette
- Don't chase losses beyond max_consecutive_losses
- Track your sessions and analyze results
- Use multiple strategies for diversification

## 🔧 Development

### Project Structure
```
brazilian.roullete/
├── roulette_assistant.py      # Main application (Professional v3)
├── test_roulette_assistant.py # Unit tests
├── config.json                 # Configuration file
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── v3.py                       # Original v3 (reference)
```

### Code Style
- **PEP 8** compliant
- Type hints on all functions
- Google-style docstrings
- Maximum line length: 100 characters

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Ensure all tests pass
6. Submit a pull request

## ⚠️ Disclaimer

**IMPORTANT**: This software is for educational and entertainment purposes only.

- Gambling involves risk of monetary loss
- No betting system can guarantee profits
- Past results do not predict future outcomes
- Only gamble with money you can afford to lose
- If you have a gambling problem, seek help

This assistant is a tool to help analyze patterns, not a guarantee of winning.

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Submit a pull request
- Contact the maintainers

## 📚 References

- [Martingale Betting System](https://en.wikipedia.org/wiki/Martingale_(betting_system))
- [La Partage Rule](https://en.wikipedia.org/wiki/Roulette#La_Partage)
- [European vs American Roulette](https://en.wikipedia.org/wiki/Roulette)

---

**Made with ❤️ by Professional Development Team**

*Version 3.0 - Professional Edition*

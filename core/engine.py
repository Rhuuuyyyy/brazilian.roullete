"""
Motor principal do Brazilian Roulette Assistant.
Gerencia a sessão de jogo, banca e estratégias.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import logging

from .models import (
    BetSignal, GameConfig, InvalidNumberError, RouletteNumber, StrategyType
)
from .strategies import (
    ColdNumberStrategy, DozenColumnStrategy, SimpleSequenceStrategy, Strategy
)


logger = logging.getLogger(__name__)


# Nomenclatura para exibição
NOMENCLATURE = {
    'R': 'VERMELHO', 'B': 'PRETO', 'G': 'VERDE (ZERO)',
    'D1': "1ª DÚZIA (1-12)", 'D2': "2ª DÚZIA (13-24)", 'D3': "3ª DÚZIA (25-36)",
    'C1': "1ª COLUNA", 'C2': "2ª COLUNA", 'C3': "3ª COLUNA",
    'PAR': 'PAR', 'IMPAR': 'ÍMPAR',
    'BAIXO': 'BAIXO (1-18)', 'ALTO': 'ALTO (19-36)',
    'ZERO': 'ZERO',
}

NOMENCLATURE_ACTION = {
    'R': 'vermelho', 'B': 'preto',
    'D1': "1ª dúzia", 'D2': "2ª dúzia", 'D3': "3ª dúzia",
    'C1': "1ª coluna", 'C2': "2ª coluna", 'C3': "3ª coluna",
    'PAR': 'par', 'IMPAR': 'ímpar',
    'BAIXO': 'baixo (1-18)', 'ALTO': 'alto (19-36)'
}


@dataclass
class GameSession:
    """
    Representa uma sessão de jogo completa.
    Thread-safe para uso em aplicações web.
    """
    config: GameConfig = field(default_factory=GameConfig)
    initial_bankroll: float = 0.0
    current_bankroll: float = 0.0
    history: List[str] = field(default_factory=list)
    active_strategies: Set[StrategyType] = field(default_factory=set)
    strategies: Dict[StrategyType, Strategy] = field(default_factory=dict)
    initialized: bool = False
    warmed_up: bool = False

    def __post_init__(self):
        """Inicializa após a criação."""
        self._init_strategies()

    def _init_strategies(self):
        """Inicializa todas as instâncias de estratégia."""
        self.strategies = {
            StrategyType.COLOR: SimpleSequenceStrategy(
                StrategyType.COLOR, self.config, 'color'
            ),
            StrategyType.EVEN_ODD: SimpleSequenceStrategy(
                StrategyType.EVEN_ODD, self.config, 'parity'
            ),
            StrategyType.HIGH_LOW: SimpleSequenceStrategy(
                StrategyType.HIGH_LOW, self.config, 'height'
            ),
            StrategyType.DOZEN: DozenColumnStrategy(
                StrategyType.DOZEN, self.config, 'dozen'
            ),
            StrategyType.COLUMN: DozenColumnStrategy(
                StrategyType.COLUMN, self.config, 'column'
            ),
            StrategyType.COLD_NUMBER: ColdNumberStrategy(
                StrategyType.COLD_NUMBER, self.config
            ),
        }

    def initialize(self, bankroll: float, strategies: Dict[str, bool]) -> dict:
        """
        Inicializa a sessão de jogo.

        Args:
            bankroll: Valor inicial da banca
            strategies: Dict com estratégias ativas {nome: True/False}

        Returns:
            Dict com resultado da inicialização
        """
        if bankroll <= 0:
            return {'success': False, 'error': 'Banca deve ser maior que zero'}

        self.initial_bankroll = bankroll
        self.current_bankroll = bankroll
        self.history.clear()

        # Ativa estratégias selecionadas
        self.active_strategies.clear()
        for name, active in strategies.items():
            if active:
                try:
                    strategy_type = StrategyType(name)
                    self.active_strategies.add(strategy_type)
                except ValueError:
                    logger.warning(f"Estratégia desconhecida: {name}")

        # Reseta todas as estratégias
        for strategy in self.strategies.values():
            strategy.reset()

        self.initialized = True
        self.warmed_up = False

        logger.info(f"Sessão inicializada: Banca R$ {bankroll:.2f}, Estratégias: {self.active_strategies}")

        return {
            'success': True,
            'message': 'Sistema inicializado com sucesso',
            'bankroll': bankroll,
            'strategies': {s.value: True for s in self.active_strategies}
        }

    def warmup(self, numbers: List[str]) -> dict:
        """
        Aquece o sistema com números históricos.

        Args:
            numbers: Lista de 12 números (do mais recente ao mais antigo)

        Returns:
            Dict com resultado do aquecimento
        """
        if not self.initialized:
            return {'success': False, 'error': 'Sistema não inicializado'}

        if len(numbers) != 12:
            return {'success': False, 'error': f'Esperado 12 números, recebidos {len(numbers)}'}

        # Valida todos os números primeiro
        valid_numbers = []
        for num_str in numbers:
            try:
                rn = RouletteNumber.from_string(str(num_str))
                valid_numbers.append(rn)
            except InvalidNumberError as e:
                return {'success': False, 'error': str(e)}

        # Processa na ordem correta (mais antigo primeiro)
        for rn in reversed(valid_numbers):
            self._update_histories(rn)

        self.warmed_up = True
        logger.info(f"Sistema aquecido com {len(numbers)} números")

        return {
            'success': True,
            'message': f'Sistema aquecido com {len(numbers)} resultados',
            'bankroll': self.current_bankroll
        }

    def _update_histories(self, number: RouletteNumber):
        """Atualiza históricos com um novo número (sem processar apostas)."""
        self.history.append(number.value)

        # Atualiza tracking do número frio
        cold_strategy = self.strategies.get(StrategyType.COLD_NUMBER)
        if cold_strategy and isinstance(cold_strategy, ColdNumberStrategy):
            if number.value in cold_strategy.number_tracker:
                cold_strategy.number_tracker[number.value] += 1
            cold_strategy.all_spins.append(number.value)

        # Atualiza históricos das outras estratégias
        for strategy_type, strategy in self.strategies.items():
            if isinstance(strategy, SimpleSequenceStrategy):
                if strategy.attribute == 'color':
                    strategy.state.history.appendleft(number.color.value)
                elif strategy.attribute == 'parity':
                    strategy.state.history.appendleft(number.parity)
                else:
                    strategy.state.history.appendleft(number.height)
            elif isinstance(strategy, DozenColumnStrategy):
                if strategy.attribute == 'dozen':
                    strategy.state.history.appendleft(number.dozen)
                else:
                    strategy.state.history.appendleft(number.column)

    def _bank_delta(self, amount: float):
        """Callback para atualizar a banca."""
        self.current_bankroll += amount

    def process_spin(self, num_str: str) -> dict:
        """
        Processa um novo número da roleta.

        Args:
            num_str: O número que saiu

        Returns:
            Dict com resultado do processamento
        """
        if not self.initialized:
            return {'success': False, 'error': 'Sistema não inicializado'}

        if not self.warmed_up:
            return {'success': False, 'error': 'Sistema não aquecido'}

        # Valida número
        try:
            number = RouletteNumber.from_string(num_str)
        except InvalidNumberError as e:
            return {'success': False, 'error': str(e)}

        # Atualiza histórico
        self.history.append(number.value)

        # Processa estratégias ativas
        all_signals: List[BetSignal] = []
        messages = []

        for strategy_type in self.active_strategies:
            strategy = self.strategies[strategy_type]
            message, signal = strategy.analyze(number, self._bank_delta)

            if message:
                messages.append(message)
            if signal:
                all_signals.append(signal)

        # Obtém números quentes/frios
        cold_strategy = self.strategies.get(StrategyType.COLD_NUMBER)
        hot_numbers, cold_numbers = [], []
        if cold_strategy and isinstance(cold_strategy, ColdNumberStrategy):
            cold_numbers, hot_numbers = cold_strategy.get_hot_cold()

        # Monta resposta
        return {
            'success': True,
            'number': number.value,
            'color': number.color.value,
            'properties': {
                'COR': number.color.value,
                'PARIDADE': number.parity,
                'ALTURA': number.height,
                'DUZIA': number.dozen,
                'COLUNA': number.column
            },
            'bankroll': self.current_bankroll,
            'profit_loss': self.current_bankroll - self.initial_bankroll,
            'result_text': ''.join(messages) if messages else 'Aguarde Sinal',
            'signals': [s.to_dict() for s in all_signals],
            'hot_numbers': hot_numbers,
            'cold_numbers': cold_numbers,
            'history': self.history[-20:]
        }

    def get_stats(self) -> dict:
        """Retorna estatísticas atuais."""
        cold_strategy = self.strategies.get(StrategyType.COLD_NUMBER)
        hot_numbers, cold_numbers = [], []
        if cold_strategy and isinstance(cold_strategy, ColdNumberStrategy):
            cold_numbers, hot_numbers = cold_strategy.get_hot_cold()

        return {
            'success': True,
            'bankroll': self.current_bankroll,
            'initial_bankroll': self.initial_bankroll,
            'profit_loss': self.current_bankroll - self.initial_bankroll,
            'total_spins': len(self.history),
            'hot_numbers': hot_numbers,
            'cold_numbers': cold_numbers,
            'history': self.history[-20:]
        }

    def reset(self) -> dict:
        """Reseta completamente a sessão."""
        self.initial_bankroll = 0.0
        self.current_bankroll = 0.0
        self.history.clear()
        self.active_strategies.clear()
        self.initialized = False
        self.warmed_up = False

        for strategy in self.strategies.values():
            strategy.reset()

        logger.info("Sessão resetada")
        return {'success': True, 'message': 'Sessão reiniciada'}


class GameEngine:
    """
    Motor principal do jogo.
    Gerencia múltiplas sessões (para suporte multi-usuário futuro).
    """

    def __init__(self, config: Optional[GameConfig] = None):
        self.config = config or GameConfig()
        self._sessions: Dict[str, GameSession] = {}
        self._default_session = GameSession(config=self.config)

    def get_session(self, session_id: Optional[str] = None) -> GameSession:
        """Obtém uma sessão de jogo."""
        if session_id is None:
            return self._default_session
        if session_id not in self._sessions:
            self._sessions[session_id] = GameSession(config=self.config)
        return self._sessions[session_id]

    def clear_session(self, session_id: Optional[str] = None):
        """Limpa uma sessão."""
        if session_id is None:
            self._default_session = GameSession(config=self.config)
        elif session_id in self._sessions:
            del self._sessions[session_id]

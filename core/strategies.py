"""
Estratégias de apostas para o Brazilian Roulette Assistant.
Implementa o padrão Strategy com classes abstratas.
"""

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .models import (
    BetSignal, BetType, Color, GameConfig, RouletteNumber,
    RouletteType, StrategyType
)


@dataclass
class StrategyState:
    """Estado de uma estratégia de aposta."""
    history: deque = field(default_factory=lambda: deque(maxlen=12))
    current_bet: Optional[str] = None
    bet_amount: float = 0.50
    consecutive_losses: int = 0
    payout_multiplier: int = 2
    min_sequence: int = 3
    bet_type: BetType = BetType.SIMPLE


class Strategy(ABC):
    """Classe base abstrata para estratégias de aposta."""

    def __init__(self, strategy_type: StrategyType, config: GameConfig):
        self.strategy_type = strategy_type
        self.config = config
        self.state = StrategyState(bet_amount=config.initial_bet)

    @abstractmethod
    def analyze(self, number: RouletteNumber, bank_delta: callable) -> Tuple[str, Optional[BetSignal]]:
        """
        Analisa um novo número e retorna mensagem e possível sinal.

        Args:
            number: O número que saiu
            bank_delta: Callback para atualizar banca (ganho/perda)

        Returns:
            Tupla de (mensagem, sinal_de_aposta ou None)
        """
        pass

    def _handle_outcome(
        self,
        result: str,
        number: RouletteNumber,
        bank_delta: callable
    ) -> Tuple[str, Optional[BetSignal]]:
        """Processa o resultado de uma aposta ativa."""
        if not self.state.current_bet:
            return "", None

        target = self.state.current_bet
        amount = self.state.bet_amount
        message = ""

        # Vitória
        if result == target:
            winnings = amount * self.state.payout_multiplier
            bank_delta(winnings)
            message = f"VITORIA ({self.strategy_type.value}): Ganho R$ {winnings:.2f}. Reset.|"
            self._reset_state()
            return message, None

        # La Partage (zero na roleta europeia para apostas 1:1)
        if (number.color == Color.GREEN and
            self.state.bet_type == BetType.SIMPLE and
            self.config.la_partage_enabled and
            self.config.roulette_type == RouletteType.EUROPEAN):

            half_loss = amount / 2
            bank_delta(-half_loss)
            message = f"LA_PARTAGE ({self.strategy_type.value}): Meia perda R$ {half_loss:.2f}.|"
            return message, BetSignal(target, amount, self.strategy_type, 0, self.state.consecutive_losses)

        # Derrota
        bank_delta(-amount)
        self.state.consecutive_losses += 1
        self.state.bet_amount *= self.config.martingale_factor

        loss_type = "ZERO" if number.color == Color.GREEN else "DERROTA"
        message = f"{loss_type} ({self.strategy_type.value}): Perda R$ {amount:.2f}. Proxima: R$ {self.state.bet_amount:.2f}.|"

        # Limite de perdas
        if self.state.consecutive_losses > self.config.max_consecutive_losses:
            message += f"ALERTA ({self.strategy_type.value}): Limite de perdas. Reset.|"
            self._reset_state()
            return message, None

        return message, BetSignal(
            target, self.state.bet_amount, self.strategy_type, 0, self.state.consecutive_losses
        )

    def _reset_state(self):
        """Reseta o estado da estratégia."""
        self.state.current_bet = None
        self.state.bet_amount = self.config.initial_bet
        self.state.consecutive_losses = 0

    def reset(self):
        """Reset completo da estratégia."""
        self._reset_state()
        self.state.history.clear()


class SimpleSequenceStrategy(Strategy):
    """Estratégia para apostas 1:1: Cor, Par/Ímpar, Alto/Baixo."""

    def __init__(self, strategy_type: StrategyType, config: GameConfig, attribute: str):
        super().__init__(strategy_type, config)
        self.attribute = attribute  # 'color', 'parity', 'height'
        self.state.min_sequence = config.min_sequence_simple
        self.state.payout_multiplier = 2
        self.state.bet_type = BetType.SIMPLE

    def analyze(self, number: RouletteNumber, bank_delta: callable) -> Tuple[str, Optional[BetSignal]]:
        """Analisa padrões de sequência para apostas simples."""
        # Obtém o valor do atributo relevante
        if self.attribute == 'color':
            result = number.color.value
        elif self.attribute == 'parity':
            result = number.parity
        else:  # height
            result = number.height

        # Processa aposta ativa
        message, signal = self._handle_outcome(result, number, bank_delta)
        if signal:
            return message, signal

        # Atualiza histórico
        self.state.history.appendleft(result)

        # Busca novo sinal
        if not self.state.current_bet and len(self.state.history) >= self.state.min_sequence:
            ref = self.state.history[0]
            history_list = list(self.state.history)

            if ref not in ('G', 'ZERO') and all(
                h == ref for h in history_list[:self.state.min_sequence]
            ):
                # Determina o alvo oposto
                if self.attribute == 'color':
                    target = 'B' if ref == 'R' else 'R'
                elif self.attribute == 'parity':
                    target = 'IMPAR' if ref == 'PAR' else 'PAR'
                else:  # height
                    target = 'ALTO' if ref == 'BAIXO' else 'BAIXO'

                self.state.current_bet = target
                message += f"SINAL ({self.strategy_type.value}): Sequencia {self.state.min_sequence}x detectada. Apostar {target}.|"
                return message, BetSignal(target, self.state.bet_amount, self.strategy_type)

        return message, None


class DozenColumnStrategy(Strategy):
    """Estratégia para apostas 2:1: Dúzias e Colunas."""

    def __init__(self, strategy_type: StrategyType, config: GameConfig, attribute: str):
        super().__init__(strategy_type, config)
        self.attribute = attribute  # 'dozen' or 'column'
        self.state.min_sequence = config.min_sequence_dozen
        self.state.payout_multiplier = 3
        self.state.bet_type = BetType.DOZEN

        if attribute == 'dozen':
            self.all_targets = ['D1', 'D2', 'D3']
        else:
            self.all_targets = ['C1', 'C2', 'C3']

    def analyze(self, number: RouletteNumber, bank_delta: callable) -> Tuple[str, Optional[BetSignal]]:
        """Analisa padrões de atraso para dúzias/colunas."""
        result = number.dozen if self.attribute == 'dozen' else number.column

        # Processa aposta ativa
        message, signal = self._handle_outcome(result, number, bank_delta)
        if signal:
            return message, signal

        # Atualiza histórico
        self.state.history.appendleft(result)

        # Busca novo sinal
        if not self.state.current_bet and len(self.state.history) >= self.state.min_sequence:
            history_list = list(self.state.history)
            recent = set(h for h in history_list[:self.state.min_sequence] if h in self.all_targets)
            missing = [t for t in self.all_targets if t not in recent]

            if len(missing) == 1:
                target = missing[0]
                strength = self._calculate_strength(target)
                self.state.current_bet = target
                message += f"SINAL ({self.strategy_type.value}): {target} em atraso. Forca: {strength}.|"
                return message, BetSignal(target, self.state.bet_amount, self.strategy_type, strength)

        return message, None

    def _calculate_strength(self, target: str) -> int:
        """Calcula a força do sinal baseado no atraso."""
        strength = 0
        for item in self.state.history:
            if item != target:
                strength += 1
            else:
                break
        return strength


class ColdNumberStrategy(Strategy):
    """Estratégia para números frios (35:1)."""

    def __init__(self, strategy_type: StrategyType, config: GameConfig):
        super().__init__(strategy_type, config)
        self.state.min_sequence = config.min_cold_number_delay
        self.state.payout_multiplier = 36
        self.state.bet_type = BetType.STRAIGHT
        self.all_spins: List[str] = []
        self.number_tracker: Dict[str, int] = {str(i): 0 for i in range(37)}

    def analyze(self, number: RouletteNumber, bank_delta: callable) -> Tuple[str, Optional[BetSignal]]:
        """Analisa números frios."""
        # Atualiza tracking
        if number.value in self.number_tracker:
            self.number_tracker[number.value] += 1
        self.all_spins.append(number.value)

        # Processa aposta ativa
        message, signal = self._handle_outcome(number.value, number, bank_delta)
        if signal:
            return message, signal

        # Busca novo sinal
        if not self.state.current_bet and len(self.all_spins) >= self.state.min_sequence:
            coldest = self._get_coldest_numbers()
            if not coldest:
                return message, None

            target = coldest[0]

            # Calcula atraso
            try:
                delay = self.all_spins[::-1].index(target) + 1
            except ValueError:
                delay = len(self.all_spins)

            if delay >= self.state.min_sequence:
                self.state.current_bet = target
                message += f"SINAL ({self.strategy_type.value}): Numero {target} a {delay} giros sem sair.|"
                return message, BetSignal(target, self.state.bet_amount, self.strategy_type, delay)

        return message, None

    def _get_coldest_numbers(self) -> List[str]:
        """Retorna os 3 números mais frios (excluindo zeros)."""
        frequencies = [
            (count, num)
            for num, count in self.number_tracker.items()
            if num not in ('0', '00')
        ]
        if not frequencies:
            return []
        frequencies.sort()
        return [num for _, num in frequencies[:3]]

    def get_hot_cold(self) -> Tuple[List[str], List[str]]:
        """Retorna números quentes e frios."""
        frequencies = [
            (count, num)
            for num, count in self.number_tracker.items()
            if num not in ('0', '00')
        ]
        if not frequencies:
            return [], []
        frequencies.sort()
        cold = [num for _, num in frequencies[:3]]
        hot = [num for _, num in frequencies[-3:]][::-1]
        return cold, hot

    def reset(self):
        """Reset completo."""
        super().reset()
        self.all_spins.clear()
        self.number_tracker = {str(i): 0 for i in range(37)}

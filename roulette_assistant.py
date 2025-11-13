#!/usr/bin/env python3
"""
Brazilian Roulette Betting Assistant - Professional Version

A sophisticated roulette betting strategy system that analyzes spin patterns
and applies multiple betting strategies including Martingale progression,
sequence analysis, and cold number tracking.

Author: Professional Refactoring
Version: 3.0 (Professional)
License: MIT
"""

import json
import logging
from abc import ABC, abstractmethod
from collections import Counter, deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# ============================================================================
# CONSTANTS AND ENUMS
# ============================================================================

class RouletteType(Enum):
    """Type of roulette wheel."""
    EUROPEAN = "EUROPEAN"  # 37 slots: 0-36
    AMERICAN = "AMERICAN"  # 38 slots: 0-36, 00


class BetType(Enum):
    """Types of bets available."""
    ONE_TO_ONE = "1:1"  # Color, Even/Odd, High/Low
    TWO_TO_ONE = "2:1"  # Dozen, Column
    STRAIGHT_UP = "35:1"  # Single number


class Color(Enum):
    """Roulette colors."""
    RED = "R"
    BLACK = "B"
    GREEN = "G"


class StrategyType(Enum):
    """Available betting strategies."""
    COLOR = "COR"
    EVEN_ODD = "PAR_IMPAR"
    HIGH_LOW = "ALTO_BAIXO"
    DOZEN = "DUZIA"
    COLUMN = "COLUNA"
    COLD_NUMBER = "FRIO"


# Red numbers on European roulette
RED_NUMBERS: Set[int] = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class RouletteAssistantError(Exception):
    """Base exception for Roulette Assistant errors."""
    pass


class InvalidNumberError(RouletteAssistantError):
    """Raised when an invalid roulette number is provided."""
    pass


class ConfigurationError(RouletteAssistantError):
    """Raised when configuration is invalid."""
    pass


class InsufficientBankrollError(RouletteAssistantError):
    """Raised when bankroll is insufficient for betting."""
    pass


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class RouletteNumber:
    """Represents a roulette number with its properties."""
    value: str
    color: Color
    parity: str  # 'PAR', 'IMPAR', 'ZERO'
    height: str  # 'BAIXO', 'ALTO', 'ZERO'
    dozen: str  # 'D1', 'D2', 'D3', 'ZERO'
    column: str  # 'C1', 'C2', 'C3', 'ZERO'

    @staticmethod
    def from_string(num_str: str) -> 'RouletteNumber':
        """
        Create a RouletteNumber from a string input.

        Args:
            num_str: String representation of the number

        Returns:
            RouletteNumber instance

        Raises:
            InvalidNumberError: If the number is invalid
        """
        # Handle zero cases
        if num_str == '0' or num_str == '00':
            return RouletteNumber(
                value=num_str,
                color=Color.GREEN,
                parity='ZERO',
                height='ZERO',
                dozen='ZERO',
                column='ZERO'
            )

        # Parse regular numbers
        try:
            n = int(num_str)
            if not (1 <= n <= 36):
                raise InvalidNumberError(f"Number {num_str} is out of range (1-36)")
        except ValueError:
            raise InvalidNumberError(f"Invalid number format: {num_str}")

        # Determine properties
        color = Color.RED if n in RED_NUMBERS else Color.BLACK
        parity = 'PAR' if n % 2 == 0 else 'IMPAR'
        height = 'BAIXO' if 1 <= n <= 18 else 'ALTO'

        if 1 <= n <= 12:
            dozen = 'D1'
        elif 13 <= n <= 24:
            dozen = 'D2'
        else:
            dozen = 'D3'

        if n % 3 == 1:
            column = 'C1'
        elif n % 3 == 2:
            column = 'C2'
        else:
            column = 'C3'

        return RouletteNumber(
            value=num_str,
            color=color,
            parity=parity,
            height=height,
            dozen=dozen,
            column=column
        )


@dataclass
class BetSignal:
    """Represents a betting signal."""
    target: str
    amount: float
    strategy_type: StrategyType
    strength: int = 0

    def __str__(self) -> str:
        return f"{self.strategy_type.value}: {self.target} @ R$ {self.amount:.2f} (força: {self.strength})"


@dataclass
class StrategyState:
    """State of a betting strategy."""
    strategy_type: StrategyType
    history: deque = field(default_factory=lambda: deque(maxlen=10))
    current_bet: Optional[str] = None
    bet_amount: float = 0.0
    consecutive_losses: int = 0
    min_sequence: int = 3
    payout_multiplier: int = 2
    bet_type: BetType = BetType.ONE_TO_ONE


@dataclass
class AssistantConfig:
    """Configuration for the Roulette Assistant."""
    initial_bet: float = 0.50
    martingale_factor: float = 2.0
    max_consecutive_losses: int = 4
    la_partage_enabled: bool = True
    min_sequence_simple: int = 3  # For 1:1 bets
    min_sequence_dozen: int = 2  # For 2:1 bets
    min_cold_number_delay: int = 37
    roulette_type: RouletteType = RouletteType.EUROPEAN
    warmup_spins: int = 12

    @classmethod
    def from_file(cls, file_path: Path) -> 'AssistantConfig':
        """Load configuration from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert roulette_type string to enum
            if 'roulette_type' in data:
                data['roulette_type'] = RouletteType[data['roulette_type']]

            return cls(**data)
        except FileNotFoundError:
            logging.warning(f"Config file not found: {file_path}. Using defaults.")
            return cls()
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in config file: {e}")

    def save_to_file(self, file_path: Path) -> None:
        """Save configuration to JSON file."""
        data = {
            'initial_bet': self.initial_bet,
            'martingale_factor': self.martingale_factor,
            'max_consecutive_losses': self.max_consecutive_losses,
            'la_partage_enabled': self.la_partage_enabled,
            'min_sequence_simple': self.min_sequence_simple,
            'min_sequence_dozen': self.min_sequence_dozen,
            'min_cold_number_delay': self.min_cold_number_delay,
            'roulette_type': self.roulette_type.name,
            'warmup_spins': self.warmup_spins
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================================
# BANK MANAGER
# ============================================================================

class BankManager:
    """Manages bankroll tracking and betting limits."""

    def __init__(self, initial_bankroll: float):
        """
        Initialize the bank manager.

        Args:
            initial_bankroll: Starting bankroll amount
        """
        if initial_bankroll <= 0:
            raise ValueError("Initial bankroll must be positive")

        self._initial_bankroll = initial_bankroll
        self._current_bankroll = initial_bankroll
        self._total_wagered = 0.0
        self._total_won = 0.0
        self._total_lost = 0.0
        self._bet_history: List[Tuple[float, str]] = []

        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def current_bankroll(self) -> float:
        """Get current bankroll."""
        return self._current_bankroll

    @property
    def initial_bankroll(self) -> float:
        """Get initial bankroll."""
        return self._initial_bankroll

    @property
    def profit_loss(self) -> float:
        """Calculate profit or loss."""
        return self._current_bankroll - self._initial_bankroll

    def can_place_bet(self, amount: float) -> bool:
        """Check if a bet can be placed with current bankroll."""
        return self._current_bankroll >= amount

    def place_bet(self, amount: float, description: str = "") -> None:
        """
        Deduct bet amount from bankroll.

        Args:
            amount: Bet amount
            description: Description of the bet

        Raises:
            InsufficientBankrollError: If bankroll is insufficient
        """
        if not self.can_place_bet(amount):
            raise InsufficientBankrollError(
                f"Insufficient bankroll: R$ {self._current_bankroll:.2f} < R$ {amount:.2f}"
            )

        self._current_bankroll -= amount
        self._total_wagered += amount
        self._bet_history.append((amount, description))
        self.logger.debug(f"Bet placed: R$ {amount:.2f} - {description}")

    def add_winnings(self, amount: float) -> None:
        """
        Add winnings to bankroll.

        Args:
            amount: Winning amount
        """
        self._current_bankroll += amount
        self._total_won += amount
        self.logger.debug(f"Winnings added: R$ {amount:.2f}")

    def record_loss(self, amount: float) -> None:
        """Record a loss (already deducted via place_bet)."""
        self._total_lost += amount
        self.logger.debug(f"Loss recorded: R$ {amount:.2f}")

    def get_statistics(self) -> Dict[str, float]:
        """Get betting statistics."""
        return {
            'initial_bankroll': self._initial_bankroll,
            'current_bankroll': self._current_bankroll,
            'profit_loss': self.profit_loss,
            'total_wagered': self._total_wagered,
            'total_won': self._total_won,
            'total_lost': self._total_lost,
            'roi': (self.profit_loss / self._initial_bankroll * 100) if self._initial_bankroll > 0 else 0
        }


# ============================================================================
# STRATEGY BASE CLASS
# ============================================================================

class Strategy(ABC):
    """Abstract base class for betting strategies."""

    def __init__(
        self,
        strategy_type: StrategyType,
        config: AssistantConfig,
        bank_manager: BankManager
    ):
        """
        Initialize strategy.

        Args:
            strategy_type: Type of strategy
            config: Assistant configuration
            bank_manager: Bank manager instance
        """
        self.strategy_type = strategy_type
        self.config = config
        self.bank = bank_manager
        self.state = StrategyState(strategy_type=strategy_type)
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{strategy_type.value}")

    @abstractmethod
    def analyze(self, number: RouletteNumber) -> Tuple[str, Optional[BetSignal]]:
        """
        Analyze a new number and return message and potential bet signal.

        Args:
            number: The roulette number that just came up

        Returns:
            Tuple of (message, bet_signal)
        """
        pass

    def _handle_bet_outcome(
        self,
        result: str,
        number: RouletteNumber
    ) -> Tuple[str, Optional[BetSignal]]:
        """
        Handle the outcome of an active bet.

        Args:
            result: The result category (e.g., 'R', 'B', 'D1', etc.)
            number: The roulette number

        Returns:
            Tuple of (message, new_bet_signal or None)
        """
        if not self.state.current_bet:
            return "", None

        message = ""
        target = self.state.current_bet
        amount = self.state.bet_amount

        # Check for win
        if result == target:
            winnings = amount * self.state.payout_multiplier
            self.bank.add_winnings(winnings)
            message = f"✅ VITÓRIA ({self.strategy_type.value})! Ganhos: R$ {winnings:.2f}. RESET.\n"
            self.logger.info(f"Win: {target} - R$ {winnings:.2f}")

            # Reset state
            self.state.current_bet = None
            self.state.bet_amount = self.config.initial_bet
            self.state.consecutive_losses = 0
            return message, None

        # Check for zero with La Partage rule
        if (number.color == Color.GREEN and
            self.state.bet_type == BetType.ONE_TO_ONE and
            self.config.la_partage_enabled and
            self.config.roulette_type == RouletteType.EUROPEAN):

            half_loss = amount / 2
            self.bank.record_loss(half_loss)
            message = f"🟡 LA PARTAGE ({self.strategy_type.value}): Zero caiu. Meia perda (R$ {half_loss:.2f}).\n"
            self.logger.info(f"La Partage: {target} - Half loss R$ {half_loss:.2f}")

            # Maintain bet without Martingale progression
            return message, BetSignal(target, amount, self.strategy_type, 0)

        # Loss
        self.bank.record_loss(amount)
        self.state.consecutive_losses += 1
        self.state.bet_amount *= self.config.martingale_factor

        loss_type = "ZERO" if number.color == Color.GREEN else "DERROTA"
        message = f"❌ {loss_type} ({self.strategy_type.value}). Perda R$ {amount:.2f}. "
        message += f"Próxima aposta: R$ {self.state.bet_amount:.2f}.\n"
        self.logger.info(f"Loss: {target} - R$ {amount:.2f}")

        # Check loss limit
        if self.state.consecutive_losses > self.config.max_consecutive_losses:
            message += f"🚨 ALERTA ({self.strategy_type.value}): Limite de perdas atingido. RESET.\n"
            self.logger.warning(f"Max losses reached for {self.strategy_type.value}")

            # Reset state
            self.state.current_bet = None
            self.state.bet_amount = self.config.initial_bet
            self.state.consecutive_losses = 0
            return message, None

        return message, BetSignal(target, self.state.bet_amount, self.strategy_type, 0)

    def _calculate_signal_strength(self, target: str) -> int:
        """Calculate how many spins since target last appeared."""
        strength = 0
        for item in self.state.history:
            if item != target:
                strength += 1
            else:
                break
        return strength


# ============================================================================
# CONCRETE STRATEGIES
# ============================================================================

class SimpleSequenceStrategy(Strategy):
    """Strategy for 1:1 bets: Color, Even/Odd, High/Low."""

    def __init__(
        self,
        strategy_type: StrategyType,
        config: AssistantConfig,
        bank_manager: BankManager,
        attribute: str  # 'color', 'parity', 'height'
    ):
        super().__init__(strategy_type, config, bank_manager)
        self.attribute = attribute
        self.state.min_sequence = config.min_sequence_simple
        self.state.payout_multiplier = 2
        self.state.bet_type = BetType.ONE_TO_ONE
        self.state.bet_amount = config.initial_bet

    def analyze(self, number: RouletteNumber) -> Tuple[str, Optional[BetSignal]]:
        """Analyze for sequence patterns in simple bets."""
        # Get the relevant attribute value
        if self.attribute == 'color':
            result = number.color.value
        elif self.attribute == 'parity':
            result = number.parity
        else:  # height
            result = number.height

        # Handle active bet
        message, signal = self._handle_bet_outcome(result, number)
        if signal:
            return message, signal

        # Update history
        self.state.history.appendleft(result)

        # Look for new signal
        if (not self.state.current_bet and
            len(self.state.history) >= self.state.min_sequence):

            # Check if we have a sequence
            ref = self.state.history[0]
            if ref not in ('G', 'ZERO') and all(
                h == ref for h in list(self.state.history)[:self.state.min_sequence]
            ):
                # Determine opposite target
                if self.attribute == 'color':
                    target = 'B' if ref == 'R' else 'R'
                elif self.attribute == 'parity':
                    target = 'IMPAR' if ref == 'PAR' else 'PAR'
                else:  # height
                    target = 'ALTO' if ref == 'BAIXO' else 'BAIXO'

                self.state.current_bet = target
                message += f"💰 SINAL ({self.strategy_type.value}): Sequência de {self.state.min_sequence}x detectada. "
                message += f"Apostar em {target}.\n"
                self.logger.info(f"New signal: {target}")

                return message, BetSignal(target, self.state.bet_amount, self.strategy_type, 0)

        return message, None


class DozenColumnStrategy(Strategy):
    """Strategy for 2:1 bets: Dozens and Columns."""

    def __init__(
        self,
        strategy_type: StrategyType,
        config: AssistantConfig,
        bank_manager: BankManager,
        attribute: str  # 'dozen' or 'column'
    ):
        super().__init__(strategy_type, config, bank_manager)
        self.attribute = attribute
        self.state.min_sequence = config.min_sequence_dozen
        self.state.payout_multiplier = 3
        self.state.bet_type = BetType.TWO_TO_ONE
        self.state.bet_amount = config.initial_bet

        if attribute == 'dozen':
            self.all_targets = ['D1', 'D2', 'D3']
        else:
            self.all_targets = ['C1', 'C2', 'C3']

    def analyze(self, number: RouletteNumber) -> Tuple[str, Optional[BetSignal]]:
        """Analyze for delay patterns in dozens/columns."""
        result = number.dozen if self.attribute == 'dozen' else number.column

        # Handle active bet
        message, signal = self._handle_bet_outcome(result, number)
        if signal:
            return message, signal

        # Update history
        self.state.history.appendleft(result)

        # Look for new signal
        if (not self.state.current_bet and
            len(self.state.history) >= self.state.min_sequence):

            # Find which target is missing from recent spins
            recent = set(
                h for h in list(self.state.history)[:self.state.min_sequence]
                if h in self.all_targets
            )
            missing = [t for t in self.all_targets if t not in recent]

            if len(missing) == 1:
                target = missing[0]
                strength = self._calculate_signal_strength(target)
                self.state.current_bet = target

                message += f"💰 SINAL ({self.strategy_type.value}): {target} em atraso. "
                message += f"Força: {strength}/{len(self.state.history)}.\n"
                self.logger.info(f"New signal: {target} (strength: {strength})")

                return message, BetSignal(target, self.state.bet_amount, self.strategy_type, strength)

        return message, None


class ColdNumberStrategy(Strategy):
    """Strategy for cold number betting (35:1)."""

    def __init__(
        self,
        strategy_type: StrategyType,
        config: AssistantConfig,
        bank_manager: BankManager,
        number_tracker: Counter
    ):
        super().__init__(strategy_type, config, bank_manager)
        self.number_tracker = number_tracker
        self.state.min_sequence = config.min_cold_number_delay
        self.state.payout_multiplier = 36
        self.state.bet_type = BetType.STRAIGHT_UP
        self.state.bet_amount = config.initial_bet
        self.all_spins: List[str] = []

    def analyze(self, number: RouletteNumber) -> Tuple[str, Optional[BetSignal]]:
        """Analyze for cold numbers."""
        # Handle active bet
        message, signal = self._handle_bet_outcome(number.value, number)
        if signal:
            return message, signal

        # Update tracking
        self.all_spins.append(number.value)

        # Look for new signal
        if (not self.state.current_bet and
            len(self.all_spins) >= self.state.min_sequence):

            # Find coldest number
            coldest_numbers = self._get_coldest_numbers()
            if not coldest_numbers:
                return message, None

            target = coldest_numbers[0]

            # Calculate delay
            try:
                delay = self.all_spins[::-1].index(target) + 1
            except ValueError:
                delay = len(self.all_spins)

            if delay >= self.state.min_sequence:
                self.state.current_bet = target
                message += f"💰 SINAL ({self.strategy_type.value}): Número {target} está "
                message += f"a {delay} giros sem sair.\n"
                self.logger.info(f"New signal: {target} (delay: {delay})")

                return message, BetSignal(target, self.state.bet_amount, self.strategy_type, delay)

        return message, None

    def _get_coldest_numbers(self) -> List[str]:
        """Get the 3 coldest numbers (excluding zeros)."""
        frequencies = [
            (count, num)
            for num, count in self.number_tracker.items()
            if num not in ('0', '00')
        ]
        if not frequencies:
            return []

        frequencies_sorted = sorted(frequencies)
        return [num for _, num in frequencies_sorted[:3]]


# ============================================================================
# MAIN ASSISTANT CLASS
# ============================================================================

class RouletteAssistant:
    """Main orchestrator for the Roulette Betting Assistant."""

    def __init__(self, config: AssistantConfig):
        """
        Initialize the assistant.

        Args:
            config: Configuration object
        """
        self.config = config
        self.console = Console()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize bank manager
        self.bank: Optional[BankManager] = None

        # Number tracking
        self.number_tracker: Counter = Counter()
        max_num = 37 if config.roulette_type == RouletteType.EUROPEAN else 38
        for i in range(max_num):
            self.number_tracker[str(i)] = 0
        if config.roulette_type == RouletteType.AMERICAN:
            self.number_tracker['00'] = 0

        # Strategies
        self.strategies: Dict[StrategyType, Strategy] = {}
        self.active_strategies: Set[StrategyType] = set()

    def setup(self) -> None:
        """Interactive setup for bankroll and strategies."""
        self.console.print(Panel.fit(
            "[bold cyan]Brazilian Roulette Assistant v3.0 Professional[/bold cyan]\n"
            "[dim]Sistema de Assistência para Apostas em Roleta[/dim]",
            border_style="cyan"
        ))

        # Get initial bankroll
        while True:
            try:
                bankroll_str = self.console.input(
                    "\n[yellow]Qual o valor da sua banca inicial? R$ [/yellow]"
                ).strip().replace(',', '.')

                bankroll = float(bankroll_str)
                if bankroll <= 0:
                    self.console.print("[red]O valor deve ser positivo![/red]")
                    continue

                self.bank = BankManager(bankroll)
                self.console.print(f"[green]✓ Banca inicial de R$ {bankroll:.2f} definida.[/green]")
                break
            except ValueError:
                self.console.print("[red]Valor inválido. Digite um número.[/red]")

        # Initialize all strategies
        self._initialize_strategies()

        # Configure active strategies
        self.console.print("\n[bold]Configuração das Estratégias[/bold]")
        self.console.print("[dim]Responda com 'S' para Sim ou 'N' para Não[/dim]\n")

        for strategy_type in StrategyType:
            while True:
                response = self.console.input(
                    f"Ativar estratégia [cyan]{strategy_type.value}[/cyan]? (S/N): "
                ).strip().upper()

                if response in ['S', 'N']:
                    if response == 'S':
                        self.active_strategies.add(strategy_type)
                    break
                else:
                    self.console.print("[red]Resposta inválida. Digite 'S' ou 'N'.[/red]")

        if self.active_strategies:
            active_names = ", ".join(s.value for s in self.active_strategies)
            self.console.print(f"\n[green]Estratégias ativas: {active_names}[/green]")
        else:
            self.console.print("\n[yellow]⚠ AVISO: Nenhuma estratégia foi ativada.[/yellow]")

        # Warmup phase
        self._warmup_phase()

    def _initialize_strategies(self) -> None:
        """Initialize all strategy instances."""
        assert self.bank is not None, "Bank manager must be initialized first"

        self.strategies = {
            StrategyType.COLOR: SimpleSequenceStrategy(
                StrategyType.COLOR, self.config, self.bank, 'color'
            ),
            StrategyType.EVEN_ODD: SimpleSequenceStrategy(
                StrategyType.EVEN_ODD, self.config, self.bank, 'parity'
            ),
            StrategyType.HIGH_LOW: SimpleSequenceStrategy(
                StrategyType.HIGH_LOW, self.config, self.bank, 'height'
            ),
            StrategyType.DOZEN: DozenColumnStrategy(
                StrategyType.DOZEN, self.config, self.bank, 'dozen'
            ),
            StrategyType.COLUMN: DozenColumnStrategy(
                StrategyType.COLUMN, self.config, self.bank, 'column'
            ),
            StrategyType.COLD_NUMBER: ColdNumberStrategy(
                StrategyType.COLD_NUMBER, self.config, self.bank, self.number_tracker
            ),
        }

    def _warmup_phase(self) -> None:
        """Collect initial spins for warmup."""
        self.console.print(f"\n[bold]Aquecimento do Sistema[/bold]")
        self.console.print(f"[dim]Insira os últimos {self.config.warmup_spins} resultados[/dim]\n")

        valid_range = [str(i) for i in range(37)]
        if self.config.roulette_type == RouletteType.AMERICAN:
            valid_range.append('00')

        warmup_numbers: List[str] = []

        for i in range(self.config.warmup_spins):
            while True:
                ordinal = f"{i + 1}º"
                prompt = "Digite o [cyan]1º resultado (mais recente)[/cyan]: " if i == 0 else f"Digite o [cyan]{ordinal} resultado[/cyan]: "

                num_str = self.console.input(prompt).strip().upper()

                if num_str in valid_range:
                    warmup_numbers.append(num_str)
                    break
                else:
                    self.console.print("[red]Número inválido. Tente novamente.[/red]")

        # Process warmup numbers (oldest to newest)
        for num_str in reversed(warmup_numbers):
            try:
                number = RouletteNumber.from_string(num_str)
                self._update_tracking(number)
            except InvalidNumberError as e:
                self.logger.error(f"Error in warmup: {e}")

        self.console.print(f"\n[green]✅ Sistema aquecido com {self.config.warmup_spins} resultados. Pronto para iniciar![/green]")
        self.console.print("─" * 70 + "\n")

    def _update_tracking(self, number: RouletteNumber) -> None:
        """Update number tracking and strategy histories."""
        self.number_tracker[number.value] += 1

        # Update cold number strategy's all_spins
        if StrategyType.COLD_NUMBER in self.strategies:
            cold_strategy = self.strategies[StrategyType.COLD_NUMBER]
            if isinstance(cold_strategy, ColdNumberStrategy):
                cold_strategy.all_spins.append(number.value)

        # Update strategy histories
        for strategy in self.strategies.values():
            if isinstance(strategy, SimpleSequenceStrategy):
                if strategy.attribute == 'color':
                    strategy.state.history.appendleft(number.color.value)
                elif strategy.attribute == 'parity':
                    strategy.state.history.appendleft(number.parity)
                else:  # height
                    strategy.state.history.appendleft(number.height)
            elif isinstance(strategy, DozenColumnStrategy):
                if strategy.attribute == 'dozen':
                    strategy.state.history.appendleft(number.dozen)
                else:  # column
                    strategy.state.history.appendleft(number.column)

    def process_number(self, num_str: str) -> None:
        """
        Process a new roulette number.

        Args:
            num_str: The number that came up
        """
        try:
            # Parse number
            number = RouletteNumber.from_string(num_str.strip().upper())

            # Display header
            self._display_spin_header(number)

            # Update tracking (already done in strategies, but keep for number_tracker)
            self.number_tracker[number.value] += 1

            # Process all active strategies
            all_signals: List[BetSignal] = []
            messages = []

            for strategy_type in self.active_strategies:
                strategy = self.strategies[strategy_type]
                message, signal = strategy.analyze(number)

                if message:
                    messages.append(message)
                if signal:
                    all_signals.append(signal)

            # Display messages
            if messages:
                self.console.print("".join(messages), end="")

            # Display action
            self._display_action(all_signals)

            # Display statistics
            self._display_statistics()

        except InvalidNumberError as e:
            self.console.print(f"[red]ERRO: {e}[/red]")
            self.logger.error(str(e))
        except Exception as e:
            self.console.print(f"[red]ERRO INESPERADO: {e}[/red]")
            self.logger.exception("Unexpected error")

    def _display_spin_header(self, number: RouletteNumber) -> None:
        """Display the current spin information."""
        color_map = {
            Color.RED: "red",
            Color.BLACK: "white on black",
            Color.GREEN: "black on green"
        }

        color_style = color_map.get(number.color, "white")

        header = Text()
        header.append("➡️ CAIU: ", style="bold")
        header.append(f"{number.value}", style=f"bold {color_style}")

        if number.value not in ('0', '00'):
            header.append(f" ({number.parity})", style="dim")

        header.append(f" | Banca: R$ {self.bank.current_bankroll:.2f}", style="cyan")

        self.console.print(header)
        self.console.print("─" * 70)

    def _display_action(self, signals: List[BetSignal]) -> None:
        """Display the recommended action."""
        if not signals:
            self.console.print("[dim]🎯 AÇÃO: Aguarde Sinal[/dim]")
        else:
            action_text = "🎯 AÇÃO: "
            instructions = []

            for signal in signals:
                instructions.append(self._format_bet_instruction(signal))

            action_text += " e ".join(instructions)
            self.console.print(f"[bold yellow]{action_text}[/bold yellow]")

        self.console.print("─" * 70)

    def _format_bet_instruction(self, signal: BetSignal) -> str:
        """Format a bet instruction for display."""
        nomenclature = {
            'R': 'vermelho', 'B': 'preto',
            'D1': '1ª dúzia', 'D2': '2ª dúzia', 'D3': '3ª dúzia',
            'C1': '1ª coluna', 'C2': '2ª coluna', 'C3': '3ª coluna',
            'PAR': 'par', 'IMPAR': 'ímpar',
            'BAIXO': 'baixo (1-18)', 'ALTO': 'alto (19-36)'
        }

        term = nomenclature.get(signal.target, signal.target)

        if signal.strategy_type in [StrategyType.DOZEN, StrategyType.COLUMN]:
            return f"R$ {signal.amount:.2f} na {term}"
        elif signal.strategy_type == StrategyType.COLD_NUMBER:
            return f"R$ {signal.amount:.2f} no número {signal.target}"
        else:
            return f"R$ {signal.amount:.2f} no {term}"

    def _display_statistics(self) -> None:
        """Display current statistics."""
        stats = self.bank.get_statistics()

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="dim")
        table.add_column(style="cyan")

        profit_loss = stats['profit_loss']
        pl_color = "green" if profit_loss >= 0 else "red"
        pl_sign = "+" if profit_loss >= 0 else ""

        table.add_row("Banca Inicial:", f"R$ {stats['initial_bankroll']:.2f}")
        table.add_row("Banca Atual:", f"R$ {stats['current_bankroll']:.2f}")
        table.add_row("Resultado:", f"[{pl_color}]{pl_sign}R$ {profit_loss:.2f}[/{pl_color}]")
        table.add_row("ROI:", f"[{pl_color}]{pl_sign}{stats['roi']:.2f}%[/{pl_color}]")

        self.console.print(table)
        self.console.print()

    def run(self) -> None:
        """Run the main interactive loop."""
        self.console.print("[bold green]Sistema iniciado! Digite os números conforme caem ou 'SAIR' para encerrar.[/bold green]\n")

        while True:
            try:
                num_input = self.console.input("[bold]Próximo número: [/bold]").strip().upper()

                if num_input == "SAIR":
                    self._display_final_summary()
                    break

                self.process_number(num_input)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrompido pelo usuário.[/yellow]")
                self._display_final_summary()
                break
            except EOFError:
                self._display_final_summary()
                break

    def _display_final_summary(self) -> None:
        """Display final session summary."""
        self.console.print("\n" + "=" * 70)
        self.console.print("[bold cyan]RESUMO DA SESSÃO[/bold cyan]")
        self.console.print("=" * 70)

        stats = self.bank.get_statistics()

        summary = Table(show_header=True, box=None)
        summary.add_column("Métrica", style="bold")
        summary.add_column("Valor", justify="right")

        summary.add_row("Banca Inicial", f"R$ {stats['initial_bankroll']:.2f}")
        summary.add_row("Banca Final", f"R$ {stats['current_bankroll']:.2f}")

        profit_loss = stats['profit_loss']
        pl_color = "green" if profit_loss >= 0 else "red"
        pl_sign = "+" if profit_loss >= 0 else ""
        summary.add_row(
            "Resultado",
            f"[{pl_color}]{pl_sign}R$ {profit_loss:.2f}[/{pl_color}]"
        )
        summary.add_row(
            "ROI",
            f"[{pl_color}]{pl_sign}{stats['roi']:.2f}%[/{pl_color}]"
        )
        summary.add_row("Total Apostado", f"R$ {stats['total_wagered']:.2f}")
        summary.add_row("Total Ganho", f"R$ {stats['total_won']:.2f}")
        summary.add_row("Total Perdido", f"R$ {stats['total_lost']:.2f}")

        self.console.print(summary)
        self.console.print("\n[dim]Obrigado por usar o Brazilian Roulette Assistant![/dim]")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def setup_logging(level: int = logging.INFO) -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)]
    )


def main() -> None:
    """Main entry point."""
    # Setup logging
    setup_logging(logging.INFO)

    # Load or create configuration
    config_path = Path("config.json")
    if config_path.exists():
        config = AssistantConfig.from_file(config_path)
    else:
        config = AssistantConfig()
        config.save_to_file(config_path)

    # Create and run assistant
    assistant = RouletteAssistant(config)
    assistant.setup()
    assistant.run()


if __name__ == "__main__":
    main()

"""
Modelos de dados para o Brazilian Roulette Assistant.
Implementa dataclasses imutáveis com validação robusta.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Set


class RouletteType(Enum):
    """Tipo de roleta."""
    EUROPEAN = "EUROPEAN"  # 37 slots: 0-36
    AMERICAN = "AMERICAN"  # 38 slots: 0-36, 00


class Color(Enum):
    """Cores da roleta."""
    RED = "R"
    BLACK = "B"
    GREEN = "G"


class BetType(Enum):
    """Tipos de apostas disponíveis."""
    SIMPLE = "1:1"      # Cor, Par/Ímpar, Alto/Baixo
    DOZEN = "2:1"       # Dúzia, Coluna
    STRAIGHT = "35:1"   # Número direto


class StrategyType(Enum):
    """Estratégias de apostas disponíveis."""
    COLOR = "COR"
    EVEN_ODD = "PAR_IMPAR"
    HIGH_LOW = "ALTO_BAIXO"
    DOZEN = "DUZIA"
    COLUMN = "COLUNA"
    COLD_NUMBER = "FRIO"


# Números vermelhos na roleta europeia
RED_NUMBERS: Set[int] = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}


class InvalidNumberError(ValueError):
    """Erro para número de roleta inválido."""
    pass


@dataclass(frozen=True)
class RouletteNumber:
    """
    Representa um número da roleta com todas as suas propriedades.
    Imutável para garantir integridade dos dados.
    """
    value: str
    color: Color
    parity: str      # 'PAR', 'IMPAR', 'ZERO'
    height: str      # 'BAIXO', 'ALTO', 'ZERO'
    dozen: str       # 'D1', 'D2', 'D3', 'ZERO'
    column: str      # 'C1', 'C2', 'C3', 'ZERO'

    @staticmethod
    def from_string(num_str: str) -> 'RouletteNumber':
        """
        Cria um RouletteNumber a partir de uma string.

        Args:
            num_str: Representação em string do número

        Returns:
            Instância de RouletteNumber

        Raises:
            InvalidNumberError: Se o número for inválido
        """
        num_str = num_str.strip().upper()

        # Casos de zero
        if num_str in ('0', '00'):
            return RouletteNumber(
                value=num_str,
                color=Color.GREEN,
                parity='ZERO',
                height='ZERO',
                dozen='ZERO',
                column='ZERO'
            )

        # Validação de números regulares
        try:
            n = int(num_str)
            if not 1 <= n <= 36:
                raise InvalidNumberError(f"Número {num_str} fora do intervalo válido (1-36)")
        except ValueError:
            raise InvalidNumberError(f"Formato de número inválido: {num_str}")

        # Determina propriedades
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
    """Representa um sinal de aposta."""
    target: str
    amount: float
    strategy: StrategyType
    strength: int = 0
    losses: int = 0

    def to_dict(self) -> dict:
        """Converte para dicionário para API."""
        return {
            'target': self.target,
            'amount': self.amount,
            'strategy': self.strategy.value,
            'strength': self.strength,
            'losses': self.losses
        }


@dataclass
class GameConfig:
    """Configuração do jogo."""
    initial_bet: float = 0.50
    martingale_factor: float = 2.0
    max_consecutive_losses: int = 4
    la_partage_enabled: bool = True
    min_sequence_simple: int = 3
    min_sequence_dozen: int = 2
    min_cold_number_delay: int = 37
    roulette_type: RouletteType = RouletteType.EUROPEAN
    warmup_spins: int = 12

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            'initial_bet': self.initial_bet,
            'martingale_factor': self.martingale_factor,
            'max_consecutive_losses': self.max_consecutive_losses,
            'la_partage_enabled': self.la_partage_enabled,
            'min_sequence_simple': self.min_sequence_simple,
            'min_sequence_dozen': self.min_sequence_dozen,
            'min_cold_number_delay': self.min_cold_number_delay,
            'roulette_type': self.roulette_type.value,
            'warmup_spins': self.warmup_spins
        }

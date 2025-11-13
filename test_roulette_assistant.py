#!/usr/bin/env python3
"""
Unit tests for Brazilian Roulette Assistant

Run with: python -m pytest test_roulette_assistant.py -v
or: python test_roulette_assistant.py
"""

import unittest
from collections import Counter

from roulette_assistant import (
    RouletteNumber,
    Color,
    InvalidNumberError,
    BankManager,
    InsufficientBankrollError,
    AssistantConfig,
    RouletteType,
    StrategyType,
    BetType,
    SimpleSequenceStrategy,
    DozenColumnStrategy,
    ColdNumberStrategy,
)


class TestRouletteNumber(unittest.TestCase):
    """Test RouletteNumber class."""

    def test_zero(self):
        """Test zero number."""
        num = RouletteNumber.from_string('0')
        self.assertEqual(num.value, '0')
        self.assertEqual(num.color, Color.GREEN)
        self.assertEqual(num.parity, 'ZERO')
        self.assertEqual(num.height, 'ZERO')
        self.assertEqual(num.dozen, 'ZERO')
        self.assertEqual(num.column, 'ZERO')

    def test_red_number(self):
        """Test red number (1)."""
        num = RouletteNumber.from_string('1')
        self.assertEqual(num.value, '1')
        self.assertEqual(num.color, Color.RED)
        self.assertEqual(num.parity, 'IMPAR')
        self.assertEqual(num.height, 'BAIXO')
        self.assertEqual(num.dozen, 'D1')
        self.assertEqual(num.column, 'C1')

    def test_black_number(self):
        """Test black number (2)."""
        num = RouletteNumber.from_string('2')
        self.assertEqual(num.value, '2')
        self.assertEqual(num.color, Color.BLACK)
        self.assertEqual(num.parity, 'PAR')
        self.assertEqual(num.height, 'BAIXO')
        self.assertEqual(num.dozen, 'D1')
        self.assertEqual(num.column, 'C2')

    def test_high_number(self):
        """Test high number (19)."""
        num = RouletteNumber.from_string('19')
        self.assertEqual(num.height, 'ALTO')
        self.assertEqual(num.dozen, 'D2')

    def test_third_dozen(self):
        """Test third dozen (25)."""
        num = RouletteNumber.from_string('25')
        self.assertEqual(num.dozen, 'D3')

    def test_invalid_number(self):
        """Test invalid number."""
        with self.assertRaises(InvalidNumberError):
            RouletteNumber.from_string('37')

        with self.assertRaises(InvalidNumberError):
            RouletteNumber.from_string('abc')

    def test_all_valid_numbers(self):
        """Test all valid numbers 0-36."""
        for i in range(37):
            num = RouletteNumber.from_string(str(i))
            self.assertIsNotNone(num)


class TestBankManager(unittest.TestCase):
    """Test BankManager class."""

    def test_initialization(self):
        """Test bank manager initialization."""
        bank = BankManager(100.0)
        self.assertEqual(bank.initial_bankroll, 100.0)
        self.assertEqual(bank.current_bankroll, 100.0)
        self.assertEqual(bank.profit_loss, 0.0)

    def test_invalid_initial_bankroll(self):
        """Test invalid initial bankroll."""
        with self.assertRaises(ValueError):
            BankManager(0)

        with self.assertRaises(ValueError):
            BankManager(-10)

    def test_can_place_bet(self):
        """Test bet placement validation."""
        bank = BankManager(100.0)
        self.assertTrue(bank.can_place_bet(50.0))
        self.assertTrue(bank.can_place_bet(100.0))
        self.assertFalse(bank.can_place_bet(100.01))

    def test_place_bet(self):
        """Test placing a bet."""
        bank = BankManager(100.0)
        bank.place_bet(10.0, "test bet")
        self.assertEqual(bank.current_bankroll, 90.0)

    def test_insufficient_bankroll(self):
        """Test insufficient bankroll error."""
        bank = BankManager(10.0)
        with self.assertRaises(InsufficientBankrollError):
            bank.place_bet(20.0)

    def test_add_winnings(self):
        """Test adding winnings."""
        bank = BankManager(100.0)
        bank.place_bet(10.0)
        bank.add_winnings(20.0)  # 10 bet + 10 profit
        self.assertEqual(bank.current_bankroll, 110.0)
        self.assertEqual(bank.profit_loss, 10.0)

    def test_statistics(self):
        """Test statistics calculation."""
        bank = BankManager(100.0)
        bank.place_bet(10.0)
        bank.record_loss(10.0)
        bank.place_bet(10.0)
        bank.add_winnings(20.0)

        stats = bank.get_statistics()
        self.assertEqual(stats['initial_bankroll'], 100.0)
        self.assertEqual(stats['total_wagered'], 20.0)
        self.assertEqual(stats['total_won'], 20.0)
        self.assertEqual(stats['total_lost'], 10.0)


class TestAssistantConfig(unittest.TestCase):
    """Test AssistantConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = AssistantConfig()
        self.assertEqual(config.initial_bet, 0.5)
        self.assertEqual(config.martingale_factor, 2.0)
        self.assertEqual(config.max_consecutive_losses, 4)
        self.assertTrue(config.la_partage_enabled)
        self.assertEqual(config.roulette_type, RouletteType.EUROPEAN)

    def test_custom_config(self):
        """Test custom configuration."""
        config = AssistantConfig(
            initial_bet=1.0,
            martingale_factor=3.0,
            max_consecutive_losses=5
        )
        self.assertEqual(config.initial_bet, 1.0)
        self.assertEqual(config.martingale_factor, 3.0)
        self.assertEqual(config.max_consecutive_losses, 5)


class TestStrategies(unittest.TestCase):
    """Test strategy classes."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = AssistantConfig()
        self.bank = BankManager(1000.0)
        self.number_tracker = Counter()

    def test_simple_sequence_strategy_initialization(self):
        """Test simple sequence strategy initialization."""
        strategy = SimpleSequenceStrategy(
            StrategyType.COLOR,
            self.config,
            self.bank,
            'color'
        )
        self.assertEqual(strategy.strategy_type, StrategyType.COLOR)
        self.assertEqual(strategy.state.bet_type, BetType.ONE_TO_ONE)
        self.assertEqual(strategy.state.payout_multiplier, 2)

    def test_dozen_column_strategy_initialization(self):
        """Test dozen/column strategy initialization."""
        strategy = DozenColumnStrategy(
            StrategyType.DOZEN,
            self.config,
            self.bank,
            'dozen'
        )
        self.assertEqual(strategy.strategy_type, StrategyType.DOZEN)
        self.assertEqual(strategy.state.bet_type, BetType.TWO_TO_ONE)
        self.assertEqual(strategy.state.payout_multiplier, 3)
        self.assertEqual(strategy.all_targets, ['D1', 'D2', 'D3'])

    def test_cold_number_strategy_initialization(self):
        """Test cold number strategy initialization."""
        strategy = ColdNumberStrategy(
            StrategyType.COLD_NUMBER,
            self.config,
            self.bank,
            self.number_tracker
        )
        self.assertEqual(strategy.strategy_type, StrategyType.COLD_NUMBER)
        self.assertEqual(strategy.state.bet_type, BetType.STRAIGHT_UP)
        self.assertEqual(strategy.state.payout_multiplier, 36)

    def test_color_strategy_sequence_detection(self):
        """Test color strategy sequence detection."""
        strategy = SimpleSequenceStrategy(
            StrategyType.COLOR,
            self.config,
            self.bank,
            'color'
        )

        # Feed 3 reds to trigger signal for black
        for _ in range(3):
            num = RouletteNumber.from_string('1')  # Red
            message, signal = strategy.analyze(num)

        # Should have a signal to bet on black
        self.assertIsNotNone(signal)
        self.assertEqual(signal.target, 'B')

    def test_dozen_strategy_delay_detection(self):
        """Test dozen strategy delay detection."""
        strategy = DozenColumnStrategy(
            StrategyType.DOZEN,
            self.config,
            self.bank,
            'dozen'
        )

        # Feed numbers from D1 and D2 only, D3 should be missing
        num1 = RouletteNumber.from_string('1')  # D1
        num2 = RouletteNumber.from_string('13')  # D2

        strategy.analyze(num1)
        message, signal = strategy.analyze(num2)

        # Should have a signal to bet on D3
        self.assertIsNotNone(signal)
        self.assertEqual(signal.target, 'D3')

    def test_martingale_progression(self):
        """Test Martingale progression on losses."""
        strategy = SimpleSequenceStrategy(
            StrategyType.COLOR,
            self.config,
            self.bank,
            'color'
        )

        # Create a sequence and get a signal
        for _ in range(3):
            num = RouletteNumber.from_string('1')  # Red
            strategy.analyze(num)

        # Should have signal for black
        initial_bet = strategy.state.bet_amount

        # Now feed a red (loss)
        num = RouletteNumber.from_string('3')  # Red
        message, signal = strategy.analyze(num)

        # Bet should have doubled
        self.assertEqual(strategy.state.bet_amount, initial_bet * self.config.martingale_factor)
        self.assertEqual(strategy.state.consecutive_losses, 1)


class TestIntegration(unittest.TestCase):
    """Integration tests."""

    def test_full_session_simulation(self):
        """Simulate a full betting session."""
        config = AssistantConfig()
        bank = BankManager(100.0)
        number_tracker = Counter()

        # Create color strategy
        strategy = SimpleSequenceStrategy(
            StrategyType.COLOR,
            config,
            bank,
            'color'
        )

        # Simulate spins
        spins = ['1', '3', '5', '2', '4', '6']  # 3 reds, then 3 blacks

        for spin in spins:
            num = RouletteNumber.from_string(spin)
            message, signal = strategy.analyze(num)

        # Strategy should have processed all spins
        self.assertEqual(len(strategy.state.history), 6)


def run_tests():
    """Run all tests."""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()

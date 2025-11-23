#!/usr/bin/env python3
"""
Brazilian Roulette Assistant - Flask Web Application
API REST moderna com arquitetura limpa e tratamento robusto de erros.
"""

import logging
import secrets
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from core.engine import GameEngine
from core.models import GameConfig

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicialização do Flask
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)

# Motor do jogo (singleton)
game_engine = GameEngine(GameConfig())


# ============================================================================
# ROTAS DE PÁGINAS
# ============================================================================

@app.route('/')
def index():
    """Serve a página principal."""
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    """Retorna favicon vazio."""
    return '', 204


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/initialize', methods=['POST'])
def api_initialize():
    """
    Inicializa a sessão com banca e estratégias.

    Request Body:
        - bankroll: float - Valor inicial da banca
        - strategies: dict - Estratégias ativas {nome: bool}

    Response:
        - success: bool
        - message: str
        - bankroll: float
        - strategies: dict
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        bankroll = float(data.get('bankroll', 0))
        strategies = data.get('strategies', {})

        if bankroll <= 0:
            return jsonify({'success': False, 'error': 'Banca deve ser maior que zero'}), 400

        session = game_engine.get_session()
        result = session.initialize(bankroll, strategies)

        if not result['success']:
            return jsonify(result), 400

        logger.info(f"Sessão inicializada: Banca R$ {bankroll:.2f}")
        return jsonify(result)

    except ValueError as e:
        logger.error(f"Erro de valor na inicialização: {e}")
        return jsonify({'success': False, 'error': 'Valor de banca inválido'}), 400
    except Exception as e:
        logger.exception(f"Erro na inicialização: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/warmup', methods=['POST'])
def api_warmup():
    """
    Aquece o sistema com números históricos.

    Request Body:
        - numbers: list - Lista de 12 números (mais recente primeiro)

    Response:
        - success: bool
        - message: str
        - bankroll: float
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        numbers = data.get('numbers', [])
        logger.info(f"Warmup recebido: {numbers}")

        if not isinstance(numbers, list):
            return jsonify({'success': False, 'error': 'Formato de números inválido'}), 400

        session = game_engine.get_session()
        result = session.warmup(numbers)

        if not result['success']:
            return jsonify(result), 400

        logger.info(f"Sistema aquecido com {len(numbers)} números")
        return jsonify(result)

    except Exception as e:
        logger.exception(f"Erro no warmup: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/spin', methods=['POST'])
def api_spin():
    """
    Processa um novo número da roleta.

    Request Body:
        - number: str - Número que saiu (0-36 ou 00)

    Response:
        - success: bool
        - number: str
        - color: str
        - properties: dict
        - bankroll: float
        - profit_loss: float
        - signals: list
        - hot_numbers: list
        - cold_numbers: list
        - history: list
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        number = str(data.get('number', '')).strip().upper()

        if not number:
            return jsonify({'success': False, 'error': 'Número não fornecido'}), 400

        session = game_engine.get_session()
        result = session.process_spin(number)

        if not result['success']:
            return jsonify(result), 400

        logger.info(f"Spin processado: {number}, Banca: R$ {result['bankroll']:.2f}")
        return jsonify(result)

    except Exception as e:
        logger.exception(f"Erro no processamento do spin: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/stats', methods=['GET'])
def api_stats():
    """
    Retorna estatísticas atuais.

    Response:
        - success: bool
        - bankroll: float
        - initial_bankroll: float
        - profit_loss: float
        - total_spins: int
        - hot_numbers: list
        - cold_numbers: list
        - history: list
    """
    try:
        session = game_engine.get_session()
        result = session.get_stats()
        return jsonify(result)

    except Exception as e:
        logger.exception(f"Erro ao obter estatísticas: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """
    Reseta a sessão completamente.

    Response:
        - success: bool
        - message: str
    """
    try:
        session = game_engine.get_session()
        result = session.reset()
        logger.info("Sessão resetada")
        return jsonify(result)

    except Exception as e:
        logger.exception(f"Erro ao resetar: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'version': '4.0.0'})


# ============================================================================
# HANDLERS DE ERRO
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handler para erro 404."""
    return jsonify({'success': False, 'error': 'Recurso não encontrado'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handler para erro 500."""
    logger.exception("Erro interno do servidor")
    return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


# ============================================================================
# PONTO DE ENTRADA
# ============================================================================

if __name__ == '__main__':
    # Cria diretórios necessários
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)

    static_dir = Path(__file__).parent / 'static'
    static_dir.mkdir(exist_ok=True)

    (static_dir / 'css').mkdir(exist_ok=True)
    (static_dir / 'js').mkdir(exist_ok=True)

    print("\n" + "=" * 70)
    print("Brazilian Roulette Assistant - Web Interface v4.0")
    print("=" * 70)
    print("\nServidor iniciando...")
    print("Acesse: http://localhost:5000")
    print("\nPressione CTRL+C para encerrar")
    print("=" * 70 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)

#!/usr/bin/env python3
"""
Flask Web Application for Brazilian Roulette Assistant
Provides a beautiful visual interface for the roulette betting system
"""

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import json
import logging
from pathlib import Path
import secrets

# Import the roulette logic from v3.py
import v3

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    """Return a simple favicon"""
    return '', 204


@app.route('/api/initialize', methods=['POST'])
def initialize():
    """Initialize the session with bankroll and strategies"""
    try:
        data = request.json
        bankroll = float(data.get('bankroll', 100))
        strategies = data.get('strategies', {})

        # Reset global state
        v3.BANCA_INICIAL = bankroll
        v3.BANCA_ATUAL = bankroll
        v3.TODOS_GIROS_HISTORICO = []
        v3.NUMEROS_RASTREAMENTO = {str(i): 0 for i in range(37)}
        if v3.TIPO_ROLETA == 'AMERICANA':
            v3.NUMEROS_RASTREAMENTO['00'] = 0

        # Reset all strategy states
        for key in v3.ESTADOS:
            v3.ESTADOS[key]['HISTORICO'] = []
            v3.ESTADOS[key]['APOSTA_EM'] = None
            v3.ESTADOS[key]['VALOR'] = v3.APOSTA_INICIAL_BASE
            v3.ESTADOS[key]['PERDAS'] = 0

        # Set active strategies
        for key in v3.ESTRATEGIAS_ATIVAS:
            v3.ESTRATEGIAS_ATIVAS[key] = strategies.get(key, False)

        # Store in session
        session['initialized'] = True
        session['bankroll'] = bankroll

        return jsonify({
            'success': True,
            'message': 'Sistema inicializado com sucesso',
            'bankroll': bankroll,
            'strategies': {k: v for k, v in v3.ESTRATEGIAS_ATIVAS.items()}
        })

    except Exception as e:
        logger.error(f"Error initializing: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/warmup', methods=['POST'])
def warmup():
    """Process warmup numbers"""
    try:
        data = request.json
        numbers = data.get('numbers', [])

        if len(numbers) != 12:
            return jsonify({
                'success': False,
                'error': f'Esperado 12 números, recebidos {len(numbers)}'
            }), 400

        # Process warmup numbers (reverse order - oldest first)
        for num_str in reversed(numbers):
            v3._atualizar_historicos(num_str)

        return jsonify({
            'success': True,
            'message': f'Sistema aquecido com {len(numbers)} resultados',
            'bankroll': v3.BANCA_ATUAL
        })

    except Exception as e:
        logger.error(f"Error in warmup: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/spin', methods=['POST'])
def process_spin():
    """Process a new spin number"""
    try:
        data = request.json
        number = data.get('number', '').strip().upper()

        if not number:
            return jsonify({'success': False, 'error': 'Número não fornecido'}), 400

        # Validate number
        valid_range = [str(i) for i in range(37)]
        if v3.TIPO_ROLETA == 'AMERICANA':
            valid_range.append('00')

        if number not in valid_range:
            return jsonify({'success': False, 'error': 'Número inválido'}), 400

        # Process the number
        result = v3.aplicar_estrategias(number)

        # Get number properties
        mapa = v3.get_mapeamento_numero(number)

        # Get hot and cold numbers
        top_frios, top_quentes = v3.analisar_frequencia_numeros()

        # Parse the result to extract signals
        signals = []
        for strategy_key in v3.ESTRATEGIAS_ATIVAS:
            if v3.ESTRATEGIAS_ATIVAS[strategy_key]:
                estado = v3.ESTADOS[strategy_key]
                if estado['APOSTA_EM']:
                    signals.append({
                        'strategy': strategy_key,
                        'target': estado['APOSTA_EM'],
                        'amount': estado['VALOR'],
                        'losses': estado['PERDAS']
                    })

        return jsonify({
            'success': True,
            'number': number,
            'color': mapa.get('COR', 'G'),
            'properties': mapa,
            'bankroll': v3.BANCA_ATUAL,
            'profit_loss': v3.BANCA_ATUAL - v3.BANCA_INICIAL,
            'result_text': result,
            'signals': signals,
            'hot_numbers': top_quentes,
            'cold_numbers': top_frios,
            'history': v3.TODOS_GIROS_HISTORICO[-20:]  # Last 20 spins
        })

    except Exception as e:
        logger.error(f"Error processing spin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get current statistics"""
    try:
        top_frios, top_quentes = v3.analisar_frequencia_numeros()

        return jsonify({
            'success': True,
            'bankroll': v3.BANCA_ATUAL,
            'initial_bankroll': v3.BANCA_INICIAL,
            'profit_loss': v3.BANCA_ATUAL - v3.BANCA_INICIAL,
            'total_spins': len(v3.TODOS_GIROS_HISTORICO),
            'hot_numbers': top_quentes,
            'cold_numbers': top_frios,
            'history': v3.TODOS_GIROS_HISTORICO[-20:]
        })

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/reset', methods=['POST'])
def reset_session():
    """Reset the entire session"""
    try:
        v3.BANCA_INICIAL = 0.0
        v3.BANCA_ATUAL = 0.0
        v3.TODOS_GIROS_HISTORICO = []
        v3.NUMEROS_RASTREAMENTO = {str(i): 0 for i in range(37)}

        for key in v3.ESTADOS:
            v3.ESTADOS[key]['HISTORICO'] = []
            v3.ESTADOS[key]['APOSTA_EM'] = None
            v3.ESTADOS[key]['VALOR'] = v3.APOSTA_INICIAL_BASE
            v3.ESTADOS[key]['PERDAS'] = 0

        for key in v3.ESTRATEGIAS_ATIVAS:
            v3.ESTRATEGIAS_ATIVAS[key] = False

        session.clear()

        return jsonify({'success': True, 'message': 'Sessão reiniciada'})

    except Exception as e:
        logger.error(f"Error resetting: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # Create templates folder if it doesn't exist
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)

    static_dir = Path(__file__).parent / 'static'
    static_dir.mkdir(exist_ok=True)

    print("\n" + "="*70)
    print("🎰 Brazilian Roulette Assistant - Web Interface")
    print("="*70)
    print("\n✨ Servidor iniciando...")
    print(f"🌐 Acesse: http://localhost:5000")
    print(f"📱 Ou:     http://127.0.0.1:5000")
    print("\n⚠️  Pressione CTRL+C para encerrar\n")
    print("="*70 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)

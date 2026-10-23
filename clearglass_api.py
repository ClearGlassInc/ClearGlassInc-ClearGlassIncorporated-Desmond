"""
ClearGlass Cryptocurrency - REST API Server
Provides HTTP endpoints for blockchain interactions
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from clearglass_blockchain import ClearGlassBlockchain, Transaction
from clearglass_wallet import ClearGlassWallet, create_wallet
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for web applications

# Initialize blockchain
blockchain = ClearGlassBlockchain()

# Store for network nodes
network_nodes = set()


@app.route('/')
def index():
    """API information"""
    return jsonify({
        'name': 'ClearGlass Cryptocurrency API',
        'version': '1.0.0',
        'description': 'Transparent, secure blockchain network',
        'endpoints': {
            'GET /blockchain': 'Get full blockchain',
            'GET /blockchain/latest': 'Get latest block',
            'GET /blockchain/validate': 'Validate blockchain',
            'POST /transaction/new': 'Create new transaction',
            'POST /mine': 'Mine pending transactions',
            'GET /balance/<address>': 'Get address balance',
            'GET /transactions/<address>': 'Get transaction history',
            'POST /wallet/create': 'Create new wallet',
            'GET /stats': 'Get blockchain statistics',
            'POST /nodes/register': 'Register network node',
            'GET /nodes': 'Get all nodes'
        }
    })


@app.route('/blockchain', methods=['GET'])
def get_blockchain():
    """Get the entire blockchain"""
    return jsonify({
        'chain': blockchain.get_chain_data(),
        'length': len(blockchain.chain)
    })


@app.route('/blockchain/latest', methods=['GET'])
def get_latest_block():
    """Get the latest block"""
    latest = blockchain.get_latest_block()
    return jsonify(latest.to_dict())


@app.route('/blockchain/validate', methods=['GET'])
def validate_blockchain():
    """Validate the blockchain"""
    is_valid = blockchain.is_chain_valid()
    return jsonify({
        'valid': is_valid,
        'blocks': len(blockchain.chain),
        'message': 'Blockchain is valid' if is_valid else 'Blockchain is invalid'
    })


@app.route('/transaction/new', methods=['POST'])
def new_transaction():
    """Create a new transaction"""
    data = request.get_json()
    
    required_fields = ['sender', 'recipient', 'amount', 'signature']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        transaction = Transaction(
            sender=data['sender'],
            recipient=data['recipient'],
            amount=float(data['amount']),
            signature=data['signature']
        )
        
        if blockchain.add_transaction(transaction):
            return jsonify({
                'message': 'Transaction added to pending pool',
                'transaction': transaction.to_dict()
            }), 201
        else:
            return jsonify({'error': 'Invalid transaction'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/mine', methods=['POST'])
def mine_block():
    """Mine pending transactions"""
    data = request.get_json()
    
    if 'miner_address' not in data:
        return jsonify({'error': 'Miner address required'}), 400
    
    miner_address = data['miner_address']
    
    # Mine the block
    start_time = time.time()
    blockchain.mine_pending_transactions(miner_address)
    mining_time = time.time() - start_time
    
    latest_block = blockchain.get_latest_block()
    
    return jsonify({
        'message': 'Block mined successfully',
        'block': latest_block.to_dict(),
        'mining_time': mining_time,
        'reward': blockchain.mining_reward
    })


@app.route('/balance/<address>', methods=['GET'])
def get_balance(address):
    """Get balance for an address"""
    balance = blockchain.get_balance(address)
    return jsonify({
        'address': address[:20] + '...',
        'balance': balance,
        'currency': 'CGLASS'
    })


@app.route('/transactions/<address>', methods=['GET'])
def get_transactions(address):
    """Get transaction history for an address"""
    history = blockchain.get_transaction_history(address)
    return jsonify({
        'address': address[:20] + '...',
        'transaction_count': len(history),
        'transactions': history
    })


@app.route('/wallet/create', methods=['POST'])
def create_new_wallet():
    """Create a new wallet"""
    public_key, private_key = create_wallet()
    
    return jsonify({
        'address': public_key,
        'public_key': public_key,
        'private_key': private_key,
        'warning': 'SAVE YOUR PRIVATE KEY SECURELY! It cannot be recovered.'
    }), 201


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get blockchain statistics"""
    total_supply = blockchain.get_total_supply()
    total_transactions = sum(len(block.transactions) for block in blockchain.chain)
    
    return jsonify({
        'blocks': len(blockchain.chain),
        'total_transactions': total_transactions,
        'total_supply': total_supply,
        'max_supply': blockchain.MAX_SUPPLY,
        'mining_reward': blockchain.mining_reward,
        'difficulty': blockchain.difficulty,
        'pending_transactions': len(blockchain.pending_transactions),
        'supply_percentage': (total_supply / blockchain.MAX_SUPPLY) * 100
    })


@app.route('/nodes/register', methods=['POST'])
def register_node():
    """Register a new network node"""
    data = request.get_json()
    
    if 'node_address' not in data:
        return jsonify({'error': 'Node address required'}), 400
    
    node_address = data['node_address']
    network_nodes.add(node_address)
    
    return jsonify({
        'message': 'Node registered successfully',
        'total_nodes': len(network_nodes),
        'nodes': list(network_nodes)
    })


@app.route('/nodes', methods=['GET'])
def get_nodes():
    """Get all registered nodes"""
    return jsonify({
        'total_nodes': len(network_nodes),
        'nodes': list(network_nodes)
    })


@app.route('/pending', methods=['GET'])
def get_pending_transactions():
    """Get all pending transactions"""
    pending = [tx.to_dict() for tx in blockchain.pending_transactions]
    return jsonify({
        'count': len(pending),
        'transactions': pending
    })


@app.route('/block/<int:index>', methods=['GET'])
def get_block(index):
    """Get a specific block by index"""
    if index < 0 or index >= len(blockchain.chain):
        return jsonify({'error': 'Block not found'}), 404
    
    block = blockchain.chain[index]
    return jsonify(block.to_dict())


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("ClearGlass Cryptocurrency API Server")
    print("=" * 60)
    print("Starting server on http://localhost:5000")
    print("API documentation: http://localhost:5000")
    print("=" * 60)
    
    # Run server
    app.run(host='0.0.0.0', port=5000, debug=True)

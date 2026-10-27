#!/usr/bin/env python3
"""
ClearGlass Cryptocurrency - Command Line Interface
Complete CLI for all ClearGlass operations
"""

import click
import os
import sys
from tabulate import tabulate
from colorama import init, Fore, Style
from clearglass_blockchain import ClearGlassBlockchain
from clearglass_wallet import WalletManager
from clearglass_network import NetworkNode

# Initialize colorama
init(autoreset=True)

# Global blockchain instance
blockchain = ClearGlassBlockchain()
wallet_manager = WalletManager()


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    ClearGlass Cryptocurrency CLI
    
    Manage wallets, transactions, mining, and blockchain operations
    """
    pass


# ============================================================================
# WALLET COMMANDS
# ============================================================================

@cli.group()
def wallet():
    """Wallet management commands"""
    pass


@wallet.command('create')
@click.option('--name', required=True, help='Wallet name')
def wallet_create(name):
    """Create a new wallet"""
    try:
        wallet = wallet_manager.create_wallet(name)
        
        click.echo(f"{Fore.GREEN}✓ Wallet created successfully!")
        click.echo(f"\n{Fore.CYAN}Wallet Name: {Fore.WHITE}{name}")
        click.echo(f"{Fore.CYAN}Address: {Fore.WHITE}{wallet.address[:40]}...")
        click.echo(f"\n{Fore.YELLOW}⚠️  IMPORTANT: Your wallet has been saved to wallets/{name}.json")
        click.echo(f"{Fore.YELLOW}    Keep this file secure and backed up!")
        
    except Exception as e:
        click.echo(f"{Fore.RED}✗ Error creating wallet: {e}")


@wallet.command('list')
def wallet_list():
    """List all wallets"""
    wallets = wallet_manager.list_wallets()
    
    if not wallets:
        click.echo(f"{Fore.YELLOW}No wallets found. Create one with: clearglass wallet create")
        return
    
    click.echo(f"\n{Fore.CYAN}Available Wallets:")
    for i, wallet_name in enumerate(wallets, 1):
        click.echo(f"  {i}. {wallet_name}")


@wallet.command('balance')
@click.option('--name', required=True, help='Wallet name')
def wallet_balance(name):
    """Check wallet balance"""
    wallet = wallet_manager.load_wallet(name)
    
    if not wallet:
        click.echo(f"{Fore.RED}✗ Wallet not found: {name}")
        return
    
    balance = wallet.get_balance(blockchain)
    
    click.echo(f"\n{Fore.CYAN}Wallet: {Fore.WHITE}{name}")
    click.echo(f"{Fore.CYAN}Address: {Fore.WHITE}{wallet.address[:40]}...")
    click.echo(f"{Fore.GREEN}Balance: {Fore.WHITE}{balance} CGLASS")


@wallet.command('send')
@click.option('--from', 'from_wallet', required=True, help='Sender wallet name')
@click.option('--to', required=True, help='Recipient address')
@click.option('--amount', required=True, type=float, help='Amount to send')
def wallet_send(from_wallet, to, amount):
    """Send CGLASS to another address"""
    wallet = wallet_manager.load_wallet(from_wallet)
    
    if not wallet:
        click.echo(f"{Fore.RED}✗ Wallet not found: {from_wallet}")
        return
    
    # Check balance
    balance = wallet.get_balance(blockchain)
    if balance < amount:
        click.echo(f"{Fore.RED}✗ Insufficient balance")
        click.echo(f"  Available: {balance} CGLASS")
        click.echo(f"  Required: {amount} CGLASS")
        return
    
    # Confirm transaction
    click.echo(f"\n{Fore.YELLOW}Transaction Details:")
    click.echo(f"  From: {wallet.address[:40]}...")
    click.echo(f"  To: {to[:40]}...")
    click.echo(f"  Amount: {amount} CGLASS")
    
    if not click.confirm("\nConfirm transaction?"):
        click.echo(f"{Fore.YELLOW}Transaction cancelled")
        return
    
    # Send transaction
    if wallet.send_transaction(to, amount, blockchain):
        click.echo(f"\n{Fore.GREEN}✓ Transaction created!")
        click.echo(f"{Fore.YELLOW}⏳ Waiting for mining confirmation...")
        click.echo(f"{Fore.CYAN}Tip: Run 'clearglass mine --address <your_address>' to mine the transaction")
    else:
        click.echo(f"{Fore.RED}✗ Transaction failed")


@wallet.command('info')
@click.option('--name', required=True, help='Wallet name')
def wallet_info(name):
    """View detailed wallet information"""
    wallet = wallet_manager.load_wallet(name)
    
    if not wallet:
        click.echo(f"{Fore.RED}✗ Wallet not found: {name}")
        return
    
    info = wallet.get_wallet_info(blockchain)
    
    click.echo(f"\n{Fore.CYAN}Wallet Information:")
    click.echo(f"  Name: {name}")
    click.echo(f"  Address: {info['address'][:40]}...")
    click.echo(f"  Balance: {info['balance']} CGLASS")
    click.echo(f"  Transactions: {info['transaction_count']}")


@wallet.command('history')
@click.option('--name', required=True, help='Wallet name')
@click.option('--limit', default=10, help='Number of transactions to show')
def wallet_history(name, limit):
    """View transaction history"""
    wallet = wallet_manager.load_wallet(name)
    
    if not wallet:
        click.echo(f"{Fore.RED}✗ Wallet not found: {name}")
        return
    
    history = wallet.get_transaction_history(blockchain)
    
    if not history:
        click.echo(f"{Fore.YELLOW}No transactions found")
        return
    
    # Display recent transactions
    recent = history[-limit:]
    
    click.echo(f"\n{Fore.CYAN}Transaction History (showing {len(recent)} of {len(history)}):")
    
    table_data = []
    for tx in recent:
        direction = "Received" if tx['recipient'] == wallet.address else "Sent"
        color = Fore.GREEN if direction == "Received" else Fore.RED
        
        table_data.append([
            tx['block_index'],
            f"{color}{direction}{Style.RESET_ALL}",
            tx['amount'],
            tx['sender'][:20] + "...",
            tx['recipient'][:20] + "..."
        ])
    
    headers = ['Block', 'Type', 'Amount', 'From', 'To']
    click.echo(tabulate(table_data, headers=headers, tablefmt='simple'))


# ============================================================================
# BLOCKCHAIN COMMANDS
# ============================================================================

@cli.group()
def blockchain_cmd():
    """Blockchain operations"""
    pass


@blockchain_cmd.command('info')
def blockchain_info():
    """View blockchain information"""
    total_supply = blockchain.get_total_supply()
    total_transactions = sum(len(block.transactions) for block in blockchain.chain)
    
    click.echo(f"\n{Fore.CYAN}Blockchain Information:")
    click.echo(f"  Blocks: {len(blockchain.chain)}")
    click.echo(f"  Total Transactions: {total_transactions}")
    click.echo(f"  Total Supply: {total_supply} CGLASS")
    click.echo(f"  Max Supply: {blockchain.MAX_SUPPLY} CGLASS")
    click.echo(f"  Supply %: {(total_supply / blockchain.MAX_SUPPLY) * 100:.2f}%")
    click.echo(f"  Mining Difficulty: {blockchain.difficulty}")
    click.echo(f"  Mining Reward: {blockchain.mining_reward} CGLASS")
    click.echo(f"  Pending Transactions: {len(blockchain.pending_transactions)}")


@blockchain_cmd.command('validate')
def blockchain_validate():
    """Validate blockchain integrity"""
    click.echo(f"{Fore.YELLOW}Validating blockchain...")
    
    is_valid = blockchain.is_chain_valid()
    
    if is_valid:
        click.echo(f"{Fore.GREEN}✓ Blockchain is valid!")
        click.echo(f"  All {len(blockchain.chain)} blocks verified")
    else:
        click.echo(f"{Fore.RED}✗ Blockchain is invalid!")
        click.echo("  Chain integrity compromised")


@blockchain_cmd.command('blocks')
@click.option('--limit', default=10, help='Number of blocks to show')
def blockchain_blocks(limit):
    """List recent blocks"""
    recent_blocks = blockchain.chain[-limit:]
    
    click.echo(f"\n{Fore.CYAN}Recent Blocks (showing {len(recent_blocks)} of {len(blockchain.chain)}):")
    
    table_data = []
    for block in recent_blocks:
        table_data.append([
            block.index,
            len(block.transactions),
            block.hash[:16] + "...",
            block.nonce
        ])
    
    headers = ['Index', 'Transactions', 'Hash', 'Nonce']
    click.echo(tabulate(table_data, headers=headers, tablefmt='simple'))


@blockchain_cmd.command('pending')
def blockchain_pending():
    """View pending transactions"""
    if not blockchain.pending_transactions:
        click.echo(f"{Fore.YELLOW}No pending transactions")
        return
    
    click.echo(f"\n{Fore.CYAN}Pending Transactions ({len(blockchain.pending_transactions)}):")
    
    table_data = []
    for tx in blockchain.pending_transactions:
        table_data.append([
            tx.sender[:20] + "...",
            tx.recipient[:20] + "...",
            tx.amount
        ])
    
    headers = ['From', 'To', 'Amount']
    click.echo(tabulate(table_data, headers=headers, tablefmt='simple'))


# ============================================================================
# MINING COMMANDS
# ============================================================================

@cli.command()
@click.option('--address', required=True, help='Mining reward address')
@click.option('--blocks', default=1, help='Number of blocks to mine')
def mine(address, blocks):
    """Mine new blocks"""
    click.echo(f"\n{Fore.CYAN}Mining {blocks} block(s)...")
    click.echo(f"{Fore.YELLOW}Difficulty: {blockchain.difficulty} (requires {blockchain.difficulty} leading zeros)")
    
    for i in range(blocks):
        click.echo(f"\n{Fore.CYAN}Mining block {i+1}/{blocks}...")
        
        import time
        start_time = time.time()
        blockchain.mine_pending_transactions(address)
        mining_time = time.time() - start_time
        
        latest_block = blockchain.get_latest_block()
        
        click.echo(f"{Fore.GREEN}✓ Block {latest_block.index} mined!")
        click.echo(f"  Hash: {latest_block.hash[:40]}...")
        click.echo(f"  Nonce: {latest_block.nonce}")
        click.echo(f"  Transactions: {len(latest_block.transactions)}")
        click.echo(f"  Time: {mining_time:.2f} seconds")
        click.echo(f"  Reward: {blockchain.mining_reward} CGLASS")


# ============================================================================
# NETWORK COMMANDS
# ============================================================================

@cli.group()
def network():
    """Network node commands"""
    pass


@network.command('start')
@click.option('--port', default=8333, help='Network port')
def network_start(port):
    """Start network node"""
    node = NetworkNode('0.0.0.0', port)
    node.start()
    
    click.echo(f"\n{Fore.GREEN}✓ Network node started")
    click.echo(f"  Address: 0.0.0.0:{port}")
    click.echo(f"  Node ID: {node.get_node_id()}")
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo(f"\n{Fore.YELLOW}Stopping node...")
        node.stop()


# ============================================================================
# UTILITY COMMANDS
# ============================================================================

@cli.command()
def init():
    """Initialize ClearGlass cryptocurrency"""
    click.echo(f"\n{Fore.CYAN}Initializing ClearGlass Cryptocurrency...")
    
    # Create necessary directories
    os.makedirs('wallets', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    click.echo(f"{Fore.GREEN}✓ Directories created")
    click.echo(f"{Fore.GREEN}✓ Blockchain initialized with genesis block")
    click.echo(f"\n{Fore.CYAN}Quick Start:")
    click.echo("  1. Create wallet: clearglass wallet create --name mywallet")
    click.echo("  2. Mine blocks: clearglass mine --address <your_address>")
    click.echo("  3. Check balance: clearglass wallet balance --name mywallet")


@cli.command()
def version():
    """Show version information"""
    click.echo(f"\n{Fore.CYAN}ClearGlass Cryptocurrency")
    click.echo(f"Version: {Fore.WHITE}1.0.0")
    click.echo(f"Python: {Fore.WHITE}{sys.version.split()[0]}")
    click.echo(f"\n{Fore.CYAN}Components:")
    click.echo("  • Blockchain Core: v1.0.0")
    click.echo("  • Wallet System: v1.0.0")
    click.echo("  • Network Protocol: v1.0.0")
    click.echo("  • REST API: v1.0.0")


if __name__ == '__main__':
    cli()

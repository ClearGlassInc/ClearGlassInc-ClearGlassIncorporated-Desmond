#!/usr/bin/env python3
"""
ClearGlass Cryptocurrency - Example Usage
Demonstrates basic functionality and usage patterns
"""

from clearglass_blockchain import (
    ClearGlassBlockchain, 
    Transaction, 
    create_wallet, 
    load_private_key
)
from clearglass_wallet import ClearGlassWallet
import time


def print_separator():
    print("\n" + "=" * 70 + "\n")


def example_1_basic_blockchain():
    """Example 1: Create blockchain and mine blocks"""
    print("EXAMPLE 1: Basic Blockchain Operations")
    print_separator()
    
    # Create blockchain
    print("1. Creating blockchain...")
    blockchain = ClearGlassBlockchain()
    print("   ✓ Genesis block created")
    print(f"   ✓ Blockchain initialized with {len(blockchain.chain)} block")
    
    # Create wallets
    print("\n2. Creating wallets...")
    alice_public, alice_private = create_wallet()
    print("   ✓ Alice's wallet created")
    print(f"     Address: {alice_public[:40]}...")
    
    bob_public, bob_private = create_wallet()
    print("   ✓ Bob's wallet created")
    print(f"     Address: {bob_public[:40]}...")
    
    # Mine initial blocks for Alice
    print("\n3. Mining blocks for Alice...")
    for i in range(3):
        print(f"   Mining block {i+1}...")
        start = time.time()
        blockchain.mine_pending_transactions(alice_public)
        elapsed = time.time() - start
        print(f"   ✓ Block mined in {elapsed:.2f} seconds")
    
    # Check Alice's balance
    balance = blockchain.get_balance(alice_public)
    print(f"\n4. Alice's balance: {balance} CGLASS")
    
    return blockchain, alice_public, alice_private, bob_public, bob_private


def example_2_transactions(blockchain, alice_public, alice_private, bob_public):
    """Example 2: Create and sign transactions"""
    print("\nEXAMPLE 2: Creating Transactions")
    print_separator()
    
    # Create transaction
    print("1. Creating transaction from Alice to Bob...")
    amount = 30.5
    transaction = Transaction(alice_public, bob_public, amount)
    print(f"   ✓ Transaction created: {amount} CGLASS")
    print(f"     From: {alice_public[:30]}...")
    print(f"     To: {bob_public[:30]}...")
    
    # Sign transaction
    print("\n2. Signing transaction with Alice's private key...")
    private_key = load_private_key(alice_private)
    transaction.sign_transaction(private_key)
    print("   ✓ Transaction signed")
    print(f"     Signature: {transaction.signature[:40]}...")
    
    # Validate transaction
    print("\n3. Validating transaction...")
    is_valid = transaction.is_valid()
    print(f"   ✓ Transaction is {'valid' if is_valid else 'invalid'}")
    
    # Add to blockchain
    print("\n4. Adding transaction to blockchain...")
    if blockchain.add_transaction(transaction):
        print("   ✓ Transaction added to pending pool")
    
    # Mine block
    print("\n5. Mining block with transaction...")
    start = time.time()
    blockchain.mine_pending_transactions(bob_public)
    elapsed = time.time() - start
    print(f"   ✓ Block mined in {elapsed:.2f} seconds")
    
    # Check balances
    print("\n6. Updated balances:")
    alice_balance = blockchain.get_balance(alice_public)
    bob_balance = blockchain.get_balance(bob_public)
    print(f"   Alice: {alice_balance} CGLASS")
    print(f"   Bob: {bob_balance} CGLASS")


def example_3_multiple_transactions(blockchain, alice_public, alice_private, bob_public):
    """Example 3: Multiple transactions in one block"""
    print("\nEXAMPLE 3: Multiple Transactions")
    print_separator()
    
    print("1. Creating multiple transactions...")
    
    # Create several transactions
    amounts = [10, 15, 20]
    for i, amount in enumerate(amounts, 1):
        transaction = Transaction(alice_public, bob_public, amount)
        private_key = load_private_key(alice_private)
        transaction.sign_transaction(private_key)
        blockchain.add_transaction(transaction)
        print(f"   ✓ Transaction {i}: {amount} CGLASS")
    
    print(f"\n2. Pending transactions: {len(blockchain.pending_transactions)}")
    
    # Mine all transactions
    print("\n3. Mining block with all transactions...")
    start = time.time()
    blockchain.mine_pending_transactions(alice_public)
    elapsed = time.time() - start
    print(f"   ✓ Block mined in {elapsed:.2f} seconds")
    
    # Show latest block
    latest = blockchain.get_latest_block()
    print("\n4. Latest block details:")
    print(f"   Block index: {latest.index}")
    print(f"   Transactions: {len(latest.transactions)}")
    print(f"   Hash: {latest.hash[:40]}...")
    print(f"   Nonce: {latest.nonce}")


def example_4_blockchain_validation(blockchain):
    """Example 4: Validate blockchain integrity"""
    print("\nEXAMPLE 4: Blockchain Validation")
    print_separator()
    
    print("1. Validating blockchain...")
    is_valid = blockchain.is_chain_valid()
    
    print(f"\n2. Validation result: {'✓ VALID' if is_valid else '✗ INVALID'}")
    
    print("\n3. Blockchain statistics:")
    print(f"   Total blocks: {len(blockchain.chain)}")
    print(f"   Total supply: {blockchain.get_total_supply()} CGLASS")
    print(f"   Max supply: {blockchain.MAX_SUPPLY} CGLASS")
    
    total_tx = sum(len(block.transactions) for block in blockchain.chain)
    print(f"   Total transactions: {total_tx}")


def example_5_wallet_management():
    """Example 5: Wallet management"""
    print("\nEXAMPLE 5: Wallet Management")
    print_separator()
    
    print("1. Creating wallet...")
    wallet = ClearGlassWallet('example_wallet.json')
    wallet_data = wallet.create_new_wallet()
    
    print("   ✓ Wallet created and saved")
    print(f"     Address: {wallet_data['address'][:40]}...")
    print(f"     Created: {wallet_data['created_at']}")
    
    print("\n2. Loading wallet from file...")
    wallet2 = ClearGlassWallet('example_wallet.json')
    if wallet2.load_wallet():
        print("   ✓ Wallet loaded successfully")
        print(f"     Address matches: {wallet2.address == wallet_data['address']}")
    
    # Clean up
    import os
    if os.path.exists('example_wallet.json'):
        os.remove('example_wallet.json')
        print("\n3. Cleanup: example wallet file removed")


def example_6_transaction_history(blockchain, alice_public, bob_public):
    """Example 6: Transaction history"""
    print("\nEXAMPLE 6: Transaction History")
    print_separator()
    
    print("1. Retrieving transaction history...")
    
    alice_history = blockchain.get_transaction_history(alice_public)
    bob_history = blockchain.get_transaction_history(bob_public)
    
    print(f"\n2. Alice's transaction history ({len(alice_history)} transactions):")
    for tx in alice_history[:5]:  # Show first 5
        tx_type = "Received" if tx['recipient'] == alice_public else "Sent"
        print(f"   [{tx['block_index']}] {tx_type}: {tx['amount']} CGLASS")
    
    print(f"\n3. Bob's transaction history ({len(bob_history)} transactions):")
    for tx in bob_history[:5]:  # Show first 5
        tx_type = "Received" if tx['recipient'] == bob_public else "Sent"
        print(f"   [{tx['block_index']}] {tx_type}: {tx['amount']} CGLASS")


def example_7_save_and_export(blockchain):
    """Example 7: Save and export blockchain"""
    print("\nEXAMPLE 7: Save and Export")
    print_separator()
    
    print("1. Saving blockchain to file...")
    blockchain.save_to_file('example_blockchain.json')
    
    print("\n2. Exporting chain data...")
    chain_data = blockchain.get_chain_data()
    print(f"   ✓ Exported {len(chain_data)} blocks")
    
    print("\n3. Block sizes:")
    import json
    for i, block in enumerate(chain_data):
        block_json = json.dumps(block)
        print(f"   Block {i}: {len(block_json)} bytes")
    
    # Clean up
    import os
    if os.path.exists('example_blockchain.json'):
        os.remove('example_blockchain.json')
        print("\n4. Cleanup: example blockchain file removed")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("ClearGlass Cryptocurrency - Example Usage Demonstrations".center(70))
    print("=" * 70)
    
    # Example 1: Basic operations
    blockchain, alice_pub, alice_priv, bob_pub, bob_priv = example_1_basic_blockchain()
    
    # Example 2: Transactions
    example_2_transactions(blockchain, alice_pub, alice_priv, bob_pub)
    
    # Example 3: Multiple transactions
    example_3_multiple_transactions(blockchain, alice_pub, alice_priv, bob_pub)
    
    # Example 4: Validation
    example_4_blockchain_validation(blockchain)
    
    # Example 5: Wallet management
    example_5_wallet_management()
    
    # Example 6: Transaction history
    example_6_transaction_history(blockchain, alice_pub, bob_pub)
    
    # Example 7: Save and export
    example_7_save_and_export(blockchain)
    
    # Final summary
    print("\n" + "=" * 70)
    print("Examples Complete!".center(70))
    print("=" * 70)
    
    print("\n📊 Final Statistics:")
    print(f"   Total blocks: {len(blockchain.chain)}")
    print(f"   Total supply: {blockchain.get_total_supply()} CGLASS")
    print(f"   Alice's balance: {blockchain.get_balance(alice_pub)} CGLASS")
    print(f"   Bob's balance: {blockchain.get_balance(bob_pub)} CGLASS")
    print(f"   Blockchain valid: {blockchain.is_chain_valid()}")
    
    print("\n✨ All examples completed successfully!")
    print("\nNext steps:")
    print("  • Try the CLI: python clearglass_cli.py --help")
    print("  • Start the API: python clearglass_api.py")
    print("  • Read the docs: README.md, WHITEPAPER.md")
    print("\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Examples interrupted by user\n")
    except Exception as e:
        print(f"\n❌ Error running examples: {e}\n")
        import traceback
        traceback.print_exc()

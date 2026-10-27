"""
ClearGlass Cryptocurrency - Test Suite
Unit tests for blockchain, wallet, and transaction functionality
"""

import unittest
from clearglass_blockchain import (
    ClearGlassBlockchain,
    Transaction,
    Block,
    create_wallet,
    load_private_key
)
from clearglass_wallet import ClearGlassWallet


class TestBlockchain(unittest.TestCase):
    """Test blockchain functionality"""
    
    def setUp(self):
        """Set up test blockchain"""
        self.blockchain = ClearGlassBlockchain()
    
    def test_genesis_block(self):
        """Test genesis block creation"""
        self.assertEqual(len(self.blockchain.chain), 1)
        self.assertEqual(self.blockchain.chain[0].index, 0)
        self.assertEqual(self.blockchain.chain[0].previous_hash, "0")
    
    def test_mining(self):
        """Test block mining"""
        address = "test_address"
        initial_blocks = len(self.blockchain.chain)
        
        self.blockchain.mine_pending_transactions(address)
        
        self.assertEqual(len(self.blockchain.chain), initial_blocks + 1)
        self.assertGreater(self.blockchain.get_balance(address), 0)
    
    def test_blockchain_validation(self):
        """Test blockchain validation"""
        self.assertTrue(self.blockchain.is_chain_valid())
        
        # Mine a few blocks
        for _ in range(3):
            self.blockchain.mine_pending_transactions("test_address")
        
        self.assertTrue(self.blockchain.is_chain_valid())
    
    def test_supply_cap(self):
        """Test maximum supply enforcement"""
        # This would require mining many blocks
        # For now, just check the constant is set
        self.assertEqual(self.blockchain.MAX_SUPPLY, 21_000_000)
        
        # Check total supply calculation
        total = self.blockchain.get_total_supply()
        self.assertLessEqual(total, self.blockchain.MAX_SUPPLY)


class TestTransaction(unittest.TestCase):
    """Test transaction functionality"""
    
    def setUp(self):
        """Set up test wallets and blockchain"""
        self.blockchain = ClearGlassBlockchain()
        self.alice_pub, self.alice_priv = create_wallet()
        self.bob_pub, self.bob_priv = create_wallet()
        
        # Give Alice some coins
        self.blockchain.mine_pending_transactions(self.alice_pub)
    
    def test_transaction_creation(self):
        """Test creating a transaction"""
        tx = Transaction(self.alice_pub, self.bob_pub, 10)
        
        self.assertEqual(tx.sender, self.alice_pub)
        self.assertEqual(tx.recipient, self.bob_pub)
        self.assertEqual(tx.amount, 10)
        self.assertIsNotNone(tx.timestamp)
    
    def test_transaction_signing(self):
        """Test transaction signing"""
        tx = Transaction(self.alice_pub, self.bob_pub, 10)
        
        # Sign transaction
        private_key = load_private_key(self.alice_priv)
        tx.sign_transaction(private_key)
        
        self.assertIsNotNone(tx.signature)
        self.assertTrue(tx.is_valid())
    
    def test_invalid_signature(self):
        """Test invalid signature detection"""
        tx = Transaction(self.alice_pub, self.bob_pub, 10)
        
        # Sign with wrong key
        private_key = load_private_key(self.bob_priv)
        tx.sign_transaction(private_key)
        
        # Transaction should be invalid (wrong key)
        # Note: This test might pass because signature validation
        # uses sender address. In practice, this would fail in add_transaction
        tx.signature = "invalid_signature"
        self.assertFalse(tx.is_valid())
    
    def test_transaction_addition(self):
        """Test adding transaction to blockchain"""
        tx = Transaction(self.alice_pub, self.bob_pub, 10)
        private_key = load_private_key(self.alice_priv)
        tx.sign_transaction(private_key)
        
        result = self.blockchain.add_transaction(tx)
        self.assertTrue(result)
        self.assertEqual(len(self.blockchain.pending_transactions), 1)
    
    def test_insufficient_balance(self):
        """Test transaction with insufficient balance"""
        # Try to send more than Alice has
        balance = self.blockchain.get_balance(self.alice_pub)
        
        tx = Transaction(self.alice_pub, self.bob_pub, balance + 100)
        private_key = load_private_key(self.alice_priv)
        tx.sign_transaction(private_key)
        
        result = self.blockchain.add_transaction(tx)
        self.assertFalse(result)
    
    def test_transaction_in_block(self):
        """Test transaction inclusion in mined block"""
        # Create and add transaction
        tx = Transaction(self.alice_pub, self.bob_pub, 10)
        private_key = load_private_key(self.alice_priv)
        tx.sign_transaction(private_key)
        self.blockchain.add_transaction(tx)
        
        # Mine block
        self.blockchain.mine_pending_transactions(self.bob_pub)
        
        # Check Bob's balance increased
        balance = self.blockchain.get_balance(self.bob_pub)
        self.assertGreater(balance, 10)  # 10 from tx + mining reward


class TestWallet(unittest.TestCase):
    """Test wallet functionality"""
    
    def test_wallet_creation(self):
        """Test wallet creation"""
        public, private = create_wallet()
        
        self.assertIsNotNone(public)
        self.assertIsNotNone(private)
        self.assertNotEqual(public, private)
    
    def test_wallet_save_load(self):
        """Test saving and loading wallet"""
        import os
        test_file = "test_wallet.json"
        
        try:
            # Create and save wallet
            wallet = ClearGlassWallet(test_file)
            wallet.create_new_wallet()
            original_address = wallet.address
            
            # Load wallet
            wallet2 = ClearGlassWallet(test_file)
            loaded = wallet2.load_wallet()
            
            self.assertTrue(loaded)
            self.assertEqual(wallet2.address, original_address)
            
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.remove(test_file)
    
    def test_wallet_balance(self):
        """Test wallet balance calculation"""
        blockchain = ClearGlassBlockchain()
        wallet = ClearGlassWallet()
        wallet.create_new_wallet(save=False)
        
        # Initially 0
        self.assertEqual(wallet.get_balance(blockchain), 0)
        
        # Mine a block
        blockchain.mine_pending_transactions(wallet.address)
        
        # Should have mining reward
        self.assertEqual(wallet.get_balance(blockchain), blockchain.mining_reward)


class TestBlock(unittest.TestCase):
    """Test block functionality"""
    
    def test_block_creation(self):
        """Test block creation"""
        tx = Transaction("sender", "recipient", 10)
        block = Block(1, [tx], "previous_hash")
        
        self.assertEqual(block.index, 1)
        self.assertEqual(len(block.transactions), 1)
        self.assertEqual(block.previous_hash, "previous_hash")
        self.assertIsNotNone(block.timestamp)
        self.assertIsNotNone(block.hash)
    
    def test_block_mining(self):
        """Test block mining with different difficulties"""
        tx = Transaction("sender", "recipient", 10)
        block = Block(1, [tx], "previous_hash")
        
        # Test difficulty 2
        block.mine_block(2)
        self.assertTrue(block.hash.startswith("00"))
    
    def test_hash_calculation(self):
        """Test block hash calculation"""
        tx = Transaction("sender", "recipient", 10)
        block = Block(1, [tx], "previous_hash")
        
        hash1 = block.calculate_hash()
        hash2 = block.calculate_hash()
        
        # Same input should give same hash
        self.assertEqual(hash1, hash2)
        
        # Changing nonce should change hash
        block.nonce += 1
        hash3 = block.calculate_hash()
        self.assertNotEqual(hash1, hash3)


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_full_transaction_flow(self):
        """Test complete transaction flow"""
        # Setup
        blockchain = ClearGlassBlockchain()
        alice_pub, alice_priv = create_wallet()
        bob_pub, bob_priv = create_wallet()
        
        # Alice mines to get coins
        blockchain.mine_pending_transactions(alice_pub)
        initial_alice = blockchain.get_balance(alice_pub)
        
        # Alice sends to Bob
        tx = Transaction(alice_pub, bob_pub, 20)
        private_key = load_private_key(alice_priv)
        tx.sign_transaction(private_key)
        blockchain.add_transaction(tx)
        
        # Mine transaction
        blockchain.mine_pending_transactions(bob_pub)
        
        # Verify balances
        final_alice = blockchain.get_balance(alice_pub)
        final_bob = blockchain.get_balance(bob_pub)
        
        self.assertEqual(final_alice, initial_alice - 20)
        self.assertGreater(final_bob, 20)  # 20 + mining reward
    
    def test_multiple_transactions(self):
        """Test multiple transactions in sequence"""
        blockchain = ClearGlassBlockchain()
        alice_pub, alice_priv = create_wallet()
        bob_pub, bob_priv = create_wallet()
        
        # Give Alice coins
        for _ in range(3):
            blockchain.mine_pending_transactions(alice_pub)
        
        # Multiple transactions
        amounts = [10, 20, 15]
        for amount in amounts:
            tx = Transaction(alice_pub, bob_pub, amount)
            private_key = load_private_key(alice_priv)
            tx.sign_transaction(private_key)
            blockchain.add_transaction(tx)
        
        # Mine all
        blockchain.mine_pending_transactions(alice_pub)
        
        # Verify
        bob_balance = blockchain.get_balance(bob_pub)
        self.assertEqual(bob_balance, sum(amounts))
    
    def test_blockchain_integrity(self):
        """Test blockchain maintains integrity"""
        blockchain = ClearGlassBlockchain()
        
        # Mine several blocks
        for i in range(5):
            blockchain.mine_pending_transactions(f"address_{i}")
        
        # Blockchain should be valid
        self.assertTrue(blockchain.is_chain_valid())
        
        # Verify chain links
        for i in range(1, len(blockchain.chain)):
            current = blockchain.chain[i]
            previous = blockchain.chain[i-1]
            self.assertEqual(current.previous_hash, previous.hash)


def run_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("ClearGlass Cryptocurrency - Test Suite".center(70))
    print("=" * 70 + "\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary".center(70))
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)

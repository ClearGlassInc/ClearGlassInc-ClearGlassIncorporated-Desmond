"""
ClearGlass Cryptocurrency - Core Blockchain Implementation
A transparent, secure blockchain-based cryptocurrency system
"""

import hashlib
import json
import time
from typing import List, Dict, Optional
from datetime import datetime
import ecdsa
import base64


class Transaction:
    """Represents a transaction in the ClearGlass blockchain"""
    
    def __init__(self, sender: str, recipient: str, amount: float, 
                 timestamp: Optional[float] = None, signature: Optional[str] = None):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.timestamp = timestamp or time.time()
        self.signature = signature
        
    def to_dict(self) -> Dict:
        """Convert transaction to dictionary"""
        return {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'timestamp': self.timestamp,
            'signature': self.signature
        }
    
    def calculate_hash(self) -> str:
        """Calculate transaction hash for signing"""
        transaction_string = json.dumps({
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'timestamp': self.timestamp
        }, sort_keys=True)
        return hashlib.sha256(transaction_string.encode()).hexdigest()
    
    def sign_transaction(self, private_key: ecdsa.SigningKey):
        """Sign the transaction with private key"""
        if self.sender == "NETWORK_REWARD":
            return  # Mining rewards don't need signatures
            
        transaction_hash = self.calculate_hash()
        signature = private_key.sign(transaction_hash.encode())
        self.signature = base64.b64encode(signature).decode()
    
    def is_valid(self) -> bool:
        """Verify transaction signature"""
        if self.sender == "NETWORK_REWARD":
            return True
            
        if not self.signature:
            return False
            
        try:
            # Decode public key from sender address
            public_key_bytes = base64.b64decode(self.sender)
            public_key = ecdsa.VerifyingKey.from_string(
                public_key_bytes, 
                curve=ecdsa.SECP256k1
            )
            
            transaction_hash = self.calculate_hash()
            signature_bytes = base64.b64decode(self.signature)
            
            return public_key.verify(signature_bytes, transaction_hash.encode())
        except Exception as e:
            print(f"Transaction validation error: {e}")
            return False


class Block:
    """Represents a block in the ClearGlass blockchain"""
    
    def __init__(self, index: int, transactions: List[Transaction], 
                 previous_hash: str, timestamp: Optional[float] = None):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate block hash"""
        block_string = json.dumps({
            'index': self.index,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int):
        """Mine the block using Proof of Work"""
        target = '0' * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        
        print(f"Block mined: {self.hash}")
    
    def to_dict(self) -> Dict:
        """Convert block to dictionary"""
        return {
            'index': self.index,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'hash': self.hash
        }


class ClearGlassBlockchain:
    """Main blockchain class for ClearGlass cryptocurrency"""
    
    # Blockchain parameters
    DIFFICULTY = 4  # Mining difficulty (number of leading zeros)
    MINING_REWARD = 50  # ClearGlass tokens per mined block
    MAX_SUPPLY = 21_000_000  # Maximum token supply
    BLOCK_TIME = 60  # Target time between blocks (seconds)
    
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.mining_reward = self.MINING_REWARD
        self.difficulty = self.DIFFICULTY
        
        # Create genesis block
        self.create_genesis_block()
    
    def create_genesis_block(self):
        """Create the first block in the blockchain"""
        genesis_transaction = Transaction(
            sender="GENESIS",
            recipient="NETWORK",
            amount=0,
            timestamp=time.time()
        )
        genesis_block = Block(0, [genesis_transaction], "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> Block:
        """Get the most recent block"""
        return self.chain[-1]
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """Add a transaction to pending transactions"""
        if not transaction.sender or not transaction.recipient:
            print("Transaction must include sender and recipient")
            return False
        
        if not transaction.is_valid():
            print("Cannot add invalid transaction")
            return False
        
        # Check if sender has sufficient balance
        if transaction.sender != "NETWORK_REWARD":
            balance = self.get_balance(transaction.sender)
            if balance < transaction.amount:
                print(f"Insufficient balance. Available: {balance}, Required: {transaction.amount}")
                return False
        
        self.pending_transactions.append(transaction)
        return True
    
    def mine_pending_transactions(self, mining_reward_address: str):
        """Mine a new block with pending transactions"""
        # Check if max supply reached
        total_supply = self.get_total_supply()
        if total_supply >= self.MAX_SUPPLY:
            print("Maximum supply reached. No more mining rewards.")
            reward_amount = 0
        else:
            reward_amount = min(self.mining_reward, self.MAX_SUPPLY - total_supply)
        
        # Create mining reward transaction
        reward_transaction = Transaction(
            sender="NETWORK_REWARD",
            recipient=mining_reward_address,
            amount=reward_amount
        )
        
        # Add reward to pending transactions
        block_transactions = self.pending_transactions + [reward_transaction]
        
        # Create new block
        new_block = Block(
            index=len(self.chain),
            transactions=block_transactions,
            previous_hash=self.get_latest_block().hash
        )
        
        # Mine the block
        new_block.mine_block(self.difficulty)
        
        # Add to chain
        self.chain.append(new_block)
        
        # Clear pending transactions
        self.pending_transactions = []
        
        print(f"Block successfully mined! Reward: {reward_amount} CGLASS")
    
    def get_balance(self, address: str) -> float:
        """Get balance for an address"""
        balance = 0
        
        for block in self.chain:
            for transaction in block.transactions:
                if transaction.sender == address:
                    balance -= transaction.amount
                if transaction.recipient == address:
                    balance += transaction.amount
        
        return balance
    
    def get_total_supply(self) -> float:
        """Calculate total supply of ClearGlass tokens"""
        total = 0
        for block in self.chain:
            for transaction in block.transactions:
                if transaction.sender == "NETWORK_REWARD":
                    total += transaction.amount
        return total
    
    def is_chain_valid(self) -> bool:
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Verify current block hash
            if current_block.hash != current_block.calculate_hash():
                print(f"Invalid hash at block {i}")
                return False
            
            # Verify link to previous block
            if current_block.previous_hash != previous_block.hash:
                print(f"Invalid previous hash at block {i}")
                return False
            
            # Verify all transactions in block
            for transaction in current_block.transactions:
                if not transaction.is_valid():
                    print(f"Invalid transaction in block {i}")
                    return False
        
        return True
    
    def get_chain_data(self) -> List[Dict]:
        """Export blockchain as JSON-serializable data"""
        return [block.to_dict() for block in self.chain]
    
    def save_to_file(self, filename: str = "clearglass_blockchain.json"):
        """Save blockchain to file"""
        with open(filename, 'w') as f:
            json.dump(self.get_chain_data(), f, indent=4)
        print(f"Blockchain saved to {filename}")
    
    def get_transaction_history(self, address: str) -> List[Dict]:
        """Get all transactions for an address"""
        history = []
        for block in self.chain:
            for transaction in block.transactions:
                if transaction.sender == address or transaction.recipient == address:
                    tx_data = transaction.to_dict()
                    tx_data['block_index'] = block.index
                    tx_data['block_timestamp'] = block.timestamp
                    history.append(tx_data)
        return history


# Utility functions

def create_wallet() -> tuple:
    """Create a new wallet with public/private key pair"""
    private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    public_key = private_key.get_verifying_key()
    
    # Encode keys as base64 for easy storage
    private_key_encoded = base64.b64encode(private_key.to_string()).decode()
    public_key_encoded = base64.b64encode(public_key.to_string()).decode()
    
    return public_key_encoded, private_key_encoded


def load_private_key(private_key_encoded: str) -> ecdsa.SigningKey:
    """Load private key from encoded string"""
    private_key_bytes = base64.b64decode(private_key_encoded)
    return ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)


if __name__ == "__main__":
    print("=" * 60)
    print("ClearGlass Cryptocurrency - Blockchain Initialized")
    print("=" * 60)
    
    # Create blockchain
    clearglass = ClearGlassBlockchain()
    
    # Create wallets
    print("\nCreating wallets...")
    alice_public, alice_private = create_wallet()
    bob_public, bob_private = create_wallet()
    
    print(f"Alice's address: {alice_public[:20]}...")
    print(f"Bob's address: {bob_public[:20]}...")
    
    # Mine initial blocks to Alice
    print("\nMining initial blocks...")
    clearglass.mine_pending_transactions(alice_public)
    clearglass.mine_pending_transactions(alice_public)
    
    print(f"\nAlice's balance: {clearglass.get_balance(alice_public)} CGLASS")
    
    # Create and sign transaction
    print("\nCreating transaction from Alice to Bob...")
    transaction = Transaction(alice_public, bob_public, 30)
    transaction.sign_transaction(load_private_key(alice_private))
    
    # Add transaction
    if clearglass.add_transaction(transaction):
        print("Transaction added to pending pool")
    
    # Mine block with transaction
    print("\nMining block with transaction...")
    clearglass.mine_pending_transactions(bob_public)
    
    # Check balances
    print(f"\nFinal balances:")
    print(f"Alice: {clearglass.get_balance(alice_public)} CGLASS")
    print(f"Bob: {clearglass.get_balance(bob_public)} CGLASS")
    
    # Validate blockchain
    print(f"\nBlockchain valid: {clearglass.is_chain_valid()}")
    print(f"Total supply: {clearglass.get_total_supply()} CGLASS")
    print(f"Blocks in chain: {len(clearglass.chain)}")

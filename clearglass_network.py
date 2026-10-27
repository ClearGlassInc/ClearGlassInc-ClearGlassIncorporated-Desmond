"""
ClearGlass Cryptocurrency - Peer-to-Peer Network Node
Decentralized networking for blockchain synchronization
"""

import socket
import json
import threading
import time
from typing import List, Set, Dict
from clearglass_blockchain import ClearGlassBlockchain, Transaction, Block


class NetworkNode:
    """P2P Network Node for ClearGlass cryptocurrency"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8333):
        self.host = host
        self.port = port
        self.blockchain = ClearGlassBlockchain()
        self.peers: Set[str] = set()
        self.server_socket = None
        self.running = False
        
    def start(self):
        """Start the network node"""
        self.running = True
        
        # Start server thread
        server_thread = threading.Thread(target=self._run_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Start peer discovery
        discovery_thread = threading.Thread(target=self._discover_peers)
        discovery_thread.daemon = True
        discovery_thread.start()
        
        # Start block sync
        sync_thread = threading.Thread(target=self._sync_blockchain)
        sync_thread.daemon = True
        sync_thread.start()
        
        print(f"✓ Node started on {self.host}:{self.port}")
        print(f"  Blockchain: {len(self.blockchain.chain)} blocks")
        
    def stop(self):
        """Stop the network node"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("✓ Node stopped")
    
    def _run_server(self):
        """Run TCP server for incoming connections"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Server error: {e}")
                    
        except Exception as e:
            print(f"Failed to start server: {e}")
    
    def _handle_client(self, client_socket: socket.socket, address):
        """Handle incoming client connection"""
        try:
            # Receive message
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                return
            
            message = json.loads(data)
            response = self._process_message(message)
            
            # Send response
            client_socket.send(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            print(f"Client handler error: {e}")
        finally:
            client_socket.close()
    
    def _process_message(self, message: Dict) -> Dict:
        """Process incoming message and return response"""
        msg_type = message.get('type')
        
        if msg_type == 'ping':
            return {'type': 'pong', 'node_id': self.get_node_id()}
        
        elif msg_type == 'get_peers':
            return {
                'type': 'peers',
                'peers': list(self.peers)
            }
        
        elif msg_type == 'get_blockchain':
            return {
                'type': 'blockchain',
                'chain': self.blockchain.get_chain_data(),
                'length': len(self.blockchain.chain)
            }
        
        elif msg_type == 'get_latest_block':
            latest = self.blockchain.get_latest_block()
            return {
                'type': 'latest_block',
                'block': latest.to_dict()
            }
        
        elif msg_type == 'new_transaction':
            tx_data = message.get('transaction')
            transaction = Transaction(
                sender=tx_data['sender'],
                recipient=tx_data['recipient'],
                amount=tx_data['amount'],
                signature=tx_data.get('signature')
            )
            
            if self.blockchain.add_transaction(transaction):
                # Broadcast to peers
                self.broadcast_transaction(transaction)
                return {'type': 'ack', 'message': 'Transaction accepted'}
            else:
                return {'type': 'error', 'message': 'Invalid transaction'}
        
        elif msg_type == 'new_block':
            # Not implemented: a peer's block is acknowledged but neither
            # validated nor added to the chain. That needs consensus rules.
            return {'type': 'ack', 'message': 'Block received'}
        
        else:
            return {'type': 'error', 'message': 'Unknown message type'}
    
    def connect_to_peer(self, peer_address: str):
        """Connect to a peer node"""
        if peer_address not in self.peers:
            self.peers.add(peer_address)
            print(f"✓ Connected to peer: {peer_address}")
            
            # Exchange peer lists
            try:
                response = self.send_message(peer_address, {'type': 'get_peers'})
                if response.get('type') == 'peers':
                    for peer in response.get('peers', []):
                        if peer != self.get_address():
                            self.peers.add(peer)
            except Exception:
                pass
    
    def send_message(self, peer_address: str, message: Dict) -> Dict:
        """Send message to peer and wait for response"""
        try:
            # Parse address
            if '://' not in peer_address:
                peer_address = f"tcp://{peer_address}"
            
            host_port = peer_address.replace('tcp://', '').replace('http://', '')
            host, port = host_port.split(':')
            port = int(port)
            
            # Connect and send
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((host, port))
            
            sock.send(json.dumps(message).encode('utf-8'))
            
            # Receive response
            response = sock.recv(4096).decode('utf-8')
            sock.close()
            
            return json.loads(response)
            
        except Exception as e:
            print(f"Failed to send message to {peer_address}: {e}")
            return {'type': 'error', 'message': str(e)}
    
    def broadcast_transaction(self, transaction: Transaction):
        """Broadcast transaction to all peers"""
        message = {
            'type': 'new_transaction',
            'transaction': transaction.to_dict()
        }
        
        for peer in list(self.peers):
            try:
                self.send_message(peer, message)
            except Exception:
                # Remove unresponsive peer
                self.peers.discard(peer)
    
    def broadcast_block(self, block: Block):
        """Broadcast new block to all peers"""
        message = {
            'type': 'new_block',
            'block': block.to_dict()
        }
        
        for peer in list(self.peers):
            try:
                self.send_message(peer, message)
            except Exception:
                self.peers.discard(peer)
    
    def _discover_peers(self):
        """Continuously discover new peers"""
        while self.running:
            # Ping all peers
            for peer in list(self.peers):
                try:
                    response = self.send_message(peer, {'type': 'ping'})
                    if response.get('type') != 'pong':
                        self.peers.discard(peer)
                except Exception:
                    self.peers.discard(peer)
            
            time.sleep(30)  # Check every 30 seconds
    
    def _sync_blockchain(self):
        """Synchronize blockchain with peers"""
        while self.running:
            if not self.peers:
                time.sleep(10)
                continue
            
            # Get longest chain from peers
            longest_chain = None
            max_length = len(self.blockchain.chain)
            
            for peer in list(self.peers):
                try:
                    response = self.send_message(peer, {'type': 'get_blockchain'})
                    if response.get('type') == 'blockchain':
                        chain_data = response.get('chain', [])
                        if len(chain_data) > max_length:
                            longest_chain = chain_data
                            max_length = len(chain_data)
                except Exception:
                    pass
            
            # Replace chain if longer valid chain found
            if longest_chain and max_length > len(self.blockchain.chain):
                print(f"⟳ Syncing blockchain ({max_length} blocks)...")
                # In full implementation, would validate and replace chain
            
            time.sleep(60)  # Sync every minute
    
    def get_node_id(self) -> str:
        """Get unique node identifier"""
        import hashlib
        node_string = f"{self.host}:{self.port}"
        return hashlib.sha256(node_string.encode()).hexdigest()[:16]
    
    def get_address(self) -> str:
        """Get node's network address"""
        return f"{self.host}:{self.port}"
    
    def get_peers_list(self) -> List[str]:
        """Get list of connected peers"""
        return list(self.peers)
    
    def get_stats(self) -> Dict:
        """Get node statistics"""
        return {
            'node_id': self.get_node_id(),
            'address': self.get_address(),
            'peers': len(self.peers),
            'blocks': len(self.blockchain.chain),
            'pending_transactions': len(self.blockchain.pending_transactions),
            'running': self.running
        }


class NetworkManager:
    """Manages multiple network nodes"""
    
    def __init__(self):
        self.nodes: Dict[str, NetworkNode] = {}
    
    def create_node(self, name: str, host: str = '0.0.0.0', 
                   port: int = 8333) -> NetworkNode:
        """Create and start a new node"""
        node = NetworkNode(host, port)
        node.start()
        self.nodes[name] = node
        return node
    
    def get_node(self, name: str) -> NetworkNode:
        """Get node by name"""
        return self.nodes.get(name)
    
    def stop_all(self):
        """Stop all nodes"""
        for node in self.nodes.values():
            node.stop()


def run_node_cli():
    """Interactive CLI for network node"""
    import sys
    
    print("=" * 60)
    print("ClearGlass Cryptocurrency - Network Node")
    print("=" * 60)
    
    # Get node configuration
    host = input("Host address (default 0.0.0.0): ").strip() or '0.0.0.0'
    port = input("Port (default 8333): ").strip() or '8333'
    port = int(port)
    
    # Create and start node
    node = NetworkNode(host, port)
    node.start()
    
    # Add seed nodes if provided
    seed_node = input("\nSeed node address (optional, format host:port): ").strip()
    if seed_node:
        node.connect_to_peer(seed_node)
    
    print("\nNode Commands:")
    print("1. View stats")
    print("2. List peers")
    print("3. Connect to peer")
    print("4. View blockchain")
    print("5. Mine block")
    print("6. Exit")
    
    try:
        while True:
            choice = input("\nEnter command (1-6): ").strip()
            
            if choice == '1':
                stats = node.get_stats()
                print("\nNode Statistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            
            elif choice == '2':
                peers = node.get_peers_list()
                print(f"\nConnected Peers ({len(peers)}):")
                for peer in peers:
                    print(f"  • {peer}")
            
            elif choice == '3':
                peer = input("Peer address (host:port): ").strip()
                node.connect_to_peer(peer)
            
            elif choice == '4':
                print(f"\nBlockchain ({len(node.blockchain.chain)} blocks):")
                for block in node.blockchain.chain[-5:]:  # Show last 5
                    print(f"  Block {block.index}: {block.hash[:16]}...")
            
            elif choice == '5':
                address = input("Mining reward address: ").strip()
                print("Mining...")
                node.blockchain.mine_pending_transactions(address)
                # Broadcast new block
                latest = node.blockchain.get_latest_block()
                node.broadcast_block(latest)
                print("✓ Block mined and broadcast")
            
            elif choice == '6':
                print("\nShutting down node...")
                node.stop()
                break
            
            else:
                print("Invalid command")
    
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        node.stop()
        sys.exit(0)


if __name__ == "__main__":
    run_node_cli()

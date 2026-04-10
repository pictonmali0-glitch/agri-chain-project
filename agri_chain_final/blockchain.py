import hashlib
import json
import time
from datetime import datetime


class BlockData:
    def __init__(self, index, timestamp, data, previous_hash, nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            'index': self.index,
            'timestamp': str(self.timestamp),
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty=2):
        target = '0' * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()
        return self


class Blockchain:
    DIFFICULTY = 2

    def __init__(self):
        from models import Block, db
        self.db = db
        self.Block = Block
        if Block.query.count() == 0:
            genesis = self._create_genesis_block()
            self._save_block(genesis)

    def _create_genesis_block(self):
        return BlockData(0, datetime.utcnow().isoformat(), {'genesis': True, 'message': 'AgriChain Genesis Block - Kasese District Uganda'}, '0' * 64)

    def _get_latest_block(self):
        return self.Block.query.order_by(self.Block.index.desc()).first()

    def _save_block(self, block_data):
        b = self.Block(
            index=block_data.index,
            timestamp=datetime.utcnow(),
            data=json.dumps(block_data.data),
            previous_hash=block_data.previous_hash,
            hash=block_data.hash,
            nonce=block_data.nonce
        )
        self.db.session.add(b)
        self.db.session.flush()
        return b

    def add_block(self, data):
        latest = self._get_latest_block()
        new_index = (latest.index + 1) if latest else 1
        prev_hash = latest.hash if latest else '0' * 64
        block = BlockData(new_index, datetime.utcnow().isoformat(), data, prev_hash)
        block.mine_block(self.DIFFICULTY)
        return self._save_block(block)

    def is_chain_valid(self):
        blocks = self.Block.query.order_by(self.Block.index).all()
        for i in range(1, len(blocks)):
            curr = blocks[i]
            prev = blocks[i - 1]
            recalc = hashlib.sha256(json.dumps({
                'index': curr.index,
                'timestamp': curr.timestamp.isoformat(),
                'data': json.loads(curr.data),
                'previous_hash': curr.previous_hash,
                'nonce': curr.nonce
            }, sort_keys=True).encode()).hexdigest()
            if curr.hash != recalc:
                return False
            if curr.previous_hash != prev.hash:
                return False
        return True

    def get_chain(self):
        return [b.to_dict() for b in self.Block.query.order_by(self.Block.index).all()]

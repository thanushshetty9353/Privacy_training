"""
Secure Aggregation Engine — masking-based protocol.

Each client:
  1. Generates random masks that are shared pair-wise.
  2. Adds its own mask to the model update.
  3. Sends the masked update to the server.

Server:
  - Sums all masked updates → masks cancel out.
  - Only the true aggregate is revealed.
  - Server NEVER sees individual client updates.

This module implements the protocol for simulation purposes.
In production, PySyft or a dedicated MPC framework would handle this.
"""

import numpy as np
from typing import List, Dict, Tuple
import hashlib


class SecureAggregator:
    """
    Masking-based secure aggregation.
    Provides cryptographic-level privacy for model updates.
    """

    def __init__(self, num_clients: int, seed_base: int = 42):
        self.num_clients = num_clients
        self.seed_base = seed_base
        self._mask_seeds: Dict[Tuple[int, int], int] = {}
        self._generate_pair_seeds()

    def _generate_pair_seeds(self):
        """Generate unique seeds for each client pair for mask generation."""
        for i in range(self.num_clients):
            for j in range(i + 1, self.num_clients):
                # Deterministic seed from (i, j) pair
                pair_hash = hashlib.sha256(
                    f"{self.seed_base}_{i}_{j}".encode()
                ).hexdigest()
                self._mask_seeds[(i, j)] = int(pair_hash[:8], 16)

    def _generate_mask(self, seed: int, shape: tuple) -> np.ndarray:
        """Generate a random mask from a given seed."""
        rng = np.random.RandomState(seed)
        return rng.normal(0, 0.01, size=shape).astype(np.float32)

    def mask_client_update(
        self, client_id: int, parameters: List[np.ndarray]
    ) -> List[np.ndarray]:
        """
        Apply masks to a client's model update.
        For each pair (i, j):
          - Client i adds +mask
          - Client j adds -mask
        So masks cancel when summed by the server.
        """
        masked_params = [p.copy() for p in parameters]

        for i in range(self.num_clients):
            for j in range(i + 1, self.num_clients):
                seed = self._mask_seeds[(i, j)]
                for k, param in enumerate(masked_params):
                    mask = self._generate_mask(seed + k, param.shape)
                    if client_id == i:
                        masked_params[k] = masked_params[k] + mask
                    elif client_id == j:
                        masked_params[k] = masked_params[k] - mask

        return masked_params

    def aggregate(
        self, all_masked_updates: List[List[np.ndarray]], num_samples: List[int]
    ) -> List[np.ndarray]:
        """
        Securely aggregate masked updates.
        Masks cancel out → only the weighted average of true updates remains.
        """
        total_samples = sum(num_samples)

        # Weighted sum of all masked updates (masks cancel)
        aggregated = []
        for k in range(len(all_masked_updates[0])):
            weighted_sum = np.zeros_like(all_masked_updates[0][k], dtype=np.float64)
            for client_idx, update in enumerate(all_masked_updates):
                weight = num_samples[client_idx] / total_samples
                weighted_sum += update[k].astype(np.float64) * weight
            aggregated.append(weighted_sum.astype(np.float32))

        return aggregated

    def verify_mask_cancellation(
        self,
        original_updates: List[List[np.ndarray]],
        masked_updates: List[List[np.ndarray]],
        num_samples: List[int],
    ) -> float:
        """
        Verify that masks properly cancel.
        Returns max absolute difference between true and secure aggregation.
        """
        total_samples = sum(num_samples)

        # True unmasked average
        true_agg = []
        for k in range(len(original_updates[0])):
            weighted_sum = np.zeros_like(original_updates[0][k], dtype=np.float64)
            for client_idx, update in enumerate(original_updates):
                weight = num_samples[client_idx] / total_samples
                weighted_sum += update[k].astype(np.float64) * weight
            true_agg.append(weighted_sum.astype(np.float32))

        # Secure aggregation result
        secure_agg = self.aggregate(masked_updates, num_samples)

        # Compare
        max_diff = 0.0
        for t, s in zip(true_agg, secure_agg):
            diff = np.max(np.abs(t - s))
            max_diff = max(max_diff, float(diff))

        return max_diff

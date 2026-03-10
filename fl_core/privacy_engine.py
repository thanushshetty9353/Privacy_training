"""
Differential Privacy Engine — wraps Opacus for privacy budget tracking.
"""

from dataclasses import dataclass, field
from typing import Optional
import math


@dataclass
class PrivacyBudget:
    """Tracks cumulative privacy cost (epsilon) across training rounds."""
    target_epsilon: float = 10.0
    target_delta: float = 1e-5
    noise_multiplier: float = 1.1
    max_grad_norm: float = 1.0
    rounds_completed: int = 0
    epsilon_per_round: list = field(default_factory=list)
    total_epsilon: float = 0.0

    @property
    def budget_remaining(self) -> float:
        return max(0.0, self.target_epsilon - self.total_epsilon)

    @property
    def budget_exhausted(self) -> bool:
        return self.total_epsilon >= self.target_epsilon

    def record_round(self, epsilon: float):
        """Record epsilon spent in one round."""
        self.rounds_completed += 1
        self.epsilon_per_round.append(epsilon)
        self.total_epsilon += epsilon

    def estimate_epsilon_per_round(
        self,
        num_samples: int,
        batch_size: int,
        epochs: int = 1,
    ) -> float:
        """
        Rough estimate of epsilon per round using RDP accountant formula.
        For accurate tracking, Opacus PrivacyEngine.get_epsilon() is used at runtime.
        """
        sampling_rate = batch_size / num_samples
        steps = epochs * math.ceil(num_samples / batch_size)
        # Simplified RDP → (ε, δ) conversion estimate
        sigma = self.noise_multiplier
        eps_per_step = (2 * sampling_rate ** 2) / (sigma ** 2)
        return math.sqrt(2 * steps * math.log(1 / self.target_delta)) * math.sqrt(eps_per_step)

    def to_dict(self) -> dict:
        return {
            "target_epsilon": self.target_epsilon,
            "target_delta": self.target_delta,
            "noise_multiplier": self.noise_multiplier,
            "max_grad_norm": self.max_grad_norm,
            "rounds_completed": self.rounds_completed,
            "epsilon_per_round": self.epsilon_per_round,
            "total_epsilon": self.total_epsilon,
            "budget_remaining": self.budget_remaining,
            "budget_exhausted": self.budget_exhausted,
        }

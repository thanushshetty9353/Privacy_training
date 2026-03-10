"""
PyTorch model definitions for federated learning.
CNN model suitable for CIFAR-10 image classification.
Extensible architecture — can be swapped for other models.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from collections import OrderedDict
from typing import List, Tuple


class FederatedCNN(nn.Module):
    """
    CNN for CIFAR‑10 (3×32×32 → 10 classes).
    Architecture modeled after the Flower PyTorch tutorial.
    """

    def __init__(self, num_classes: int = 10):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.conv3 = nn.Conv2d(64, 128, 3, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.5)
        self.fc1 = nn.Linear(128 * 4 * 4, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        x = self.pool(F.relu(self.bn3(self.conv3(x))))
        x = x.view(-1, 128 * 4 * 4)
        x = self.dropout1(x)
        x = F.relu(self.fc1(x))
        x = self.dropout2(x)
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


def get_model_parameters(model: nn.Module) -> List[torch.Tensor]:
    """Extract model parameters as a list of NumPy arrays."""
    return [val.cpu().detach().numpy() for val in model.state_dict().values()]


def set_model_parameters(model: nn.Module, parameters: List[torch.Tensor]):
    """Set model parameters from a list of NumPy arrays."""
    import numpy as np
    state_dict = model.state_dict()
    keys = list(state_dict.keys())
    new_state_dict = OrderedDict()
    for key, param in zip(keys, parameters):
        if isinstance(param, np.ndarray):
            new_state_dict[key] = torch.tensor(param)
        else:
            new_state_dict[key] = param
    model.load_state_dict(new_state_dict, strict=True)


def train_model(
    model: nn.Module,
    train_loader: torch.utils.data.DataLoader,
    epochs: int = 1,
    lr: float = 0.01,
    device: str = "cpu",
    use_dp: bool = False,
    noise_multiplier: float = 1.1,
    max_grad_norm: float = 1.0,
) -> Tuple[float, float]:
    """
    Train the model on a local dataset.
    Optionally applies Opacus differential privacy.
    Returns (average loss, epsilon spent or 0.0).
    """
    model.to(device)
    model.train()
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.9)

    epsilon = 0.0

    if use_dp:
        try:
            from opacus import PrivacyEngine
            from opacus.validators import ModuleValidator

            # Fix model for Opacus compatibility (replace BatchNorm etc.)
            model = ModuleValidator.fix(model)
            model.to(device)

            privacy_engine = PrivacyEngine()
            model, optimizer, train_loader = privacy_engine.make_private(
                module=model,
                optimizer=optimizer,
                data_loader=train_loader,
                noise_multiplier=noise_multiplier,
                max_grad_norm=max_grad_norm,
            )
        except ImportError:
            print("[WARNING] Opacus not installed, training without DP")
            use_dp = False

    running_loss = 0.0
    num_batches = 0

    for epoch in range(epochs):
        for batch_idx, (images, labels) in enumerate(train_loader):
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            num_batches += 1

    avg_loss = running_loss / max(num_batches, 1)

    if use_dp:
        try:
            epsilon = privacy_engine.get_epsilon(delta=1e-5)
        except Exception:
            epsilon = 0.0

    return avg_loss, epsilon


def evaluate_model(
    model: nn.Module,
    test_loader: torch.utils.data.DataLoader,
    device: str = "cpu",
) -> Tuple[float, float]:
    """Evaluate model on test set. Returns (loss, accuracy)."""
    model.to(device)
    model.eval()
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            total_loss += loss.item() * labels.size(0)
            _, predicted = torch.max(outputs, 1)
            correct += (predicted == labels).sum().item()
            total += labels.size(0)

    avg_loss = total_loss / max(total, 1)
    accuracy = correct / max(total, 1)
    return avg_loss, accuracy

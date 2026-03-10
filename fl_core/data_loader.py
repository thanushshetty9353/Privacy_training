"""
Data loading and partitioning for federated learning simulation.
Splits CIFAR-10 into disjoint partitions to simulate multiple hospital nodes.
"""

import torch
from torch.utils.data import DataLoader, Subset
import torchvision
import torchvision.transforms as transforms
import numpy as np
from typing import Tuple, List


def get_transforms():
    """Standard CIFAR-10 transforms."""
    transform_train = transforms.Compose([
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    return transform_train, transform_test


def load_datasets(
    data_dir: str = "./data",
) -> Tuple[torchvision.datasets.CIFAR10, torchvision.datasets.CIFAR10]:
    """Download and load CIFAR-10 train and test sets."""
    transform_train, transform_test = get_transforms()
    trainset = torchvision.datasets.CIFAR10(
        root=data_dir, train=True, download=True, transform=transform_train
    )
    testset = torchvision.datasets.CIFAR10(
        root=data_dir, train=False, download=True, transform=transform_test
    )
    return trainset, testset


def partition_data(
    dataset: torchvision.datasets.CIFAR10,
    num_clients: int,
    seed: int = 42,
) -> List[Subset]:
    """
    Split dataset into `num_clients` disjoint partitions.
    Simulates data at different hospital nodes.
    """
    np.random.seed(seed)
    total = len(dataset)
    indices = np.random.permutation(total)
    split_indices = np.array_split(indices, num_clients)
    return [Subset(dataset, idx.tolist()) for idx in split_indices]


def get_client_dataloader(
    partition: Subset,
    batch_size: int = 32,
    shuffle: bool = True,
) -> DataLoader:
    """Create a DataLoader from a client partition."""
    return DataLoader(partition, batch_size=batch_size, shuffle=shuffle, num_workers=0)


def get_test_dataloader(
    data_dir: str = "./data",
    batch_size: int = 64,
) -> DataLoader:
    """Load the global test set."""
    _, testset = load_datasets(data_dir)
    return DataLoader(testset, batch_size=batch_size, shuffle=False, num_workers=0)

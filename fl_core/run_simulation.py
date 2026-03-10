"""
Federated Learning Simulation Runner.

Orchestrates the full FL pipeline:
  1. Initialize global model
  2. Partition data for N hospital nodes
  3. For each round:
     a. Send global model to all clients
     b. Each client trains locally with Opacus DP
     c. Secure aggregation of masked updates
     d. Update global model
     e. Evaluate on test set
     f. Record metrics to DB
  4. Save final model

Usage:
  python fl_core/run_simulation.py --job-id <uuid> --rounds 5 --clients 3
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
import torch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fl_core.model import (
    FederatedCNN,
    get_model_parameters,
    set_model_parameters,
    train_model,
    evaluate_model,
)
from fl_core.data_loader import (
    load_datasets,
    partition_data,
    get_client_dataloader,
    get_test_dataloader,
)
from fl_core.privacy_engine import PrivacyBudget
from fl_core.secure_aggregation import SecureAggregator


async def update_db_metrics(db_url: str, job_id: str, round_num: int, metrics: dict):
    """Write per-round metrics to the database."""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from sqlalchemy import text

        engine = create_async_engine(db_url, echo=False)
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            import uuid as uuid_mod
            metric_id = str(uuid_mod.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            await session.execute(text(
                "INSERT INTO training_metrics "
                "(id, job_id, round_number, train_loss, eval_loss, eval_accuracy, epsilon, num_clients, round_duration_sec, timestamp) "
                "VALUES (:id, :job_id, :round_number, :train_loss, :eval_loss, :eval_accuracy, :epsilon, :num_clients, :round_duration_sec, :timestamp)"
            ), {
                "id": metric_id,
                "job_id": job_id,
                "round_number": round_num,
                "train_loss": metrics.get("train_loss"),
                "eval_loss": metrics.get("eval_loss"),
                "eval_accuracy": metrics.get("eval_accuracy"),
                "epsilon": metrics.get("epsilon"),
                "num_clients": metrics.get("num_clients"),
                "round_duration_sec": metrics.get("round_duration_sec"),
                "timestamp": now,
            })

            # Update job current_round
            await session.execute(text(
                "UPDATE training_jobs SET current_round = :round WHERE id = :job_id"
            ), {"round": round_num, "job_id": job_id})

            await session.commit()
        await engine.dispose()
    except Exception as e:
        print(f"[DB] Error writing metrics: {e}")


async def update_job_status(db_url: str, job_id: str, status: str, **kwargs):
    """Update job status in the database."""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from sqlalchemy import text

        engine = create_async_engine(db_url, echo=False)
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            set_clauses = [f"status = :status"]
            params = {"status": status, "job_id": job_id}

            for key, value in kwargs.items():
                set_clauses.append(f"{key} = :{key}")
                params[key] = value

            query = f"UPDATE training_jobs SET {', '.join(set_clauses)} WHERE id = :job_id"
            await session.execute(text(query), params)
            await session.commit()
        await engine.dispose()
    except Exception as e:
        print(f"[DB] Error updating job status: {e}")


def run_federated_learning(
    job_id: str = "local",
    num_rounds: int = 5,
    num_clients: int = 3,
    noise_multiplier: float = 1.1,
    max_grad_norm: float = 1.0,
    target_epsilon: float = 10.0,
    local_epochs: int = 1,
    batch_size: int = 32,
    learning_rate: float = 0.01,
    use_dp: bool = True,
    use_secure_agg: bool = True,
    db_url: str = "",
    data_dir: str = "./data",
    model_save_dir: str = "./model_storage",
):
    """
    Main federated learning loop.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n{'='*70}")
    print(f" Privacy-Preserving Federated Learning Simulation")
    print(f"{'='*70}")
    print(f" Job ID:            {job_id}")
    print(f" Rounds:            {num_rounds}")
    print(f" Clients:           {num_clients}")
    print(f" Device:            {device}")
    print(f" Differential Privacy: {'ON' if use_dp else 'OFF'}")
    print(f"   Noise Multiplier: {noise_multiplier}")
    print(f"   Max Grad Norm:    {max_grad_norm}")
    print(f" Secure Aggregation: {'ON' if use_secure_agg else 'OFF'}")
    print(f"{'='*70}\n")

    # ── Initialize ──────────────────────────────────────────────────
    print("[1/4] Initializing global model...")
    global_model = FederatedCNN()
    global_params = get_model_parameters(global_model)

    # ── Load and partition data ──────────────────────────────────────
    print(f"[2/4] Loading CIFAR-10 and partitioning into {num_clients} nodes...")
    trainset, testset = load_datasets(data_dir)
    partitions = partition_data(trainset, num_clients)
    test_loader = get_test_dataloader(data_dir, batch_size=64)

    for i, part in enumerate(partitions):
        print(f"  ├── Hospital Node {chr(65+i)}: {len(part)} samples")

    # ── Privacy budget ──────────────────────────────────────────────
    privacy_budget = PrivacyBudget(
        target_epsilon=target_epsilon,
        noise_multiplier=noise_multiplier,
        max_grad_norm=max_grad_norm,
    )

    # ── Secure aggregator ────────────────────────────────────────────
    secure_agg = SecureAggregator(num_clients) if use_secure_agg else None

    # ── Update DB: running ───────────────────────────────────────────
    if db_url:
        asyncio.run(update_job_status(db_url, job_id, "running"))

    all_metrics = []

    # ── Training rounds ──────────────────────────────────────────────
    print(f"\n[3/4] Starting federated training ({num_rounds} rounds)...\n")

    for round_num in range(1, num_rounds + 1):
        round_start = time.time()
        print(f"  ┌── ROUND {round_num}/{num_rounds} {'─'*50}")

        client_updates = []
        client_samples = []
        original_updates = []
        round_epsilons = []
        round_losses = []

        # ── Each client trains locally ──────────────────────────────
        for client_id in range(num_clients):
            # Create fresh model with global parameters
            client_model = FederatedCNN()
            set_model_parameters(client_model, global_params)

            # Load local data
            train_loader = get_client_dataloader(
                partitions[client_id], batch_size=batch_size
            )

            # Train locally (with DP if enabled)
            loss, epsilon = train_model(
                client_model, train_loader,
                epochs=local_epochs,
                lr=learning_rate,
                device=device,
                use_dp=use_dp,
                noise_multiplier=noise_multiplier,
                max_grad_norm=max_grad_norm,
            )

            round_losses.append(loss)
            round_epsilons.append(epsilon)

            # Get updated parameters
            updated_params = get_model_parameters(client_model)
            original_updates.append(updated_params)
            client_samples.append(len(partitions[client_id]))

            print(f"  │  Node {chr(65+client_id)}: loss={loss:.4f}, "
                  f"ε={epsilon:.4f}, samples={len(partitions[client_id])}")

        # ── Secure Aggregation ──────────────────────────────────────
        if use_secure_agg and secure_agg:
            print(f"  │  🔒 Applying secure aggregation masks...")
            # Mask each client's update
            masked_updates = []
            for client_id in range(num_clients):
                masked = secure_agg.mask_client_update(
                    client_id, original_updates[client_id]
                )
                masked_updates.append(masked)

            # Verify mask cancellation
            max_diff = secure_agg.verify_mask_cancellation(
                original_updates, masked_updates, client_samples
            )
            print(f"  │  🔒 Mask verification: max_diff={max_diff:.2e} (should be ~0)")

            # Aggregate masked updates (masks cancel out)
            new_global_params = secure_agg.aggregate(masked_updates, client_samples)
        else:
            # Standard FedAvg without secure aggregation
            total_samples = sum(client_samples)
            new_global_params = []
            for k in range(len(original_updates[0])):
                weighted_sum = np.zeros_like(original_updates[0][k], dtype=np.float64)
                for client_idx, update in enumerate(original_updates):
                    weight = client_samples[client_idx] / total_samples
                    weighted_sum += update[k].astype(np.float64) * weight
                new_global_params.append(weighted_sum.astype(np.float32))

        # ── Update global model ─────────────────────────────────────
        global_params = new_global_params
        set_model_parameters(global_model, global_params)

        # ── Evaluate global model ────────────────────────────────────
        eval_loss, eval_accuracy = evaluate_model(global_model, test_loader, device)

        round_duration = time.time() - round_start
        avg_loss = np.mean(round_losses)
        avg_epsilon = np.mean(round_epsilons) if use_dp else 0.0

        # Record privacy cost
        privacy_budget.record_round(avg_epsilon)

        round_metrics = {
            "round": round_num,
            "train_loss": float(avg_loss),
            "eval_loss": float(eval_loss),
            "eval_accuracy": float(eval_accuracy),
            "epsilon": float(privacy_budget.total_epsilon),
            "epsilon_this_round": float(avg_epsilon),
            "num_clients": num_clients,
            "round_duration_sec": float(round_duration),
        }
        all_metrics.append(round_metrics)

        print(f"  │  📊 Global: loss={eval_loss:.4f}, "
              f"acc={eval_accuracy:.4f} ({eval_accuracy*100:.1f}%)")
        print(f"  │  🔐 Privacy: ε={privacy_budget.total_epsilon:.4f} / "
              f"{target_epsilon} (remaining: {privacy_budget.budget_remaining:.4f})")
        print(f"  └── Round {round_num} completed in {round_duration:.2f}s\n")

        # Write to DB
        if db_url:
            asyncio.run(update_db_metrics(db_url, job_id, round_num, round_metrics))

        # Check privacy budget
        if privacy_budget.budget_exhausted:
            print(f"  ⚠️  Privacy budget exhausted! Stopping early.")
            break

    # ── Save final model ─────────────────────────────────────────────
    print(f"[4/4] Saving final model...")
    os.makedirs(model_save_dir, exist_ok=True)
    model_path = os.path.join(model_save_dir, f"model_{job_id}.pt")
    torch.save(global_model.state_dict(), model_path)
    print(f"  ✓ Model saved to: {model_path}")

    # Save metrics JSON
    metrics_path = os.path.join(model_save_dir, f"metrics_{job_id}.json")
    output_data = {
        "job_id": job_id,
        "config": {
            "num_rounds": num_rounds,
            "num_clients": num_clients,
            "noise_multiplier": noise_multiplier,
            "max_grad_norm": max_grad_norm,
            "use_dp": use_dp,
            "use_secure_agg": use_secure_agg,
        },
        "privacy_budget": privacy_budget.to_dict(),
        "metrics": all_metrics,
    }
    with open(metrics_path, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"  ✓ Metrics saved to: {metrics_path}")

    # ── Update DB: completed ─────────────────────────────────────────
    if db_url and all_metrics:
        final = all_metrics[-1]
        asyncio.run(update_job_status(
            db_url, job_id, "completed",
            final_accuracy=final["eval_accuracy"],
            final_loss=final["eval_loss"],
            epsilon_spent=privacy_budget.total_epsilon,
            model_path=model_path,
            completed_at=datetime.now(timezone.utc).isoformat(),
        ))

    # ── Summary ──────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f" Training Complete!")
    print(f" Final Accuracy: {all_metrics[-1]['eval_accuracy']*100:.2f}%")
    print(f" Final Loss:     {all_metrics[-1]['eval_loss']:.4f}")
    print(f" Privacy Cost:   ε = {privacy_budget.total_epsilon:.4f}")
    print(f"{'='*70}\n")

    return output_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Federated Learning Simulation")
    parser.add_argument("--job-id", type=str, default="local-test")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--clients", type=int, default=3)
    parser.add_argument("--noise-multiplier", type=float, default=1.1)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--target-epsilon", type=float, default=10.0)
    parser.add_argument("--local-epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--no-dp", action="store_true", help="Disable differential privacy")
    parser.add_argument("--no-secure-agg", action="store_true", help="Disable secure aggregation")
    parser.add_argument("--db-url", type=str, default="")
    parser.add_argument("--data-dir", type=str, default="./data")
    parser.add_argument("--model-dir", type=str, default="./model_storage")

    args = parser.parse_args()

    run_federated_learning(
        job_id=args.job_id,
        num_rounds=args.rounds,
        num_clients=args.clients,
        noise_multiplier=args.noise_multiplier,
        max_grad_norm=args.max_grad_norm,
        target_epsilon=args.target_epsilon,
        local_epochs=args.local_epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        use_dp=not args.no_dp,
        use_secure_agg=not args.no_secure_agg,
        db_url=args.db_url,
        data_dir=args.data_dir,
        model_save_dir=args.model_dir,
    )

# Privacy-Preserving Federated Learning Platform

A production-ready platform for collaborative machine learning without raw data sharing, utilizing **Federated Learning (FL)**, **Differential Privacy (DP)**, and **Secure Aggregation (SA)**.

## 🚀 Features

- **Federated Learning Core**: Orchestrates decentralized model training across multiple hospital/organization nodes.
- **Differential Privacy**: Uses **Opacus** (PyTorch) for Gaussian noise injection, protecting against membership inference and model inversion.
- **Secure Aggregation**: Implements a masking-based SA protocol to ensure the server only sees aggregated updates.
- **Privacy Budgeting**: Tracks cumulative **ε (epsilon)** consumption across training rounds.
- **Researcher Dashboard**: A premium, dark-themed Next.js interface for job management, real-time metrics, and model performance visualization.
- **Secure Backend**: FastAPI with JWT authentication and Role-Based Access Control (RBAC).
- **Compliance & Security**: Complete audit logging of all actions and automated sensitivity level tracking.

---

## 🛠️ Project Structure

```text
.
├── backend/            # FastAPI Backend
│   ├── routers/        # API Endpoints (Auth, Training, Orgs, etc.)
│   ├── models.py       # SQLAlchemy ORM Models
│   ├── schemas.py      # Pydantic Schemas
│   └── main.py         # Main entry point
├── fl_core/            # Federated Learning Simulation
│   ├── model.py        # PyTorch CNN with DP support
│   ├── data_loader.py  # CIFAR-10 data loading & partitioning
│   ├── privacy_engine.py   # Epsilon budget tracking
│   ├── secure_aggregation.py # Masking-based protocol
│   └── run_simulation.py   # Full simulation pipeline
├── frontend/           # Next.js 14 Dashboard
│   ├── src/app/        # React pages & components
│   └── src/lib/api.ts  # API utility functions
├── docker-compose.yml  # Docker orchestration
└── requirements.txt    # Python dependencies
```

---

## ⚙️ How to Run the Project (Manual Setup)

Since Docker is not available on your system, please follow these steps to run the backend and frontend separately.

### 1. Backend Setup (FastAPI)
1. Open a terminal and navigate to the project folder.
2. Activate your virtual environment:
   ```powershell
   .\.venv\Scripts\activate
   ```
3. Install Python dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Start the FastAPI server:
   ```powershell
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   *The backend will be running at http://localhost:8000*

### 2. Frontend Setup (Next.js)
1. Open a **new terminal** and navigate to the `frontend` directory:
   ```powershell
   cd frontend
   ```
2. Install Node.js dependencies:
   ```powershell
   npm install
   ```
3. Start the development server:
   ```powershell
   npm run dev
   ```
   *The dashboard will be available at http://localhost:3000*

---

## 🔗 Running with Docker (Optional)

If you install [Docker Desktop](https://www.docker.com/products/docker-desktop/), you can run everything with a single command:
```bash
docker compose up --build
```
*(Note: Modern Docker uses `docker compose` without the hyphen)*

Access the dashboard at `http://localhost:3000`.

---

## 🔐 Security & Privacy

- **Differential Privacy**: Each local training round injects noise scaled by the sensitivity of the update.
- **Epsilon Tracking**: Researchers set an ε-budget; if the budget is exhausted, further training is blocked.
- **Masking-SA**: Client-side masks are added to local updates; they sum to zero across all clients, revealing only the aggregate to the server.
- **Audit Trails**: Every action (job creation, login, node participation) is logged for auditor review.

---

## 📈 Demo Simulation

To run a simulated federated learning round locally:
```bash
python fl_core/run_simulation.py --rounds 5 --clients 3 --dp True --privacy_budget 10
```
This will:
1. Initialize the global model.
2. Partition the CIFAR-10 dataset among 3 simulated nodes.
3. Perform 5 rounds of training with noise injection.
4. Apply secure aggregation masks.
5. Record metrics to the database in real-time.

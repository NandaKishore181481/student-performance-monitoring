import os
import sys
import argparse
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def init_db():
    print("--> Initializing and seeding database...")
    from src.database import seed_database
    seed_database()

def train_model():
    print("--> Running PyCaret/Scikit-Learn Model Training & Comparison...")
    from src.ml_models import train_and_select_best_model
    train_and_select_best_model()

def start_api():
    print("--> Starting FastAPI Server on http://localhost:8000...")
    subprocess.run([
        sys.executable, "-m", "uvicorn", "src.api.main:app", 
        "--host", "127.0.0.1", "--port", "8000", "--reload"
    ], cwd=BASE_DIR)

def start_dashboard():
    print("--> Starting Streamlit Dashboard...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "src/dashboard/app.py"
    ], cwd=BASE_DIR)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Student Performance System Services Launcher")
    parser.add_argument("--init-db", action="store_true", help="Create tables and seed sample records")
    parser.add_argument("--train", action="store_true", help="Run AutoML AutoML training pipeline")
    parser.add_argument("--api", action="store_true", help="Start FastAPI REST endpoints")
    parser.add_argument("--dashboard", action="store_true", help="Start Streamlit client interface")
    
    args = parser.parse_args()
    
    # Add project directory to sys.path so scripts can find src modules
    sys.path.insert(0, BASE_DIR)
    
    if not (args.init_db or args.train or args.api or args.dashboard):
        # Default behavior: Initialize DB, train models, then tell the user how to run
        init_db()
        train_model()
        print("\n" + "="*50)
        print("Setup and initialization complete!")
        print("To launch the FastAPI REST API, run:")
        print("    python run.py --api")
        print("\nTo launch the Streamlit Web Dashboard, run:")
        print("    python run.py --dashboard")
        print("="*50 + "\n")
    else:
        if args.init_db:
            init_db()
        if args.train:
            train_model()
        if args.api:
            start_api()
        if args.dashboard:
            start_dashboard()

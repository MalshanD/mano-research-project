import torch
import numpy as np
import sys
from pathlib import Path

# Add backend/app/ to sys.path so "from models_repo.xxx" resolves as a package import
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import the architecture definition we migrated
from ml_models.component1.lstm_model_Def import RiskPredictionModel
from ml_models.component1.lstm_config import LSTMConfig

class RiskPredictionService:
    """Singleton service to hold the LSTM model in VRAM."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RiskPredictionService, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.device = None
        return cls._instance

    def load_model(self, model_path: str, device: str):
        print(f"[RiskService] Loading LSTM from {model_path}...")
        self.device = device

        # Initialize Architecture with dummy config
        config = LSTMConfig()
        self.model = RiskPredictionModel(config)

        # Load Weights (weights_only=False allows loading our custom model structures safely)
        state_dict = torch.load(model_path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(state_dict)

        self.model.to(self.device)
        self.model.eval()
        print("   [OK] [RiskService] Model Loaded Successfully.")

    def predict(self, dynamic_data: np.ndarray, static_data: np.ndarray):
        if self.model is None:
            raise RuntimeError("Risk Model is not loaded!")

        dyn_tensor = torch.FloatTensor(dynamic_data).to(self.device)
        stat_tensor = torch.FloatTensor(static_data).to(self.device)

        with torch.no_grad():
            logits = self.model(dyn_tensor, stat_tensor)
            probs = torch.softmax(logits, dim=1)

            risk_class = torch.argmax(probs, dim=1).item()
            confidence = probs[0, risk_class].item()

        return {
            "risk_class": risk_class,
            "confidence": confidence,
            "probabilities": probs.cpu().numpy().tolist()[0]
        }

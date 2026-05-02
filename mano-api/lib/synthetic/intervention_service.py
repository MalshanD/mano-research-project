import torch
import numpy as np
import sys
from pathlib import Path

# Add backend/app/ to sys.path so "from models_repo.xxx" resolves as a package import
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import Architecture Definitions
from ml_models.component1.seq2seq_model_Def import InterventionSimulator
from ml_models.component1.sim_config import SimConfig
from ml_models.component1.rl_agent_Def import ActorCritic

# Minimal config matching Component 1 training parameters
class RLAgentConfig:
    STATE_DIM = 48 # 28 dynamic features (7 days * 4) + 20 static features
    NUM_INTERVENTIONS = 5
    HIDDEN_DIM = 128

class InterventionService:
    """Singleton service to hold AMISE Simulator and PPO Agent in VRAM."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InterventionService, cls).__new__(cls)
            cls._instance.simulator = None
            cls._instance.agent = None
            cls._instance.device = None
        return cls._instance

    def load_models(self, sim_path: str, agent_path: str, device: str):
        """Loads both the Seq2Seq world model and the PPO Agent policy."""
        print(f"[InterventionService] Loading AMISE Engines...")
        self.device = device

        # 1. Load Seq2Seq Simulator (World Model)
        sim_config = SimConfig()
        self.simulator = InterventionSimulator(sim_config)
        # weights_only=False required to load custom PyTorch class architecture securely from our local repo
        self.simulator.load_state_dict(torch.load(sim_path, map_location=self.device, weights_only=False))
        self.simulator.to(self.device).eval()

        # 2. Load RL Agent (Policy Network)
        self.agent = ActorCritic(
            state_dim=RLAgentConfig.STATE_DIM,
            action_dim=RLAgentConfig.NUM_INTERVENTIONS,
            hidden_dim=RLAgentConfig.HIDDEN_DIM,
            device=self.device
        )
        self.agent.load_state_dict(torch.load(agent_path, map_location=self.device, weights_only=False))
        self.agent.to(self.device).eval()

        print("   [OK] [InterventionService] AMISE Loaded Successfully.")

    def simulate_outcome(self, patient_dynamic: np.ndarray, intervention_type: int, intensity: float):
        """Simulates the 7-day future trajectory based on an intervention."""
        if self.simulator is None:
            raise RuntimeError("Simulator not loaded!")

        # Create the intervention condition vector
        intervention_vec = torch.zeros(1, 6).to(self.device)
        intervention_vec[0, intervention_type] = 1.0 # One-hot encoding for the intervention type
        intervention_vec[0, 5] = intensity           # The continuous intensity value

        patient_tensor = torch.FloatTensor(patient_dynamic).to(self.device)

        with torch.no_grad():
            # teacher_forcing_ratio=0.0 because we want pure prediction, no ground truth guidance
            future_dynamic = self.simulator(patient_tensor, intervention_vec, target=None, teacher_forcing_ratio=0.0)

        return future_dynamic.cpu().numpy()

    def get_prescription(self, dynamic_flat: np.ndarray, static_flat: np.ndarray):
        """Asks the RL Agent for the optimal intervention and intensity."""
        if self.agent is None:
            raise RuntimeError("Agent not loaded!")

        # Concatenate into the 48-dimensional state vector expected by the PPO Agent
        state = np.concatenate([dynamic_flat, static_flat])
        state_tensor = torch.FloatTensor(state).to(self.device)

        with torch.no_grad():
            (action_cat, action_cont), _, _ = self.agent.act(state_tensor)

            # Extract softmax probability of the chosen action as confidence
            if state_tensor.dim() == 1:
                state_tensor = state_tensor.unsqueeze(0)
            features = self.agent.features(state_tensor)
            logits = self.agent.actor_discrete(features)
            probs = torch.softmax(logits, dim=-1)
            confidence = float(probs[0, action_cat].item())

        return {
            "intervention_id": action_cat,
            "intensity": action_cont,
            "confidence": confidence,
        }

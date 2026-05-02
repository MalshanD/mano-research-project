"""
LSTM Config for Backend Inference.
Mirrors the config structure expected by RiskPredictionModel in lstm_model_Def.py,
with only the attributes needed at inference time.

Original source: ml-services/privacy-preserving-lstm/src/lstm_config.py
"""
import torch


class ModelConfig:
    """Hybrid Architecture Settings"""
    # Dynamic Branch (Time Series)
    SEQ_LEN = 7
    DYNAMIC_INPUT_DIM = 4   # [Sleep, Quality, HR, Stress]
    LSTM_HIDDEN_DIM = 64
    LSTM_LAYERS = 2
    DROPOUT = 0.3

    # Static Branch (Demographics)
    STATIC_INPUT_DIM = 20
    STATIC_HIDDEN_DIM = 32

    # Fusion & Output
    FUSION_HIDDEN_DIM = 64
    NUM_CLASSES = 3  # 0=Low, 1=Medium, 2=High Risk


class TrainingConfig:
    DEVICE = 'cuda' if torch.cuda.is_available() and torch.cuda.device_count() > 0 else 'cpu'


class LSTMConfig:
    """Minimal Config object matching the structure expected by RiskPredictionModel."""

    def __init__(self):
        self.model = ModelConfig()
        self.training = TrainingConfig()

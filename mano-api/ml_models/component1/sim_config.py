"""
Simulator Config for Backend Inference.
Mirrors the config structure expected by InterventionSimulator in seq2seq_model_Def.py,
with only the attributes needed at inference time.
"""
import torch


class InterventionConfig:
    INTERVENTION_TYPES = ['Control', 'Wellness_App', 'CBT', 'Exercise', 'Medication']
    NUM_INTERVENTIONS = len(INTERVENTION_TYPES)


class ModelConfig:
    SEQ_LEN = 7
    PRED_LEN = 7
    INPUT_DIM = 4

    HIDDEN_DIM = 64
    LAYERS = 2

    ENC_HIDDEN_DIM = HIDDEN_DIM
    DEC_HIDDEN_DIM = HIDDEN_DIM
    ENC_LAYERS = LAYERS
    DEC_LAYERS = LAYERS

    DROPOUT = 0.2


class TrainingConfig:
    DEVICE = 'cuda' if torch.cuda.is_available() and torch.cuda.device_count() > 0 else 'cpu'


class SimConfig:
    """Minimal Config object matching the structure expected by InterventionSimulator."""

    def __init__(self):
        self.interventions = InterventionConfig()
        self.model = ModelConfig()
        self.training = TrainingConfig()

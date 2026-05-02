"""
MANO Component 2: Hybrid LSTM Model Architecture
A Dual-Branch Network that fuses Temporal and Static data.

WHAT THIS DOES:
It acts as a "Multi-Modal" brain. It reads two different types of data at once:
1. Dynamic Branch (Time): Reads the 7-day wearable sequence.
2. Static Branch (Demographics): Reads the patient's profile.

WHY THIS ARCHITECTURE?
Standard LSTMs ignore static context (like Age). Standard Dense nets ignore time.
This "Fusion Architecture" combines the best of both worlds to predict Risk (0, 1, 2).
"""
import torch
import torch.nn as nn

class RiskPredictionModel(nn.Module):
    def __init__(self, config):
        super(RiskPredictionModel, self).__init__()
        
        # ====================================================
        # BRANCH 1: TEMPORAL PROCESSING (The "Movie" Watcher)
        # ====================================================
        # WHAT: An LSTM (Long Short-Term Memory) network.
        # WHY: Unlike standard RNNs, LSTMs have a "forget gate" that lets them 
        # remember important events (e.g., "Poor Sleep on Monday") and ignore 
        # noise, even if the event happened 7 days ago.
        self.lstm = nn.LSTM(
            input_size=config.model.DYNAMIC_INPUT_DIM,  # 4 Signals (Sleep, HR, etc.)
            hidden_size=config.model.LSTM_HIDDEN_DIM,   # e.g., 64 Neurons memory capacity
            num_layers=config.model.LSTM_LAYERS,        # Stacked layers for complex pattern recognition
            batch_first=True,                           # Input shape: [Batch, Time, Feat]
            dropout=config.model.DROPOUT if config.model.LSTM_LAYERS > 1 else 0
        )
        
        # ====================================================
        # BRANCH 2: STATIC PROCESSING (The "Profile" Reader)
        # ====================================================
        # WHAT: A Dense (Fully Connected) network for demographics.
        # WHY BATCH NORM?: Static features have wild ranges (Age is 0-100, Gender is 0-1).
        # Normalization forces them into a standardized range so they don't overpower the LSTM features.
        self.static_net = nn.Sequential(
            nn.Linear(config.model.STATIC_INPUT_DIM, config.model.STATIC_HIDDEN_DIM),
            nn.BatchNorm1d(config.model.STATIC_HIDDEN_DIM),
            nn.ReLU(),
            nn.Dropout(config.model.DROPOUT)
        )
        
        # ====================================================
        # BRANCH 3: FUSION & CLASSIFICATION (The Decision Maker)
        # ====================================================
        # WHAT: Concatenates the "Memory" from the LSTM and the "Features" from the Static Net.
        # Calculation: 64 (Time features) + 32 (Static features) = 96 Combined Features.
        fusion_dim = config.model.LSTM_HIDDEN_DIM + config.model.STATIC_HIDDEN_DIM
        
        self.classifier = nn.Sequential(
            # Fusion Layer: Mixes the two data types together
            nn.Linear(fusion_dim, config.model.FUSION_HIDDEN_DIM),
            nn.ReLU(),
            nn.Dropout(config.model.DROPOUT),
            
            # Final Output Layer: Predicts scores for 3 classes
            # Output Shape: [Batch, 3] -> [Score_Low, Score_Medium, Score_High]
            # WHY NO SIGMOID?: We use CrossEntropyLoss for training, which applies
            # Softmax internally. This is more numerically stable than adding Softmax here.
            nn.Linear(config.model.FUSION_HIDDEN_DIM, config.model.NUM_CLASSES)
        )

    def forward(self, x_dynamic, x_static):
        """
        Forward Pass: The flow of data through the brain.
        
        Args:
            x_dynamic: Temporal data [Batch, 7, 4]
            x_static:  Demographic data [Batch, 20]
        """
        # 1. Process Time Series
        # The LSTM outputs 'out' (history of all steps) and 'hidden' (final state).
        # We only care about the final state 'h_n' because it summarizes the whole week.
        # h_n shape: [num_layers, batch, hidden_dim]. 
        # We grab [-1] to get the state from the very last layer.
        _, (h_n, _) = self.lstm(x_dynamic)
        dynamic_emb = h_n[-1] 
        
        # 2. Process Demographics
        static_emb = self.static_net(x_static)
        
        # 3. Fuse Together
        # We simply glue the two vectors together side-by-side.
        combined = torch.cat((dynamic_emb, static_emb), dim=1)
        
        # 4. Predict
        logits = self.classifier(combined)
        return logits

# ====================================================
# UTILITY FUNCTIONS
# ====================================================

def count_parameters(model):
    """Returns the total number of trainable weights."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

def print_model_architecture(model):
    """Prints a summary of the model structure."""
    print("\n" + "="*70)
    print("HYBRID LSTM ARCHITECTURE")
    print("="*70)
    print(model)
    print(f"\nTrainable Parameters: {count_parameters(model):,}")
    print("="*70 + "\n")

if __name__ == "__main__":
    # Self-Test to ensure shapes are correct
    # This block only runs if you execute this script directly
    from lstm_config import config
    
    device = torch.device('cpu')
    model = RiskPredictionModel(config).to(device)
    print_model_architecture(model)
    
    # Simulate dummy data
    fake_dynamic = torch.randn(32, 7, 4)  # Batch of 32 users
    fake_static = torch.randn(32, 20)     # Batch of 32 users
    
    output = model(fake_dynamic, fake_static)
    print(f"Test Output Shape: {output.shape}") 
    # Expected: [32, 3] (32 users, 3 class scores)
    assert output.shape == (32, 3), "Shape Mismatch! Check model configuration."
    print("✅ Shape Test Passed")
"""
TimeGAN Model Definition (Backend-Adapted)

Based on the training architecture from:
  ml-services/Component 1/privacy-preserving-gan/src/timegan_model.py

Contains the 4+1 core networks:
  Embedder, Recovery, Generator, Supervisor, Discriminator

Architecture: GRU-based (Yoon et al., 2019)
Input: Random noise (batch, 7, 4)
Output: Synthetic 7-day × 4-signal wearable sequences
  (Sleep Duration, Sleep Quality, Heart Rate, Stress Level)
"""
import torch
import torch.nn as nn
import torch.nn.init as init


# Default config values (matching training config)
TIMEGAN_DEFAULTS = {
    "seq_len": 7,
    "n_signals": 4,
    "noise_dim": 24,
    "hidden_dim": 24,
    "num_layers": 3,
}

SIGNAL_NAMES = ["Sleep Duration", "Quality of Sleep", "Heart Rate", "Stress Level"]


class TimeGAN(nn.Module):
    """
    TimeGAN Main Class
    Encapsulates the four distinct neural networks required for the framework.
    """

    def __init__(self, feature_dim=4, hidden_dim=24, num_layers=3, device="cpu"):
        super(TimeGAN, self).__init__()
        self.feature_dim = feature_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.device = device

        # --- 1. EMBEDDER NETWORK (Autoencoder Encoder) ---
        self.embedder = nn.GRU(
            input_size=self.feature_dim,
            hidden_size=self.hidden_dim,
            num_layers=self.num_layers,
            batch_first=True
        )
        self.embedder_out = nn.Linear(self.hidden_dim, self.hidden_dim)

        # --- 2. RECOVERY NETWORK (Autoencoder Decoder) ---
        self.recovery = nn.GRU(
            input_size=self.hidden_dim,
            hidden_size=self.hidden_dim,
            num_layers=self.num_layers,
            batch_first=True
        )
        self.recovery_out = nn.Linear(self.hidden_dim, self.feature_dim)

        # --- 3. GENERATOR NETWORK ---
        self.generator = nn.GRU(
            input_size=self.feature_dim,
            hidden_size=self.hidden_dim,
            num_layers=self.num_layers,
            batch_first=True
        )
        self.generator_out = nn.Linear(self.hidden_dim, self.hidden_dim)

        # --- 4. SUPERVISOR NETWORK ---
        self.supervisor = nn.GRU(
            input_size=self.hidden_dim,
            hidden_size=self.hidden_dim,
            num_layers=self.num_layers - 1,
            batch_first=True
        )
        self.supervisor_out = nn.Linear(self.hidden_dim, self.hidden_dim)

        # --- 5. DISCRIMINATOR NETWORK ---
        self.discriminator = nn.GRU(
            input_size=self.hidden_dim,
            hidden_size=self.hidden_dim,
            num_layers=self.num_layers,
            batch_first=True
        )
        self.discriminator_out = nn.Linear(self.hidden_dim, 1)

        self.to(self.device)
        self._init_weights()

    def _init_weights(self):
        """Xavier Normal initialization for GRU-compatible weight init."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                init.xavier_normal_(m.weight)
                if m.bias is not None:
                    init.constant_(m.bias, 0)

    # --- Forward Passes ---

    def forward_embedder(self, X):
        """Input: Real Data -> Output: Latent Code"""
        H, _ = self.embedder(X)
        H = torch.sigmoid(self.embedder_out(H))
        return H

    def forward_recovery(self, H):
        """Input: Latent Code -> Output: Reconstructed Data"""
        X_tilde, _ = self.recovery(H)
        X_tilde = torch.sigmoid(self.recovery_out(X_tilde))
        return X_tilde

    def forward_generator(self, Z):
        """Input: Random Noise -> Output: Fake Latent Code"""
        E, _ = self.generator(Z)
        E = torch.sigmoid(self.generator_out(E))
        return E

    def forward_supervisor(self, H):
        """Input: Latent Code(t) -> Output: Latent Code(t+1)"""
        S, _ = self.supervisor(H)
        S = torch.sigmoid(self.supervisor_out(S))
        return S

    def forward_discriminator(self, H):
        """Input: Latent Code -> Output: Real/Fake Score"""
        Y_hat, _ = self.discriminator(H)
        Y_hat = self.discriminator_out(Y_hat)
        return Y_hat

"""
MANO Component 3: Hybrid PPO Agent (Actor-Critic)
Handles complex Dual-Action Spaces (Discrete Intervention + Continuous Intensity).
"""
import torch
import torch.nn as nn
from torch.distributions import Categorical, Normal
import numpy as np


class ActorCritic(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_dim, device):
        super(ActorCritic, self).__init__()
        self.device = device

        # --- Shared Feature Extractor ---
        # Reads the patient state (Dynamic + Static)
        self.features = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh()
        )

        # --- Head 1: Discrete Actor (Treatment Type) ---
        # Outputs logits for 5 classes (Control, CBT, etc.)
        self.actor_discrete = nn.Linear(hidden_dim, action_dim)

        # --- Head 2: Continuous Actor (Intensity) ---
        # Outputs Mean (Mu) for Gaussian Distribution.
        # We learn Log_Std as a parameter to allow exploration adaptation.
        self.actor_continuous_mu = nn.Linear(hidden_dim, 1)
        self.actor_continuous_log_std = nn.Parameter(torch.zeros(1))

        # --- Head 3: Critic (Value Function) ---
        # Estimates "How good is this state?" for Advantage calculation
        self.critic = nn.Linear(hidden_dim, 1)

        self.to(device)

    def act(self, state):
        """
        Sample an action for the environment (Interaction Phase)
        Returns: Action Tuple, LogProbs, StateValue
        """
        if not isinstance(state, torch.Tensor):
            state = torch.FloatTensor(state).to(self.device)

        # Add batch dim if missing
        if state.dim() == 1:
            state = state.unsqueeze(0)

        # Extract features
        features = self.features(state)

        # 1. Discrete Action
        logits = self.actor_discrete(features)
        dist_cat = Categorical(logits=logits)
        action_cat = dist_cat.sample()
        action_logprob_cat = dist_cat.log_prob(action_cat)

        # 2. Continuous Action
        mu = torch.sigmoid(self.actor_continuous_mu(
            features))  # Sigmoid -> [0, 1]
        std = torch.exp(self.actor_continuous_log_std)
        dist_cont = Normal(mu, std)
        action_cont = dist_cont.sample()

        # Clamp intensity to valid range [0.1, 1.0]
        action_cont = torch.clamp(action_cont, 0.1, 1.0)
        action_logprob_cont = dist_cont.log_prob(action_cont)

        # Combine LogProbs
        total_logprob = action_logprob_cat + action_logprob_cont.sum(dim=-1)

        return (action_cat.item(), action_cont.item()), \
            total_logprob.item(), \
            self.critic(features).item()

    def evaluate(self, state, action_cat, action_cont):
        """
        Evaluate actions for PPO Update (Training Phase)
        Returns: LogProbs, StateValues, Entropy
        """
        features = self.features(state)

        # 1. Discrete Evaluation
        logits = self.actor_discrete(features)
        dist_cat = Categorical(logits=logits)
        action_logprob_cat = dist_cat.log_prob(action_cat)
        dist_entropy_cat = dist_cat.entropy()

        # 2. Continuous Evaluation
        mu = torch.sigmoid(self.actor_continuous_mu(features))
        std = torch.exp(self.actor_continuous_log_std)
        dist_cont = Normal(mu, std)
        action_logprob_cont = dist_cont.log_prob(action_cont)
        dist_entropy_cont = dist_cont.entropy()

        # Combine
        # Squeeze helps ensure dimensions match [Batch]
        action_logprobs = action_logprob_cat + action_logprob_cont.squeeze()
        dist_entropy = dist_entropy_cat + dist_entropy_cont.squeeze()
        state_values = self.critic(features).squeeze()

        return action_logprobs, state_values, dist_entropy

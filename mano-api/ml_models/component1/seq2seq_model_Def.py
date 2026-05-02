"""
MANO Component 3: Seq2Seq Simulator Architecture
Advanced Encoder-Decoder with Bahdanau Attention.

UPGRADE:
- Replaced GRU with LSTM for better long-term dependency capture.
- Added Attention Layer to focus on specific past days.
- Implemented Teacher Forcing support in Decoder.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import random


class Encoder(nn.Module):
    """
    Reads the 7-day patient history.
    Returns: Outputs (for attention) and Final Hidden State (context).
    """

    def __init__(self, input_dim, hidden_dim, num_layers, dropout):
        super(Encoder, self).__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

    def forward(self, x):
        # x: [Batch, Seq_Len, Features]
        outputs, (hidden, cell) = self.lstm(x)
        return outputs, (hidden, cell)


class Attention(nn.Module):
    """
    Calculates importance weights for each time step in history.
    """

    def __init__(self, hidden_dim):
        super(Attention, self).__init__()
        self.attn = nn.Linear(hidden_dim * 2, hidden_dim)
        self.v = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, hidden, encoder_outputs):
        # hidden: [Batch, Hidden] (Current Decoder State)
        # encoder_outputs: [Batch, Seq, Hidden] (All Encoder States)

        seq_len = encoder_outputs.size(1)

        # Repeat hidden state seq_len times
        # [Batch, Seq, Hidden]
        hidden_expanded = hidden.unsqueeze(1).repeat(1, seq_len, 1)

        # Calculate Energy
        energy = torch.tanh(
            self.attn(torch.cat((hidden_expanded, encoder_outputs), dim=2)))
        attention = self.v(energy).squeeze(2)

        # Softmax to get weights (0-1)
        return F.softmax(attention, dim=1)


class Decoder(nn.Module):
    """
    Predicts the future, one step at a time.
    Conditioned on:
    1. Previous Output
    2. Attention Context (Weighted History)
    3. Intervention Vector (Treatment)
    """

    def __init__(self, input_dim, hidden_dim, output_dim, num_layers, dropout):
        super(Decoder, self).__init__()
        self.output_dim = output_dim
        self.attention = Attention(hidden_dim)

        # Input = Prev_Output(4) + Context(Hidden) + Intervention(6)
        self.lstm = nn.LSTM(
            input_size=input_dim + hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        self.fc = nn.Linear(hidden_dim, output_dim)
        self.sigmoid = nn.Sigmoid()  # Bound output to [0,1]

    def forward(self, input_step, hidden, cell, encoder_outputs, intervention):
        # 1. Calculate Attention
        # Use the hidden state from the *last layer* of the LSTM
        attn_weights = self.attention(hidden[-1], encoder_outputs)

        # 2. Calculate Context Vector (Weighted sum of history)
        # [Batch, 1, Seq] * [Batch, Seq, Hidden] -> [Batch, 1, Hidden]
        context = torch.bmm(attn_weights.unsqueeze(1), encoder_outputs)

        # 3. Combine Inputs
        # Input: [Batch, 1, Feat]
        # Context: [Batch, 1, Hidden]
        # Intervention: [Batch, 1, Cond_Dim]
        rnn_input = torch.cat(
            (input_step, context, intervention.unsqueeze(1)), dim=2)

        # 4. LSTM Step
        output, (hidden, cell) = self.lstm(rnn_input, (hidden, cell))

        # 5. Prediction
        prediction = self.fc(output)
        prediction = self.sigmoid(prediction)

        return prediction, hidden, cell


class InterventionSimulator(nn.Module):
    """
    The Full Seq2Seq Model.
    """

    def __init__(self, config):
        super(InterventionSimulator, self).__init__()
        self.config = config
        self.device = config.training.DEVICE

        # Dimensions
        self.input_dim = config.model.INPUT_DIM
        # Intervention (5 One-Hot) + Intensity (1 Scalar) = 6
        self.cond_dim = len(config.interventions.INTERVENTION_TYPES) + 1

        self.encoder = Encoder(
            self.input_dim,
            config.model.ENC_HIDDEN_DIM,
            config.model.ENC_LAYERS,
            config.model.DROPOUT
        )

        self.decoder = Decoder(
            input_dim=self.input_dim + self.cond_dim,  # Signal + Condition
            hidden_dim=config.model.DEC_HIDDEN_DIM,
            output_dim=self.input_dim,
            num_layers=config.model.DEC_LAYERS,
            dropout=config.model.DROPOUT
        )

        self.to(self.device)

    def forward(self, source, condition, target=None, teacher_forcing_ratio=0.5):
        batch_size = source.shape[0]
        seq_len = self.config.model.PRED_LEN

        # Container for outputs
        outputs = torch.zeros(batch_size, seq_len,
                              self.input_dim).to(self.device)

        # 1. Encode
        encoder_outputs, (hidden, cell) = self.encoder(source)

        # 2. Initialize Decoder
        # Start with the last known value from history
        decoder_input = source[:, -1, :].unsqueeze(1)

        # 3. Decode Loop
        for t in range(seq_len):
            output, hidden, cell = self.decoder(
                decoder_input,
                hidden,
                cell,
                encoder_outputs,
                condition
            )

            outputs[:, t, :] = output.squeeze(1)

            # Teacher Forcing
            if target is not None and random.random() < teacher_forcing_ratio:
                decoder_input = target[:, t, :].unsqueeze(1)  # True Value
            else:
                decoder_input = output  # Predicted Value (Autoregression)

        return outputs

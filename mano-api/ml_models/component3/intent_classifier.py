"""
Intent Classification Model
Uses BERT-based model for classifying user intents in mental health conversations
"""

import torch
import torch.nn as nn
from transformers import BertTokenizer, BertModel, AutoTokenizer, AutoModel
from torch.utils.data import Dataset, DataLoader
import numpy as np
from sklearn.preprocessing import LabelEncoder
from typing import List, Tuple, Dict
import pickle
import os


class IntentDataset(Dataset):
    """Custom dataset for intent classification"""

    def __init__(self, texts: List[str], labels: List[str], tokenizer, max_length: int = 128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'label': torch.tensor(label, dtype=torch.long)
        }


class IntentClassifier(nn.Module):
    """BERT-based intent classification model"""

    def __init__(self, n_classes: int, model_name: str = 'bert-base-uncased', dropout: float = 0.3):
        super(IntentClassifier, self).__init__()

        self.bert = BertModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(self.bert.config.hidden_size, n_classes)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        # Use [CLS] token representation
        pooled_output = outputs.pooler_output
        output = self.dropout(pooled_output)
        return self.classifier(output)


class IntentClassificationEngine:
    """Training and inference engine for intent classification"""

    def __init__(self, model_name: str = 'bert-base-uncased', max_length: int = 128):
        self.model_name = model_name
        self.max_length = max_length
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.label_encoder = LabelEncoder()
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() and torch.cuda.device_count() > 0 else 'cpu')
        print(f"Using device: {self.device}")

    def prepare_data(self, texts: List[str], labels: List[str]) -> Tuple:
        """Prepare data for training"""
        # Encode labels
        encoded_labels = self.label_encoder.fit_transform(labels)

        # Create dataset
        dataset = IntentDataset(texts, encoded_labels, self.tokenizer, self.max_length)

        return dataset, len(self.label_encoder.classes_)

    def train(self, train_texts: List[str], train_labels: List[str],
              val_texts: List[str] = None, val_labels: List[str] = None,
              epochs: int = 5, batch_size: int = 16, learning_rate: float = 2e-5):
        """Train the intent classification model"""

        # Fit label encoder on all labels (train + val) to avoid unseen labels
        all_labels = train_labels + (val_labels if val_labels else [])
        self.label_encoder.fit(all_labels)

        # Prepare training data
        train_encoded_labels = self.label_encoder.transform(train_labels)
        train_dataset = IntentDataset(train_texts, train_encoded_labels,
                                     self.tokenizer, self.max_length)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        n_classes = len(self.label_encoder.classes_)

        # Prepare validation data if provided
        val_loader = None
        if val_texts and val_labels:
            val_encoded_labels = self.label_encoder.transform(val_labels)
            val_dataset = IntentDataset(val_texts, val_encoded_labels,
                                       self.tokenizer, self.max_length)
            val_loader = DataLoader(val_dataset, batch_size=batch_size)

        # Initialize model
        self.model = IntentClassifier(n_classes, self.model_name).to(self.device)

        # Loss and optimizer with weight decay for regularization
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate, weight_decay=0.01)

        # Learning rate scheduler for better convergence
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=2)

        # Training loop
        best_val_accuracy = 0
        print(f"\nTraining for {epochs} epochs...")
        for epoch in range(epochs):
            self.model.train()
            train_loss = 0
            train_correct = 0
            train_total = 0

            for batch in train_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['label'].to(self.device)

                optimizer.zero_grad()
                outputs = self.model(input_ids, attention_mask)
                loss = criterion(outputs, labels)

                loss.backward()

                # Gradient clipping to prevent exploding gradients
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)

                optimizer.step()

                train_loss += loss.item()
                _, predicted = torch.max(outputs, 1)
                train_total += labels.size(0)
                train_correct += (predicted == labels).sum().item()

            train_accuracy = 100 * train_correct / train_total
            avg_train_loss = train_loss / len(train_loader)

            print(f"Epoch {epoch+1}/{epochs}")
            print(f"  Train Loss: {avg_train_loss:.4f}, Train Accuracy: {train_accuracy:.2f}%")

            # Validation
            if val_loader:
                val_loss, val_accuracy = self.evaluate(val_loader, criterion)
                print(f"  Val Loss: {val_loss:.4f}, Val Accuracy: {val_accuracy:.2f}%")

                # Update learning rate based on validation accuracy
                scheduler.step(val_accuracy)

                # Save best model
                if val_accuracy > best_val_accuracy:
                    best_val_accuracy = val_accuracy
                    print(f"  🎯 New best validation accuracy: {val_accuracy:.2f}%")

        print(f"\n✓ Training completed! Best validation accuracy: {best_val_accuracy:.2f}%")

    def evaluate(self, data_loader, criterion):
        """Evaluate model on validation/test data"""
        self.model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for batch in data_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['label'].to(self.device)

                outputs = self.model(input_ids, attention_mask)
                loss = criterion(outputs, labels)

                val_loss += loss.item()
                _, predicted = torch.max(outputs, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()

        accuracy = 100 * val_correct / val_total
        avg_loss = val_loss / len(data_loader)

        return avg_loss, accuracy

    def predict(self, text: str, return_confidence: bool = False) -> str or Tuple[str, float]:
        """Predict intent for a single text"""
        self.model.eval()

        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )

        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids, attention_mask)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)

        predicted_label = self.label_encoder.inverse_transform([predicted.item()])[0]

        if return_confidence:
            return predicted_label, confidence.item()
        else:
            return predicted_label

    def predict_top_k(self, text: str, k: int = 3) -> List[Tuple[str, float]]:
        """Predict top k intents with confidence scores"""
        self.model.eval()

        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )

        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids, attention_mask)
            probabilities = torch.softmax(outputs, dim=1)
            top_probs, top_indices = torch.topk(probabilities, k)

        results = []
        for prob, idx in zip(top_probs[0], top_indices[0]):
            label = self.label_encoder.inverse_transform([idx.item()])[0]
            results.append((label, prob.item()))

        return results

    def save_model(self, save_dir: str):
        """Save model and label encoder"""
        os.makedirs(save_dir, exist_ok=True)

        # Save model
        torch.save(self.model.state_dict(), f"{save_dir}/intent_model.pt")

        # Save label encoder
        with open(f"{save_dir}/label_encoder.pkl", 'wb') as f:
            pickle.dump(self.label_encoder, f)

        # Save config
        config = {
            'model_name': self.model_name,
            'max_length': self.max_length,
            'n_classes': len(self.label_encoder.classes_)
        }
        with open(f"{save_dir}/config.pkl", 'wb') as f:
            pickle.dump(config, f)

        print(f"Model saved to {save_dir}")

    def load_model(self, save_dir: str):
        """Load trained model"""
        # Load config
        with open(f"{save_dir}/config.pkl", 'rb') as f:
            config = pickle.load(f)

        # Load label encoder
        with open(f"{save_dir}/label_encoder.pkl", 'rb') as f:
            self.label_encoder = pickle.load(f)

        # Initialize and load model
        self.model = IntentClassifier(config['n_classes'], config['model_name']).to(self.device)
        self.model.load_state_dict(torch.load(f"{save_dir}/intent_model.pt", map_location=self.device))
        self.model.eval()

        print(f"Model loaded from {save_dir}")


if __name__ == "__main__":
    print("Intent Classification Model Module")
    print("This module should be imported and used with the data loader")

"""
MANO Component 2: Data Fusion & Medical Rule Engine
Combines component1 static profiles (CTGAN) with dynamic rhythms (TimeGAN).
Applies medical domain logic to generate Ground Truth Risk Labels.

Creates: data/component1/synthetic_labeled_dataset.npz
Ready for: LSTM Risk Prediction Training
"""

import numpy as np
import pandas as pd
import json
import sys
import os
from pathlib import Path
from sklearn.preprocessing import LabelEncoder

# --- SETUP PATHS ---
# We need to reach back to the GAN component to find the config
# Current: ml-services/privacy-preserving-lstm/src
# Target:  ml-services/privacy-preserving-gan/config
current_dir = Path(__file__).resolve().parent
gan_config_path = current_dir.parent.parent / "privacy-preserving-gan" / "config"
sys.path.append(str(gan_config_path))

try:
    import config
    print("✅ Configuration imported from GAN component")
except ImportError:
    print("⚠️ WARNING: Could not import central config. Using default paths.")

class MedicalRuleEngine:
    """
    Rule-based risk classification using medical domain knowledge.
    
    Risk Labels:
    0 = Low Risk (Healthy)
    1 = Medium Risk (Monitor)
    2 = High Risk (Intervention)
    """
    
    # Thresholds (Based on normalized 0-1 values)
    HIGH_STRESS_THRESHOLD = 0.70
    MEDIUM_STRESS_THRESHOLD = 0.60
    HIGH_STRESS_SLEEP_THRESHOLD = 0.40
    MEDIUM_STRESS_SLEEP_THRESHOLD = 0.50
    LOW_SLEEP_QUALITY_THRESHOLD = 0.35
    LOW_HR_STABILITY_THRESHOLD = 0.25
    
    @staticmethod
    def calculate_metrics(sequence):
        """
        Calculate health metrics from 7-day wearable sequence.
        Sequence Shape: (7, 4) -> [Sleep, Quality, HR, Stress]
        """
        metrics = {
            'avg_sleep': sequence[:, 0].mean(),
            'avg_quality': sequence[:, 1].mean(),
            'avg_hr': sequence[:, 2].mean(),
            'avg_stress': sequence[:, 3].mean(),
            'hr_std': sequence[:, 2].std(),  # HR Volatility
            'stress_volatility': sequence[:, 3].std(),
        }
        return metrics
    
    @classmethod
    def classify_risk(cls, sequence, static_profile=None):
        """
        Apply medical rules to classify risk level.
        Combines Dynamic Metrics (Wearables) + Static Metrics (History).
        """
        metrics = cls.calculate_metrics(sequence)
        
        avg_sleep = metrics['avg_sleep']
        avg_stress = metrics['avg_stress']
        avg_quality = metrics['avg_quality']
        hr_stability = 1.0 - metrics['hr_std'] # Inverse: Low std = High stability
        
        # --- 1. STATIC FACTORS (Multiplier Effect) ---
        risk_multiplier = 1.0
        if static_profile is not None:
            # If family history or treatment exists, lower the threshold for risk
            if static_profile.get('family_history', 0) == 1: risk_multiplier *= 0.9
            if static_profile.get('treatment', 0) == 1: risk_multiplier *= 0.9

        # --- 2. HIGH RISK RULES ---
        if avg_stress > (cls.HIGH_STRESS_THRESHOLD * risk_multiplier) and \
           avg_sleep < (cls.HIGH_STRESS_SLEEP_THRESHOLD / risk_multiplier):
            return 2, "High stress + low sleep"
        
        if hr_stability < cls.LOW_HR_STABILITY_THRESHOLD:
            return 2, "Critical heart rate instability"
        
        if avg_stress > cls.HIGH_STRESS_THRESHOLD and avg_quality < 0.3:
            return 2, "High stress + poor sleep quality"
        
        # --- 3. MEDIUM RISK RULES ---
        if avg_stress > cls.MEDIUM_STRESS_THRESHOLD:
            return 1, "Elevated stress levels"
        
        if avg_quality < cls.LOW_SLEEP_QUALITY_THRESHOLD:
            return 1, "Poor sleep quality"
        
        if avg_sleep < 0.4:
            return 1, "Low sleep duration"
        
        # --- 4. LOW RISK ---
        return 0, "Healthy baseline"

class DataFusionPipeline:
    """
    Main pipeline: Merges Static + Dynamic Data, Applies Rules, Encoder, Saves Output.
    """
    
    def __init__(self):
        # Define paths explicitly relative to Project Root
        project_root = current_dir.parent.parent.parent # y4-research-project
        self.paths = {
            'synthetic_wearable': project_root / 'data/component1/synthetic_wearable_sequences.npz',
            'synthetic_static': project_root / 'data/component1/synthetic_mental_health_data_v1.csv',
            'output_data': project_root / 'data/component1/synthetic_labeled_dataset.npz',
            'report': project_root / 'ml-services/privacy-preserving-lstm/reports/data_fusion_report.json'
        }
        self.engine = MedicalRuleEngine()
        self.encoders = {} # Store label encoders for decoding later

    def load_data(self):
        """Load and validate all source files."""
        print("\n" + "="*70)
        print("STEP 1: LOADING ARTIFACTS")
        print("="*70)
        
        # 1. Dynamic Data (TimeGAN)
        if not self.paths['synthetic_wearable'].exists():
            raise FileNotFoundError(f"Missing TimeGAN output: {self.paths['synthetic_wearable']}")
        
        dynamic_data = np.load(self.paths['synthetic_wearable'])['sequences']
        print(f"✅ Dynamic Data (TimeGAN): {dynamic_data.shape}")
        
        # 2. Static Data (CTGAN)
        if not self.paths['synthetic_static'].exists():
            raise FileNotFoundError(f"Missing CTGAN output: {self.paths['synthetic_static']}")
            
        static_df = pd.read_csv(self.paths['synthetic_static'])
        print(f"✅ Static Data (CTGAN):   {static_df.shape}")
        
        # 3. Align Sizes
        n_samples = min(len(dynamic_data), len(static_df))
        dynamic_data = dynamic_data[:n_samples]
        static_df = static_df.iloc[:n_samples]
        print(f"🔗 Merging {n_samples} users...")
        
        return dynamic_data, static_df

    def encode_static_features(self, df):
        """
        LSTM cannot read strings like 'Male'. 
        We must encode categorical features into integers.
        """
        print("\n" + "="*70)
        print("STEP 2: ENCODING STATIC FEATURES")
        print("="*70)
        
        df_encoded = df.copy()
        
        for col in df_encoded.select_dtypes(include=['object']).columns:
            le = LabelEncoder()
            # Convert to string to handle mixed types safely
            df_encoded[col] = le.fit_transform(df_encoded[col].astype(str))
            self.encoders[col] = le
            # print(f"   Encoded {col}: {len(le.classes_)} classes")
            
        print(f"✅ Static features encoded successfully.")
        return df_encoded

    def generate_labels(self, dynamic_data, static_df):
        """Apply medical rules to generate 'Ground Truth'."""
        print("\n" + "="*70)
        print("STEP 3: GENERATING RISK LABELS")
        print("="*70)
        
        n_samples = len(dynamic_data)
        labels = np.zeros(n_samples, dtype=int)
        reasons = []
        
        # Pre-calculate simplified static dicts for speed
        # (Converting DataFrame rows to dict is slow in loops)
        print(f"Classifying {n_samples} component1 patients...")
        
        for i in range(n_samples):
            # Extract static risk factors (using raw dataframe before encoding for logic)
            # We look for specific keywords in the raw data
            static_profile = {
                'family_history': 1 if static_df.iloc[i]['family_history'] == 'Yes' else 0,
                'treatment': 1 if static_df.iloc[i]['treatment'] == 'Yes' else 0
            }
            
            risk, reason = self.engine.classify_risk(dynamic_data[i], static_profile)
            labels[i] = risk
            reasons.append(reason)
            
            if (i+1) % 2500 == 0:
                print(f"   Processed {i+1}/{n_samples}...")
                
        # Stats
        unique, counts = np.unique(labels, return_counts=True)
        print(f"\n✅ Label Distribution:")
        for label, count in zip(unique, counts):
            name = ["Low", "Medium", "High"][label]
            print(f"   {name} ({label}): {count} ({count/n_samples:.1%})")
            
        return labels, reasons

    def save_and_report(self, X_dynamic, X_static, y, feature_names):
        """Save final fused dataset and JSON report."""
        print("\n" + "="*70)
        print("STEP 4: SAVING ARTIFACTS")
        print("="*70)
        
        # 1. Save .npz
        # Use standard ML naming: X_dynamic (Time), X_static (Features), y (Labels)
        output_path = self.paths['output_data']
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        np.savez_compressed(
            output_path,
            X_dynamic=X_dynamic,
            X_static=X_static,
            y=y,
            feature_names=feature_names
        )
        
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"💾 Saved Dataset: {output_path}")
        print(f"   Size: {size_mb:.2f} MB")
        
        # 2. Save Report
        report_path = self.paths['report']
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            'timestamp': str(pd.Timestamp.now()),
            'samples': len(y),
            'shapes': {
                'X_dynamic': str(X_dynamic.shape),
                'X_static': str(X_static.shape),
                'y': str(y.shape)
            },
            'class_balance': {
                'low_risk': int((y==0).sum()),
                'medium_risk': int((y==1).sum()),
                'high_risk': int((y==2).sum())
            },
            'status': 'READY_FOR_LSTM'
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"📄 Saved Report: {report_path}")

    def run(self):
        """Execute pipeline."""
        print("\n" + "█"*70)
        print("█ MANO COMPONENT 2: DATA FUSION PIPELINE")
        print("█"*70)
        
        try:
            # 1. Load
            dynamic_data, static_df_raw = self.load_data()
            
            # 2. Encode Static (Keep raw for rule logic inside generate_labels if needed, 
            # but usually we pass specific dicts. Here we encode first for X_static output)
            # Note: We need raw values for the rule engine logic (e.g. "Yes"/"No"),
            # so we generate labels using raw_df BEFORE encoding it for the output.
            
            # 3. Label (Using Raw Static Data for readability in logic)
            y, reasons = self.generate_labels(dynamic_data, static_df_raw)
            
            # 4. Encode (Prepare for LSTM input)
            static_df_encoded = self.encode_static_features(static_df_raw)
            X_static = static_df_encoded.values
            
            # 5. Save
            self.save_and_report(dynamic_data, X_static, y, list(static_df_encoded.columns))
            
            print("\n" + "█"*70)
            print("█ DATA FUSION COMPLETE ✅")
            print("█"*70)
            
        except Exception as e:
            print(f"\n❌ CRITICAL FAILURE: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    pipeline = DataFusionPipeline()
    pipeline.run()
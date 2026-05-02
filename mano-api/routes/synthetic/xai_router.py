"""
XAI (Explainable AI) — Router

Implements Integrated Gradients for the Hybrid LSTM Risk Predictor.
Explains WHY a patient is classified as Low/Medium/High risk by
attributing importance to each feature on each day.

WHAT IS INTEGRATED GRADIENTS?
It's a gradient-based attribution method that:
1. Defines a neutral "baseline" input (e.g., all zeros)
2. Creates N interpolation steps between baseline → actual input
3. Computes the model's gradient at each step
4. Averages the gradients
5. Multiplies by (input - baseline) to get attributions

The result tells you: "This feature on this day
pushed the prediction toward High risk by X amount."

WHY NOT SHAP?
- SHAP requires installing a heavy external library (shap or captum)
- Integrated Gradients is pure PyTorch — zero new dependencies
- For temporal models, IG produces cleaner per-timestep attributions

SAFETY: No model modifications. We just call model.forward() with
gradients enabled (torch.enable_grad) instead of the usual no_grad.
"""
from fastapi import APIRouter, HTTPException, Depends
import torch
import numpy as np

# --- Schemas ---
from schemas.synthetic.xai_schema import (
    XAIResponse,
    FeatureAttribution,
    FeatureSummary,
    StaticAttribution,
)
from schemas.synthetic.simulation_schema import (
    PatientState,
    RiskPredictionResponse,
    RiskLevel,
)

# --- Reuse existing helper ---
from routes.synthetic.simulation_router import parse_patient_state

# --- Services ---
from lib.synthetic.risk_service import RiskPredictionService

from core.logging import get_logger

logger = get_logger("xai_router")

router = APIRouter()

# Feature names in the same order as parse_patient_state
DYNAMIC_FEATURES = ["Sleep Duration", "Sleep Quality", "Heart Rate", "Stress Level"]
RISK_CLASSES = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}


def get_risk_service():
    return RiskPredictionService()


def integrated_gradients(
    model,
    dyn_tensor: torch.Tensor,
    stat_tensor: torch.Tensor,
    target_class: int,
    n_steps: int = 50,
    device: str = "cpu",
) -> tuple:
    """
    Computes Integrated Gradients for the Hybrid LSTM.

    Args:
        model: The RiskPredictionModel (LSTM)
        dyn_tensor: Dynamic input [1, 7, 4]
        stat_tensor: Static input [1, 20]
        target_class: Which output class to explain (0, 1, or 2)
        n_steps: Number of interpolation steps (more = more accurate, slower)
        device: CPU or CUDA

    Returns:
        (dyn_attributions, stat_attributions) — same shapes as inputs
    """
    # 1. Define baselines (zeros = "no signal")
    dyn_baseline = torch.zeros_like(dyn_tensor).to(device)
    stat_baseline = torch.zeros_like(stat_tensor).to(device)

    # 2. Create interpolation steps: baseline → input
    #    alpha goes from 0.0 to 1.0 in n_steps
    alphas = torch.linspace(0, 1, n_steps + 1).to(device)

    # 3. Accumulate gradients along the path
    dyn_grads_sum = torch.zeros_like(dyn_tensor)
    stat_grads_sum = torch.zeros_like(stat_tensor)

    # cuDNN's RNN kernels only support backward in training mode.
    # Temporarily disable cuDNN so PyTorch falls back to its own RNN
    # implementation, which supports backward in eval mode.
    # model.train() is NOT used here to avoid activating dropout/batchnorm noise.
    with torch.backends.cudnn.flags(enabled=False):
        model.eval()

        for alpha in alphas:
            # Interpolated input
            dyn_interp = dyn_baseline + alpha * (dyn_tensor - dyn_baseline)
            stat_interp = stat_baseline + alpha * (stat_tensor - stat_baseline)

            # Enable gradients for these inputs
            dyn_interp = dyn_interp.clone().detach().requires_grad_(True)
            stat_interp = stat_interp.clone().detach().requires_grad_(True)

            # Forward pass (with gradients enabled)
            logits = model(dyn_interp, stat_interp)
            target_score = logits[0, target_class]

            # Backward pass
            model.zero_grad()
            target_score.backward()

            # Accumulate gradients
            if dyn_interp.grad is not None:
                dyn_grads_sum += dyn_interp.grad.detach()
            if stat_interp.grad is not None:
                stat_grads_sum += stat_interp.grad.detach()

    # 4. Average gradients and multiply by (input - baseline)
    avg_dyn_grads = dyn_grads_sum / (n_steps + 1)
    avg_stat_grads = stat_grads_sum / (n_steps + 1)

    dyn_attributions = (dyn_tensor - dyn_baseline) * avg_dyn_grads
    stat_attributions = (stat_tensor - stat_baseline) * avg_stat_grads

    return dyn_attributions.detach().cpu().numpy(), stat_attributions.detach().cpu().numpy()


def build_explanation(
    risk_class: int,
    confidence: float,
    feature_rankings: list,
    dyn_attr: np.ndarray,
) -> str:
    """Generates a human-readable explanation string."""
    risk_names = {0: "Low", 1: "Medium", 2: "High"}
    risk_name = risk_names[risk_class]

    top_feature = feature_rankings[0] if feature_rankings else None
    second_feature = feature_rankings[1] if len(feature_rankings) > 1 else None

    explanation = f"The model predicts {risk_name} risk with {confidence:.0%} confidence. "

    if top_feature:
        # Find the most impactful day for the top feature
        feat_idx = DYNAMIC_FEATURES.index(top_feature.feature)
        day_attrs = dyn_attr[0, :, feat_idx]
        peak_day = int(np.argmax(np.abs(day_attrs))) + 1
        direction = "increases" if top_feature.direction == "risk-increasing" else "decreases"

        explanation += (
            f"The most influential factor is {top_feature.feature} "
            f"(especially Day {peak_day}), which {direction} predicted risk. "
        )

    if second_feature:
        explanation += (
            f"{second_feature.feature} is the second most important factor."
        )

    return explanation


# === ENDPOINT ===

@router.post("/explain_risk", response_model=XAIResponse)
async def explain_risk(
    state: PatientState,
    risk_service: RiskPredictionService = Depends(get_risk_service),
):
    """
    Explains a risk prediction using Integrated Gradients.

    Returns:
    - Temporal heatmap: per-day, per-feature attribution scores
    - Feature rankings: which features matter most overall
    - Static attributions: top demographic factor impacts
    - Human-readable explanation
    """
    if risk_service.model is None:
        raise HTTPException(status_code=503, detail="Risk model not loaded")

    logger.info("xai_explain_request")

    # Step 1: Parse patient state
    dyn_np, stat_np = parse_patient_state(state)

    # Step 2: Get the risk prediction first
    risk_result = risk_service.predict(dyn_np, stat_np)
    target_class = risk_result["risk_class"]

    # Step 3: Compute Integrated Gradients
    device = risk_service.device
    dyn_tensor = torch.FloatTensor(dyn_np).to(device)
    stat_tensor = torch.FloatTensor(stat_np).to(device)

    try:
        dyn_attr, stat_attr = integrated_gradients(
            model=risk_service.model,
            dyn_tensor=dyn_tensor,
            stat_tensor=stat_tensor,
            target_class=target_class,
            n_steps=50,
            device=device,
        )
    except Exception as e:
        logger.error("xai_computation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"XAI computation failed: {str(e)}")

    # Step 4: Build temporal attribution list (7 days × 4 features)
    # Normalize: find the max absolute attribution for scaling to [0, 1]
    max_abs = float(np.max(np.abs(dyn_attr))) if np.max(np.abs(dyn_attr)) > 0 else 1.0

    temporal_attributions = []
    for day in range(7):
        for feat_idx, feat_name in enumerate(DYNAMIC_FEATURES):
            raw = float(dyn_attr[0, day, feat_idx])
            temporal_attributions.append(FeatureAttribution(
                day=day + 1,
                feature=feat_name,
                attribution=round(raw, 6),
                normalized=round(abs(raw) / max_abs, 4),
            ))

    # Step 5: Aggregate feature importance (sum abs attributions per feature)
    feature_totals = {}
    feature_signs = {}
    for feat_idx, feat_name in enumerate(DYNAMIC_FEATURES):
        total = float(np.sum(np.abs(dyn_attr[0, :, feat_idx])))
        signed_sum = float(np.sum(dyn_attr[0, :, feat_idx]))
        feature_totals[feat_name] = total
        feature_signs[feat_name] = signed_sum

    # Sort by total importance
    sorted_features = sorted(feature_totals.items(), key=lambda x: x[1], reverse=True)

    feature_rankings = []
    for rank, (feat_name, total) in enumerate(sorted_features, 1):
        feature_rankings.append(FeatureSummary(
            feature=feat_name,
            total_attribution=round(total, 6),
            direction="risk-increasing" if feature_signs[feat_name] > 0 else "risk-decreasing",
            rank=rank,
        ))

    # Step 6: Static attributions (top 5 by absolute value)
    stat_max_abs = float(np.max(np.abs(stat_attr))) if np.max(np.abs(stat_attr)) > 0 else 1.0
    stat_indices = np.argsort(np.abs(stat_attr[0]))[::-1][:5]

    static_attributions = []
    for idx in stat_indices:
        raw = float(stat_attr[0, idx])
        static_attributions.append(StaticAttribution(
            feature_index=int(idx),
            attribution=round(raw, 6),
            normalized=round(abs(raw) / stat_max_abs, 4),
        ))

    # Step 7: Build risk prediction response
    risk_response = RiskPredictionResponse(
        current_risk_class=RISK_CLASSES[target_class],
        confidence=risk_result["confidence"],
        probabilities=risk_result["probabilities"],
    )

    # Step 8: Generate explanation
    explanation = build_explanation(
        target_class, risk_result["confidence"], feature_rankings, dyn_attr
    )

    logger.info(
        "xai_explain_complete",
        risk_class=target_class,
        top_feature=feature_rankings[0].feature if feature_rankings else "unknown",
    )

    return XAIResponse(
        risk_prediction=risk_response,
        temporal_attributions=temporal_attributions,
        feature_rankings=feature_rankings,
        static_attributions=static_attributions,
        explanation=explanation,
    )

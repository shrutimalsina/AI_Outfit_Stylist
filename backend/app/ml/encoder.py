"""Pinned CLIP image inference and embedding validation."""

import numpy as np

MODEL_ID = "openai/clip-vit-base-patch32"
MODEL_REVISION = "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"
DIMENSION = 512


def normalize(vectors):
    values = np.asarray(vectors, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] != DIMENSION or not np.isfinite(values).all():
        raise ValueError("Expected a finite matrix with 512 columns")
    norms = np.linalg.norm(values.astype(np.float64), axis=1, keepdims=True)
    if (norms == 0).any():
        raise ValueError("Zero embedding cannot be normalized")
    return (values / norms).astype(np.float32)


class ClipEncoder:
    def __init__(self, device="cpu"):
        import torch
        from transformers import CLIPImageProcessor, CLIPVisionModelWithProjection

        self.torch = torch
        self.device = device
        self.processor = CLIPImageProcessor.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
        self.model = CLIPVisionModelWithProjection.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, use_safetensors=False, weights_only=True,
        ).to(device).eval()

    def __call__(self, images):
        with self.torch.inference_mode():
            pixels = self.processor(images=images, return_tensors="pt").pixel_values
            output = self.model(pixel_values=pixels.to(self.device)).image_embeds
            return normalize(output.float().cpu().numpy())

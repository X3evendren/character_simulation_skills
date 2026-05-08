"""Transform private inner experience into external behavior."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExpressionPolicy:
    default_mask_text: str = "没事，你忙吧。"

    def compose(
        self,
        inner_items: list[dict],
        self_model: dict,
        proposed_text: str = "",
    ) -> dict:
        unexpressible = [
            item for item in inner_items
            if not item.get("expressible", True) and item.get("intensity", 0.0) >= 0.6
        ]
        if unexpressible:
            mask = self_model.get("active_mask", "")
            outer_text = self._masked_text(mask, proposed_text)
            return {
                "outer": {"type": "speech", "content": outer_text},
                "mechanism": "masking",
                "omitted": [item.get("content", "") for item in unexpressible],
                "inner_used": unexpressible,
            }
        text = proposed_text.strip() or self.default_mask_text
        return {
            "outer": {"type": "speech", "content": text},
            "mechanism": "direct_expression",
            "omitted": [],
            "inner_used": list(inner_items),
        }

    def _masked_text(self, mask: str, proposed_text: str) -> str:
        if "无所谓" in mask or "短句" in mask:
            return self.default_mask_text
        if "讽刺" in mask:
            return "行，你当然有你的理由。"
        return proposed_text.strip() or self.default_mask_text

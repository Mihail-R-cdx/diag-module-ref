"""Backward-compatible public Matrix handler name."""

import re
import time

from .matrix import ExtronMatrixHandler, resolve_matrix_capabilities


class ExtronIN1804Handler(ExtronMatrixHandler):
    """Historic import retained; identity selects an exact Matrix profile."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Preserve the direct IN1804 API's established route-read behaviour.
        # A full refresh always reads 1I and replaces this provisional profile.
        self.model = "IN1804"
        self.capabilities = resolve_matrix_capabilities(self.model)
        self.inputs_num = 4
        self.outputs_num = 1

    @staticmethod
    def _parse_current_connection(response, inputs_num):
        if not isinstance(response, str) or not isinstance(inputs_num, int) or inputs_num < 1:
            return None
        lines = [line.strip() for line in response.replace("\r", "\n").split("\n") if line.strip()]
        if lines[:1] == ["!"]: lines.pop(0)
        if len(lines) != 1: return None
        match = re.fullmatch(r"(?:([1-9]\d*)|In([1-9]\d*) All)", lines[0])
        value = int(match.group(1) or match.group(2)) if match else None
        return value if value is not None and value <= inputs_num else None

    def get_hdcp_info(self):
        """Keep the legacy standalone IN1804 list-shaped diagnostic API."""
        if self.model != "IN1804":
            return super().get_hdcp_info()
        auth, states = [], []
        for item in range(1, int(self.inputs_num or 0) + 1):
            value = self.send_command("wE%sHDCP" % item).get("response", "")
            auth.append(int(value) if str(value).strip().isdigit() else 0)
            states.append(self.send_command("wI%sHDCP" % item).get("response") or None)
            time.sleep(.2)
        output = self.send_command("wO1HDCP").get("response") or None
        return {"input_auth": auth, "input_status": states, "output_status": output}

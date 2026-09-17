"""Backward-compatible public Matrix handler name."""

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

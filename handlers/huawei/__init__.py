# Импортируем классы после того, как они определены
from .te20 import HuaweiTE20Handler
from .te40 import HuaweiTE40Handler
from .box300 import CloudLinkBox300Handler
from .bar310 import CloudLinkBar310Handler

__all__ = [
    'HuaweiTE20Handler',
    'HuaweiTE40Handler',
    'CloudLinkBox300Handler',
    'CloudLinkBar310Handler'
]

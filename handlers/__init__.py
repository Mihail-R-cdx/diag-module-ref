"""Handler package exports with lazy imports."""

__all__ = [
    "HuaweiTE20Handler",
    "HuaweiTE40Handler",
    "CloudLinkBox300Handler",
    "CloudLinkBar310Handler",
    "PolycomRPG310Handler",
    "BiampTesiraForteCIHandler",
    "aten",
]


def __getattr__(name):
    if name in {
        "HuaweiTE20Handler",
        "HuaweiTE40Handler",
        "CloudLinkBox300Handler",
        "CloudLinkBar310Handler",
    }:
        from handlers.huawei import (
            CloudLinkBar310Handler,
            CloudLinkBox300Handler,
            HuaweiTE20Handler,
            HuaweiTE40Handler,
        )

        return {
            "HuaweiTE20Handler": HuaweiTE20Handler,
            "HuaweiTE40Handler": HuaweiTE40Handler,
            "CloudLinkBox300Handler": CloudLinkBox300Handler,
            "CloudLinkBar310Handler": CloudLinkBar310Handler,
        }[name]
    if name == "PolycomRPG310Handler":
        from handlers.polycom import PolycomRPG310Handler

        return PolycomRPG310Handler
    if name == "BiampTesiraForteCIHandler":
        from handlers.biamp import BiampTesiraForteCIHandler

        return BiampTesiraForteCIHandler
    if name == "aten":
        from importlib import import_module

        return import_module("handlers.aten")
    raise AttributeError(name)

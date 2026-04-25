"""Compatibility alias for the Hyundai-Kia-Connect/kia_uvo mapped adapter."""

from .hyundai_kia_connect_kia_uvo import (
    HyundaiKiaConnectKiaUvoVehicleAdapter,
)

KiaUvoVehicleAdapter = HyundaiKiaConnectKiaUvoVehicleAdapter

__all__ = [
    "HyundaiKiaConnectKiaUvoVehicleAdapter",
    "KiaUvoVehicleAdapter",
]

"""Thin mapped adapter for Hyundai-Kia-Connect/kia_uvo."""

from __future__ import annotations

from .mapped import MappedVehicleAdapter


class HyundaiKiaConnectKiaUvoVehicleAdapter(MappedVehicleAdapter):
    """Thin kia_uvo adapter that delegates mapping to the generic mapped adapter."""

    mapping_name = "hyundai_kia_connect_kia_uvo"
    friendly_name = "Hyundai / Kia Connect"

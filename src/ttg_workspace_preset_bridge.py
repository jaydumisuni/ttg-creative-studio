#!/usr/bin/env python3
"""Workspace bridge for Advanced Mode preset application.

Kept separate from the large workspace module so preset wiring can be tested and
maintained safely. The main workspace should call install_preset_bridge(self)
after creating AdvancedModePanel.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox

from ttg_preset_actions import PresetActions


LAYER_PRESET_GROUPS = {"Text Material", "Effects"}
PROJECT_PRESET_GROUPS = {"Scene", "Motion", "Export"}


def install_preset_bridge(workspace) -> None:  # noqa: ANN001
    workspace.preset_actions = getattr(workspace, "preset_actions", PresetActions())
    if hasattr(workspace, "advanced") and hasattr(workspace.advanced, "presetRequested"):
        workspace.advanced.presetRequested.connect(lambda group, preset_id: apply_advanced_preset(workspace, group, preset_id))


def apply_advanced_preset(workspace, group: str, preset_id: str) -> None:  # noqa: ANN001
    if workspace.project is None:
        workspace.new_project()
    if workspace.project is None:
        return
    actions = getattr(workspace, "preset_actions", PresetActions())
    workspace.preset_actions = actions

    if group in LAYER_PRESET_GROUPS:
        if not workspace.selected_layer_id:
            QMessageBox.information(workspace, "Advanced Preset", "Select a layer first for this preset.")
            return
        workspace.remember(f"advanced preset {preset_id}")
        actions.apply_to_layer(workspace.project, workspace.selected_layer_id, preset_id)
        workspace.status.setText(f"Applied layer preset: {preset_id}")
    elif group == "Scene":
        workspace.remember(f"scene preset {preset_id}")
        actions.apply_scene_preset(workspace.project, preset_id)
        workspace.status.setText(f"Applied scene preset: {preset_id}")
    elif group == "Motion":
        workspace.remember(f"motion preset {preset_id}")
        actions.apply_motion_preset(workspace.project, preset_id)
        workspace.status.setText(f"Applied motion preset: {preset_id}")
    elif group == "Export":
        workspace.remember(f"export preset {preset_id}")
        actions.apply_export_preset(workspace.project, preset_id)
        workspace.status.setText(f"Applied export preset: {preset_id}")
    else:
        QMessageBox.information(workspace, "Advanced Preset", f"Unknown preset group: {group}")
        return
    workspace.refresh_all()

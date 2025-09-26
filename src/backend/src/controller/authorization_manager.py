import json
from typing import Dict, List, Optional
from collections import defaultdict

from src.controller.settings_manager import SettingsManager
from src.models.settings import AppRole
from src.common.features import FeatureAccessLevel, ACCESS_LEVEL_ORDER, get_feature_config
from src.common.logging import get_logger

logger = get_logger(__name__)

class AuthorizationManager:
    def __init__(self, settings_manager: SettingsManager):
        """Requires SettingsManager to access role configurations."""
        self._settings_manager = settings_manager

    def get_user_effective_permissions(self, user_groups: Optional[List[str]], team_role_override: Optional[str] = None) -> Dict[str, FeatureAccessLevel]:
        """
        Calculates the effective permission level for each feature based on the user's groups and team role overrides.
        Permissions are merged by taking the highest level granted by any matching role.
        Team role overrides take precedence over group-based roles.

        Args:
            user_groups: A list of group names the user belongs to.
            team_role_override: Optional team role that overrides group-based permissions.

        Returns:
            A dictionary mapping feature IDs to the highest granted FeatureAccessLevel.
        """
        if not user_groups:
            user_groups = []
            logger.warning("Received empty or None user_groups for permission calculation.") # Log if groups are empty
        else:
            logger.debug(f"Calculating effective permissions for user groups: {user_groups}") # Log received groups

        user_group_set = set(user_groups)
        effective_permissions: Dict[str, FeatureAccessLevel] = defaultdict(lambda: FeatureAccessLevel.NONE)

        # Log before fetching roles
        logger.debug("Fetching all application roles from SettingsManager...")
        all_roles = self._settings_manager.list_app_roles() # Fetches roles from DB via SettingsManager
        logger.debug(f"Fetched {len(all_roles)} roles total.")

        feature_config = get_feature_config()

        # If team role override is provided, prioritize it
        if team_role_override:
            logger.debug(f"Processing team role override: {team_role_override}")
            team_role = next((role for role in all_roles if role.name == team_role_override), None)
            if team_role:
                logger.debug(f"Found team role '{team_role_override}' in roles, applying as override")
                for feature_id, assigned_level in team_role.feature_permissions.items():
                    if feature_id in feature_config:
                        effective_permissions[feature_id] = assigned_level
                        logger.debug(f"Applied team role override for '{feature_id}': {assigned_level.value}")
                    else:
                        logger.warning(f"Team role '{team_role_override}' contains permission for unknown feature ID '{feature_id}'. Skipping.")

                # Return team role permissions (team override takes full precedence)
                for feature_id in feature_config:
                    if feature_id not in effective_permissions:
                        effective_permissions[feature_id] = FeatureAccessLevel.NONE

                final_perms_str = {k: v.value for k, v in effective_permissions.items()}
                logger.debug(f"Final permissions using team role override '{team_role_override}': {final_perms_str}")
                return dict(effective_permissions)
            else:
                logger.warning(f"Team role override '{team_role_override}' not found in available roles. Falling back to group-based permissions.")

        matching_roles = []
        logger.debug("Identifying matching roles based on group intersection...")
        for role in all_roles:
            role_assigned_groups_set = set(role.assigned_groups or []) # Ensure it's a set, handle None
            # Check for intersection
            if user_group_set.intersection(role_assigned_groups_set):
                matching_roles.append(role)
                logger.debug(f"  MATCH FOUND: User group(s) {list(user_group_set.intersection(role_assigned_groups_set))} match role: '{role.name}' (Assigned: {role.assigned_groups})")
            # else: 
            #    logger.debug(f"  NO MATCH: User groups {list(user_group_set)} vs Role '{role.name}' groups {list(role_assigned_groups_set)}")

        if not matching_roles:
            logger.warning(f"No matching roles found for user groups: {user_groups}. Returning NONE access for all features.")
            return {feat_id: FeatureAccessLevel.NONE for feat_id in feature_config}

        logger.debug(f"Merging permissions from {len(matching_roles)} matching roles...")
        # Merge permissions from matching roles
        for role in matching_roles:
            logger.debug(f"Processing permissions from role: '{role.name}'")
            for feature_id, assigned_level in role.feature_permissions.items():
                if feature_id not in feature_config:
                    logger.warning(f"Role '{role.name}' contains permission for unknown feature ID '{feature_id}'. Skipping.")
                    continue

                current_effective_level = effective_permissions[feature_id]
                # Compare levels using the defined order
                if ACCESS_LEVEL_ORDER[assigned_level] > ACCESS_LEVEL_ORDER[current_effective_level]:
                    effective_permissions[feature_id] = assigned_level
                    logger.debug(f"  Updated effective permission for '{feature_id}' to '{assigned_level.value}' (was '{current_effective_level.value}') from role '{role.name}'")
                # else:
                #    logger.debug(f"  Keeping existing permission for '{feature_id}' ('{current_effective_level.value}') - Role '{role.name}' level ('{assigned_level.value}') is not higher.")

        # Ensure all features have at least NONE permission defined
        for feature_id in feature_config:
            if feature_id not in effective_permissions:
                effective_permissions[feature_id] = FeatureAccessLevel.NONE

        # Log the final permissions
        final_perms_str = {k: v.value for k, v in effective_permissions.items()}
        logger.debug(f"Final calculated effective permissions: {final_perms_str}")
        return dict(effective_permissions)

    def has_permission(self, effective_permissions: Dict[str, FeatureAccessLevel], feature_id: str, required_level: FeatureAccessLevel) -> bool:
        """
        Checks if the user's effective permissions meet the required level for a specific feature.

        Args:
            effective_permissions: The user's calculated effective permissions.
            feature_id: The ID of the feature to check.
            required_level: The minimum FeatureAccessLevel required.

        Returns:
            True if the user has sufficient permission, False otherwise.
        """
        user_level = effective_permissions.get(feature_id, FeatureAccessLevel.NONE)
        has_perm = ACCESS_LEVEL_ORDER[user_level] >= ACCESS_LEVEL_ORDER[required_level]
        logger.debug(f"Permission check for feature '{feature_id}': Required='{required_level.value}', User has='{user_level.value}'. Granted: {has_perm}")
        return has_perm 
import logging
import voluptuous as vol
import fnmatch

from homeassistant.const import CONF_NAME, CONF_ENTITIES
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

DOMAIN = "auto_group"
_LOGGER = logging.getLogger(__name__)

CONF_GROUPS = "groups"
CONF_INCLUDE = "include"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        CONF_GROUPS: vol.Schema({
            cv.slug: vol.Schema({
                vol.Optional(CONF_NAME): cv.string,
                vol.Required(CONF_INCLUDE): dict
            })
        })
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Set up the Auto Group component."""
    conf = config.get(DOMAIN, {})
    groups_conf = conf.get(CONF_GROUPS, {})

    if not groups_conf:
        _LOGGER.warning("No groups defined in auto_group config.")
        return True

    entity_reg = er.async_get(hass)

    for group_id, group_cfg in groups_conf.items():
        name = group_cfg.get(CONF_NAME, group_id.replace('_', ' ').title())
        include = group_cfg.get(CONF_INCLUDE, {})

        _LOGGER.info(f"Creating group {group_id} with name {name}")

        # Match entities from registry
        matched_entities = _find_matching_entities(entity_reg, include)

        if not matched_entities:
            _LOGGER.warning(f"No entities found matching for group: {group_id}")

        # Create the group dynamically
        hass.services.call(
            "group", "set", {
                "object_id": group_id,
                "name": name,
                "entities": matched_entities
            }
        )

        _LOGGER.info(f"Group {group_id} created with {len(matched_entities)} entities.")

    return True


def _find_matching_entities(entity_reg, include_filters):
    """Find entities that match include filters."""
    entities = []

    for entity_id, entity_entry in entity_reg.entities.items():
        if not _match_filters(entity_id, entity_entry, include_filters):
            continue
        entities.append(entity_id)

    return entities


def _match_filters(entity_id, entity_entry, filters):
    """Check if an entity matches the provided filters."""
    # Match domain
    domain_filter = filters.get('domain')
    if domain_filter and not entity_id.startswith(f"{domain_filter}."):
        return False

    # Match entity_id pattern
    entity_id_filter = filters.get('entity_id')
    if entity_id_filter:
        # Use fnmatch for wildcard matching
        if not fnmatch.fnmatch(entity_id, f"{entity_id_filter}"):
            return False

    # Match device_class (if entity has one)
    device_class_filter = filters.get('device_class')
    if device_class_filter:
        if entity_entry.device_class != device_class_filter:
            return False

    return True

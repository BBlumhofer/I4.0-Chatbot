"""
Neo4j tools for the **Nameplate** submodel.

Covers: manufacturer info, serial number, hardware/software versions.
Semantic ID: https://admin-shell.io/idta/nameplate/3/0/Nameplate
"""
from __future__ import annotations

from typing import Any, Optional

from app.services import neo4j_service as db
from app.tools.neo4j._base import SubmodelToolset, register_submodel


def _asset_match_clause() -> str:
    """Return a WHERE-clause that accepts id and globalAssetId variants."""
    return """
    WHERE a.id = $asset_id
       OR a.globalAssetId = $asset_id
       OR a.globalAssetId = replace($asset_id, '/asset/', '/assets/')
       OR a.globalAssetId = replace($asset_id, '/assets/', '/asset/')
    """


def _get_nameplate_elements(asset_id: str, id_short: Optional[str] = None) -> list[dict[str, Any]]:
    """Query Nameplate elements, optionally filtered by element idShort."""
    cypher = f"""
    MATCH (a:Asset)
    {_asset_match_clause()}
    WITH a LIMIT 1
    MATCH (a)
          <-[:DESCRIBES_ASSET]-(s:Shell)
          -[:HAS_SUBMODEL]->(sm:Submodel {{idShort: 'Nameplate'}})
          -[:HAS_ELEMENT]->(el)
    WHERE $id_short IS NULL OR el.idShort = $id_short
    RETURN el.idShort AS idShort, el.value AS value,
           el.valueType AS valueType, labels(el) AS elementTypes
    """
    return db.run_query(cypher, {"asset_id": asset_id, "id_short": id_short})


    def _get_nameplate_elements_by_parent(asset_id: str, parent_id_short: str) -> list[dict[str, Any]]:
        """Query Nameplate elements by parent container idShort."""
        cypher = f"""
        MATCH (a:Asset)
        {_asset_match_clause()}
        WITH a LIMIT 1
        MATCH (a)
            <-[:DESCRIBES_ASSET]-(s:Shell)
            -[:HAS_SUBMODEL]->(:Submodel {{idShort: 'Nameplate'}})
            -[:HAS_ELEMENT]->(root)
        MATCH (root)-[:HAS_ELEMENT*0..]->(parent {{idShort: $parent_id_short}})
        MATCH (parent)-[:HAS_ELEMENT]->(el)
        RETURN el.idShort AS idShort,
             el.value AS value,
             el.valueType AS valueType,
             labels(el) AS elementTypes,
             parent.idShort AS parentIdShort
        """
        return db.run_query(cypher, {"asset_id": asset_id, "parent_id_short": parent_id_short})


def get_nameplate(asset_id: str) -> list[dict[str, Any]]:
    """Return all Nameplate elements for an asset."""
    return _get_nameplate_elements(asset_id)


def get_nameplate_element(asset_id: str, element_id_short: str) -> list[dict[str, Any]]:
    """Return one specific Nameplate element by idShort."""
    return _get_nameplate_elements(asset_id, element_id_short)


def get_date_of_manufacture(asset_id: str) -> list[dict[str, Any]]:
    """Return DateOfManufacture from Nameplate."""
    return _get_nameplate_elements(asset_id, "DateOfManufacture")


def get_manufacturer_name(asset_id: str) -> list[dict[str, Any]]:
    """Return ManufacturerName from Nameplate."""
    return _get_nameplate_elements(asset_id, "ManufacturerName")


def get_hardware_version(asset_id: str) -> list[dict[str, Any]]:
    """Return HardwareVersion from Nameplate."""
    return _get_nameplate_elements(asset_id, "HardwareVersion")


def get_software_version(asset_id: str) -> list[dict[str, Any]]:
    """Return SoftwareVersion from Nameplate."""
    return _get_nameplate_elements(asset_id, "SoftwareVersion")


def get_uri_of_the_product(asset_id: str) -> list[dict[str, Any]]:
    """Return URIOfTheProduct from Nameplate."""
    return _get_nameplate_elements(asset_id, "URIOfTheProduct")


def get_country_of_origin(asset_id: str) -> list[dict[str, Any]]:
    """Return CountryOfOrigin from Nameplate."""
    return _get_nameplate_elements(asset_id, "CountryOfOrigin")


def get_year_of_construction(asset_id: str) -> list[dict[str, Any]]:
    """Return YearOfConstruction from Nameplate."""
    return _get_nameplate_elements(asset_id, "YearOfConstruction")


def get_manufacturer_product_type(asset_id: str) -> list[dict[str, Any]]:
    """Return ManufacturerProductType from Nameplate."""
    return _get_nameplate_elements(asset_id, "ManufacturerProductType")


def get_manufacturer_product_family(asset_id: str) -> list[dict[str, Any]]:
    """Return ManufacturerProductFamily from Nameplate."""
    return _get_nameplate_elements(asset_id, "ManufacturerProductFamily")


def get_manufacturer_product_root(asset_id: str) -> list[dict[str, Any]]:
    """Return ManufacturerProductRoot from Nameplate."""
    return _get_nameplate_elements(asset_id, "ManufacturerProductRoot")


def get_manufacturer_product_designation(asset_id: str) -> list[dict[str, Any]]:
    """Return ManufacturerProductDesignation from Nameplate."""
    return _get_nameplate_elements(asset_id, "ManufacturerProductDesignation")


def list_address_information(asset_id: str) -> list[dict[str, Any]]:
    """Return direct fields from AddressInformation as one consolidated tool."""
    return _get_nameplate_elements_by_parent(asset_id, "AddressInformation")


def list_contact_channels(asset_id: str) -> list[dict[str, Any]]:
    """Return contact channel fields from Phone, Email and Fax containers."""
    results: list[dict[str, Any]] = []
    for parent in ("Phone", "Email", "Fax"):
        results.extend(_get_nameplate_elements_by_parent(asset_id, parent))
    return results


# Alias – same data, explicit intent name for the fallback
get_properties = get_nameplate


register_submodel(SubmodelToolset(
    idShort="Nameplate",
    semantic_id="https://admin-shell.io/idta/nameplate/3/0/Nameplate",
    description="Typschild: Hersteller, Seriennummer, Hardware-/Softwareversion",
    tools={
        "get_nameplate": get_nameplate,
        "get_nameplate_element": get_nameplate_element,
        "get_date_of_manufacture": get_date_of_manufacture,
        "get_manufacturer_name": get_manufacturer_name,
        "get_hardware_version": get_hardware_version,
        "get_software_version": get_software_version,
        "get_uri_of_the_product": get_uri_of_the_product,
        "get_country_of_origin": get_country_of_origin,
        "get_year_of_construction": get_year_of_construction,
        "get_manufacturer_product_type": get_manufacturer_product_type,
        "get_manufacturer_product_family": get_manufacturer_product_family,
        "get_manufacturer_product_root": get_manufacturer_product_root,
        "get_manufacturer_product_designation": get_manufacturer_product_designation,
        "list_address_information": list_address_information,
        "list_contact_channels": list_contact_channels,
        "get_manufacture_date": get_date_of_manufacture,
        "get_product_uri": get_uri_of_the_product,
        "get_properties": get_properties,
    },
))



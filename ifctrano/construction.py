import logging
from typing import List, Optional

from ifcopenshell import file, entity_instance

from pydantic import BaseModel
from trano.elements.construction import (  # type: ignore
    Material,
    Layer,
    Construction,
    GlassMaterial,
    Gas,
    Glass,
    GlassLayer,
    GasLayer,
)
from ifctrano.utils import remove_non_alphanumeric, generate_alphanumeric_uuid

logger = logging.getLogger(__name__)


DEFAULT_MATERIAL = {
    "thermal_conductivity": 0.046,
    "specific_heat_capacity": 940,
    "density": 80,
}


material_1 = Material(
    name="material_1",
    thermal_conductivity=0.046,
    specific_heat_capacity=940,
    density=80,
)
default_construction = Construction(
    name="default_construction",
    layers=[
        Layer(material=material_1, thickness=0.18),
    ],
)
id_100 = GlassMaterial(
    name="id_100",
    thermal_conductivity=1,
    density=2500,
    specific_heat_capacity=840,
    solar_transmittance=[0.646],
    solar_reflectance_outside_facing=[0.062],
    solar_reflectance_room_facing=[0.063],
    infrared_transmissivity=0,
    infrared_absorptivity_outside_facing=0.84,
    infrared_absorptivity_room_facing=0.84,
)
air = Gas(
    name="Air",
    thermal_conductivity=0.025,
    density=1.2,
    specific_heat_capacity=1005,
)
glass = Glass(
    name="double_glazing",
    u_value_frame=1.4,
    layers=[
        GlassLayer(thickness=0.003, material=id_100),
        GasLayer(thickness=0.0127, material=air),
        GlassLayer(thickness=0.003, material=id_100),
    ],
)


class MaterialId(Material):  # type: ignore
    id: int

    def to_material(self) -> Material:
        return Material.model_validate(self.model_dump(exclude={"id"}))


class LayerId(Layer):  # type: ignore
    id: int

    def to_layer(self) -> Layer:
        return Layer.model_validate(self.model_dump(exclude={"id"}))


class ConstructionId(Construction):  # type: ignore
    id: int

    def to_construction(self) -> Construction:
        return Construction.model_validate(self.model_dump(exclude={"id"}))


class Materials(BaseModel):
    materials: List[MaterialId]

    @classmethod
    def from_ifc(cls, ifc_file: file) -> "Materials":
        materials = ifc_file.by_type("IfcMaterial")
        return cls.from_ifc_materials(materials)

    @classmethod
    def from_ifc_materials(cls, ifc_materials: List[entity_instance]) -> "Materials":
        materials = []
        for material in ifc_materials:
            material_name = remove_non_alphanumeric(material.Name)
            materials.append(
                MaterialId.model_validate(
                    {"name": material_name, "id": material.id(), **DEFAULT_MATERIAL}
                )
            )
        return cls(materials=materials)

    def get_material(self, id: int) -> Material:
        for material in self.materials:
            if material.id == id:
                return material.to_material()
        raise ValueError(f"Material {id} not found in materials list.")


def _get_unit_factor(ifc_file: file) -> float:
    length_unit = next(
        unit for unit in ifc_file.by_type("IfcSiUnit") if unit.UnitType == "LENGTHUNIT"
    )
    if length_unit.Prefix == "MILLI" and length_unit.Name == "METRE":
        return 0.001
    return 1


class Layers(BaseModel):
    layers: List[LayerId]

    @classmethod
    def from_ifc(cls, ifc_file: file, materials: Materials) -> "Layers":
        material_layers = ifc_file.by_type("IfcMaterialLayer")
        unit_factor = _get_unit_factor(ifc_file)
        return cls.from_ifc_material_layers(
            material_layers, materials, unit_factor=unit_factor
        )

    @classmethod
    def from_ifc_material_layers(
        cls,
        ifc_material_layers: List[entity_instance],
        materials: Materials,
        unit_factor: float = 1,
    ) -> "Layers":
        layers = []
        for layer in ifc_material_layers:
            thickness = layer.LayerThickness * unit_factor
            layers.append(
                LayerId(
                    id=layer.id(),
                    thickness=thickness,
                    material=materials.get_material(layer.Material.id()),
                )
            )
        return cls(layers=layers)

    def from_ids(self, ids: List[int]) -> List[Layer]:
        return [layer.to_layer() for layer in self.layers if layer.id in ids]


class Constructions(BaseModel):
    constructions: List[ConstructionId]

    @classmethod
    def from_ifc(cls, ifc_file: file) -> "Constructions":
        materials = Materials.from_ifc(ifc_file)
        layers = Layers.from_ifc(ifc_file, materials)
        material_layers_sets = ifc_file.by_type("IfcMaterialLayerSet")
        return cls.from_ifc_material_layer_sets(material_layers_sets, layers)

    @classmethod
    def from_ifc_material_layer_sets(
        cls, ifc_material_layer_sets: List[entity_instance], layers: Layers
    ) -> "Constructions":
        constructions = []
        for layer_set in ifc_material_layer_sets:
            name_ = layer_set.LayerSetName or generate_alphanumeric_uuid()
            name = remove_non_alphanumeric(name_)
            layer_ids = [
                int(material_layer.id()) for material_layer in layer_set.MaterialLayers
            ]
            constructions.append(
                ConstructionId(
                    id=layer_set.id(), name=name, layers=layers.from_ids(layer_ids)
                )
            )
        return cls(constructions=constructions)

    def get_construction(self, entity: entity_instance) -> Construction:
        construction_id = self._get_construction_id(entity)
        if construction_id is None:
            logger.warning(
                f"Construction ID not found for {entity.GlobalId} ({entity.is_a()}). "
                f"Using default construction."
            )
            return default_construction
        constructions = [
            construction.to_construction()
            for construction in self.constructions
            if construction.id == construction_id
        ]
        if not constructions:
            raise ValueError(f"No construction found for {entity.GlobalId}")
        return constructions[0]

    def _get_construction_id(self, entity: entity_instance) -> Optional[int]:
        associates_materials = [
            association
            for association in entity.HasAssociations
            if association.is_a() == "IfcRelAssociatesMaterial"
        ]
        if not associates_materials:
            logger.warning(f"Associate materials not found for {entity.GlobalId}.")
            return None
        relating_material = associates_materials[0].RelatingMaterial
        if relating_material.is_a() == "IfcMaterialList":
            logger.warning(
                f"Material list found for {entity.GlobalId}, but no construction ID available."
            )
            return None
        elif relating_material.is_a() == "IfcMaterialLayerSetUsage":
            return int(associates_materials[0].RelatingMaterial.ForLayerSet.id())
        elif relating_material.is_a() == "IfcMaterialLayerSet":
            return int(relating_material.id())
        else:
            logger.error("Unexpected material type found.")
            return None

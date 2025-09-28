import json
import math
import sys
from itertools import combinations
from multiprocessing import Process
from pathlib import Path
from typing import Tuple, Literal, List, Annotated, Any, Dict, cast

import ifcopenshell.geom
import numpy as np
import open3d  # type: ignore
from numpy import ndarray
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    model_validator,
    computed_field,
)
from shapely.geometry.polygon import Polygon  # type: ignore
from vedo import Line, Arrow, Mesh, show, write  # type: ignore

from ifctrano.exceptions import VectorWithNansError

settings = ifcopenshell.geom.settings()  # type: ignore
Coordinate = Literal["x", "y", "z"]
AREA_TOLERANCE = 0.5
ROUNDING_FACTOR = 5
CLASH_CLEARANCE = 0.5


class BaseModelConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


def round_two_decimals(value: float) -> float:
    return round(value, 10)


def _show(lines: List[Line], interactive: bool = True) -> None:
    show(
        *lines,
        axes=1,
        viewup="z",
        bg="white",
        interactive=interactive,
    )


class BaseShow(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def lines(self) -> List[Line]: ...  # type: ignore

    def description(self) -> Any: ...  # noqa: ANN401

    def show(self, interactive: bool = True) -> None:
        if sys.platform == "win32":
            _show(self.lines(), interactive)
            return
        p = Process(target=_show, args=(self.lines(), interactive))
        p.start()

    def write(self) -> None:

        write(
            *self.lines(),
            axes=1,
            viewup="z",
            bg="white",
            interactive=True,
        )

    @classmethod
    def load_description(cls, file_path: Path) -> Dict[str, Any]:
        return cast(Dict[str, Any], json.loads(file_path.read_text()))

    def save_description(self, file_path: Path) -> None:
        file_path.write_text(json.dumps(sorted(self.description()), indent=4))

    def description_loaded(self) -> Dict[str, Any]:
        return cast(Dict[str, Any], json.loads(json.dumps(sorted(self.description()))))


class BasePoint(BaseModel):
    x: Annotated[float, BeforeValidator(round_two_decimals)]
    y: Annotated[float, BeforeValidator(round_two_decimals)]
    z: Annotated[float, BeforeValidator(round_two_decimals)]

    @classmethod
    def from_coordinate(cls, point: Tuple[float, float, float]) -> "BasePoint":
        return cls(x=point[0], y=point[1], z=point[2])

    def to_array(self) -> np.ndarray:  # type: ignore
        return np.array([self.x, self.y, self.z])

    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @classmethod
    def from_array(cls, array: np.ndarray) -> "BasePoint":  # type: ignore
        try:
            return cls(x=array[0], y=array[1], z=array[2])
        except IndexError as e:
            raise ValueError("Array must have three components") from e

    def __eq__(self, other: "BasePoint") -> bool:  # type: ignore
        return all([self.x == other.x, self.y == other.y, self.z == other.z])


Signs = Literal[-1, 1]


class Sign(BaseModel):
    x: Signs = 1
    y: Signs = 1
    z: Signs = 1

    def __hash__(self) -> int:
        return hash((self.x, self.y, self.z))


class Vector(BasePoint):

    @model_validator(mode="after")
    def _validator(self) -> "Vector":
        if any(np.isnan(v) for v in self.to_list()):
            raise VectorWithNansError("Vector cannot have NaN values")
        return self

    def __mul__(self, other: "Vector") -> "Vector":

        array = np.cross(self.to_array(), other.to_array())
        return Vector(x=array[0], y=array[1], z=array[2])

    def dot(self, other: "Vector") -> float:
        return np.dot(self.to_array(), other.to_array())  # type: ignore

    def angle(self, other: "Vector") -> int:
        dot_product = np.dot(self.to_xy(), other.to_xy())
        cross_product = np.cross(self.to_xy(), other.to_xy())
        angle_rad = np.arctan2(cross_product, dot_product)
        angle_deg = np.degrees(angle_rad)
        if angle_deg < 0:
            angle_deg += 360
        return int(angle_deg)

    def project(self, other: "Vector") -> "Vector":
        a = self.dot(other) / other.dot(other)
        return Vector(x=a * other.x, y=a * other.y, z=a * other.z)

    def normalize(self) -> "Vector":
        normalized_vector = self.to_array() / np.linalg.norm(self.to_array())
        return Vector(
            x=normalized_vector[0], y=normalized_vector[1], z=normalized_vector[2]
        )

    def norm(self) -> float:
        return float(np.linalg.norm(self.to_array()))

    def to_array(self) -> np.ndarray:  # type: ignore
        return np.array([self.x, self.y, self.z])

    def to_xy(self) -> np.ndarray:  # type: ignore
        return np.array([self.x, self.y])

    def get_normal_index(self) -> int:
        normal_index_list = [abs(v) for v in self.to_list()]
        return normal_index_list.index(max(normal_index_list))

    def is_null(self, tolerance: float = 0.1) -> bool:
        return all(abs(value) < tolerance for value in self.to_list())

    @classmethod
    def from_array(cls, array: np.ndarray) -> "Vector":  # type: ignore
        return cls.model_validate(super().from_array(array).model_dump())


class Point(BasePoint):
    def __sub__(self, other: "Point") -> Vector:

        return Vector(x=self.x - other.x, y=self.y - other.y, z=self.z - other.z)

    def __add__(self, other: "Point") -> "Point":
        return Point(x=self.x + other.x, y=self.y + other.y, z=self.z + other.z)

    def s(self, signs: Sign) -> "Point":
        return Point(x=self.x * signs.x, y=self.y * signs.y, z=self.z * signs.z)


class P(Point):
    pass


class GlobalId(BaseModelConfig):
    global_id: str


class CoordinateSystem(BaseModel):
    x: Vector
    y: Vector
    z: Vector

    def __eq__(self, other: "CoordinateSystem") -> bool:  # type: ignore
        return all(
            [
                self.x == other.x,
                self.y == other.y,
                self.z == other.z,
            ]
        )

    @classmethod
    def from_array(cls, array: np.ndarray) -> "CoordinateSystem":  # type: ignore
        return cls(
            x=Vector.from_array(array[0]),
            y=Vector.from_array(array[1]),
            z=Vector.from_array(array[2]),
        )

    def to_array(self) -> np.ndarray:  # type: ignore
        return np.array([self.x.to_array(), self.y.to_array(), self.z.to_array()])

    def inverse(self, array: np.array) -> np.array:  # type: ignore
        return np.round(np.dot(array, self.to_array()), ROUNDING_FACTOR)  # type: ignore

    def project(self, array: np.array) -> np.ndarray:  # type: ignore
        return np.round(np.dot(array, np.linalg.inv(self.to_array())), ROUNDING_FACTOR)  # type: ignore


class Vertices(BaseModel):
    points: List[Point]

    @classmethod
    def from_arrays(
        cls, arrays: np.ndarray[tuple[int, ...], np.dtype[np.float64]]
    ) -> "Vertices":
        return cls(
            points=[Point(x=array[0], y=array[1], z=array[2]) for array in arrays]
        )

    def to_array(self) -> ndarray:  # type: ignore
        return np.array([point.to_array() for point in self.points])

    def to_list(self) -> List[List[float]]:
        return self.to_array().tolist()  # type: ignore

    def to_tuple(self) -> List[List[float]]:
        return tuple(tuple(t) for t in self.to_array().tolist())  # type: ignore

    def to_face_vertices(self) -> "FaceVertices":
        return FaceVertices(points=self.points)

    def get_local_coordinate_system(self) -> CoordinateSystem:
        vectors = [
            (a - b).normalize().to_array() for a, b in combinations(self.points, 2)
        ]
        found = False
        for v1, v2, v3 in combinations(vectors, 3):
            if (
                np.isclose(abs(np.dot(v1, v2)), 0)
                and np.isclose(abs(np.dot(v1, v3)), 0)
                and np.isclose(abs(np.dot(v2, v3)), 0)
            ):
                found = True
                x = Vector.from_array(v1)
                y = Vector.from_array(v2)
                z = Vector.from_array(v3)
                break
        if not found:
            raise ValueError("Cannot find coordinate system")
        return CoordinateSystem(x=x, y=y, z=z)

    def get_bounding_box(self) -> "Vertices":
        coordinates = self.get_local_coordinate_system()
        projected = coordinates.project(self.to_array())
        points_ = open3d.utility.Vector3dVector(projected)
        aab = open3d.geometry.AxisAlignedBoundingBox.create_from_points(points_)
        reversed = coordinates.inverse(np.array(aab.get_box_points()))
        return Vertices.from_arrays(reversed)

    def is_box_shaped(self) -> bool:
        return len(self.points) == 8


class FaceVertices(Vertices):

    @model_validator(mode="after")
    def _model_validator(self) -> "FaceVertices":
        if len(self.points) < 3:
            raise ValueError("Face must have more than 3 vertices.")
        return self

    @computed_field
    def _vector_1(self) -> Vector:
        point_0 = self.points[0]
        point_1 = self.points[1]
        vector_0 = point_1 - point_0
        return Vector.from_array(
            vector_0.to_array() / np.linalg.norm(vector_0.to_array())
        )

    @computed_field
    def _vector_2(self) -> Vector:
        point_0 = self.points[0]
        point_2 = self.points[2]
        vector_0 = point_2 - point_0
        return Vector.from_array(
            vector_0.to_array() / np.linalg.norm(vector_0.to_array())
        )

    def get_normal(self) -> Vector:
        normal_vector = self._vector_1 * self._vector_2  # type: ignore
        normal_normalized = normal_vector.to_array() / np.linalg.norm(
            normal_vector.to_array()
        )
        return Vector.from_array(normal_normalized)

    def get_coordinates(self) -> CoordinateSystem:
        z_axis = self.get_normal()
        x_axis = self._vector_1
        y_axis = z_axis * x_axis  # type: ignore
        return CoordinateSystem(x=x_axis, y=y_axis, z=z_axis)

    def project(self, vertices: "FaceVertices") -> "ProjectedFaceVertices":
        coordinates = self.get_coordinates()
        projected = coordinates.project(vertices.to_array())
        return ProjectedFaceVertices.from_arrays_(projected, coordinates)

    def get_face_area(self) -> float:
        projected = self.project(self)
        return float(round(projected.to_polygon().area, ROUNDING_FACTOR))

    def get_center(self) -> Point:
        x = np.mean([point.x for point in self.points])
        y = np.mean([point.y for point in self.points])
        z = np.mean([point.z for point in self.points])
        return Point(x=x, y=y, z=z)

    def get_distance(self, other: "FaceVertices") -> float:
        return math.dist(self.get_center().to_list(), other.get_center().to_list())


class FixedIndex(BaseModel):
    index: int
    value: float


class ProjectedFaceVertices(FaceVertices):
    coordinate_system: CoordinateSystem

    def get_fixed_index(self) -> FixedIndex:
        fixed_indexes = [
            FixedIndex(index=i, value=x[0])
            for i, x in enumerate(self.to_array().T)
            if len(set(x)) == 1
        ]
        if len(fixed_indexes) != 1:
            raise ValueError("No or wrong fixed index found")
        return fixed_indexes[0]

    def to_polygon(self) -> Polygon:
        vertices_ = self.to_list()
        try:
            fixed_index = self.get_fixed_index()
        except ValueError:
            return Polygon()
        indexes = [0, 1, 2]
        indexes.remove(fixed_index.index)
        vertices_ = [*vertices_, vertices_[0]]
        points = [np.array(v)[indexes] for v in vertices_]
        return Polygon(points)

    def common_vertices(self, polygon: Polygon) -> FaceVertices:
        fixed_index = self.get_fixed_index()
        coords = [list(coord) for coord in list(polygon.exterior.coords)]
        [coord.insert(fixed_index.index, fixed_index.value) for coord in coords]  # type: ignore
        vertices = FaceVertices.from_arrays(np.array(coords))
        original = self.coordinate_system.inverse(vertices.to_array())
        return FaceVertices.from_arrays(original)  # type: ignore

    @classmethod
    def from_arrays_(
        cls, arrays: ndarray[Any, Any], coordinate_system: CoordinateSystem
    ) -> "ProjectedFaceVertices":
        return cls(
            points=[Point(x=array[0], y=array[1], z=array[2]) for array in arrays],
            coordinate_system=coordinate_system,
        )


class CommonSurface(BaseShow):
    area: float
    orientation: Vector
    main_vertices: FaceVertices
    common_vertices: FaceVertices
    exterior: bool = True
    polygon: str

    def __hash__(self) -> int:
        return hash(
            (
                self.area,
                tuple(self.orientation.to_list()),
                self.main_vertices.to_tuple(),
                self.common_vertices.to_tuple(),
            )
        )

    @model_validator(mode="after")
    def _model_validator(self) -> "CommonSurface":
        self.area = round(self.area, ROUNDING_FACTOR)
        return self

    def description(self) -> tuple[list[float], list[float]]:
        return ([self.area], self.orientation.to_list())

    def lines(self) -> List[Line]:
        lines = []
        lst = self.common_vertices.to_list()[:4]

        # for a, b in [[lst[i], lst[(i + 1) % len(lst)]] for i in range(len(lst))]:
        color = "red" if self.exterior else "blue"
        alpha = 0.1 if self.exterior else 0.9
        lines.append(Mesh([lst, [(0, 1, 2, 3)]], c=color, alpha=alpha))
        arrow = Arrow(
            self.main_vertices.get_center().to_list(),
            (
                self.main_vertices.get_center().to_array() + self.orientation.to_array()
            ).tolist(),
            c="deepskyblue",
            s=0.001,  # thinner shaft
            head_length=0.05,  # smaller tip
            head_radius=0.05,  # sharper tip
            res=16,  # shaft resolution
        )
        lines.append(arrow)
        return lines


Libraries = Literal["IDEAS", "Buildings", "reduced_order", "iso_13790"]

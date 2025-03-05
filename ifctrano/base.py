from typing import Tuple, Literal, List, Annotated

import ifcopenshell.geom
import numpy as np
from pydantic import BaseModel, Field, BeforeValidator

Coordinate = Literal["x", "y", "z"]

def round_two_decimals(value: float) -> float:
    return round(value, 2)


class BasePoint(BaseModel):
    x: Annotated[float, BeforeValidator(round_two_decimals)]
    y: Annotated[float, BeforeValidator(round_two_decimals)]
    z: Annotated[float, BeforeValidator(round_two_decimals)]

    @classmethod
    def from_coordinate(cls, point: Tuple[float, float, float]):
        return cls(x=point[0], y=point[1], z=point[2])

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def get_component(self, component: Coordinate) -> float:
        return getattr(self, component)

    @classmethod
    def from_array(cls, array: np.ndarray):
        return cls(x=array[0], y=array[1], z=array[2])

Signs = Literal[-1, 1]


class Sign(BaseModel):
    x: Signs = 1
    y: Signs = 1
    z: Signs = 1

    def __hash__(self) -> int:
        return hash((self.x, self.y, self.z))


class Vector(BasePoint):
    def __mul__(self, other: "Vector") -> "Vector":

        array = np.cross(self.to_array(), other.to_array())
        return Vector(x=array[0], y=array[1], z=array[2])

    def dot(self, other: "Vector") -> float:
        return np.dot(self.to_array(), other.to_array())

    def project(self, other: "Vector") -> "Vector":
        a = self.dot(other) / other.dot(other)
        return Vector(x=a * other.x, y=a * other.y, z=a * other.z)

    def norm(self)-> "Vector":
        normalized_vector =  self.to_array()/np.linalg.norm(self.to_array())
        return Vector(x=normalized_vector[0], y=normalized_vector[1], z=normalized_vector[2])


    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    def get_normal_index(self) -> int:
        if 1.0 in self.to_list():
            return self.to_list().index(1.0)
        elif -1.0 in self.to_list():
            return self.to_list().index(-1.0)
        else:
            raise ValueError("No normal index found")


class Point(BasePoint):
    def __sub__(self, other: "Point") -> Vector:

        return Vector(x=self.x - other.x, y=self.y - other.y, z=self.z - other.z)

    def __add__(self, other):
        return Point(x=self.x + other.x, y=self.y + other.y, z=self.z + other.z)

    def s(self, signs: Sign) -> "Point":
        return Point(x=self.x * signs.x, y=self.y * signs.y, z=self.z * signs.z)


class P(Point):
    pass


class GlobalId(BaseModel):
    global_id: str

class CoordinateSystem(BaseModel):
    x: Vector
    y: Vector
    z: Vector
    @classmethod
    def from_array(cls, array: np.ndarray):
        return cls(x=Vector.from_array(array[0]), y=Vector.from_array(array[1]), z=Vector.from_array(array[2]))

    def to_array(self) -> np.ndarray:
        return np.array([self.x.to_array(), self.y.to_array(), self.z.to_array()])

    def project(self, array: np.array) -> np.array:
        return np.dot(array, self.to_array())

    def inverse(self, array: np.array) -> np.array:
        return np.dot(array, np.linalg.inv(self.to_array()))

settings = ifcopenshell.geom.settings()


class Vertices(BaseModel):
    points: List[Point]

    @classmethod
    def from_arrays(cls, arrays: List[np.ndarray]):
        return cls(points=[Point(x=array[0], y=array[1], z=array[2]) for array in arrays])

    def to_array(self):
        return np.array([point.to_array() for point in self.points])

    def to_list(self):
        return self.to_array().tolist()
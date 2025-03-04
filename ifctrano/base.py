from typing import Tuple

import ifcopenshell.geom
import numpy as np
from pydantic import BaseModel

class BasePoint(BaseModel):
    x: float
    y: float
    z: float
    @classmethod
    def from_coordinate(cls, point: Tuple[float, float, float]):
        return cls(x=point[0], y=point[1], z=point[2])

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

class Vector(BasePoint):
    def __mul__(self, other: "Vector") -> "Vector":

        array = np.cross(self.to_array(), other.to_array())
        return Vector(x=array[0], y=array[1], z=array[2])

    def dot(self, other: "Vector") -> float:
        return np.dot(self.to_array(), other.to_array())
    def project(self, other: "Vector") -> "Vector":
        a = (self.dot(other) / other.dot(other))
        return Vector(x=a * other.x, y=a * other.y, z=a * other.z)

class Point(BasePoint):

    def __sub__(self, other: "Point") -> Vector:

        return Vector(x=self.x - other.x, y=self.y - other.y, z=self.z - other.z)




class GlobalId(BaseModel):
    global_id: str


settings = ifcopenshell.geom.settings()

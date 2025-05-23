import numpy as np

from ifctrano.base import Vector, FaceVertices, ROUNDING_FACTOR
from ifctrano.bounding_box import OrientedBoundingBox


def test_oriented_bounding_box_along_x() -> None:
    vertices = [
        [0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        [10.0, 0.5, 0.0],
        [0.0, 0.5, 0.0],
        [0.0, 0.0, 2.0],
        [10.0, 0.0, 2.0],
        [10.0, 0.5, 2.0],
        [0.0, 0.5, 2.0],
    ]

    obb = OrientedBoundingBox.from_vertices(vertices=vertices)
    assert obb.faces.description() == [
        (
            [
                [-3e-10, 2e-10, -0.0],
                [10.0000000001, -2e-10, -3e-10],
                [10.0000000001, -6e-10, 2.0],
                [-3e-10, -3e-10, 2.0000000003],
            ],
            (-0.0, -1.0, -5e-10),
        ),
        (
            [
                [-3e-10, 0.5000000003, 2.0000000004],
                [-3e-10, -3e-10, 2.0000000003],
                [10.0000000001, -6e-10, 2.0],
                [10.0000000002, 0.4999999999, 2.0000000001],
            ],
            (-0.0, -2e-10, 1.0),
        ),
        (
            [
                [-3e-10, 0.5000000007, 1e-10],
                [-3e-10, 2e-10, -0.0],
                [-3e-10, -3e-10, 2.0000000003],
                [-3e-10, 0.5000000003, 2.0000000004],
            ],
            (-1.0, -0.0, 0.0),
        ),
        (
            [
                [-3e-10, 0.5000000007, 1e-10],
                [-3e-10, 0.5000000003, 2.0000000004],
                [10.0000000002, 0.4999999999, 2.0000000001],
                [10.0000000001, 0.5000000004, -2e-10],
            ],
            (1e-10, 1.0, 2e-10),
        ),
        (
            [
                [-3e-10, 0.5000000007, 1e-10],
                [10.0000000001, 0.5000000004, -2e-10],
                [10.0000000001, -2e-10, -3e-10],
                [-3e-10, 2e-10, -0.0],
            ],
            (0.0, 0.0, -1.0),
        ),
        (
            [
                [10.0000000001, 0.5000000004, -2e-10],
                [10.0000000002, 0.4999999999, 2.0000000001],
                [10.0000000001, -6e-10, 2.0],
                [10.0000000001, -2e-10, -3e-10],
            ],
            (1.0, 0.0, 0.0),
        ),
    ]


def test_oriented_bounding_box_not_aligned_with_coordinate() -> None:
    vertices = [
        [0.0, 0.0, 0.0],
        [4.47213595, -8.94427191, 0.0],
        [4.91934955, -8.72066511, 0.0],
        [0.4472136, 0.2236068, 0.0],
        [0.0, 0.0, 2.0],
        [4.47213595, -8.94427191, 2.0],
        [4.91934955, -8.72066511, 2.0],
        [0.4472136, 0.2236068, 2.0],
    ]
    obb = OrientedBoundingBox.from_vertices(vertices=vertices)
    assert obb.faces.description() == [
        (
            [
                [-4e-10, 4e-10, -0.0],
                [4.4721359501, -8.9442719103, -3e-10],
                [4.4721359498, -8.9442719105, 2.0000000001],
                [-6e-10, 2e-10, 2.0000000004],
            ],
            (-0.8944271912, -0.4472135951, -5e-10),
        ),
        (
            [
                [0.4472136001, 0.2236068003, 2.0000000004],
                [-6e-10, 2e-10, 2.0000000004],
                [4.4721359498, -8.9442719105, 2.0000000001],
                [4.9193495505, -8.7206651104, 2.0000000001],
            ],
            (0.0, 0.0, 1.0),
        ),
        (
            [
                [0.4472136003, 0.2236068005, 0.0],
                [-4e-10, 4e-10, -0.0],
                [-6e-10, 2e-10, 2.0000000004],
                [0.4472136001, 0.2236068003, 2.0000000004],
            ],
            (-0.4472135951, 0.8944271912, 0.0),
        ),
        (
            [
                [0.4472136003, 0.2236068005, 0.0],
                [0.4472136001, 0.2236068003, 2.0000000004],
                [4.9193495505, -8.7206651104, 2.0000000001],
                [4.9193495508, -8.7206651102, -3e-10],
            ],
            (0.8944271912, 0.4472135951, 1e-10),
        ),
        (
            [
                [0.4472136003, 0.2236068005, 0.0],
                [4.9193495508, -8.7206651102, -3e-10],
                [4.4721359501, -8.9442719103, -3e-10],
                [-4e-10, 4e-10, -0.0],
            ],
            (0.0, 0.0, -1.0),
        ),
        (
            [
                [4.9193495508, -8.7206651102, -3e-10],
                [4.9193495505, -8.7206651104, 2.0000000001],
                [4.4721359498, -8.9442719105, 2.0000000001],
                [4.4721359501, -8.9442719103, -3e-10],
            ],
            (0.4472135948, -0.8944271913, -0.0),
        ),
    ]


def test_oriented_bounding_box_not_aligned_with_coordinate_different_origin() -> None:
    vertices = [
        [1.46446609, 0.46446609, 1.0],
        [8.53553391, 7.53553391, 1.0],
        [8.18198052, 7.8890873, 1.0],
        [1.1109127, 0.81801948, 1.0],
        [1.46446609, 0.46446609, 3.0],
        [8.53553391, 7.53553391, 3.0],
        [8.18198052, 7.8890873, 3.0],
        [1.1109127, 0.81801948, 3.0],
    ]
    obb = OrientedBoundingBox.from_vertices(vertices=vertices)
    assert obb.faces.description() == [
        (
            [
                [1.1109126996, 0.8180194798, 3.0000000002],
                [8.18198052, 7.8890873003, 3.0000000001],
                [8.1819805201, 7.8890873002, 0.9999999997],
                [1.1109126996, 0.8180194797, 0.9999999998],
            ],
            (-0.7071067812, 0.7071067812, 0.0),
        ),
        (
            [
                [1.4644660899, 0.4644660894, 3.0000000003],
                [1.1109126996, 0.8180194798, 3.0000000002],
                [1.1109126996, 0.8180194797, 0.9999999998],
                [1.46446609, 0.4644660893, 0.9999999998],
            ],
            (-0.7071067813, -0.7071067811, 0.0),
        ),
        (
            [
                [1.4644660899, 0.4644660894, 3.0000000003],
                [1.46446609, 0.4644660893, 0.9999999998],
                [8.5355339104, 7.5355339098, 0.9999999997],
                [8.5355339104, 7.5355339099, 3.0000000002],
            ],
            (0.7071067812, -0.7071067812, 0.0),
        ),
        (
            [
                [1.4644660899, 0.4644660894, 3.0000000003],
                [8.5355339104, 7.5355339099, 3.0000000002],
                [8.18198052, 7.8890873003, 3.0000000001],
                [1.1109126996, 0.8180194798, 3.0000000002],
            ],
            (0.0, 0.0, 1.0),
        ),
        (
            [
                [1.46446609, 0.4644660893, 0.9999999998],
                [1.1109126996, 0.8180194797, 0.9999999998],
                [8.1819805201, 7.8890873002, 0.9999999997],
                [8.5355339104, 7.5355339098, 0.9999999997],
            ],
            (-0.0, 0.0, -1.0),
        ),
        (
            [
                [8.5355339104, 7.5355339099, 3.0000000002],
                [8.5355339104, 7.5355339098, 0.9999999997],
                [8.1819805201, 7.8890873002, 0.9999999997],
                [8.18198052, 7.8890873003, 3.0000000001],
            ],
            (0.7071067812, 0.7071067812, 0.0),
        ),
    ]


def test_oriented_bounding_box_compare_faces() -> None:
    vertices = [
        [0.0, 0.0, 0.0],
        [4.47213595, -8.94427191, 0.0],
        [4.91934955, -8.72066511, 0.0],
        [0.4472136, 0.2236068, 0.0],
        [0.0, 0.0, 2.0],
        [4.47213595, -8.94427191, 2.0],
        [4.91934955, -8.72066511, 2.0],
        [0.4472136, 0.2236068, 2.0],
    ]

    vertices_ = (
        np.array(vertices) + Vector(x=-0.4472, y=0.8944, z=0.0).to_array() * 20
    ).tolist()

    obb_1 = OrientedBoundingBox.from_vertices(vertices=vertices)
    obb_2 = OrientedBoundingBox.from_vertices(vertices=vertices_)
    common_surface = obb_2.intersect_faces(obb_1)
    assert round(common_surface.area, 2) == 1


def test_oriented_bounding_box_compare_faces_another_direction() -> None:
    vertices = [
        [0.0, 0.0, 0.0],
        [4.47213595, -8.94427191, 0.0],
        [4.91934955, -8.72066511, 0.0],
        [0.4472136, 0.2236068, 0.0],
        [0.0, 0.0, 2.0],
        [4.47213595, -8.94427191, 2.0],
        [4.91934955, -8.72066511, 2.0],
        [0.4472136, 0.2236068, 2.0],
    ]

    vertices_ = (
        np.array(vertices) + Vector(x=-0.8944, y=-0.4472, z=0.0).to_array() * 20
    ).tolist()

    obb_1 = OrientedBoundingBox.from_vertices(vertices=vertices)
    obb_2 = OrientedBoundingBox.from_vertices(vertices=vertices_)
    common_surface = obb_2.intersect_faces(obb_1)
    assert round(common_surface.area, 2) == 20


def test_common_area_multiple_boxes_following_x() -> None:
    vertices = [
        [0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        [10.0, 0.5, 0.0],
        [0.0, 0.5, 0.0],
        [0.0, 0.0, 2.0],
        [10.0, 0.0, 2.0],
        [10.0, 0.5, 2.0],
        [0.0, 0.5, 2.0],
    ]
    vertices_1 = (
        np.array(vertices) + Vector(x=1, y=-0, z=0.0).to_array() * 20
    ).tolist()
    vertices_2 = (
        np.array(vertices) + Vector(x=-1, y=-0, z=0.0).to_array() * 20
    ).tolist()
    obb_space = OrientedBoundingBox.from_vertices(vertices=vertices)
    obb_1 = OrientedBoundingBox.from_vertices(vertices=vertices_1)
    obb_2 = OrientedBoundingBox.from_vertices(vertices=vertices_2)
    common_surface_1 = obb_space.intersect_faces(obb_1)
    common_surface_2 = obb_space.intersect_faces(obb_2)
    assert common_surface_2.description() == ([1.0], [-1.0, -0.0, -0.0])
    assert common_surface_1.description() == ([1.0], [1.0, 0.0, 0.0])


def test_common_area_multiple_boxes_following_y() -> None:
    vertices = [
        [0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        [10.0, 0.5, 0.0],
        [0.0, 0.5, 0.0],
        [0.0, 0.0, 2.0],
        [10.0, 0.0, 2.0],
        [10.0, 0.5, 2.0],
        [0.0, 0.5, 2.0],
    ]
    vertices_1 = (np.array(vertices) + Vector(x=0, y=1, z=0.0).to_array() * 20).tolist()
    vertices_2 = (
        np.array(vertices) + Vector(x=0, y=-1, z=0.0).to_array() * 20
    ).tolist()
    obb_space = OrientedBoundingBox.from_vertices(vertices=vertices)
    obb_1 = OrientedBoundingBox.from_vertices(vertices=vertices_1)
    obb_2 = OrientedBoundingBox.from_vertices(vertices=vertices_2)
    common_surface_1 = obb_space.intersect_faces(obb_1)
    common_surface_2 = obb_space.intersect_faces(obb_2)
    assert common_surface_2.description() == ([20.0], [-0.0, -1.0, -5e-10])
    assert common_surface_1.description() == ([20.0], [1e-10, 1.0, 2e-10])


def test_space_face_area() -> None:
    vertices = np.array(
        [
            [5.84186610583, 0.23500000000000001, 3.1],
            [5.84186610583, 0.23500000000000001, 6.1],
            [5.84186610583, 3.235, 6.1],
            [5.84186610583, 3.235, 3.1],
            [2.8418661058300003, 3.235, 6.1],
            [2.8418661058300003, 3.235, 3.1],
            [2.8418661058300003, 0.23500000000000001, 6.1],
            [2.8418661058300003, 0.23500000000000001, 3.1],
        ]
    )
    obb_space = OrientedBoundingBox.from_vertices(vertices=vertices)
    assert [f.vertices.get_face_area() for f in obb_space.faces.faces] == [
        9.0,
        9.0,
        9.0,
        9.0,
        9.0,
        9.0,
    ]


def test_space_face_area_2() -> None:
    vertices = np.array(
        [
            [5.84186610583, -3.0, 3.1],
            [5.84186610583, -3.0, 6.1],
            [5.84186610583, 0.0, 6.1],
            [5.84186610583, 0.0, 3.1],
            [2.8418661058300003, 0.0, 6.1],
            [2.8418661058300003, 0.0, 3.1],
            [2.8418661058300003, -3.0, 6.1],
            [2.8418661058300003, -3.0, 3.1],
        ]
    )
    obb_space = OrientedBoundingBox.from_vertices(vertices=vertices)
    assert [f.vertices.get_face_area() for f in obb_space.faces.faces] == [
        9.0,
        9.0,
        9.0,
        9.0,
        9.0,
        9.0,
    ]


def test_non_properly_computed_bounding_box() -> None:
    vertices = [
        [7.475, -0.05, -0.43],
        [7.475, -0.05, -0.25],
        [7.475, 6.96, -0.25],
        [7.475, 6.96, -0.43],
        [-0.05000000000000071, -0.05, -0.43],
        [-0.05000000000000071, -0.05, -0.25],
        [-0.05000000000000071, 6.96, -0.25],
        [-0.05000000000000071, 6.96, -0.43],
    ]
    obb_space = OrientedBoundingBox.from_vertices(vertices=vertices)
    assert [f.vertices.get_face_area() for f in obb_space.faces.faces] == [
        1.2618,
        1.2618,
        1.3545,
        1.3545,
        52.75025,
        52.75025,
    ]


def test_face_vertices_coordinates() -> None:
    vertices = np.round(
        np.array(
            [
                [3.74540119, 9.50714306, 7.31993942],
                [3.55023721, 9.88995042, 6.74363045],
                [3.05972707, 9.74077508, 7.04172513],
                [3.25489105, 9.35796773, 7.61803411],
            ]
        ),
        ROUNDING_FACTOR,
    )
    projected_vertices = [
        [-1.82243, -2.50432, 12.18205],
        [-1.10357, -2.50432, 12.18205],
        [-1.28882, -1.94094, 12.18205],
        [-2.00768, -1.94094, 12.18205],
    ]
    face_vertices = FaceVertices.from_arrays(vertices)
    coordinate_system = face_vertices.get_coordinates()
    projected_face_vertice = face_vertices.project(FaceVertices.from_arrays(vertices))
    polygon = projected_face_vertice.to_polygon()
    transformed_vertices = projected_face_vertice.common_vertices(polygon)
    assert transformed_vertices.to_list() == [
        [3.7454, 9.50714, 7.31994],
        [3.55024, 9.88995, 6.74363],
        [3.05973, 9.74078, 7.04172],
        [3.25489, 9.35797, 7.61803],
        [3.7454, 9.50714, 7.31994],
    ]
    assert coordinate_system.project(vertices).tolist() == projected_vertices
    assert coordinate_system.inverse(np.array(projected_vertices)).tolist() == [
        [3.7454, 9.50714, 7.31994],
        [3.55024, 9.88995, 6.74363],
        [3.05973, 9.74078, 7.04172],
        [3.25489, 9.35797, 7.61803],
    ]

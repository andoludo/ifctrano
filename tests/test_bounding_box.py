import numpy as np

from ifctrano.base import Vector
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
                [0.0, 0.0, 0.0],
                [0.0, 0.5, 0.0],
                [0.0, 0.5, 2.0],
                [0.0, 0.0, 2.0],
                [0.0, 0.0, 0.0],
            ],
            (1.0, 0.0, 0.0),
        ),
        (
            [
                [0.0, 0.0, 0.0],
                [10.0, 0.0, 0.0],
                [10.0, 0.0, 2.0],
                [0.0, 0.0, 2.0],
                [0.0, 0.0, 0.0],
            ],
            (0.0, -1.0, 0.0),
        ),
        (
            [
                [0.0, 0.0, 0.0],
                [10.0, 0.0, 0.0],
                [10.0, 0.5, 0.0],
                [0.0, 0.5, 0.0],
                [0.0, 0.0, 0.0],
            ],
            (0.0, 0.0, 1.0),
        ),
        (
            [
                [0.0, 0.0, 2.0],
                [10.0, 0.0, 2.0],
                [10.0, 0.5, 2.0],
                [0.0, 0.5, 2.0],
                [0.0, 0.0, 2.0],
            ],
            (0.0, 0.0, 1.0),
        ),
        (
            [
                [0.0, 0.5, 0.0],
                [10.0, 0.5, 0.0],
                [10.0, 0.5, 2.0],
                [0.0, 0.5, 2.0],
                [0.0, 0.5, 0.0],
            ],
            (0.0, -1.0, 0.0),
        ),
        (
            [
                [10.0, 0.0, 0.0],
                [10.0, 0.5, 0.0],
                [10.0, 0.5, 2.0],
                [10.0, 0.0, 2.0],
                [10.0, 0.0, 0.0],
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
                [-1e-10, 2e-10, 0.0],
                [4.47213595, -8.94427191, 0.0],
                [4.47213595, -8.94427191, 2.0],
                [-1e-10, 2e-10, 2.0],
                [-1e-10, 2e-10, 0.0],
            ],
            (-0.8944271912, -0.4472135951, 0.0),
        ),
        (
            [
                [0.4472136, 0.2236068, 0.0],
                [-1e-10, 2e-10, 0.0],
                [-1e-10, 2e-10, 2.0],
                [0.4472136, 0.2236068, 2.0],
                [0.4472136, 0.2236068, 0.0],
            ],
            (-0.4472135951, 0.8944271912, 0.0),
        ),
        (
            [
                [0.4472136, 0.2236068, 0.0],
                [-1e-10, 2e-10, 0.0],
                [4.47213595, -8.94427191, 0.0],
                [4.9193495501, -8.7206651102, 0.0],
                [0.4472136, 0.2236068, 0.0],
            ],
            (0.0, 0.0, 1.0),
        ),
        (
            [
                [0.4472136, 0.2236068, 0.0],
                [4.9193495501, -8.7206651102, 0.0],
                [4.9193495501, -8.7206651102, 2.0],
                [0.4472136, 0.2236068, 2.0],
                [0.4472136, 0.2236068, 0.0],
            ],
            (-0.8944271912, -0.4472135951, 0.0),
        ),
        (
            [
                [0.4472136, 0.2236068, 2.0],
                [-1e-10, 2e-10, 2.0],
                [4.47213595, -8.94427191, 2.0],
                [4.9193495501, -8.7206651102, 2.0],
                [0.4472136, 0.2236068, 2.0],
            ],
            (0.0, 0.0, 1.0),
        ),
        (
            [
                [4.9193495501, -8.7206651102, 0.0],
                [4.47213595, -8.94427191, 0.0],
                [4.47213595, -8.94427191, 2.0],
                [4.9193495501, -8.7206651102, 2.0],
                [4.9193495501, -8.7206651102, 0.0],
            ],
            (-0.4472135951, 0.8944271912, 0.0),
        ),
    ]


def test_oriented_bounding_box_not_aligned_with_coordinate_different_origin() -> None:
    center = (5, 4, 2)
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
                [1.1109127, 0.81801948, 1.0],
                [8.1819805202, 7.8890873002, 1.0],
                [8.1819805202, 7.8890873002, 3.0],
                [1.1109127, 0.81801948, 3.0],
                [1.1109127, 0.81801948, 1.0],
            ],
            (0.7071067812, -0.7071067812, 0.0),
        ),
        (
            [
                [1.46446609, 0.46446609, 1.0],
                [1.1109127, 0.81801948, 1.0],
                [1.1109127, 0.81801948, 3.0],
                [1.46446609, 0.46446609, 3.0],
                [1.46446609, 0.46446609, 1.0],
            ],
            (0.7071067812, 0.7071067812, 0.0),
        ),
        (
            [
                [1.46446609, 0.46446609, 1.0],
                [8.5355339102, 7.5355339102, 1.0],
                [8.1819805202, 7.8890873002, 1.0],
                [1.1109127, 0.81801948, 1.0],
                [1.46446609, 0.46446609, 1.0],
            ],
            (0.0, 0.0, 1.0),
        ),
        (
            [
                [1.46446609, 0.46446609, 1.0],
                [8.5355339102, 7.5355339102, 1.0],
                [8.5355339102, 7.5355339102, 3.0],
                [1.46446609, 0.46446609, 3.0],
                [1.46446609, 0.46446609, 1.0],
            ],
            (0.7071067812, -0.7071067812, 0.0),
        ),
        (
            [
                [1.46446609, 0.46446609, 3.0],
                [8.5355339102, 7.5355339102, 3.0],
                [8.1819805202, 7.8890873002, 3.0],
                [1.1109127, 0.81801948, 3.0],
                [1.46446609, 0.46446609, 3.0],
            ],
            (0.0, 0.0, 1.0),
        ),
        (
            [
                [8.5355339102, 7.5355339102, 1.0],
                [8.1819805202, 7.8890873002, 1.0],
                [8.1819805202, 7.8890873002, 3.0],
                [8.5355339102, 7.5355339102, 3.0],
                [8.5355339102, 7.5355339102, 1.0],
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
        np.array(vertices) + Vector(x=-0.45, y=0.89, z=0.0).to_array() * 20
    ).tolist()

    obb_1 = OrientedBoundingBox.from_vertices(vertices=vertices)
    obb_2 = OrientedBoundingBox.from_vertices(vertices=vertices_)
    common_surface = obb_2.intersect_faces(obb_1)
    assert round(common_surface.area,2) == 0.82


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
        np.array(vertices) + Vector(x=-0.89, y=-0.45, z=0.0).to_array() * 20
    ).tolist()

    obb_1 = OrientedBoundingBox.from_vertices(vertices=vertices)
    obb_2 = OrientedBoundingBox.from_vertices(vertices=vertices_)
    common_surface = obb_2.intersect_faces(obb_1)
    assert round(common_surface.area,2) == 19.82


def test_common_area_multiple_boxes_following_x():

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
    assert common_surface_2.description() == (1.0, [-1.0, -0.0, -0.0])
    assert common_surface_1.description() == (1.0, [1.0, 0.0, 0.0])


def test_common_area_multiple_boxes_following_y():

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
    assert common_surface_2.description() == (20.0, [0.0, -1.0, 0.0])
    assert common_surface_1.description() == (20.0, [-0.0, 1.0, -0.0])

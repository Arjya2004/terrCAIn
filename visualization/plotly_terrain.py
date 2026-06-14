from __future__ import annotations

import numpy as np
import plotly.graph_objects as go


MAX_BLOCK_HEIGHT = 20


def _append_quad(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, int, int]],
    intensity_values: list[float],
    point_a: tuple[float, float, float],
    point_b: tuple[float, float, float],
    point_c: tuple[float, float, float],
    point_d: tuple[float, float, float],
    intensity: float,
) -> None:
    start_index = len(vertices)
    vertices.extend([point_a, point_b, point_c, point_d])
    intensity_values.extend([intensity, intensity, intensity, intensity])
    faces.extend(
        [
            (start_index, start_index + 1, start_index + 2),
            (start_index, start_index + 2, start_index + 3),
        ]
    )


def _heightmap_to_block_heights(heightmap: np.ndarray) -> np.ndarray:
    clipped = np.clip(heightmap.astype(float), a_min=0.0, a_max=1.0)
    scaled = np.rint(clipped * MAX_BLOCK_HEIGHT).astype(int)
    return np.maximum(1, scaled)


def _build_voxel_traces(heightmap: np.ndarray) -> list[go.BaseTraceType]:
    block_heights = _heightmap_to_block_heights(heightmap)
    rows, cols = block_heights.shape

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    intensity_values: list[float] = []

    outline_x: list[float | None] = []
    outline_y: list[float | None] = []
    outline_z: list[float | None] = []

    for row in range(rows):
        for col in range(cols):
            height = float(block_heights[row, col])
            x0, x1 = float(col), float(col + 1)
            y0, y1 = float(row), float(row + 1)

            _append_quad(
                vertices,
                faces,
                intensity_values,
                (x0, y0, height),
                (x1, y0, height),
                (x1, y1, height),
                (x0, y1, height),
                height,
            )
            _append_quad(
                vertices,
                faces,
                intensity_values,
                (x0, y1, 0.0),
                (x1, y1, 0.0),
                (x1, y0, 0.0),
                (x0, y0, 0.0),
                0.0,
            )
            _append_quad(
                vertices,
                faces,
                intensity_values,
                (x0, y0, 0.0),
                (x1, y0, 0.0),
                (x1, y0, height),
                (x0, y0, height),
                height,
            )
            _append_quad(
                vertices,
                faces,
                intensity_values,
                (x1, y1, 0.0),
                (x0, y1, 0.0),
                (x0, y1, height),
                (x1, y1, height),
                height,
            )
            _append_quad(
                vertices,
                faces,
                intensity_values,
                (x0, y1, 0.0),
                (x0, y0, 0.0),
                (x0, y0, height),
                (x0, y1, height),
                height,
            )
            _append_quad(
                vertices,
                faces,
                intensity_values,
                (x1, y0, 0.0),
                (x1, y1, 0.0),
                (x1, y1, height),
                (x1, y0, height),
                height,
            )

            outline_x.extend([x0, x1, x1, x0, x0, None])
            outline_y.extend([y0, y0, y1, y1, y0, None])
            outline_z.extend([height, height, height, height, height, None])

    x_values, y_values, z_values = (list(values) for values in zip(*vertices))
    i_values, j_values, k_values = (list(indices) for indices in zip(*faces))

    mesh_trace = go.Mesh3d(
        x=x_values,
        y=y_values,
        z=z_values,
        i=i_values,
        j=j_values,
        k=k_values,
        intensity=intensity_values,
        colorscale="Earth",
        flatshading=True,
        showscale=True,
        colorbar={"title": "Block Height"},
        hoverinfo="skip",
        opacity=1.0,
        lighting={"ambient": 0.45, "diffuse": 0.9, "specular": 0.05, "roughness": 1.0},
    )

    outline_trace = go.Scatter3d(
        x=outline_x,
        y=outline_y,
        z=outline_z,
        mode="lines",
        line={"color": "rgba(25, 25, 25, 0.55)", "width": 2},
        hoverinfo="skip",
        showlegend=False,
    )

    return [mesh_trace, outline_trace]


def create_terrain_figure(heightmap: np.ndarray, title: str) -> go.Figure:
    rows, cols = heightmap.shape
    block_heights = _heightmap_to_block_heights(heightmap)
    traces = _build_voxel_traces(heightmap)
    figure = go.Figure(data=traces)

    figure.update_layout(
        title=title,
        scene={
            "xaxis_title": "Grid X (cells)",
            "yaxis_title": "Grid Y (cells)",
            "zaxis_title": "Block Height",
            "xaxis": {"range": [0, cols], "nticks": 11},
            "yaxis": {"range": [0, rows], "nticks": 11},
            "zaxis": {"range": [0, max(1.0, float(np.max(block_heights))) if block_heights.size else 1.0]},
            "aspectmode": "manual",
            "aspectratio": {"x": 1, "y": 1, "z": 0.55},
            "camera": {"eye": {"x": 1.6, "y": 1.55, "z": 1.05}},
        },
        margin={"l": 0, "r": 0, "t": 50, "b": 0},
        height=700,
    )
    return figure

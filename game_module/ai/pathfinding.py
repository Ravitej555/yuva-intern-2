"""
A* pathfinding on a 2D grid.

Grid convention:
- 0 = walkable, 1 = blocked
- grid[y][x]
- find_path returns list[Vector2] of world positions (cell centers)
"""
from __future__ import annotations
import heapq
import math
from game_module.physics.vector2 import Vector2


class AStarPathfinder:
    def __init__(self, grid: list[list[int]], cell_size: float = 1.0,
                 allow_diagonal: bool = True) -> None:
        self.grid = grid
        self.cell_size = cell_size
        self.allow_diagonal = allow_diagonal
        self.rows = len(grid)
        self.cols = len(grid[0]) if self.rows > 0 else 0

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.cols and 0 <= y < self.rows

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.grid[y][x] == 0

    def world_to_cell(self, pos: Vector2) -> tuple[int, int]:
        return (int(math.floor(pos.x / self.cell_size)),
                int(math.floor(pos.y / self.cell_size)))

    def cell_to_world(self, x: int, y: int) -> Vector2:
        return Vector2((x + 0.5) * self.cell_size, (y + 0.5) * self.cell_size)

    def neighbors(self, x: int, y: int):
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if self.allow_diagonal:
            dirs += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if not self.is_walkable(nx, ny):
                continue
            # Prevent cutting corners diagonally
            if dx != 0 and dy != 0:
                if not self.is_walkable(x + dx, y) or not self.is_walkable(x, y + dy):
                    continue
                cost = math.sqrt(2)
            else:
                cost = 1.0
            yield (nx, ny, cost)

    def heuristic(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        # Octile distance
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        if self.allow_diagonal:
            return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)
        return dx + dy

    def find_path(self, start: Vector2, goal: Vector2) -> list[Vector2]:
        """
        Returns path as list of world positions from start cell to goal cell inclusive.
        Empty list if no path.
        """
        s = self.world_to_cell(start)
        g = self.world_to_cell(goal)
        if not self.is_walkable(*s) or not self.is_walkable(*g):
            return []
        if s == g:
            return [self.cell_to_world(*s)]

        open_heap: list[tuple[float, int, tuple[int, int]]] = []
        counter = 0
        heapq.heappush(open_heap, (0, counter, s))
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {s: None}
        g_score: dict[tuple[int, int], float] = {s: 0}
        f_score: dict[tuple[int, int], float] = {s: self.heuristic(s, g)}

        closed: set[tuple[int, int]] = set()

        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            if current == g:
                break
            closed.add(current)
            for nx, ny, cost in self.neighbors(current[0], current[1]):
                nb = (nx, ny)
                if nb in closed:
                    continue
                tentative = g_score[current] + cost
                if tentative < g_score.get(nb, float("inf")):
                    came_from[nb] = current
                    g_score[nb] = tentative
                    f = tentative + self.heuristic(nb, g)
                    f_score[nb] = f
                    counter += 1
                    heapq.heappush(open_heap, (f, counter, nb))

        if g not in came_from:
            return []

        # Reconstruct
        path_cells: list[tuple[int, int]] = []
        cur: tuple[int, int] | None = g
        while cur is not None:
            path_cells.append(cur)
            cur = came_from[cur]
        path_cells.reverse()
        return [self.cell_to_world(x, y) for x, y in path_cells]

    def smooth_path(self, path: list[Vector2]) -> list[Vector2]:
        """Simple line-of-sight smoothing."""
        if len(path) <= 2:
            return path[:]
        smoothed = [path[0]]
        i = 0
        while i < len(path) - 1:
            # Try to jump as far as possible with line of sight
            farthest = i + 1
            for j in range(len(path) - 1, i + 1, -1):
                if self._has_line_of_sight(path[i], path[j]):
                    farthest = j
                    break
            smoothed.append(path[farthest])
            i = farthest
        return smoothed

    def _has_line_of_sight(self, a: Vector2, b: Vector2) -> bool:
        # Bresenham over cells
        x0, y0 = self.world_to_cell(a)
        x1, y1 = self.world_to_cell(b)
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        while True:
            if not self.is_walkable(x, y):
                return False
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        return True

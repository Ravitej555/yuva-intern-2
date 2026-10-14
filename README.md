# Game Module - Week 2 Task Deliverable
## Physics Simulation, AI State Machine & Dynamic Player Input System

> **Week 2 Task:** Coding and Implementation of a Game Module  
> **Language:** Python 3.10+  
> **Core Dependencies:** None (Standard Library only for core simulation & testing)  
> **Optional Dependencies:** `pygame` (for 60 FPS interactive visual demo)

---

## 1. Executive Summary

This project implements a modular, high-performance **2D Game Engine Subsystem** designed around three foundational game systems:

1. **Rigid Body 2D Physics Engine:** Semi-implicit Euler integration, sub-stepping, Sweep-and-Prune broad-phase, AABB narrow-phase with Minimum Translation Vector (MTV) separation, Baumgarte positional stabilization, impulse-based collision response with restitution and Coulomb friction, and Bresenham slab-based raycasting.
2. **Autonomous Enemy AI & Pathfinding Subsystem:** Hierarchical Finite State Machine (FSM) managing `Idle`, `Patrol`, `Chase`, `Attack`, and low-health `Flee` behaviors, paired with a grid-based **A* pathfinding** engine featuring an octile distance heuristic and line-of-sight path smoothing.
3. **Dynamic Action-Based Input Management:** Decoupled input layer supporting dynamic key rebinding, input buffering (e.g. jump buffering), coyote-time state tracking, multi-button combo detection within configurable time windows, and virtual axes.

The module includes both a **deterministic headless simulation** mode (which prints physics state, velocity, ground contacts, and combat logs at 60 Hz) and an **interactive visual demo** powered by Pygame.

---

## 2. Architecture & File Structure

```
week2/
├── game_module/                  # Core reusable game engine package
│   ├── __init__.py               # Package exports & version metadata
│   ├── physics/                  # Physics Engine Module
│   │   ├── __init__.py
│   │   ├── vector2.py            # 2D Vector mathematics (dot, cross, lerp, dist)
│   │   ├── aabb.py               # Axis-Aligned Bounding Box & MTV calculation
│   │   ├── rigidbody.py          # Rigid body dynamics (mass, velocity, forces)
│   │   └── world.py              # PhysicsWorld (integration, broad/narrow phase, collisions)
│   ├── ai/                       # AI Subsystem
│   │   ├── __init__.py
│   │   ├── state_machine.py      # Generic FSM base classes (State, StateMachine)
│   │   ├── behaviours.py         # Concrete states: Idle, Patrol, Chase, Attack, Flee
│   │   └── pathfinding.py        # A* Pathfinding with octile heuristic & smoothing
│   ├── input/                    # Dynamic Input Management
│   │   ├── __init__.py
│   │   └── handler.py            # Action-mapped input, buffering, combo detection
│   ├── entities/                 # Game entities
│   │   ├── __init__.py
│   │   ├── player.py             # Player entity (jump buffer, coyote time, dash)
│   │   └── enemy.py              # Enemy entity (steering, sensing, FSM integration)
│   └── utils/                    # Math & helper utilities
│       ├── __init__.py
│       └── math_utils.py         # Clamp, lerp, approach functions
├── tests/                        # Comprehensive test suite
│   ├── test_physics.py           # Unit tests for Vector2, AABB, forces, collisions
│   ├── test_ai.py                # Unit tests for A*, smoothing, state machine
│   ├── test_input.py             # Unit tests for actions, buffering, combos, rebinding
│   └── test_integration.py       # End-to-end simulation & combat integration tests
├── main.py                       # Main executable (headless simulation + visual demo)
├── run_tests.py                  # Test suite runner
├── requirements.txt              # Optional dependencies
└── README.md                     # Documentation & technical guide
```

---

## 3. Key Implemented Modules & Functionality

### 3.1 2D Physics Engine (`game_module/physics`)
- **`Vector2`**: Immutable-friendly 2D vector class supporting addition, subtraction, scalar multiplication, dot products, 2D cross products, Euclidean normalization, distance calculation, angle interpolation, and linear interpolation (`lerp`).
- **`AABB` (Axis-Aligned Bounding Box)**: Computes bounding bounds from center positions and extents. Implements overlapping tests (`intersects`), point containment (`contains_point`), and calculates the **Minimum Translation Vector (MTV)** specifying the exact direction and depth required to resolve intersections.
- **`Rigidbody`**: Supports three body types: `STATIC` (immovable obstacles/platforms), `DYNAMIC` (fully simulated entities subjected to forces and gravity), and `KINEMATIC` (scripted velocity). Tracks accumulated forces, linear damping (drag), restitution (bounciness), friction coefficient, and grounded contacts.
- **`PhysicsWorld`**:
  - **Sub-stepping**: Divides simulation frames into $N$ sub-steps (default 4) to eliminate tunneling and jitter.
  - **Semi-Implicit Euler Integration**: Velocity is updated prior to position update ($\vec{v}_{t+1} = \vec{v}_t + \vec{a}\Delta t$; $\vec{x}_{t+1} = \vec{x}_t + \vec{v}_{t+1}\Delta t$), preserving numerical energy stability.
  - **Broad-Phase (Sweep and Prune)**: Sorts bodies along the X-axis to reduce $O(N^2)$ checks down to active intervals.
  - **Impulse-Based Narrow-Phase Resolution**: Computes momentum transfer along collision normals weighted by inverse masses ($m_1^{-1}, m_2^{-1}$), with Baumgarte positional stabilization to eliminate sinking.
  - **Coulomb Tangent Friction**: Applies tangent damping opposing relative sliding velocity clamped to $\mu \cdot J_n$.
  - **Raycasting**: Implements the slab method for line-of-sight and projectile hit testing against AABB geometry.

### 3.2 Enemy AI & Pathfinding (`game_module/ai`)
- **Finite State Machine (`StateMachine`, `State`)**:
  - Implements clean lifecycle hooks: `on_enter(entity)`, `on_update(entity, dt) -> Optional[str]`, and `on_exit(entity)`.
  - Decouples logic from entities, allowing AI state re-use across different character types.
- **Hierarchical Behaviors (`behaviours.py`)**:
  - `IdleState`: Pauses, periodically looks around, scans for player in sensory range.
  - `PatrolState`: Traverses an arbitrary list of waypoints with steering forces; switches to `Chase` upon player detection.
  - `ChaseState`: Pursues player directly or follows pathfinding waypoints when obstacles block direct sight.
  - `AttackState`: Executes melee strikes upon entering attack radius, honoring attack cooldowns and firing callbacks.
  - `FleeState`: Prioritized survival state triggered when health drops below 25%, steering the entity away from danger.
- **A* Pathfinding & Path Smoothing (`pathfinding.py`)**:
  - Priority queue (`heapq`) implementation over 2D occupancy grids.
  - Uses the **Octile distance heuristic** ($d_{\max} + (\sqrt{2}-1)d_{\min}$) for optimal 8-directional movement without corner cutting.
  - **Bresenham Line-of-Sight Path Smoothing**: Post-processes raw grid steps into clean, continuous vector trajectories by eliminating redundant waypoints across unobstructed line-of-sight corridors.

### 3.3 Dynamic Input Management (`game_module/input`)
- **Action Abstraction (`Action` Enum)**: Decouples high-level gameplay intents (`MOVE_LEFT`, `MOVE_RIGHT`, `JUMP`, `DASH`, `ATTACK`) from hardware inputs.
- **Multi-Key & Rebinding**: Any action can map to multiple physical keys (e.g. WASD, Arrow keys, Gamepad buttons). Keys can be rebound dynamically at runtime via `rebind(action, keys)`.
- **State Tracking**: Accurate detection of `is_action_pressed`, `is_action_just_pressed`, and `is_action_just_released` across discrete game ticks.
- **Input Buffering**: Retains button presses for a short configurable duration (e.g., 150ms jump buffer). If a player hits Jump 100ms before touching the ground, the jump executes cleanly upon contact.
- **Coyote Time**: Allows players to jump for a fraction of a second (e.g., 120ms) after walking off a platform edge, delivering fluid platformer gameplay feel.
- **Combo Detection**: Tracks a timestamped ring buffer of inputs to detect fighting-game-style sequences (e.g. `['a', 'b', 'c']` or `['down', 'right', 'attack']`) within a time window.

---

## 4. Key Code Sections Explained

### 4.1 Impulse-Based Collision Resolution & Baumgarte Stabilization
Located in [`game_module/physics/world.py`](file:///c:/Users/Ravitej%20Manu/Downloads/week2/game_module/physics/world.py):
```python
# 1. Positional correction (Baumgarte stabilization)
total_inv = a.inv_mass + b.inv_mass
percent = 0.8  # Baumgarte factor
correction = mtv * percent
a.position = a.position + correction * (a.inv_mass / total_inv)
b.position = b.position - correction * (b.inv_mass / total_inv)

# 2. Normal Impulse with Restitution
normal = mtv.normalized()
rel_vel = a.velocity - b.velocity
vel_along_normal = rel_vel.dot(normal)

if vel_along_normal <= 0:  # Moving towards each other
    restitution = min(a.restitution, b.restitution)
    j = -(1 + restitution) * vel_along_normal / total_inv
    impulse = normal * j
    if a.body_type == BodyType.DYNAMIC:
        a.velocity += impulse * a.inv_mass
    if b.body_type == BodyType.DYNAMIC:
        b.velocity -= impulse * b.inv_mass

    # 3. Tangent Friction Impulse (Coulomb Model)
    tangent_vel = rel_vel - normal * rel_vel.dot(normal)
    if tangent_vel.magnitude_sq() > 1e-9:
        tangent = tangent_vel.normalized()
        jt = -rel_vel.dot(tangent) / total_inv
        mu = (a.friction + b.friction) * 0.5
        jt = max(-j * mu, min(jt, j * mu))  # Clamped to friction cone
        friction_impulse = tangent * jt
        if a.body_type == BodyType.DYNAMIC:
            a.velocity += friction_impulse * a.inv_mass
        if b.body_type == BodyType.DYNAMIC:
            b.velocity -= friction_impulse * b.inv_mass
```
*Why this matters:* Positional correction prevents bodies from penetrating platforms due to discrete timestep truncation, while normal and tangential impulses accurately conserve momentum and simulate realistic surface friction.

### 4.2 Bresenham Line-of-Sight Path Smoothing
Located in [`game_module/ai/pathfinding.py`](file:///c:/Users/Ravitej%20Manu/Downloads/week2/game_module/ai/pathfinding.py):
```python
def smooth_path(self, path: list[Vector2]) -> list[Vector2]:
    if len(path) <= 2:
        return path[:]
    smoothed = [path[0]]
    i = 0
    while i < len(path) - 1:
        farthest = i + 1
        # Raycast backwards from goal towards current waypoint
        for j in range(len(path) - 1, i + 1, -1):
            if self._has_line_of_sight(path[i], path[j]):
                farthest = j
                break
        smoothed.append(path[farthest])
        i = farthest
    return smoothed
```
*Why this matters:* Standard A* produces jagged stair-step paths conforming to the grid. This algorithm uses Bresenham grid traversal to cast rays between distant waypoints, eliminating intermediate nodes whenever an unblocked straight line exists (e.g. compressing 19 waypoints down to 3).

### 4.3 Action Buffering & Coyote Time Jump Mechanics
Located in [`game_module/entities/player.py`](file:///c:/Users/Ravitej%20Manu/Downloads/week2/game_module/entities/player.py):
```python
# Coyote timer decays when in the air, resets when grounded
if self.body.is_grounded:
    self._coyote_timer = self._coyote_time
else:
    self._coyote_timer = max(0, self._coyote_timer - dt)

# Auto-buffer jump action for 0.15 seconds upon press
self.input.auto_buffer_on_press(Action.JUMP, self._jump_buffer)

# Execute jump if buffered and within coyote time window
can_jump = self._coyote_timer > 0 or self.body.is_grounded
if self.input.consume_buffer(Action.JUMP) and can_jump:
    self.body.velocity.y = -self.jump_force
    self._coyote_timer = 0
    self.body.is_grounded = False
```
*Why this matters:* In high-speed action platformers, strict binary ground checks cause missed jumps if the player presses jump slightly before touching down or right as they run off a ledge. Combining an input buffer with coyote time makes controls feel responsive and fair.

---

## 5. How to Compile, Test, and Run

### 5.1 Prerequisites
- **Python 3.10 or higher**
- No external libraries required for core simulation or tests.
- *(Optional)* `pygame` for graphical display mode:
  ```bash
  pip install pygame
  ```

### 5.2 Running the Automated Test Suite
The project contains 19 comprehensive unit and integration tests covering vector arithmetic, AABB intersection/depth, gravity integration, collision resolution, impulse response, A* pathfinding, path smoothing, FSM state transitions, input actions, buffers, combos, rebinding, and simulated combat.

Run all tests via the unified runner:
```bash
python run_tests.py
```

Or using Python's built-in `unittest` discovery:
```bash
python -m unittest discover tests
```

Or run individual test suites:
```bash
python tests/test_physics.py
python tests/test_ai.py
python tests/test_input.py
python tests/test_integration.py
```

### 5.3 Running the Simulation

#### Mode A: Headless Simulation (Default, No External Dependencies)
Runs a 60 Hz deterministic simulation showcasing physics gravity, static platform collisions, player movement, jump, dash, enemy state transitions (Idle $\to$ Patrol $\to$ Chase), combat damage callbacks, pathfinding, and combo detection:
```bash
python main.py
```

You can customize the simulation duration:
```bash
python main.py --duration 12.0
```

#### Mode B: Interactive Visual Demo (Requires `pygame`)
Launches a 60 FPS graphical window with real-time rendering, HUD, dynamic path visualization, collision debug boxes, and player controls:
```bash
python main.py --visual
```

#### Mode C: Interactive Web Engine Studio (`localhost:8000`)
Launches a web-based engine playground and live telemetry studio with zero external dependencies (pure standard library HTTP server + HTML5 Canvas):
```bash
python server.py
```
Open **[http://localhost:8000](http://localhost:8000)** in any modern web browser to access:
- **Interactive 60 FPS Canvas Simulation**: Real-time physics, collisions, jump buffers, dashes, and melee combat.
- **Live AI & Pathfinding Visualization**: View dynamic A* paths, line-of-sight rays, and enemy state transitions (`Idle` / `Patrol` / `Chase` / `Attack` / `Flee`).
- **Telemetry HUD**: Real-time position, velocity, grounding, coyote timer, and sensory radii.
- **One-Click Backend Integration**: Run unit tests and headless simulations directly from the browser UI.

**Controls in Interactive Mode:**
- **`A` / `D` or `Left` / `Right`**: Move player horizontally
- **`Space`**: Jump (Buffered + Coyote time enabled)
- **`Shift`**: Dash in facing direction
- **`J`**: Melee Attack (damages enemy when in range)
- **`R`**: Reset Sandbox
- **`Esc`**: Quit (in Pygame mode)

---

## 6. Adherence to Design Principles & Standards

1. **Clean Code & Modularity:**
   - Strict separation of concerns: Physics knows nothing of AI; Entities compose Physics and Input; State Machine is generic and decoupled.
   - 100% type-annotated codebase adhering to PEP 8 standards.
2. **Defensive Programming & Stability:**
   - Sub-stepping prevents high-speed penetration.
   - Zero-division checks on vector normalization and zero-mass bodies.
   - Comprehensive unit test coverage across edge cases (blocked paths, corner cases, empty inputs).
3. **Documentation:**
   - Every class, method, and module contains explicit docstrings explaining formulas, parameters, and invariants.

"""
Main Demo - headless simulation + optional pygame visual.

Run headless:
    python main.py

Run with visuals (requires pygame):
    pip install pygame
    python main.py --visual

This demo showcases:
- PhysicsWorld with gravity, static platforms, and dynamic bodies
- Player with InputHandler (WASD/Space/Shift), coyote time, buffered jump, dash
- Enemy AI (Idle -> Patrol -> Chase -> Attack -> Flee) with A* pathfinding
- Collision detection & resolution

No external dependencies for headless mode.
"""
from __future__ import annotations
import argparse
import time
import sys

from game_module.physics.vector2 import Vector2
from game_module.physics.rigidbody import Rigidbody, BodyType
from game_module.physics.world import PhysicsWorld
from game_module.input.handler import InputHandler, Action
from game_module.entities.player import Player
from game_module.entities.enemy import Enemy
from game_module.ai.pathfinding import AStarPathfinder


# ---------------------------------------------------------------------------
# World setup shared by both modes
# ---------------------------------------------------------------------------

def create_world_and_entities():
    world = PhysicsWorld(gravity=Vector2(0, 22.0), sub_steps=4)

    # Ground
    ground = Rigidbody(name="ground", body_type=BodyType.STATIC,
                       position=Vector2(10, 19), size=Vector2(20, 2),
                       friction=0.6)
    world.add_body(ground)

    # Platforms
    plat1 = Rigidbody(name="plat1", body_type=BodyType.STATIC,
                      position=Vector2(5, 14), size=Vector2(6, 0.8), friction=0.5)
    plat2 = Rigidbody(name="plat2", body_type=BodyType.STATIC,
                      position=Vector2(14, 11), size=Vector2(5, 0.8), friction=0.5)
    plat3 = Rigidbody(name="plat3", body_type=BodyType.STATIC,
                      position=Vector2(8, 7), size=Vector2(4, 0.8), friction=0.5)
    for p in [plat1, plat2, plat3]:
        world.add_body(p)

    # Walls
    left_wall = Rigidbody(name="wall_l", body_type=BodyType.STATIC,
                          position=Vector2(0, 10), size=Vector2(1, 20))
    right_wall = Rigidbody(name="wall_r", body_type=BodyType.STATIC,
                           position=Vector2(20, 10), size=Vector2(1, 20))
    world.add_body(left_wall)
    world.add_body(right_wall)

    # Player
    player_body = Rigidbody(name="player", body_type=BodyType.DYNAMIC,
                            position=Vector2(3, 5), size=Vector2(0.9, 1.4),
                            mass=1.0, restitution=0.0, friction=0.4,
                            drag=0.05, gravity_scale=1.0)
    world.add_body(player_body)
    input_handler = InputHandler()
    player = Player(body=player_body, input=input_handler)

    # Enemy
    enemy_body = Rigidbody(name="enemy", body_type=BodyType.DYNAMIC,
                           position=Vector2(15, 5), size=Vector2(0.9, 1.4),
                           mass=1.0, restitution=0.0, friction=0.4,
                           drag=0.05)
    world.add_body(enemy_body)

    # Grid for pathfinding (20x20 cells, 1 unit per cell)
    grid = [[0 for _ in range(20)] for _ in range(20)]
    # Mark ground & platforms as blocked in grid
    for b in [ground, plat1, plat2, plat3, left_wall, right_wall]:
        mi, ma = b.aabb.min, b.aabb.max
        for y in range(int(mi.y), int(ma.y) + 1):
            for x in range(int(mi.x), int(ma.x) + 1):
                if 0 <= x < 20 and 0 <= y < 20:
                    grid[y][x] = 1

    pathfinder = AStarPathfinder(grid, cell_size=1.0, allow_diagonal=True)

    enemy = Enemy(body=enemy_body, player_pos=player_body.position.copy(),
                  waypoints=[Vector2(14, 5), Vector2(16, 5), Vector2(15, 10)],
                  world=world, pathfinder=pathfinder)

    # Damage callback
    def on_enemy_attack(dmg: float):
        player.take_damage(dmg)
        print(f"[COMBAT] Enemy attacked player for {dmg} dmg. Player HP: {player.hp:.0f}")

    enemy.on_attack_cb = on_enemy_attack

    return world, player, enemy, pathfinder


# ---------------------------------------------------------------------------
# Headless demo
# ---------------------------------------------------------------------------

def run_headless(duration: float = 8.0):
    print("=== Game Module - Headless Simulation ===")
    world, player, enemy, _ = create_world_and_entities()
    dt = 1 / 60
    steps = int(duration / dt)

    # Scripted input sequence to showcase mechanics
    # [0-1s] move right, [1-1.2s] jump, [2-3s] move right, [3s] dash, [4-6s] move left
    def script_input(t: float, handler: InputHandler):
        # Reset keys
        for k in ["a", "d", "space", "shift", "left", "right"]:
            handler.feed(k, False)
        if 0.0 <= t < 1.0:
            handler.feed("d", True)
        elif 1.0 <= t < 1.05:
            handler.feed("space", True)
            handler.feed("d", True)
        elif 2.0 <= t < 3.0:
            handler.feed("d", True)
        elif 3.0 <= t < 3.1:
            handler.feed("shift", True)
        elif 4.0 <= t < 6.0:
            handler.feed("a", True)

    print(f"Simulating {duration}s at {1/dt:.0f} Hz ...\n")
    print(f"{'t':>5} | {'player_pos':>16} | {'vel':>14} | {'grounded':>8} | {'enemy_pos':>16} | {'enemy_state':>10} | HP")
    print("-" * 95)

    for i in range(steps):
        t = i * dt
        script_input(t, player.input)
        player.input.update(dt)
        player.update(dt)
        enemy.update(dt, player.body.position)
        world.step(dt)

        if i % 30 == 0:  # every 0.5s
            p = player.body.position
            v = player.body.velocity
            e = enemy.body.position
            print(f"{t:5.2f} | ({p.x:5.2f},{p.y:5.2f}) | ({v.x:5.2f},{v.y:5.2f}) | {str(player.body.is_grounded):>8} | ({e.x:5.2f},{e.y:5.2f}) | {enemy.state_name:>10} | {player.hp:.0f}/{enemy.hp:.0f}")

        # Simulate player attacking when close
        if player.body.position.distance_to(enemy.body.position) < 1.6:
            if i % 50 == 0:
                enemy.take_damage(8)
                # print(f"[COMBAT] Player hit enemy. Enemy HP: {enemy.hp:.0f}")

        if not player.is_alive or not enemy.is_alive:
            break

    print("\n--- Simulation finished ---")
    print(f"Player: pos={player.body.position} hp={player.hp:.0f} alive={player.is_alive}")
    print(f"Enemy:  pos={enemy.body.position} hp={enemy.hp:.0f} state={enemy.state_name} alive={enemy.is_alive}")

    # Pathfinding demo
    print("\n--- Pathfinding Demo ---")
    _, _, _, pf = create_world_and_entities()
    start, goal = Vector2(2, 2), Vector2(17, 16)
    path = pf.find_path(start, goal)
    print(f"Path from {start} to {goal}: {len(path)} waypoints")
    if path:
        print(f"  Start: {path[0]}")
        print(f"  End:   {path[-1]}")
        sm = pf.smooth_path(path)
        print(f"  Smoothed: {len(sm)} waypoints (was {len(path)})")

    # Input handler combo demo
    print("\n--- Input Handler Demo ---")
    ih = InputHandler()
    for k in ["w", "w", "s", "s", "a", "d", "a", "d"]:
        ih.feed(k, True)
        ih.update(0.1)
        ih.feed(k, False)
        ih.update(0.05)
    print(f"History: {list(ih._history)}")
    # Simple combo check
    ih2 = InputHandler()
    for k in ["a", "b", "c"]:
        ih2.feed(k, True); ih2.update(0.1); ih2.feed(k, False); ih2.update(0.05)
    print(f"Combo ['a','b','c'] detected: {ih2.check_combo(['a','b','c'], max_interval=0.3)}")
    print(f"Combo ['x','y'] detected: {ih2.check_combo(['x','y'], max_interval=0.3)}")

    print("\nAll modules functional. Run with --visual for pygame demo.")


# ---------------------------------------------------------------------------
# Visual demo (pygame optional)
# ---------------------------------------------------------------------------

def run_visual():
    try:
        import pygame
    except ImportError:
        print("pygame not installed. Install with: pip install pygame")
        print("Falling back to headless mode.\n")
        run_headless()
        return

    world, player, enemy, _ = create_world_and_entities()

    pygame.init()
    WIDTH, HEIGHT = 900, 700
    SCALE = 32  # pixels per world unit
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Game Module Demo - WASD/Arrows Move | Space Jump | Shift Dash | J Attack")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)
    small_font = pygame.font.SysFont("consolas", 12)

    # Key map pygame -> handler names
    key_map = {
        pygame.K_a: "a", pygame.K_d: "d", pygame.K_w: "w", pygame.K_s: "s",
        pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
        pygame.K_UP: "up", pygame.K_DOWN: "down",
        pygame.K_SPACE: "space",
        pygame.K_LSHIFT: "shift", pygame.K_RSHIFT: "shift",
        pygame.K_j: "j", pygame.K_e: "e", pygame.K_ESCAPE: "escape",
    }

    def world_to_screen(pos: Vector2) -> tuple[int, int]:
        return (int(pos.x * SCALE), int(pos.y * SCALE))

    def draw_body(body: Rigidbody, color, label=""):
        mi = world_to_screen(body.aabb.min)
        wh = (int(body.size.x * SCALE), int(body.size.y * SCALE))
        rect = pygame.Rect(mi[0], mi[1], wh[0], wh[1])
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (255, 255, 255), rect, 1)
        if label:
            t = small_font.render(label, True, (255, 255, 255))
            screen.blit(t, (mi[0], mi[1] - 14))

    running = True
    dt = 0
    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 1 / 30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                name = key_map.get(event.key)
                if name:
                    player.input.feed(name, True)
                # Attack: damage enemy if close
                if event.key == pygame.K_j:
                    if player.body.position.distance_to(enemy.body.position) < 1.8:
                        enemy.take_damage(15)
            elif event.type == pygame.KEYUP:
                name = key_map.get(event.key)
                if name:
                    player.input.feed(name, False)

        player.input.update(dt)
        player.update(dt)
        enemy.update(dt, player.body.position)
        world.step(dt)

        # Player melee with J already handled; also continuous overlap damage from enemy is via AI AttackState
        # (enemy calls on_attack_cb)

        # Draw
        screen.fill((18, 18, 28))

        # Grid
        for x in range(0, WIDTH, SCALE):
            pygame.draw.line(screen, (30, 30, 45), (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, SCALE):
            pygame.draw.line(screen, (30, 30, 45), (0, y), (WIDTH, y))

        # Bodies
        for b in world.bodies:
            if b.name.startswith("ground") or b.name.startswith("plat") or b.name.startswith("wall"):
                draw_body(b, (70, 70, 90), b.name)
            elif b.name == "player":
                draw_body(b, (80, 200, 120), "PLAYER")
            elif b.name == "enemy":
                col = (220, 80, 80) if enemy.state_name == "Attack" else (220, 180, 60)
                draw_body(b, col, f"ENEMY:{enemy.state_name}")

        # Enemy path
        if enemy.path:
            pts = [world_to_screen(p) for p in enemy.path]
            if len(pts) > 1:
                pygame.draw.lines(screen, (100, 180, 255), False, pts, 2)
            for pt in pts:
                pygame.draw.circle(screen, (100, 180, 255), pt, 4)

        # HUD
        hud = [
            f"Player  HP: {player.hp:.0f}  Pos: {player.body.position}  Vel: {player.body.velocity}  Grounded: {player.body.is_grounded}",
            f"Enemy   HP: {enemy.hp:.0f}  State: {enemy.state_name}  Pos: {enemy.body.position}",
            f"Controls: WASD/Arrows Move  SPACE Jump (buffered+coyote)  SHIFT Dash  J Attack  ESC Quit",
            f"FPS: {clock.get_fps():.0f}",
        ]
        for i, line in enumerate(hud):
            t = font.render(line, True, (220, 220, 230))
            screen.blit(t, (8, 8 + i * 18))

        if not player.is_alive:
            t = font.render("PLAYER DEFEATED - Press ESC to quit", True, (255, 80, 80))
            screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2))
        elif not enemy.is_alive:
            t = font.render("ENEMY DEFEATED!", True, (80, 255, 120))
            screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Game Module Demo")
    parser.add_argument("--visual", action="store_true", help="Run pygame visual demo")
    parser.add_argument("--duration", type=float, default=8.0, help="Headless duration seconds")
    args = parser.parse_args()

    if args.visual:
        run_visual()
    else:
        run_headless(duration=args.duration)

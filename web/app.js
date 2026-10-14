/**
 * Game Module - Interactive Canvas Engine & Telemetry Studio
 * Replicates the Python physics, AI state machine, and player input subsystems
 * with real-time HUD telemetry and Python backend test integration.
 */

(function () {
    // Canvas & Setup
    const canvas = document.getElementById("game-canvas");
    const ctx = canvas.getContext("2d");
    const SCALE = 32; // pixels per world unit

    // UI Elements
    const statPlayerPos = document.getElementById("stat-player-pos");
    const statPlayerVel = document.getElementById("stat-player-vel");
    const statPlayerGrounded = document.getElementById("stat-player-grounded");
    const statPlayerCoyote = document.getElementById("stat-player-coyote");
    const statPlayerDash = document.getElementById("stat-player-dash");
    const statPlayerBuffer = document.getElementById("stat-player-buffer");
    const playerHpBadge = document.getElementById("player-hp-badge");
    const playerHpBar = document.getElementById("player-hp-bar");

    const statEnemyPos = document.getElementById("stat-enemy-pos");
    const statEnemyDist = document.getElementById("stat-enemy-dist");
    const statEnemyWaypoints = document.getElementById("stat-enemy-waypoints");
    const statEnemyLos = document.getElementById("stat-enemy-los");
    const enemyStateBadge = document.getElementById("enemy-state-badge");
    const enemyHpBar = document.getElementById("enemy-hp-bar");

    const sliderGravity = document.getElementById("slider-gravity");
    const labelGravity = document.getElementById("label-gravity");
    const sliderJump = document.getElementById("slider-jump");
    const labelJump = document.getElementById("label-jump");

    const toggleColliders = document.getElementById("toggle-colliders");
    const togglePath = document.getElementById("toggle-path");
    const toggleRanges = document.getElementById("toggle-ranges");
    const toggleGrid = document.getElementById("toggle-grid");

    const btnReset = document.getElementById("btn-reset-game");
    const btnSpawnBox = document.getElementById("btn-spawn-box");
    const btnDamageEnemy = document.getElementById("btn-damage-enemy");
    const btnRunTests = document.getElementById("btn-run-tests");
    const btnRunSim = document.getElementById("btn-run-sim");
    const terminalOutput = document.getElementById("terminal-output");
    const combatBanner = document.getElementById("combat-banner");
    const combatBannerText = document.getElementById("combat-banner-text");
    const fpsCounter = document.getElementById("fps-counter");

    // Math Classes
    class Vector2 {
        constructor(x = 0, y = 0) {
            this.x = x;
            this.y = y;
        }
        copy() { return new Vector2(this.x, this.y); }
        add(v) { return new Vector2(this.x + v.x, this.y + v.y); }
        sub(v) { return new Vector2(this.x - v.x, this.y - v.y); }
        mul(s) { return new Vector2(this.x * s, this.y * s); }
        div(s) { return s !== 0 ? new Vector2(this.x / s, this.y / s) : new Vector2(); }
        dot(v) { return this.x * v.x + this.y * v.y; }
        magSq() { return this.x * this.x + this.y * this.y; }
        mag() { return Math.sqrt(this.magSq()); }
        dist(v) { return this.sub(v).mag(); }
        normalized() {
            const m = this.mag();
            return m > 1e-9 ? this.div(m) : new Vector2(0, 0);
        }
    }

    class AABB {
        constructor(min, max) {
            this.min = min;
            this.max = max;
        }
        intersects(other) {
            return (
                this.min.x <= other.max.x &&
                this.max.x >= other.min.x &&
                this.min.y <= other.max.y &&
                this.max.y >= other.min.y
            );
        }
        getDepth(other) {
            const dx1 = other.max.x - this.min.x;
            const dx2 = this.max.x - other.min.x;
            const dy1 = other.max.y - this.min.y;
            const dy2 = this.max.y - other.min.y;

            const ox = Math.min(dx1, dx2);
            const oy = Math.min(dy1, dy2);

            if (ox <= 0 || oy <= 0) return null;

            if (ox < oy) {
                return new Vector2(dx1 < dx2 ? -ox : ox, 0);
            } else {
                return new Vector2(0, dy1 < dy2 ? -oy : oy);
            }
        }
    }

    // Physics Engine
    class Rigidbody {
        constructor(name, type, pos, size, mass = 1.0, friction = 0.5, restitution = 0.0) {
            this.name = name;
            this.type = type; // "STATIC" or "DYNAMIC"
            this.position = pos.copy();
            this.size = size.copy();
            this.mass = mass;
            this.invMass = type === "STATIC" ? 0 : 1 / mass;
            this.velocity = new Vector2(0, 0);
            this.friction = friction;
            this.restitution = restitution;
            this.isGrounded = false;
        }
        get aabb() {
            const hx = this.size.x / 2;
            const hy = this.size.y / 2;
            return new AABB(
                new Vector2(this.position.x - hx, this.position.y - hy),
                new Vector2(this.position.x + hx, this.position.y + hy)
            );
        }
        integrate(dt, gravity) {
            if (this.type === "STATIC") return;
            this.velocity = this.velocity.add(gravity.mul(dt));
            this.position = this.position.add(this.velocity.mul(dt));
        }
    }

    class PhysicsWorld {
        constructor(gravity = new Vector2(0, 22), subSteps = 4) {
            this.gravity = gravity;
            this.subSteps = subSteps;
            this.bodies = [];
        }
        add(b) { this.bodies.push(b); }
        step(dt) {
            const subDt = dt / this.subSteps;
            for (let s = 0; s < this.subSteps; s++) {
                for (const b of this.bodies) {
                    if (b.type === "DYNAMIC") {
                        b.isGrounded = false;
                        b.integrate(subDt, this.gravity);
                    }
                }
                this.resolveCollisions();
            }
        }
        resolveCollisions() {
            for (let i = 0; i < this.bodies.length; i++) {
                for (let j = i + 1; j < this.bodies.length; j++) {
                    const a = this.bodies[i];
                    const b = this.bodies[j];
                    if (a.type === "STATIC" && b.type === "STATIC") continue;

                    const mtv = a.aabb.getDepth(b.aabb);
                    if (!mtv || mtv.magSq() < 1e-9) continue;

                    const totalInv = a.invMass + b.invMass;
                    if (totalInv === 0) continue;

                    // Positional separation (Baumgarte)
                    const percent = 0.8;
                    const corr = mtv.mul(percent);
                    if (a.type === "DYNAMIC") a.position = a.position.add(corr.mul(a.invMass / totalInv));
                    if (b.type === "DYNAMIC") b.position = b.position.sub(corr.mul(b.invMass / totalInv));

                    // Normal impulse
                    const normal = mtv.normalized();
                    const relVel = a.velocity.sub(b.velocity);
                    const velNorm = relVel.dot(normal);

                    if (velNorm <= 0) {
                        const rest = Math.min(a.restitution, b.restitution);
                        const jImp = -(1 + rest) * velNorm / totalInv;
                        const impulse = normal.mul(jImp);
                        if (a.type === "DYNAMIC") a.velocity = a.velocity.add(impulse.mul(a.invMass));
                        if (b.type === "DYNAMIC") b.velocity = b.velocity.sub(impulse.mul(b.invMass));

                        // Coulomb Friction
                        const tanVel = relVel.sub(normal.mul(velNorm));
                        if (tanVel.magSq() > 1e-9) {
                            const tangent = tanVel.normalized();
                            let jt = -relVel.dot(tangent) / totalInv;
                            const mu = (a.friction + b.friction) * 0.5;
                            jt = Math.max(-jImp * mu, Math.min(jt, jImp * mu));
                            const fImp = tangent.mul(jt);
                            if (a.type === "DYNAMIC") a.velocity = a.velocity.add(fImp.mul(a.invMass));
                            if (b.type === "DYNAMIC") b.velocity = b.velocity.sub(fImp.mul(b.invMass));
                        }
                    }

                    // Grounded check (positive Y is down)
                    if (mtv.y < 0 && Math.abs(mtv.y) > Math.abs(mtv.x)) {
                        if (a.type === "DYNAMIC") a.isGrounded = true;
                    } else if (mtv.y > 0 && Math.abs(mtv.y) > Math.abs(mtv.x)) {
                        if (b.type === "DYNAMIC") b.isGrounded = true;
                    }
                }
            }
        }
    }

    // A* Pathfinding with smoothing
    class AStarPathfinder {
        constructor(grid, cellSize = 1.0) {
            this.grid = grid;
            this.rows = grid.length;
            this.cols = grid[0].length;
            this.cellSize = cellSize;
        }
        isWalkable(x, y) {
            return x >= 0 && x < this.cols && y >= 0 && y < this.rows && this.grid[y][x] === 0;
        }
        toCell(pos) {
            return { x: Math.floor(pos.x / this.cellSize), y: Math.floor(pos.y / this.cellSize) };
        }
        toWorld(cx, cy) {
            return new Vector2((cx + 0.5) * this.cellSize, (cy + 0.5) * this.cellSize);
        }
        findPath(start, goal) {
            const s = this.toCell(start);
            const g = this.toCell(goal);
            if (!this.isWalkable(s.x, s.y) || !this.isWalkable(g.x, g.y)) return [];
            if (s.x === g.x && s.y === g.y) return [this.toWorld(s.x, s.y)];

            const open = [{ x: s.x, y: s.y, g: 0, f: this.heuristic(s, g) }];
            const cameFrom = new Map();
            const gScores = new Map();
            gScores.set(`${s.x},${s.y}`, 0);

            while (open.length > 0) {
                open.sort((a, b) => a.f - b.f);
                const cur = open.shift();

                if (cur.x === g.x && cur.y === g.y) {
                    const path = [];
                    let c = `${g.x},${g.y}`;
                    while (cameFrom.has(c)) {
                        const [px, py] = c.split(",").map(Number);
                        path.unshift(this.toWorld(px, py));
                        c = cameFrom.get(c);
                    }
                    path.unshift(this.toWorld(s.x, s.y));
                    return path;
                }

                const dirs = [
                    { dx: 1, dy: 0, cost: 1 }, { dx: -1, dy: 0, cost: 1 },
                    { dx: 0, dy: 1, cost: 1 }, { dx: 0, dy: -1, cost: 1 },
                    { dx: 1, dy: 1, cost: Math.SQRT2 }, { dx: 1, dy: -1, cost: Math.SQRT2 },
                    { dx: -1, dy: 1, cost: Math.SQRT2 }, { dx: -1, dy: -1, cost: Math.SQRT2 }
                ];

                for (const d of dirs) {
                    const nx = cur.x + d.dx;
                    const ny = cur.y + d.dy;
                    if (!this.isWalkable(nx, ny)) continue;
                    if (d.dx !== 0 && d.dy !== 0) {
                        if (!this.isWalkable(cur.x + d.dx, cur.y) || !this.isWalkable(cur.x, cur.y + d.dy)) continue;
                    }
                    const nKey = `${nx},${ny}`;
                    const tentative = (gScores.get(`${cur.x},${cur.y}`) || 0) + d.cost;
                    if (tentative < (gScores.get(nKey) ?? Infinity)) {
                        cameFrom.set(nKey, `${cur.x},${cur.y}`);
                        gScores.set(nKey, tentative);
                        const f = tentative + this.heuristic({ x: nx, y: ny }, g);
                        open.push({ x: nx, y: ny, g: tentative, f });
                    }
                }
            }
            return [];
        }
        heuristic(a, b) {
            const dx = Math.abs(a.x - b.x);
            const dy = Math.abs(a.y - b.y);
            return Math.max(dx, dy) + (Math.SQRT2 - 1) * Math.min(dx, dy);
        }
        hasLOS(p1, p2) {
            const c1 = this.toCell(p1);
            const c2 = this.toCell(p2);
            let x0 = c1.x, y0 = c1.y, x1 = c2.x, y1 = c2.y;
            const dx = Math.abs(x1 - x0);
            const dy = Math.abs(y1 - y0);
            const sx = x0 < x1 ? 1 : -1;
            const sy = y0 < y1 ? 1 : -1;
            let err = dx - dy;

            while (true) {
                if (!this.isWalkable(x0, y0)) return false;
                if (x0 === x1 && y0 === y1) break;
                const e2 = 2 * err;
                if (e2 > -dy) { err -= dy; x0 += sx; }
                if (e2 < dx) { err += dx; y0 += sy; }
            }
            return true;
        }
        smoothPath(path) {
            if (path.length <= 2) return path;
            const smoothed = [path[0]];
            let i = 0;
            while (i < path.length - 1) {
                let farthest = i + 1;
                for (let j = path.length - 1; j > i + 1; j--) {
                    if (this.hasLOS(path[i], path[j])) {
                        farthest = j;
                        break;
                    }
                }
                smoothed.push(path[farthest]);
                i = farthest;
            }
            return smoothed;
        }
    }

    // Floating damage texts & effects
    const particles = [];
    function spawnDamageText(text, pos, color = "#ef4444") {
        particles.push({
            text,
            x: pos.x * SCALE,
            y: pos.y * SCALE,
            vx: (Math.random() - 0.5) * 40,
            vy: -50 - Math.random() * 30,
            life: 0.8,
            maxLife: 0.8,
            color
        });
    }

    // World & Entities State
    let world, player, enemy, pathfinder;
    let keysDown = {};
    let jumpBufferTimer = 0;
    let dashCooldownTimer = 0;
    let coyoteTimer = 0;
    let screenShake = 0;

    function initGame() {
        world = new PhysicsWorld(new Vector2(0, parseFloat(sliderGravity.value)), 4);

        // Ground (y=19, size 24x2)
        const ground = new Rigidbody("ground", "STATIC", new Vector2(14, 19.5), new Vector2(28, 2), 0, 0.6);
        world.add(ground);

        // Platforms
        const p1 = new Rigidbody("plat1", "STATIC", new Vector2(7, 14.5), new Vector2(7, 0.8), 0, 0.5);
        const p2 = new Rigidbody("plat2", "STATIC", new Vector2(18, 12), new Vector2(7, 0.8), 0, 0.5);
        const p3 = new Rigidbody("plat3", "STATIC", new Vector2(12, 7.5), new Vector2(6, 0.8), 0, 0.5);
        world.add(p1);
        world.add(p2);
        world.add(p3);

        // Boundaries
        const wallL = new Rigidbody("wallL", "STATIC", new Vector2(0.2, 10), new Vector2(0.8, 22), 0, 0.5);
        const wallR = new Rigidbody("wallR", "STATIC", new Vector2(27.8, 10), new Vector2(0.8, 22), 0, 0.5);
        world.add(wallL);
        world.add(wallR);

        // Player Body
        const pBody = new Rigidbody("player", "DYNAMIC", new Vector2(4, 10), new Vector2(1.1, 1.5), 1.0, 0.4, 0.0);
        world.add(pBody);

        player = {
            body: pBody,
            hp: 100,
            maxHp: 100,
            speed: 8.0,
            facing: 1,
            isAlive: true
        };

        // Enemy Body
        const eBody = new Rigidbody("enemy", "DYNAMIC", new Vector2(18, 9), new Vector2(1.1, 1.5), 1.0, 0.4, 0.0);
        world.add(eBody);

        enemy = {
            body: eBody,
            hp: 80,
            maxHp: 80,
            state: "Idle",
            stateTimer: 0,
            attackTimer: 0,
            waypoints: [new Vector2(15, 10), new Vector2(21, 10), new Vector2(12, 6)],
            waypointIdx: 0,
            path: [],
            pathTimer: 0,
            isAlive: true
        };

        // 28x22 occupancy grid for pathfinding
        const grid = Array.from({ length: 22 }, () => Array(28).fill(0));
        for (const b of [ground, p1, p2, p3, wallL, wallR]) {
            const minX = Math.max(0, Math.floor(b.aabb.min.x));
            const maxX = Math.min(27, Math.ceil(b.aabb.max.x));
            const minY = Math.max(0, Math.floor(b.aabb.min.y));
            const maxY = Math.min(21, Math.ceil(b.aabb.max.y));
            for (let y = minY; y <= maxY; y++) {
                for (let x = minX; x <= maxX; x++) {
                    grid[y][x] = 1;
                }
            }
        }
        pathfinder = new AStarPathfinder(grid, 1.0);

        combatBanner.classList.add("hidden");
    }

    // Input Listeners
    window.addEventListener("keydown", (e) => {
        const k = e.key.toLowerCase();
        keysDown[k] = true;

        if (e.code === "Space") {
            jumpBufferTimer = 0.15; // 150ms buffer
        }
        if (e.key === "Shift") {
            tryDash();
        }
        if (k === "j") {
            tryPlayerAttack();
        }
        if (k === "r") {
            initGame();
        }
    });

    window.addEventListener("keyup", (e) => {
        keysDown[e.key.toLowerCase()] = false;
    });

    function tryDash() {
        if (dashCooldownTimer <= 0 && player.isAlive) {
            player.body.velocity.x += player.facing * 16.0;
            dashCooldownTimer = 0.6;
            screenShake = 0.15;
            spawnDamageText("DASH!", player.body.position, "#06b6d4");
        }
    }

    function tryPlayerAttack() {
        if (!player.isAlive || !enemy.isAlive) return;
        const dist = player.body.position.dist(enemy.body.position);
        if (dist < 2.0) {
            enemy.hp = Math.max(0, enemy.hp - 20);
            screenShake = 0.2;
            spawnDamageText("-20", enemy.body.position, "#fca5a5");
            // Knockback
            const dir = enemy.body.position.sub(player.body.position).normalized();
            enemy.body.velocity = enemy.body.velocity.add(dir.mul(8.0).add(new Vector2(0, -4)));
            if (enemy.hp <= 0) {
                enemy.isAlive = false;
                combatBannerText.innerText = "ENEMY DEFEATED!";
                combatBanner.classList.remove("hidden");
            }
        } else {
            spawnDamageText("MISS", player.body.position, "#94a3b8");
        }
    }

    // Enemy AI Update (FSM)
    function updateEnemyAI(dt) {
        if (!enemy.isAlive) return;

        enemy.stateTimer += dt;
        enemy.attackTimer -= dt;
        enemy.pathTimer -= dt;

        const distToPlayer = enemy.body.position.dist(player.body.position);
        const hasLOS = pathfinder.hasLOS(enemy.body.position, player.body.position);

        // State Transitions
        if (enemy.hp < enemy.maxHp * 0.25) {
            enemy.state = "Flee";
        } else if (distToPlayer <= 1.6) {
            enemy.state = "Attack";
        } else if (distToPlayer <= 10.0 && hasLOS) {
            enemy.state = "Chase";
        } else if (enemy.state === "Chase" && distToPlayer > 12.0) {
            enemy.state = "Idle";
            enemy.stateTimer = 0;
        } else if (enemy.state === "Idle" && enemy.stateTimer > 2.0) {
            enemy.state = "Patrol";
        }

        // State Behaviors & Steering
        let desiredVx = 0;
        if (enemy.state === "Idle") {
            desiredVx = 0;
        } else if (enemy.state === "Patrol") {
            const targetWp = enemy.waypoints[enemy.waypointIdx];
            const toWp = targetWp.sub(enemy.body.position);
            if (toWp.mag() < 0.8) {
                enemy.waypointIdx = (enemy.waypointIdx + 1) % enemy.waypoints.length;
            }
            desiredVx = Math.sign(toWp.x) * 3.5;
        } else if (enemy.state === "Chase") {
            if (enemy.pathTimer <= 0) {
                enemy.pathTimer = 0.35;
                const rawPath = pathfinder.findPath(enemy.body.position, player.body.position);
                enemy.path = pathfinder.smoothPath(rawPath);
            }
            if (enemy.path && enemy.path.length > 1) {
                const nextNode = enemy.path[1];
                const toNode = nextNode.sub(enemy.body.position);
                desiredVx = Math.sign(toNode.x) * 5.5;
                if (toNode.y < -1.0 && enemy.body.isGrounded) {
                    enemy.body.velocity.y = -11.0; // AI Jump platform
                }
            } else {
                desiredVx = Math.sign(player.body.position.x - enemy.body.position.x) * 5.5;
            }
        } else if (enemy.state === "Attack") {
            desiredVx = 0;
            if (enemy.attackTimer <= 0 && player.isAlive) {
                enemy.attackTimer = 0.9;
                player.hp = Math.max(0, player.hp - 15);
                screenShake = 0.3;
                spawnDamageText("-15", player.body.position, "#ef4444");
                const dir = player.body.position.sub(enemy.body.position).normalized();
                player.body.velocity = player.body.velocity.add(dir.mul(10).add(new Vector2(0, -5)));
                if (player.hp <= 0) {
                    player.isAlive = false;
                    combatBannerText.innerText = "PLAYER DEFEATED - Press R to Restart";
                    combatBanner.classList.remove("hidden");
                }
            }
        } else if (enemy.state === "Flee") {
            const away = enemy.body.position.sub(player.body.position);
            desiredVx = Math.sign(away.x) * 6.5;
            if (enemy.body.isGrounded && Math.random() < 0.05) {
                enemy.body.velocity.y = -10.0;
            }
        }

        // Apply smooth steering
        const diff = desiredVx - enemy.body.velocity.x;
        enemy.body.velocity.x += diff * Math.min(1.0, 10 * dt);
    }

    // Main Update Loop
    let lastTime = performance.now();
    let frameCount = 0;
    let fpsTimer = 0;

    function gameLoop(now) {
        let dt = (now - lastTime) / 1000.0;
        lastTime = now;
        dt = Math.min(dt, 1 / 20); // avoid spiral of death

        frameCount++;
        fpsTimer += dt;
        if (fpsTimer >= 0.5) {
            fpsCounter.innerText = `${Math.round(frameCount / fpsTimer)} FPS`;
            frameCount = 0;
            fpsTimer = 0;
        }

        // Coyote & buffer timers
        if (player.body.isGrounded) {
            coyoteTimer = 0.12;
        } else {
            coyoteTimer = Math.max(0, coyoteTimer - dt);
        }
        jumpBufferTimer = Math.max(0, jumpBufferTimer - dt);
        dashCooldownTimer = Math.max(0, dashCooldownTimer - dt);
        screenShake = Math.max(0, screenShake - dt);

        // Player movement
        if (player.isAlive) {
            let axis = 0;
            if (keysDown["a"] || keysDown["arrowleft"]) axis -= 1;
            if (keysDown["d"] || keysDown["arrowright"]) axis += 1;

            if (axis !== 0) {
                player.facing = axis;
                const targetVx = axis * player.speed;
                const diff = targetVx - player.body.velocity.x;
                player.body.velocity.x += diff * Math.min(1.0, 14 * dt);
            } else {
                player.body.velocity.x *= Math.max(0, 1 - 10 * dt);
                if (Math.abs(player.body.velocity.x) < 0.05) player.body.velocity.x = 0;
            }

            // Buffered jump + coyote time
            const canJump = coyoteTimer > 0 || player.body.isGrounded;
            if (jumpBufferTimer > 0 && canJump) {
                const jumpForce = parseFloat(sliderJump.value);
                player.body.velocity.y = -jumpForce;
                coyoteTimer = 0;
                jumpBufferTimer = 0;
                player.body.isGrounded = false;
            }
        }

        // Physics step & AI update
        world.gravity.y = parseFloat(sliderGravity.value);
        world.step(dt);
        updateEnemyAI(dt);

        // Update Particles
        for (let i = particles.length - 1; i >= 0; i--) {
            const p = particles[i];
            p.life -= dt;
            p.x += p.vx * dt;
            p.y += p.vy * dt;
            if (p.life <= 0) particles.splice(i, 1);
        }

        render();
        updateHUD();
        requestAnimationFrame(gameLoop);
    }

    // Render Canvas
    function render() {
        ctx.save();
        if (screenShake > 0) {
            const mag = screenShake * 16;
            ctx.translate((Math.random() - 0.5) * mag, (Math.random() - 0.5) * mag);
        }

        ctx.fillStyle = "#0c101b";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Grid
        if (toggleGrid.checked) {
            ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
            ctx.lineWidth = 1;
            for (let x = 0; x < canvas.width; x += SCALE) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
            }
            for (let y = 0; y < canvas.height; y += SCALE) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
            }
        }

        // Sensory Radii
        if (toggleRanges.checked && enemy.isAlive) {
            ctx.strokeStyle = "rgba(245, 158, 11, 0.15)";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(enemy.body.position.x * SCALE, enemy.body.position.y * SCALE, 10 * SCALE, 0, Math.PI * 2);
            ctx.stroke();

            ctx.strokeStyle = "rgba(239, 68, 68, 0.35)";
            ctx.beginPath();
            ctx.arc(enemy.body.position.x * SCALE, enemy.body.position.y * SCALE, 1.6 * SCALE, 0, Math.PI * 2);
            ctx.stroke();
        }

        // A* Path
        if (togglePath.checked && enemy.path && enemy.path.length > 1) {
            ctx.strokeStyle = "#06b6d4";
            ctx.lineWidth = 3;
            ctx.setLineDash([6, 4]);
            ctx.beginPath();
            for (let i = 0; i < enemy.path.length; i++) {
                const pt = enemy.path[i];
                if (i === 0) ctx.moveTo(pt.x * SCALE, pt.y * SCALE);
                else ctx.lineTo(pt.x * SCALE, pt.y * SCALE);
            }
            ctx.stroke();
            ctx.setLineDash([]);

            // Draw nodes
            for (const pt of enemy.path) {
                ctx.fillStyle = "#22d3ee";
                ctx.beginPath();
                ctx.arc(pt.x * SCALE, pt.y * SCALE, 4, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        // Bodies
        for (const b of world.bodies) {
            const rx = b.aabb.min.x * SCALE;
            const ry = b.aabb.min.y * SCALE;
            const rw = b.size.x * SCALE;
            const rh = b.size.y * SCALE;

            if (b.type === "STATIC") {
                ctx.fillStyle = "#1e293b";
                ctx.fillRect(rx, ry, rw, rh);
                ctx.strokeStyle = "#334155";
                ctx.lineWidth = 1.5;
                ctx.strokeRect(rx, ry, rw, rh);
            } else if (b.name === "player") {
                ctx.fillStyle = "#10b981";
                ctx.shadowColor = "rgba(16, 185, 129, 0.4)";
                ctx.shadowBlur = 12;
                ctx.fillRect(rx, ry, rw, rh);
                ctx.shadowBlur = 0;
                ctx.strokeStyle = "#a7f3d0";
                ctx.strokeRect(rx, ry, rw, rh);

                // Eye / Facing Indicator
                ctx.fillStyle = "#064e3b";
                const eyeX = player.facing > 0 ? rx + rw - 8 : rx + 4;
                ctx.fillRect(eyeX, ry + 8, 4, 6);
            } else if (b.name === "enemy") {
                let eColor = "#f59e0b";
                if (enemy.state === "Chase") eColor = "#f97316";
                else if (enemy.state === "Attack") eColor = "#ef4444";
                else if (enemy.state === "Flee") eColor = "#ec4899";

                ctx.fillStyle = eColor;
                ctx.shadowColor = eColor;
                ctx.shadowBlur = 12;
                ctx.fillRect(rx, ry, rw, rh);
                ctx.shadowBlur = 0;
                ctx.strokeStyle = "#ffffff";
                ctx.strokeRect(rx, ry, rw, rh);

                // State Tag over Enemy
                ctx.font = "bold 11px 'JetBrains Mono', monospace";
                ctx.fillStyle = "#f8fafc";
                ctx.textAlign = "center";
                ctx.fillText(`AI: ${enemy.state}`, rx + rw / 2, ry - 8);
            } else {
                // Physics crate
                ctx.fillStyle = "#818cf8";
                ctx.fillRect(rx, ry, rw, rh);
                ctx.strokeStyle = "#c7d2fe";
                ctx.strokeRect(rx, ry, rw, rh);
            }

            // Collider wireframe
            if (toggleColliders.checked) {
                ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
                ctx.lineWidth = 1;
                ctx.strokeRect(rx, ry, rw, rh);
            }
        }

        // Damage particles
        for (const p of particles) {
            ctx.font = "bold 15px 'Outfit', sans-serif";
            ctx.fillStyle = p.color;
            ctx.globalAlpha = p.life / p.maxLife;
            ctx.fillText(p.text, p.x, p.y);
            ctx.globalAlpha = 1.0;
        }

        ctx.restore();
    }

    // Update Telemetry HUD
    function updateHUD() {
        statPlayerPos.innerText = `(${player.body.position.x.toFixed(2)}, ${player.body.position.y.toFixed(2)})`;
        statPlayerVel.innerText = `(${player.body.velocity.x.toFixed(2)}, ${player.body.velocity.y.toFixed(2)})`;
        statPlayerGrounded.innerText = player.body.isGrounded ? "YES" : "NO";
        statPlayerGrounded.className = `stat-val stat-badge ${player.body.isGrounded ? "true" : "false"}`;
        statPlayerCoyote.innerText = `${coyoteTimer.toFixed(2)}s`;
        statPlayerDash.innerText = dashCooldownTimer <= 0 ? "READY" : `${dashCooldownTimer.toFixed(1)}s`;
        statPlayerBuffer.innerText = jumpBufferTimer > 0 ? "BUFFERED" : "IDLE";
        playerHpBadge.innerText = `${Math.round(player.hp)} HP`;
        playerHpBar.style.width = `${(player.hp / player.maxHp) * 100}%`;

        statEnemyPos.innerText = `(${enemy.body.position.x.toFixed(2)}, ${enemy.body.position.y.toFixed(2)})`;
        const dist = enemy.body.position.dist(player.body.position);
        statEnemyDist.innerText = `${dist.toFixed(2)} m`;
        statEnemyWaypoints.innerText = `${enemy.path ? enemy.path.length : 0} nodes`;
        const hasLOS = pathfinder.hasLOS(enemy.body.position, player.body.position);
        statEnemyLos.innerText = hasLOS ? "CLEAR" : "BLOCKED";
        statEnemyLos.className = `stat-val stat-badge ${hasLOS ? "true" : "false"}`;
        enemyStateBadge.innerText = enemy.state;
        enemyStateBadge.className = `badge ${
            enemy.state === "Attack" ? "badge-danger" : enemy.state === "Flee" ? "badge-warning" : "badge-success"
        }`;
        enemyHpBar.style.width = `${(enemy.hp / enemy.maxHp) * 100}%`;
    }

    // UI Listeners & Sliders
    sliderGravity.addEventListener("input", (e) => {
        labelGravity.innerText = parseFloat(e.target.value).toFixed(1);
    });
    sliderJump.addEventListener("input", (e) => {
        labelJump.innerText = parseFloat(e.target.value).toFixed(1);
    });

    btnReset.addEventListener("click", initGame);

    btnSpawnBox.addEventListener("click", () => {
        const crate = new Rigidbody("crate", "DYNAMIC", new Vector2(player.body.position.x + 2, 4), new Vector2(1, 1), 0.8, 0.4, 0.2);
        world.add(crate);
        spawnDamageText("+CRATE", crate.position, "#818cf8");
    });

    btnDamageEnemy.addEventListener("click", () => {
        if (enemy.isAlive) {
            enemy.hp = Math.max(0, enemy.hp - 20);
            spawnDamageText("-20", enemy.body.position, "#ef4444");
            if (enemy.hp <= 0) {
                enemy.isAlive = false;
                combatBannerText.innerText = "ENEMY DEFEATED!";
                combatBanner.classList.remove("hidden");
            }
        }
    });

    // Backend Python Test & Simulation API Integration
    btnRunTests.addEventListener("click", async () => {
        terminalOutput.innerText = "Running 'python run_tests.py' on local backend...\n";
        btnRunTests.disabled = true;
        try {
            const res = await fetch("/api/run-tests", { method: "POST" });
            const data = await res.json();
            terminalOutput.innerText = data.output || "Tests executed successfully.";
        } catch (err) {
            terminalOutput.innerText = `Error executing backend tests: ${err.message}`;
        } finally {
            btnRunTests.disabled = false;
        }
    });

    btnRunSim.addEventListener("click", async () => {
        terminalOutput.innerText = "Running 'python main.py --duration 5.0' on local backend...\n";
        btnRunSim.disabled = true;
        try {
            const res = await fetch("/api/run-simulation", { method: "POST" });
            const data = await res.json();
            terminalOutput.innerText = data.output || "Simulation finished.";
        } catch (err) {
            terminalOutput.innerText = `Error running simulation: ${err.message}`;
        } finally {
            btnRunSim.disabled = false;
        }
    });

    // Start
    initGame();
    requestAnimationFrame(gameLoop);
})();

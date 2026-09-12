from __future__ import annotations

import base64
import hashlib
import html
import json
import math
import re
from pathlib import Path
from typing import Any

from .mixed_project import build_mixed_project
from .procedural_media import generate_media
from .project import ProjectError
from .state_machine import STATE_MACHINE_SCHEMA, StateMachineError, compile_state_machine


BROWSER_GAME_SCHEMA = "axm.browser-arena/v0.1"
MAX_ENEMIES = 64
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,79}")


class BrowserGameError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def browser_game_summary() -> dict[str, Any]:
    return {
        "truth_status": "LIVE_DETERMINISTIC_OFFLINE_BROWSER_GAME_ASSEMBLY",
        "schema": BROWSER_GAME_SCHEMA,
        "project_type": "static-web",
        "runtime_dependencies": [],
        "generated_media": ["rgba8-png-target-icon", "mono-pcm16-wav-fire-cue"],
        "generated_systems": ["canvas-renderer", "game-loop", "input-map", "hud", "arena-rules", "session-state-machine"],
        "maximum_enemies": MAX_ENEMIES,
        "source_and_asset_bytes_reverified_after_publish": True,
        "browser_execution_observed": False,
    }


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BrowserGameError("game specification must be finite JSON data") from exc


def _object(raw: Any, label: str, required: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BrowserGameError(f"{label} must be an object")
    missing = sorted(required - set(raw))
    unexpected = sorted(set(raw) - required)
    if missing or unexpected:
        raise BrowserGameError(
            f"{label} fields do not match the bounded browser-arena grammar",
            {"label": label, "missing_fields": missing, "unexpected_fields": unexpected},
        )
    return raw


def _integer(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise BrowserGameError(f"{label} must be an integer from {minimum} through {maximum}")
    return value


def _number(value: Any, label: str, minimum: float, maximum: float) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise BrowserGameError(f"{label} must be a finite number")
    if not minimum <= float(value) <= maximum:
        raise BrowserGameError(f"{label} must be from {minimum:g} through {maximum:g}")
    return value


def _text(value: Any, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise BrowserGameError(f"{label} must be 1..{maximum} characters of text")
    return value.strip()


def _identifier(value: Any, label: str) -> str:
    text = _text(value, label, 80).casefold()
    if ID_PATTERN.fullmatch(text) is None:
        raise BrowserGameError(f"{label} must use lowercase letters, digits, dot, dash, or underscore")
    return text


def _color(value: Any, label: str) -> str:
    text = _text(value, label, 9).upper()
    if len(text) not in {7, 9} or not text.startswith("#"):
        raise BrowserGameError(f"{label} must be #RRGGBB or #RRGGBBAA")
    try:
        int(text[1:], 16)
    except ValueError as exc:
        raise BrowserGameError(f"{label} must be #RRGGBB or #RRGGBBAA") from exc
    return text


def validate_browser_game_spec(raw: Any) -> dict[str, Any]:
    spec = _object(
        raw,
        "specification",
        {
            "schema",
            "id",
            "title",
            "viewport",
            "theme",
            "player",
            "tower",
            "enemies",
            "rules",
        },
    )
    if spec["schema"] != BROWSER_GAME_SCHEMA:
        raise BrowserGameError(f"specification.schema must be {BROWSER_GAME_SCHEMA}")
    viewport = _object(spec["viewport"], "specification.viewport", {"width", "height"})
    width = _integer(viewport["width"], "specification.viewport.width", 480, 1920)
    height = _integer(viewport["height"], "specification.viewport.height", 320, 1080)
    theme = _object(
        spec["theme"],
        "specification.theme",
        {"background", "ground", "panel", "accent", "danger", "text"},
    )
    normalized_theme = {key: _color(theme[key], f"specification.theme.{key}") for key in sorted(theme)}

    player = _object(
        spec["player"],
        "specification.player",
        {"x", "y", "size", "color", "speed", "max_health"},
    )
    normalized_player = {
        "x": _integer(player["x"], "specification.player.x", 0, width),
        "y": _integer(player["y"], "specification.player.y", 0, height),
        "size": _integer(player["size"], "specification.player.size", 8, min(width, height) // 4),
        "color": _color(player["color"], "specification.player.color"),
        "speed": _number(player["speed"], "specification.player.speed", 20, 1000),
        "max_health": _integer(player["max_health"], "specification.player.max_health", 1, 1_000_000),
    }

    tower = _object(
        spec["tower"],
        "specification.tower",
        {"x", "y", "width", "height", "color", "max_health"},
    )
    normalized_tower = {
        "x": _integer(tower["x"], "specification.tower.x", 0, width - 1),
        "y": _integer(tower["y"], "specification.tower.y", 0, height - 1),
        "width": _integer(tower["width"], "specification.tower.width", 16, width),
        "height": _integer(tower["height"], "specification.tower.height", 16, height),
        "color": _color(tower["color"], "specification.tower.color"),
        "max_health": _integer(tower["max_health"], "specification.tower.max_health", 1, 1_000_000),
    }
    if normalized_tower["x"] + normalized_tower["width"] > width or normalized_tower["y"] + normalized_tower["height"] > height:
        raise BrowserGameError("specification.tower must stay inside the viewport")

    enemies = spec["enemies"]
    if not isinstance(enemies, list) or not enemies or len(enemies) > MAX_ENEMIES:
        raise BrowserGameError(f"specification.enemies must contain 1..{MAX_ENEMIES} entries")
    normalized_enemies: list[dict[str, Any]] = []
    enemy_ids: set[str] = set()
    for index, raw_enemy in enumerate(enemies):
        label = f"specification.enemies[{index}]"
        enemy = _object(
            raw_enemy,
            label,
            {"id", "label", "x", "y", "size", "color", "health", "speed", "damage", "reward"},
        )
        enemy_id = _identifier(enemy["id"], f"{label}.id")
        if enemy_id in enemy_ids:
            raise BrowserGameError("enemy ids must be unique", {"duplicate_id": enemy_id})
        enemy_ids.add(enemy_id)
        normalized_enemies.append(
            {
                "id": enemy_id,
                "label": _text(enemy["label"], f"{label}.label", 80),
                "x": _integer(enemy["x"], f"{label}.x", 0, width),
                "y": _integer(enemy["y"], f"{label}.y", 0, height),
                "size": _integer(enemy["size"], f"{label}.size", 8, min(width, height) // 4),
                "color": _color(enemy["color"], f"{label}.color"),
                "health": _integer(enemy["health"], f"{label}.health", 1, 1_000_000),
                "speed": _number(enemy["speed"], f"{label}.speed", 0, 1000),
                "damage": _number(enemy["damage"], f"{label}.damage", 0, 100_000),
                "reward": _integer(enemy["reward"], f"{label}.reward", 0, 1_000_000),
            }
        )

    rules = _object(
        spec["rules"],
        "specification.rules",
        {
            "projectile_speed",
            "projectile_damage",
            "fire_cooldown_ms",
            "ammo_capacity",
            "reload_ms",
            "contact_distance",
        },
    )
    normalized_rules = {
        "projectile_speed": _number(rules["projectile_speed"], "specification.rules.projectile_speed", 20, 3000),
        "projectile_damage": _integer(rules["projectile_damage"], "specification.rules.projectile_damage", 1, 1_000_000),
        "fire_cooldown_ms": _integer(rules["fire_cooldown_ms"], "specification.rules.fire_cooldown_ms", 20, 10_000),
        "ammo_capacity": _integer(rules["ammo_capacity"], "specification.rules.ammo_capacity", 1, 1000),
        "reload_ms": _integer(rules["reload_ms"], "specification.rules.reload_ms", 100, 30_000),
        "contact_distance": _number(rules["contact_distance"], "specification.rules.contact_distance", 1, 500),
    }
    return {
        "schema": BROWSER_GAME_SCHEMA,
        "id": _identifier(spec["id"], "specification.id"),
        "title": _text(spec["title"], "specification.title", 120),
        "viewport": {"width": width, "height": height},
        "theme": normalized_theme,
        "player": normalized_player,
        "tower": normalized_tower,
        "enemies": normalized_enemies,
        "rules": normalized_rules,
    }


def _session_machine(game_id: str) -> dict[str, Any]:
    return {
        "schema": STATE_MACHINE_SCHEMA,
        "id": f"{game_id}.session",
        "states": ["ready", "playing", "paused", "won", "lost"],
        "initial_state": "ready",
        "transitions": [
            {"from": "ready", "event": "start", "to": "playing", "effects": [{"type": "begin-session"}]},
            {"from": "playing", "event": "pause", "to": "paused", "effects": []},
            {"from": "paused", "event": "resume", "to": "playing", "effects": []},
            {"from": "playing", "event": "win", "to": "won", "effects": [{"type": "freeze-arena"}]},
            {"from": "playing", "event": "lose", "to": "lost", "effects": [{"type": "freeze-arena"}]},
            {"from": "won", "event": "reset", "to": "ready", "effects": [{"type": "reset-session"}]},
            {"from": "lost", "event": "reset", "to": "ready", "effects": [{"type": "reset-session"}]},
            {"from": "paused", "event": "reset", "to": "ready", "effects": [{"type": "reset-session"}]},
            {"from": "playing", "event": "reset", "to": "ready", "effects": [{"type": "reset-session"}]},
        ],
    }


INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="__AXM_BACKGROUND__">
  <title>__AXM_TITLE__</title>
  <link rel="icon" type="image/png" href="assets/target.png">
  <link rel="preload" href="assets/fire.wav" as="audio" type="audio/wav">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main class="shell">
    <header class="hud">
      <div class="brand"><img src="assets/target.png" alt=""><span>__AXM_TITLE__</span></div>
      <div><span class="label">Target</span><strong id="targetName">Scanning…</strong><meter id="targetHealth" min="0" max="100" value="100"></meter></div>
      <div><span class="label">Tower</span><strong id="towerValue">100%</strong></div>
      <div><span class="label">Credits</span><strong id="scoreValue">0</strong></div>
      <div><span class="label">Ammo</span><strong id="ammoValue">0 / 0</strong></div>
    </header>
    <section class="arena" aria-label="Offline tactical arena">
      <canvas id="game" width="__AXM_WIDTH__" height="__AXM_HEIGHT__" tabindex="0" aria-label="Playable arena canvas. Move with WASD or arrows and fire by clicking, tapping, or pressing Space. Q selects the next target.">Canvas is unavailable.</canvas>
      <div id="status" class="status" role="status">Ready — start when you choose.</div>
    </section>
    <nav class="controls" aria-label="Game controls">
      <button id="sessionButton" type="button">Start</button>
      <button id="fireButton" type="button">Fire at target</button>
      <button id="targetButton" type="button">Next target</button>
      <button id="reloadButton" type="button">Reload</button>
      <button id="resetButton" type="button">Reset</button>
      <span class="hint">Move: WASD / arrows · Fire: hold canvas / Space · Target: Q · Reload: R · Pause: P</span>
    </nav>
    <div class="touch" aria-label="Touch movement controls">
      <button type="button" data-key="ArrowUp" aria-label="Move up">↑</button>
      <button type="button" data-key="ArrowLeft" aria-label="Move left">←</button>
      <button type="button" data-key="ArrowDown" aria-label="Move down">↓</button>
      <button type="button" data-key="ArrowRight" aria-label="Move right">→</button>
    </div>
  </main>
  <script src="game.js"></script>
</body>
</html>
"""


STYLE_TEMPLATE = """:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif;--background:__AXM_BACKGROUND__;--panel:__AXM_PANEL__;--accent:__AXM_ACCENT__;--text:__AXM_TEXT__;background:var(--background);color:var(--text)}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 50% 0,color-mix(in srgb,var(--accent) 18%,var(--background)) 0,var(--background) 52%);padding:max(12px,env(safe-area-inset-top)) max(12px,env(safe-area-inset-right)) max(12px,env(safe-area-inset-bottom)) max(12px,env(safe-area-inset-left))}.shell{width:min(1180px,100%);margin:auto;display:grid;gap:10px}.hud{display:grid;grid-template-columns:minmax(180px,1.5fr) repeat(4,minmax(90px,1fr));gap:8px}.hud>div,.controls,.touch{background:color-mix(in srgb,var(--panel) 92%,transparent);border:1px solid color-mix(in srgb,var(--accent) 30%,transparent);border-radius:12px;padding:10px 12px}.brand{display:flex;align-items:center;gap:10px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}.brand img{width:28px;height:28px}.label{display:block;color:color-mix(in srgb,var(--accent) 58%,var(--text));font-size:.68rem;letter-spacing:.14em;text-transform:uppercase}.hud strong{font-variant-numeric:tabular-nums}.hud meter{display:block;width:100%;height:6px}.arena{position:relative;border:1px solid color-mix(in srgb,var(--accent) 42%,transparent);border-radius:14px;overflow:hidden;box-shadow:0 24px 80px #000;background:var(--panel)}canvas{display:block;width:100%;height:auto;touch-action:none}.status{position:absolute;left:50%;top:18px;transform:translateX(-50%);padding:8px 14px;border:1px solid color-mix(in srgb,var(--text) 24%,transparent);border-radius:999px;background:color-mix(in srgb,var(--panel) 88%,transparent);font-size:.82rem;pointer-events:none}.controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.controls button,.touch button{border:1px solid color-mix(in srgb,var(--text) 28%,transparent);border-radius:10px;background:color-mix(in srgb,var(--panel) 72%,var(--accent));color:var(--text);padding:10px 14px;font:inherit;font-weight:800;cursor:pointer}.controls button:disabled{opacity:.4;cursor:default}.controls button:focus-visible,.touch button:focus-visible,canvas:focus-visible{outline:3px solid var(--accent);outline-offset:-3px}#fireButton{background:var(--accent);color:var(--background)}.controls button:hover,.touch button:hover{border-color:var(--accent)}.hint{color:color-mix(in srgb,var(--accent) 52%,var(--text));font-size:.8rem}.touch{display:none;grid-template-columns:repeat(4,1fr);gap:8px}.touch button{font-size:1.25rem;padding:14px}@media(max-width:760px){.hud{grid-template-columns:1fr 1fr}.brand{grid-column:1/-1}.touch{display:grid}.hint{width:100%}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}\n"""


GAME_JS_TEMPLATE = r'''"use strict";
const SPEC = Object.freeze(__AXM_SPEC__);
const SESSION = Object.freeze(__AXM_SESSION__);
const SPEC_DIGEST = "__AXM_SPEC_DIGEST__";
const SESSION_DIGEST = "__AXM_SESSION_DIGEST__";
const canvas = document.querySelector("#game");
const ctx = canvas.getContext("2d");
const statusNode = document.querySelector("#status");
const sessionButton = document.querySelector("#sessionButton");
const reloadButton = document.querySelector("#reloadButton");
const resetButton = document.querySelector("#resetButton");
const fireButton = document.querySelector("#fireButton");
const targetButton = document.querySelector("#targetButton");
const targetName = document.querySelector("#targetName");
const targetHealth = document.querySelector("#targetHealth");
const towerValue = document.querySelector("#towerValue");
const scoreValue = document.querySelector("#scoreValue");
const ammoValue = document.querySelector("#ammoValue");
const fireSound = new Audio("assets/fire.wav");
const keys = new Set();
let state;
let lastFrame = 0;
let pointerAim = null;
let pointerHeld = false;
let targetHeld = false;

function clearInputs() { keys.clear(); pointerHeld = false; targetHeld = false; }

function transition(event) {
  const row = SESSION.transitions.find(item => item.from === state.phase && item.event === event);
  if (!row) return false;
  state.phase = row.to;
  if (state.phase !== "playing") clearInputs();
  return true;
}

function freshState() {
  return {
    phase: SESSION.initial_state,
    player: {...SPEC.player, health: SPEC.player.max_health},
    tower: {...SPEC.tower, health: SPEC.tower.max_health},
    enemies: SPEC.enemies.map(enemy => ({...enemy, maxHealth: enemy.health, alive: true, contactCooldown: 0})),
    bullets: [], ammo: SPEC.rules.ammo_capacity, reloadRemaining: 0,
    fireCooldown: 0, score: 0, selectedId: SPEC.enemies[0].id,
  };
}

function reset() {
  clearInputs();
  pointerAim = null;
  state = freshState();
  lastFrame = 0;
  updateHud();
  draw();
}

function selectedEnemy() {
  return state.enemies.find(enemy => enemy.id === state.selectedId && enemy.alive)
    || state.enemies.find(enemy => enemy.alive) || null;
}

function nextTarget() {
  const alive = state.enemies.filter(enemy => enemy.alive);
  if (!alive.length) return;
  const index = alive.findIndex(enemy => enemy.id === state.selectedId);
  state.selectedId = alive[(index + 1) % alive.length].id;
  updateHud();
}

function fireSelected() {
  const target = selectedEnemy();
  if (target) fireAt(target.x, target.y);
}

function setStatus() {
  const labels = {ready:"Ready — start when you choose.",playing:"Defend the command tower.",paused:"Paused.",won:"Arena secured.",lost:"Command tower lost."};
  statusNode.textContent = labels[state.phase];
  sessionButton.textContent = state.phase === "ready" ? "Start" : state.phase === "playing" ? "Pause" : state.phase === "paused" ? "Resume" : "Play again";
}

function updateHud() {
  const target = selectedEnemy();
  targetName.textContent = target ? target.label : "No hostiles";
  targetHealth.max = target ? target.maxHealth : 1;
  targetHealth.value = target ? Math.max(0, target.health) : 0;
  towerValue.textContent = `${Math.ceil(100 * state.tower.health / state.tower.max_health)}%`;
  scoreValue.textContent = String(state.score);
  ammoValue.textContent = state.reloadRemaining > 0 ? "RELOADING" : `${state.ammo} / ${SPEC.rules.ammo_capacity}`;
  fireButton.disabled = state.phase !== "playing";
  reloadButton.disabled = state.phase !== "playing" || state.reloadRemaining > 0 || state.ammo === SPEC.rules.ammo_capacity;
  targetButton.disabled = !target;
  setStatus();
}

function startReload() {
  if (state.phase === "playing" && state.reloadRemaining <= 0 && state.ammo < SPEC.rules.ammo_capacity) {
    state.reloadRemaining = SPEC.rules.reload_ms / 1000;
  }
}

function fireAt(x, y) {
  if (state.phase !== "playing" || state.fireCooldown > 0 || state.reloadRemaining > 0) return;
  if (state.ammo <= 0) { startReload(); return; }
  const dx = x - state.player.x;
  const dy = y - state.player.y;
  const length = Math.hypot(dx, dy) || 1;
  state.bullets.push({x:state.player.x,y:state.player.y,vx:dx/length*SPEC.rules.projectile_speed,vy:dy/length*SPEC.rules.projectile_speed,r:4});
  state.ammo -= 1;
  state.fireCooldown = SPEC.rules.fire_cooldown_ms / 1000;
  try { const cue = fireSound.cloneNode(); cue.volume = 0.25; const playback = cue.play(); if (playback) playback.catch(() => {}); } catch (_) { /* audio permission is host-controlled */ }
  if (state.ammo === 0) startReload();
  updateHud();
}

function update(dt) {
  if (state.phase !== "playing") return;
  let dx = (keys.has("ArrowRight") || keys.has("d") ? 1 : 0) - (keys.has("ArrowLeft") || keys.has("a") ? 1 : 0);
  let dy = (keys.has("ArrowDown") || keys.has("s") ? 1 : 0) - (keys.has("ArrowUp") || keys.has("w") ? 1 : 0);
  const movement = Math.hypot(dx, dy) || 1;
  state.player.x = Math.max(state.player.size, Math.min(canvas.width-state.player.size, state.player.x + dx/movement*state.player.speed*dt));
  state.player.y = Math.max(state.player.size, Math.min(canvas.height-state.player.size, state.player.y + dy/movement*state.player.speed*dt));
  state.fireCooldown = Math.max(0, state.fireCooldown - dt);
  if (state.reloadRemaining > 0) {
    state.reloadRemaining -= dt;
    if (state.reloadRemaining <= 0) { state.reloadRemaining = 0; state.ammo = SPEC.rules.ammo_capacity; }
  }
  if (pointerHeld && pointerAim) fireAt(pointerAim.x, pointerAim.y);
  else if (targetHeld || keys.has(" ")) fireSelected();
  const tx = state.tower.x + state.tower.width / 2;
  const ty = state.tower.y + state.tower.height / 2;
  for (const enemy of state.enemies) {
    if (!enemy.alive) continue;
    const ex = tx - enemy.x;
    const ey = ty - enemy.y;
    const distance = Math.hypot(ex, ey) || 1;
    enemy.contactCooldown = Math.max(0, enemy.contactCooldown - dt);
    if (distance > SPEC.rules.contact_distance) {
      enemy.x += ex / distance * enemy.speed * dt;
      enemy.y += ey / distance * enemy.speed * dt;
    } else if (enemy.contactCooldown <= 0) {
      state.tower.health = Math.max(0, state.tower.health - enemy.damage);
      enemy.contactCooldown = 0.75;
    }
  }
  for (const bullet of state.bullets) { bullet.x += bullet.vx*dt; bullet.y += bullet.vy*dt; }
  for (const bullet of state.bullets) {
    for (const enemy of state.enemies) {
      if (!enemy.alive || bullet.hit || Math.hypot(bullet.x-enemy.x,bullet.y-enemy.y) > enemy.size/2+bullet.r) continue;
      bullet.hit = true;
      enemy.health -= SPEC.rules.projectile_damage;
      if (enemy.health <= 0) { enemy.alive = false; state.score += enemy.reward; }
      break;
    }
  }
  state.bullets = state.bullets.filter(b => !b.hit && b.x>=0 && b.x<=canvas.width && b.y>=0 && b.y<=canvas.height);
  if (state.tower.health <= 0) transition("lose");
  else if (!state.enemies.some(enemy => enemy.alive)) transition("win");
  updateHud();
}

function drawBlock(x,y,size,color) {
  ctx.fillStyle = color; ctx.fillRect(x-size/2,y-size/2,size,size);
  ctx.fillStyle = "rgba(255,255,255,.22)"; ctx.fillRect(x-size*.28,y-size*.28,size*.2,size*.2);
}

function draw() {
  const {width,height} = canvas;
  ctx.fillStyle = SPEC.theme.background; ctx.fillRect(0,0,width,height);
  ctx.strokeStyle = "rgba(59,232,218,.08)"; ctx.lineWidth = 1;
  for (let x=0;x<width;x+=48){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,height);ctx.stroke();}
  for (let y=0;y<height;y+=48){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y);ctx.stroke();}
  ctx.fillStyle = SPEC.theme.ground;
  ctx.beginPath(); ctx.moveTo(width*.12,height); ctx.lineTo(width*.36,height*.38); ctx.lineTo(width*.66,height*.38); ctx.lineTo(width*.9,height); ctx.closePath(); ctx.fill();
  const glow=ctx.createRadialGradient(state.tower.x+state.tower.width/2,state.tower.y+state.tower.height/2,10,state.tower.x+state.tower.width/2,state.tower.y+state.tower.height/2,180);
  glow.addColorStop(0,SPEC.theme.accent.slice(0,7)+"24");glow.addColorStop(1,SPEC.theme.accent.slice(0,7)+"00");
  ctx.fillStyle=glow;ctx.fillRect(0,0,width,height);
  ctx.fillStyle = state.tower.color; ctx.fillRect(state.tower.x,state.tower.y,state.tower.width,state.tower.height);
  ctx.fillStyle = SPEC.theme.accent; ctx.fillRect(state.tower.x+state.tower.width*.2,state.tower.y-18,state.tower.width*.6,18);
  ctx.fillStyle="rgba(0,0,0,.4)";ctx.fillRect(state.tower.x+12,state.tower.y+12,state.tower.width-24,state.tower.height-24);
  ctx.strokeStyle=SPEC.theme.accent;ctx.strokeRect(state.tower.x+5,state.tower.y+5,state.tower.width-10,state.tower.height-10);
  ctx.fillStyle=SPEC.theme.text;ctx.textAlign="center";ctx.font="700 12px system-ui";ctx.fillText("COMMAND",state.tower.x+state.tower.width/2,state.tower.y+state.tower.height/2);
  ctx.fillStyle=SPEC.theme.accent;ctx.fillRect(state.tower.x,state.tower.y+state.tower.height+10,state.tower.width*state.tower.health/state.tower.max_health,5);
  const target = selectedEnemy();
  const aim = pointerHeld && pointerAim ? pointerAim : target;
  if (aim) {ctx.strokeStyle=SPEC.theme.accent.slice(0,7)+"55";ctx.setLineDash([5,8]);ctx.beginPath();ctx.moveTo(state.player.x,state.player.y);ctx.lineTo(aim.x,aim.y);ctx.stroke();ctx.setLineDash([]);}
  ctx.fillStyle=SPEC.theme.text;ctx.textAlign="left";ctx.font="700 13px system-ui";ctx.fillText("HOSTILES  " + state.enemies.filter(e=>e.alive).length + " / " + state.enemies.length,20,height-20);
  for (const enemy of state.enemies) {
    if (!enemy.alive) continue;
    drawBlock(enemy.x,enemy.y,enemy.size,enemy.color);
    ctx.fillStyle = SPEC.theme.danger; ctx.fillRect(enemy.x-enemy.size/2,enemy.y-enemy.size*.78,enemy.size*Math.max(0,enemy.health)/enemy.maxHealth,4);
    if (target && enemy.id === target.id) { ctx.strokeStyle=SPEC.theme.accent;ctx.lineWidth=2;ctx.strokeRect(enemy.x-enemy.size*.72,enemy.y-enemy.size*.72,enemy.size*1.44,enemy.size*1.44); }
  }
  ctx.save(); ctx.translate(state.player.x,state.player.y); if(aim)ctx.rotate(Math.atan2(aim.y-state.player.y,aim.x-state.player.x)+Math.PI/2); ctx.fillStyle=state.player.color; ctx.beginPath(); ctx.moveTo(0,-state.player.size);ctx.lineTo(state.player.size*.75,state.player.size);ctx.lineTo(-state.player.size*.75,state.player.size);ctx.closePath();ctx.fill();ctx.restore();
  ctx.fillStyle = SPEC.theme.accent; for(const bullet of state.bullets){ctx.beginPath();ctx.arc(bullet.x,bullet.y,bullet.r,0,Math.PI*2);ctx.fill();}
  if (state.phase === "won" || state.phase === "lost") { ctx.fillStyle="rgba(0,0,0,.6)";ctx.fillRect(0,0,width,height);ctx.fillStyle=SPEC.theme.text;ctx.textAlign="center";ctx.font="900 48px system-ui";ctx.fillText(state.phase === "won" ? "ARENA SECURED" : "TOWER LOST",width/2,height/2); }
}

function frame(timestamp) {
  const dt = lastFrame ? Math.min((timestamp-lastFrame)/1000,0.05) : 0;
  lastFrame = timestamp;
  update(dt); draw(); requestAnimationFrame(frame);
}

function pointerPosition(event) {
  const rect = canvas.getBoundingClientRect();
  return {x:(event.clientX-rect.left)*canvas.width/rect.width,y:(event.clientY-rect.top)*canvas.height/rect.height};
}
canvas.addEventListener("pointerdown", event => {
  if (event.button !== 0) return;
  pointerAim = pointerPosition(event);
  const nearest = state.enemies.filter(e=>e.alive).sort((a,b)=>Math.hypot(a.x-pointerAim.x,a.y-pointerAim.y)-Math.hypot(b.x-pointerAim.x,b.y-pointerAim.y))[0];
  if (nearest) state.selectedId = nearest.id;
  pointerHeld = state.phase === "playing";
  canvas.setPointerCapture(event.pointerId);
  fireAt(pointerAim.x,pointerAim.y); canvas.focus(); updateHud();
});
canvas.addEventListener("pointermove", event => { pointerAim = pointerPosition(event); });
for (const name of ["pointerup","pointercancel","lostpointercapture"]) canvas.addEventListener(name,()=>{pointerHeld=false;});
window.addEventListener("keydown", event => {
  // Native controls keep Space/arrow behavior; game keys belong to the canvas.
  if (event.target !== canvas) return;
  const key = event.key.length===1 ? event.key.toLowerCase() : event.key;
  if (["ArrowUp","ArrowDown","ArrowLeft","ArrowRight"," "].includes(key)) event.preventDefault();
  keys.add(key);
  if (!event.repeat) {
    if(key==="p") { if(state.phase==="playing") transition("pause"); else if(state.phase==="paused") transition("resume"); updateHud(); }
    if(key==="q") nextTarget();
    if(key==="r") startReload();
  }
});
window.addEventListener("keyup", event => keys.delete(event.key.length===1?event.key.toLowerCase():event.key));
function pauseOnLeave() { clearInputs(); if(state.phase==="playing") transition("pause"); updateHud(); }
window.addEventListener("blur",pauseOnLeave);
document.addEventListener("visibilitychange",()=>{if(document.hidden) pauseOnLeave();});
for(const button of document.querySelectorAll("[data-key]")){
  const key=button.dataset.key;
  button.addEventListener("pointerdown",event=>{event.preventDefault();button.setPointerCapture(event.pointerId);if(state.phase==="playing")keys.add(key);});
  for(const name of ["pointerup","pointercancel","lostpointercapture"])button.addEventListener(name,()=>keys.delete(key));
}
fireButton.addEventListener("pointerdown",event=>{if(event.button!==0)return;event.preventDefault();fireButton.setPointerCapture(event.pointerId);targetHeld=state.phase==="playing";fireSelected();});
for(const name of ["pointerup","pointercancel","lostpointercapture"])fireButton.addEventListener(name,()=>{targetHeld=false;});
fireButton.addEventListener("click",event=>{if(event.detail===0)fireSelected();});
targetButton.addEventListener("click",nextTarget);
sessionButton.addEventListener("click",()=>{if(state.phase==="ready")transition("start");else if(state.phase==="playing")transition("pause");else if(state.phase==="paused")transition("resume");else{reset();transition("start");}updateHud();canvas.focus();});
reloadButton.addEventListener("click",startReload);
resetButton.addEventListener("click",()=>{if(state.phase!=="ready")transition("reset");reset();});
reset(); requestAnimationFrame(frame);
// Optional read-only browser tool; ordinary play needs no agent or service.
if (document.modelContext?.registerTool) {
  const lifecycle = new AbortController();
  window.addEventListener("pagehide",()=>lifecycle.abort(),{once:true});
  try {
    Promise.resolve(document.modelContext.registerTool({
      name:"read_arena_status", title:"Read arena status",
      description:"Read the same session, target, tower, credits and ammunition shown in the arena HUD. Does not play or modify the game.",
      inputSchema:{type:"object",properties:{},additionalProperties:false},
      annotations:{readOnlyHint:true,untrustedContentHint:false},
      execute(input) {
        if (!input || typeof input !== "object" || Array.isArray(input) || Object.keys(input).length) throw new Error("Expected an empty object");
        return {status:statusNode.textContent,target:targetName.textContent,tower:towerValue.textContent,credits:scoreValue.textContent,ammo:ammoValue.textContent};
      }
    },{signal:lifecycle.signal})).catch(()=>{});
  } catch (_) { /* optional browser tool support does not control gameplay */ }
}
console.info("AXM browser arena source", {specDigest:SPEC_DIGEST,sessionDigest:SESSION_DIGEST,browserExecutionObserved:false});
'''


def _render_project(spec: dict[str, Any], compiled: dict[str, Any]) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    spec_digest = hashlib.sha256(_canonical(spec)).hexdigest()
    session = compiled["machine"]
    session_digest = compiled["machine_digest"]
    index = (
        INDEX_TEMPLATE.replace("__AXM_TITLE__", html.escape(spec["title"]))
        .replace("__AXM_BACKGROUND__", spec["theme"]["background"][:7])
        .replace("__AXM_WIDTH__", str(spec["viewport"]["width"]))
        .replace("__AXM_HEIGHT__", str(spec["viewport"]["height"]))
    )
    game_js = (
        GAME_JS_TEMPLATE.replace("__AXM_SPEC__", json.dumps(spec, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
        .replace("__AXM_SESSION__", json.dumps(session, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
        .replace("__AXM_SPEC_DIGEST__", spec_digest)
        .replace("__AXM_SESSION_DIGEST__", session_digest)
    )
    style = (
        STYLE_TEMPLATE.replace("__AXM_BACKGROUND__", spec["theme"]["background"])
        .replace("__AXM_PANEL__", spec["theme"]["panel"])
        .replace("__AXM_ACCENT__", spec["theme"]["accent"])
        .replace("__AXM_TEXT__", spec["theme"]["text"])
    )
    game_json = json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    session_json = json.dumps(session, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    readme = (
        f"# {spec['title']}\n\n"
        "A dependency-free offline browser arena generated by AXM Universal Creation.\n\n"
        "Open `index.html` in a modern browser. Move with WASD or arrow keys, aim and hold click/tap to fire, or hold Space to fire at the selected target. Q cycles targets, P pauses, and R reloads. On touch screens use the movement pad and hold Fire at target. Leaving the window pauses the session; resume is always explicit.\n\n"
        f"Game specification SHA-256: `{spec_digest}`\n\n"
        f"Session machine SHA-256: `{session_digest}`\n\n"
        "The source, links, JSON, PNG payload, WAV payload, and exact bytes were deterministically validated. Browser execution, visual quality, input behavior, audio playback, accessibility, and gameplay balance require separate host evidence.\n"
    )
    icon = generate_media(
        "png",
        {
            "width": 64,
            "height": 64,
            "background": "#00000000",
            "shapes": [
                {"kind": "circle", "cx": 32, "cy": 32, "radius": 27, "color": spec["theme"]["danger"]},
                {"kind": "circle", "cx": 32, "cy": 32, "radius": 17, "color": spec["theme"]["background"]},
                {"kind": "rectangle", "x": 29, "y": 8, "width": 6, "height": 48, "color": spec["theme"]["accent"]},
                {"kind": "rectangle", "x": 8, "y": 29, "width": 48, "height": 6, "color": spec["theme"]["accent"]},
            ],
        },
    )
    fire = generate_media(
        "wav",
        {
            "sample_rate": 16_000,
            "tones": [
                {"frequency_hz": 880, "duration_ms": 45, "amplitude": 5_000},
                {"frequency_hz": 440, "duration_ms": 35, "amplitude": 3_200},
            ],
        },
    )
    text_files = {
        "README.md": readme,
        "game.js": game_js,
        "game.json": game_json,
        "index.html": index,
        "state-machine.json": session_json,
        "style.css": style,
    }
    binary_files = {
        "assets/target.png": {
            "encoding": "base64",
            "content": base64.b64encode(icon["body"]).decode("ascii"),
            "media_type": "image/png",
            "sha256": icon["sha256"],
        },
        "assets/fire.wav": {
            "encoding": "base64",
            "content": base64.b64encode(fire["body"]).decode("ascii"),
            "media_type": "audio/wav",
            "sha256": fire["sha256"],
        },
    }
    return text_files, binary_files


def build_browser_game(
    target: Path,
    *,
    specification: Any,
    checks: list[dict[str, Any]] | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    spec = validate_browser_game_spec(specification)
    spec_digest = hashlib.sha256(_canonical(spec)).hexdigest()
    try:
        compiled = compile_state_machine(_session_machine(spec["id"]))
    except StateMachineError as exc:
        raise BrowserGameError(str(exc), exc.details) from exc
    text_files, binary_files = _render_project(spec, compiled)
    built_in_checks: list[dict[str, Any]] = [
        {"type": "json-value", "path": "game.json", "json_path": ["schema"], "equals": BROWSER_GAME_SCHEMA},
        {"type": "json-value", "path": "state-machine.json", "json_path": ["schema"], "equals": STATE_MACHINE_SCHEMA},
        {"type": "contains", "path": "game.js", "text": spec_digest},
        {"type": "contains", "path": "game.js", "text": compiled["machine_digest"]},
        {"type": "media-signature", "path": "assets/target.png", "format": "png"},
        {"type": "media-signature", "path": "assets/fire.wav", "format": "wav"},
    ]
    try:
        result = build_mixed_project(
            Path(target),
            text_files=text_files,
            binary_files=binary_files,
            project_type="static-web",
            checks=built_in_checks + list(checks or []),
            replace=replace,
            publish_mode="validated",
        )
    except ProjectError as exc:
        raise BrowserGameError(str(exc), exc.details) from exc
    return {
        **result,
        "truth_status": "VALIDATED_OFFLINE_BROWSER_GAME_SOURCE_PROJECT",
        "game_schema": BROWSER_GAME_SCHEMA,
        "game_specification": spec,
        "game_specification_digest": spec_digest,
        "session_machine_digest": compiled["machine_digest"],
        "runtime_dependencies": [],
        "generated_systems": browser_game_summary()["generated_systems"],
        "browser_execution_observed": False,
        "proof_scope": "exact source and media bytes, closed game/session specifications, static local references, JSON structure, and generated PNG/WAV payloads; browser runtime behavior and player experience are not proven",
    }

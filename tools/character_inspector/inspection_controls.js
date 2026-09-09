const KEY_ACTIONS = Object.freeze({
  ' ': 'toggle-play',
  Spacebar: 'toggle-play',
  r: 'restart-clip',
  R: 'restart-clip',
  '[': 'previous-clip',
  ']': 'next-clip',
  '1': 'lod-0',
  '2': 'lod-1',
  '3': 'lod-2',
  f: 'view-front',
  F: 'view-front',
  b: 'view-back',
  B: 'view-back',
  v: 'view-three-quarter',
  V: 'view-three-quarter',
  w: 'toggle-wireframe',
  W: 'toggle-wireframe',
  k: 'toggle-skeleton',
  K: 'toggle-skeleton',
  ArrowLeft: 'orbit-left',
  ArrowRight: 'orbit-right',
  ArrowUp: 'zoom-in',
  ArrowDown: 'zoom-out'
});

const BUTTON_ACTIONS = Object.freeze({
  0: 'toggle-play',       // A / Cross
  2: 'restart-clip',      // X / Square
  4: 'lod-previous',      // LB / L1
  5: 'lod-next',          // RB / R1
  12: 'view-front',       // D-pad up
  13: 'view-back',        // D-pad down
  14: 'previous-clip',    // D-pad left
  15: 'next-clip'         // D-pad right
});

function isEditableTarget(target) {
  if (!target || typeof target !== 'object') return false;
  if (target.isContentEditable) return true;
  const tag = String(target.tagName || '').toUpperCase();
  return tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA' || tag === 'BUTTON';
}

export function actionForKey(event) {
  if (!event || event.altKey || event.ctrlKey || event.metaKey || isEditableTarget(event.target)) return null;
  return KEY_ACTIONS[event.key] || null;
}

export function gamepadActions(gamepad, previous = []) {
  if (!gamepad || !Array.isArray(gamepad.buttons)) return [];
  const actions = [];
  for (const [indexText, action] of Object.entries(BUTTON_ACTIONS)) {
    const index = Number(indexText);
    const pressed = Boolean(gamepad.buttons[index]?.pressed);
    if (pressed && !previous[index]) actions.push(action);
  }
  return actions;
}

export class InspectionInputRouter {
  constructor({target = window, navigatorRef = navigator, onAction, onInputMode, deadzone = 0.55} = {}) {
    if (typeof onAction !== 'function') throw new TypeError('onAction callback is required');
    this.target = target;
    this.navigatorRef = navigatorRef;
    this.onAction = onAction;
    this.onInputMode = typeof onInputMode === 'function' ? onInputMode : () => {};
    this.deadzone = deadzone;
    this.previousButtons = [];
    this.previousAxes = [0, 0];
    this.frame = null;
    this.boundKey = event => {
      const action = actionForKey(event);
      if (!action) return;
      event.preventDefault?.();
      this.onInputMode('keyboard');
      this.onAction(action, 'keyboard');
    };
  }

  start() {
    this.target.addEventListener?.('keydown', this.boundKey);
    if (typeof requestAnimationFrame === 'function') this.frame = requestAnimationFrame(() => this.poll());
  }

  stop() {
    this.target.removeEventListener?.('keydown', this.boundKey);
    if (this.frame !== null && typeof cancelAnimationFrame === 'function') cancelAnimationFrame(this.frame);
    this.frame = null;
  }

  poll() {
    const pads = this.navigatorRef?.getGamepads?.() || [];
    const pad = [...pads].find(Boolean);
    if (pad) {
      const nextButtons = pad.buttons.map(button => Boolean(button?.pressed));
      for (const action of gamepadActions(pad, this.previousButtons)) {
        this.onInputMode('gamepad');
        this.onAction(action, 'gamepad');
      }
      const x = Math.abs(pad.axes?.[0] || 0) >= this.deadzone ? Math.sign(pad.axes[0]) : 0;
      const y = Math.abs(pad.axes?.[1] || 0) >= this.deadzone ? Math.sign(pad.axes[1]) : 0;
      if (x && !this.previousAxes[0]) {
        this.onInputMode('gamepad');
        this.onAction(x > 0 ? 'orbit-right' : 'orbit-left', 'gamepad');
      }
      if (y && !this.previousAxes[1]) {
        this.onInputMode('gamepad');
        this.onAction(y > 0 ? 'zoom-out' : 'zoom-in', 'gamepad');
      }
      this.previousButtons = nextButtons;
      this.previousAxes = [x, y];
    } else {
      this.previousButtons = [];
      this.previousAxes = [0, 0];
    }
    if (typeof requestAnimationFrame === 'function') this.frame = requestAnimationFrame(() => this.poll());
  }
}

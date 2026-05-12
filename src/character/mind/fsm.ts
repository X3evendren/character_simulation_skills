/**
 * Finite State Machine — Dialog phase management.
 * 
 *
 * Provides deterministic scaffolding; LLM provides the muscle.
 * State transitions are driven by action fields, not LLM reasoning.
 */
export enum State {
  IDLE = 'idle',
  ANALYZE = 'analyze',
  PLAN = 'plan',
  EXEC = 'exec',
  VERIFY = 'verify',
  RESPOND = 'respond',
}

// Transition table: { currentState: { event: nextState } }
const TRANSITIONS: Record<string, Record<string, State>> = {
  [State.IDLE]: {
    user_input: State.ANALYZE,
    initiative: State.RESPOND,
  },
  [State.ANALYZE]: {
    understood: State.PLAN,
    simple: State.RESPOND,
    unclear: State.RESPOND,
  },
  [State.PLAN]: {
    need_tool: State.EXEC,
    no_tool: State.RESPOND,
    planned: State.EXEC,
  },
  [State.EXEC]: {
    done: State.VERIFY,
    error: State.PLAN,
    timeout: State.RESPOND,
  },
  [State.VERIFY]: {
    success: State.RESPOND,
    retry: State.EXEC,
    fail: State.RESPOND,
  },
  [State.RESPOND]: {
    done: State.IDLE,
  },
};

export interface FSMContext {
  action: string;
  intent: string;
  planSteps: string[];
  toolResults: Record<string, unknown>[];
  error: string;
  metadata: Record<string, unknown>;
}

export function createFSMContext(): FSMContext {
  return { action: '', intent: '', planSteps: [], toolResults: [], error: '', metadata: {} };
}

type EnterHook = (ctx: FSMContext) => void;
type HistoryEntry = { from: string; event: string; to: string };

export class FiniteStateMachine {
  state: State;
  previousState: State;
  context: FSMContext;
  private _history: HistoryEntry[];
  private _hooks: Map<State, EnterHook[]>;

  constructor(initialState: State = State.IDLE) {
    this.state = initialState;
    this.previousState = initialState;
    this.context = createFSMContext();
    this._history = [];
    this._hooks = new Map();
  }

  transition(event: string, context?: FSMContext): State {
    if (context) this.context = context;

    const validEvents = TRANSITIONS[this.state] ?? {};
    let matchedEvent = event;

    if (!(event in validEvents)) {
      // Fuzzy match: try partial matching
      for (const key of Object.keys(validEvents)) {
        if (key.includes(event) || event.includes(key)) {
          matchedEvent = key;
          break;
        }
      }
      if (!(matchedEvent in validEvents)) return this.state; // no match
    }

    const nextState = validEvents[matchedEvent];
    this.previousState = this.state;
    this._history.push({ from: this.state, event: matchedEvent, to: nextState });
    if (this._history.length > 50) this._history = this._history.slice(-50);

    // Execute enter hooks
    for (const hook of this._hooks.get(nextState) ?? []) {
      hook(this.context);
    }

    this.state = nextState;
    return nextState;
  }

  onEnter(state: State, hook: EnterHook): void {
    const hooks = this._hooks.get(state) ?? [];
    hooks.push(hook);
    this._hooks.set(state, hooks);
  }

  canTransition(event: string): boolean {
    return event in (TRANSITIONS[this.state] ?? {});
  }

  availableEvents(): string[] {
    return Object.keys(TRANSITIONS[this.state] ?? {});
  }

  history(n: number = 5): HistoryEntry[] {
    return this._history.slice(-n);
  }

  reset(): void {
    this.state = State.IDLE;
    this.previousState = State.IDLE;
    this.context = createFSMContext();
  }
}

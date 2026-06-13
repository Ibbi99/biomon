// src/app/EventBus.ts
//
// A simple typed publish/subscribe event bus.
// Used to decouple Firebase data reception from UI rendering.
//
// Data flow:
//   FirebaseService (subscribe) → emits "dashboard:update"
//   DashboardController (bind)  → listens for "dashboard:update" → renders UI
//
// This means VirtualPatient.ts and RealPatient.ts don't need to know
// anything about the UI components — they just emit events.

type Listener<T> = (payload: T) => void;

export class EventBus {
  private listeners: Map<string, Listener<unknown>[]> = new Map();

  /**
   * Registers a listener for the given event name.
   * Multiple listeners can be registered for the same event.
   *
   * @param eventName - Event identifier (e.g. "dashboard:update")
   * @param listener  - Callback invoked when the event is emitted
   */
  public on<T>(eventName: string, listener: Listener<T>): void {
    const current = this.listeners.get(eventName) ?? [];
    current.push(listener as Listener<unknown>);
    this.listeners.set(eventName, current);
  }

  /**
   * Emits an event, invoking all registered listeners with the given payload.
   *
   * @param eventName - Event identifier to emit
   * @param payload   - Data passed to all listeners
   */
  public emit<T>(eventName: string, payload: T): void {
    const listeners = this.listeners.get(eventName) ?? [];
    listeners.forEach((listener) => {
      (listener as Listener<T>)(payload);
    });
  }
}

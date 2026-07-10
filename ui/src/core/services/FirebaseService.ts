import { initializeApp, FirebaseApp } from "firebase/app";
import {
  Database,
  getDatabase,
  onValue,
  ref,
  get,
  query,
  orderByChild,
  startAt,
  endAt,
  set,
} from "firebase/database";

/**
 * Wraps the Firebase Realtime Database SDK.
 * Provides a single subscribe() method used by all patient pages to listen for live data updates from the Python processor.
 * The Python processor writes processed data to:  /patients/{patientId}/dashboard/current
 * FirebaseService reads from any path passed in — the caller is responsible for providing the correct path.
 * @author Cristina Vedinas
 */

export class FirebaseService {
  private app: FirebaseApp;
  private database: Database;

  constructor() {
    this.app = initializeApp({
      apiKey: "AIzaSyCxPSj5Y6gcNnxVJb0ixLrFxpV21GJ_oEY",
      authDomain: "bachelordegree-6ed5c.firebaseapp.com",
      databaseURL:
        "https://bachelordegree-6ed5c-default-rtdb.europe-west1.firebasedatabase.app",
      projectId: "bachelordegree-6ed5c",
      storageBucket: "bachelordegree-6ed5c.firebasestorage.app",
      messagingSenderId: "822664200294",
      appId: "1:822664200294:web:8cb59c291cc63c1bf46da7",
      measurementId: "G-ZP7Y39XVDL",
    });

    this.database = getDatabase(this.app);
  }

  /**
   * Subscribes to a Firebase Realtime Database path.
   * The callback fires immediately with the current value,
   * then again on every subsequent change (real-time updates).
   *
   * @param path     - Firebase path, e.g. "/patients/Patient_01/dashboard/current"
   *                   NOTE: Firebase paths are case-sensitive.
   * @param callback - Called with the snapshot value cast to T, or null if the path is empty
   */
  public subscribe<T>(
    path: string,
    callback: (payload: T | null) => void,
  ): void {
    const dbRef = ref(this.database, path);

    onValue(dbRef, (snapshot) => {
      const raw = snapshot.val();
      console.log(`FIREBASE [${path}]:`, raw);

      if (!raw) {
        callback(null);
        return;
      }

      callback(raw as T);
    });
  }

  public async fetchHistory<T>(
    path: string,
    startTs: number,
    endTs: number,
  ): Promise<T[]> {
    const dbRef = ref(this.database, path);

    const historyQuery = query(
      dbRef,
      orderByChild("timestamp"),
      startAt(startTs),
      endAt(endTs),
    );

    try {
      const snapshot = await get(historyQuery);
      const results: T[] = [];

      if (snapshot.exists()) {
        snapshot.forEach((childSnapshot) => {
          results.push(childSnapshot.val() as T);
        });
      }
      return results;
    } catch (error) {
      console.error("Error fetching history:", error);
      return [];
    }
  }

  public async getValue<T>(path: string): Promise<T | null> {
    const dbRef = ref(this.database, path);
    const snapshot = await get(dbRef);
    return snapshot.exists() ? (snapshot.val() as T) : null;
  }

  public async setValue<T>(path: string, value: T): Promise<void> {
    const dbRef = ref(this.database, path);
    await set(dbRef, value);
  }
}

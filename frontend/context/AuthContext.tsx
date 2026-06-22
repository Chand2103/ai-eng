"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  updateProfile,
  type User as FirebaseUser,
} from "firebase/auth";
import { doc, getDoc, setDoc, serverTimestamp, onSnapshot } from "firebase/firestore";
import { getAuthInstance, getDbInstance } from "@/lib/firebase";

export interface AppUser {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
}

interface AuthContextType {
  user: AppUser | null;
  loading: boolean;
  subscriptionActive: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function mapFirebaseUser(fu: FirebaseUser): AppUser {
  return {
    uid: fu.uid,
    email: fu.email,
    displayName: fu.displayName,
    photoURL: fu.photoURL,
  };
}

async function ensureUserDoc(user: FirebaseUser) {
  const db = getDbInstance();
  const ref = doc(db, "users", user.uid);
  const snap = await getDoc(ref);
  if (!snap.exists()) {
    await setDoc(ref, {
      uid: user.uid,
      email: user.email,
      displayName: user.displayName,
      photoURL: user.photoURL,
      createdAt: serverTimestamp(),
      subscription: { active: false, plan: null, startedAt: null },
    });
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [subscriptionActive, setSubscriptionActive] = useState(false);

  useEffect(() => {
    let auth: ReturnType<typeof getAuthInstance> | null = null;
    try {
      auth = getAuthInstance();
    } catch {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLoading(false);
      return;
    }
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      if (firebaseUser) {
        setUser(mapFirebaseUser(firebaseUser));
      } else {
        setUser(null);
        setSubscriptionActive(false);
      }
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  // Listen to Firestore user doc for subscription state
  useEffect(() => {
    if (!user) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSubscriptionActive(false);
      return;
    }
    let unsub: (() => void) | null = null;
    try {
      const db = getDbInstance();
      const ref = doc(db, "users", user.uid);
      unsub = onSnapshot(ref, (snap) => {
        if (snap.exists()) {
          const data = snap.data();
          setSubscriptionActive(data.subscription?.active === true);
        }
      });
    } catch { /* ignore */ }
    return () => { if (unsub) unsub(); };
  }, [user]);

  const login = async (email: string, password: string) => {
    const auth = getAuthInstance();
    await signInWithEmailAndPassword(auth, email, password);
  };

  const register = async (name: string, email: string, password: string) => {
    const auth = getAuthInstance();
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    await updateProfile(cred.user, { displayName: name });
    await ensureUserDoc(cred.user);
    setUser(mapFirebaseUser({ ...cred.user, displayName: name }));
  };

  const loginWithGoogle = async () => {
    const auth = getAuthInstance();
    const provider = new GoogleAuthProvider();
    const cred = await signInWithPopup(auth, provider);
    await ensureUserDoc(cred.user);
  };

  const logout = async () => {
    const auth = getAuthInstance();
    await signOut(auth);
    setUser(null);
    setSubscriptionActive(false);
  };

  return (
    <AuthContext.Provider value={{ user, loading, subscriptionActive, login, register, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

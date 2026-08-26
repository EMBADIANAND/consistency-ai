import { useState, type FormEvent } from "react";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Mode = "signin" | "signup";

export function AuthPage() {
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setFieldErrors({});
    try {
      if (mode === "signin") {
        await signIn(email, password);
      } else {
        await signUp(email, password, displayName);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        setFieldErrors(
          Object.fromEntries(err.details.map((detail) => [detail.field, detail.message])),
        );
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <div className="auth-card">
        <div className="brand auth-brand">
          <div className="logo">C</div>
          <div>
            <strong>ConsistencyAI</strong>
            <span>Your day, made meaningful.</span>
          </div>
        </div>

        <h1>{mode === "signin" ? "Welcome back." : "Start where you are."}</h1>
        <p className="muted">
          {mode === "signin"
            ? "Pick up your streak where you left it."
            : "A few honest intentions a day is all this asks of you."}
        </p>

        <form onSubmit={submit} noValidate>
          {mode === "signup" && (
            <label className="field">
              <span>What should we call you?</span>
              <input
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder="Anand"
                autoComplete="name"
                required
              />
              {fieldErrors.display_name && <em>{fieldErrors.display_name}</em>}
            </label>
          )}

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />
            {fieldErrors.email && <em>{fieldErrors.email}</em>}
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={mode === "signup" ? "At least 8 characters" : "••••••••"}
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
              required
            />
            {fieldErrors.password && <em>{fieldErrors.password}</em>}
          </label>

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <button className="primary" type="submit" disabled={busy}>
            {busy
              ? "One moment…"
              : mode === "signin"
                ? "Sign in →"
                : "Create my account →"}
          </button>
        </form>

        <button
          className="link"
          onClick={() => {
            setMode(mode === "signin" ? "signup" : "signin");
            setError(null);
            setFieldErrors({});
          }}
        >
          {mode === "signin"
            ? "New here? Create an account"
            : "Already have an account? Sign in"}
        </button>
      </div>
    </div>
  );
}

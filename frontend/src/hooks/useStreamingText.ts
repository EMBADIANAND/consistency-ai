import { useCallback, useEffect, useRef, useState } from "react";

const TICK_MS = 16;

/**
 * Reveals streamed text at a readable pace.
 *
 * The two providers deliver at completely different speeds: the rule-based one
 * knows its whole answer before the request even finishes, while the model
 * trickles it over a second or two. Pacing here rather than on the server gives
 * both the same unhurried feel, and — unlike a `sleep` in the route — it costs
 * no worker time to do it.
 *
 * The step scales with how far behind the display is, so a long answer that
 * arrived in one lump still finishes quickly instead of crawling.
 */
export function useStreamingText() {
  const [shown, setShown] = useState("");
  const [settled, setSettled] = useState(true);
  const received = useRef("");
  const revealed = useRef(0);

  useEffect(() => {
    if (settled) return;
    const timer = window.setInterval(() => {
      const full = received.current;
      if (revealed.current >= full.length) {
        setSettled(true);
        return;
      }
      const behind = full.length - revealed.current;
      revealed.current += Math.max(3, Math.ceil(behind / 25));
      setShown(full.slice(0, revealed.current));
    }, TICK_MS);
    return () => window.clearInterval(timer);
  }, [settled]);

  const push = useCallback((text: string) => {
    received.current += text;
    setSettled(false);
  }, []);

  const reset = useCallback(() => {
    received.current = "";
    revealed.current = 0;
    setShown("");
    setSettled(true);
  }, []);

  /** Everything received, whether or not it has been revealed yet. */
  const complete = useCallback(() => received.current, []);

  return { shown, push, reset, settled, complete };
}

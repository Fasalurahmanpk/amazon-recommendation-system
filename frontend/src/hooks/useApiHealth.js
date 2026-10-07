import { useCallback, useEffect, useState } from "react";
import { checkHealth } from "../services/recommendationApi";

// Tracks whether the backend is reachable: "checking" | "online" | "offline".
// Re-checks periodically and whenever the tab regains focus.
export default function useApiHealth(intervalMs = 30000) {
  const [state, setState] = useState("checking");

  const check = useCallback(async (signal) => {
    try {
      await checkHealth(signal);
      setState("online");
    } catch (error) {
      if (error.name === "AbortError") return;
      setState("offline");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    check(controller.signal);
    const timer = setInterval(() => check(controller.signal), intervalMs);
    const onFocus = () => check(controller.signal);
    window.addEventListener("focus", onFocus);
    return () => {
      controller.abort();
      clearInterval(timer);
      window.removeEventListener("focus", onFocus);
    };
  }, [check, intervalMs]);

  return state;
}

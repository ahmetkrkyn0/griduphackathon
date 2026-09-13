import { useEffect, useState } from "react";

/** "10 sn önce" gibi goreli sureler guncel kalsin diye bileseni periyodik olarak yeniden cizer. */
export function useNow(intervalMs: number): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);
  return now;
}

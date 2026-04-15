import { useEffect, useRef, useState } from "react";
import { pollJobStatus, JobStatusResponse } from "../lib/api";

const POLL_INTERVAL_MS = 3000;

export function useJobPoller(jobId: string) {
  const [status, setStatus] = useState<JobStatusResponse | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const poll = async () => {
      try {
        const data = await pollJobStatus(jobId);
        setStatus(data);
        if (data.status !== "done" && data.status !== "failed") {
          timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch {
        timerRef.current = setTimeout(poll, POLL_INTERVAL_MS * 2);
      }
    };

    poll();

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [jobId]);

  return status;
}

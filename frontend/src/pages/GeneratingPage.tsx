import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "react-hot-toast";
import ProgressBar from "../components/ProgressBar";
import { pollJobStatus, JobStatusResponse } from "../lib/api";

const POLL_MS = 3000;

const TIPS = [
  "InstantID фиксирует уникальные черты твоего лица...",
  "SDXL создаёт окружение под выбранные стили...",
  "CodeFormer восстанавливает детали лица...",
  "Real-ESRGAN увеличивает разрешение до максимума...",
  "Последние штрихи — скоро будет готово!",
];

export default function GeneratingPage() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  // jobIds passed via navigate state from StylesPage
  const jobIds: string[] = location.state?.jobIds ?? [];

  const [statuses, setStatuses] = useState<Record<string, JobStatusResponse>>({});
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  // Redirect home if arrived without jobIds
  useEffect(() => {
    if (jobIds.length === 0) {
      navigate("/", { replace: true });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Poll each job independently
  useEffect(() => {
    if (jobIds.length === 0) return;

    const pollOne = async (jobId: string) => {
      try {
        const data = await pollJobStatus(jobId);
        setStatuses((prev) => ({ ...prev, [jobId]: data }));
        if (data.status !== "done" && data.status !== "failed") {
          timers.current[jobId] = setTimeout(() => pollOne(jobId), POLL_MS);
        }
      } catch {
        timers.current[jobId] = setTimeout(() => pollOne(jobId), POLL_MS * 2);
      }
    };

    jobIds.forEach((id) => pollOne(id));

    return () => {
      Object.values(timers.current).forEach(clearTimeout);
    };
  }, [jobIds.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  // Navigate to result when all jobs are finished
  useEffect(() => {
    if (jobIds.length === 0) return;
    const finished = jobIds.every(
      (id) => statuses[id]?.status === "done" || statuses[id]?.status === "failed",
    );
    if (!finished) return;

    const anyDone = jobIds.some((id) => statuses[id]?.status === "done");
    if (anyDone) {
      navigate(`/result/${userId}`, { state: { jobIds }, replace: true });
    } else {
      toast.error("Все задачи завершились с ошибкой");
    }
  }, [statuses]); // eslint-disable-line react-hooks/exhaustive-deps

  // Compute aggregate progress (average across all jobs)
  const totalProgress =
    jobIds.length === 0
      ? 0
      : Math.round(
          jobIds.reduce((sum, id) => sum + (statuses[id]?.progress ?? 0), 0) / jobIds.length,
        );

  const tipIdx = Math.min(Math.floor(totalProgress / 25), TIPS.length - 1);

  const failedJobs = jobIds.filter((id) => statuses[id]?.status === "failed");

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12 gap-10">
      {/* Animated orb */}
      <div className="relative w-24 h-24">
        <motion.div
          animate={{ scale: [1, 1.1, 1], opacity: [0.6, 1, 0.6] }}
          transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut" }}
          className="absolute inset-0 rounded-full bg-gradient-to-br from-brand-500 to-pink-400 blur-xl"
        />
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 3, ease: "linear" }}
          className="absolute inset-0 rounded-full border-4 border-brand-500/30 border-t-brand-500"
        />
      </div>

      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">Создаём твою фотосессию</h2>
        <p className="text-white/50 text-sm">{TIPS[tipIdx]}</p>
        {jobIds.length > 1 && (
          <p className="text-white/30 text-xs mt-1">
            {jobIds.length} стилей в очереди
          </p>
        )}
      </div>

      <ProgressBar
        progress={totalProgress}
        label={`${totalProgress}% выполнено`}
      />

      {failedJobs.length > 0 && (
        <p className="text-yellow-400/80 text-sm text-center max-w-xs">
          {failedJobs.length} из {jobIds.length} задач завершились с ошибкой — остальные продолжаются
        </p>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "react-hot-toast";
import StyleSwipe from "../components/StyleSwipe";
import { fetchStyles, startGeneration, StyleOption } from "../lib/api";

export default function StylesPage() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const [styles, setStyles] = useState<StyleOption[]>([]);

  useEffect(() => {
    fetchStyles().then(setStyles).catch(() => toast.error("Не удалось загрузить стили"));
  }, []);

  const handleDone = async (selectedIds: string[]) => {
    if (!userId || selectedIds.length === 0) return;

    try {
      // Launch one job per selected style in parallel
      const jobs = await Promise.all(
        selectedIds.map((style_id) => startGeneration(userId, style_id)),
      );
      const jobIds = jobs.map((j) => j.job_id);
      navigate(`/generating/${userId}`, { state: { jobIds } });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Ошибка запуска генерации");
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12">
      <div className="mb-8 text-center">
        <h2 className="text-3xl font-bold">Выбери стили</h2>
        <p className="text-white/50 mt-2 text-sm">
          Свайп вправо — нравится, влево — следующий
        </p>
      </div>

      {styles.length > 0 ? (
        <StyleSwipe styles={styles} onDone={handleDone} />
      ) : (
        <div className="text-white/40">Загружаем стили...</div>
      )}
    </div>
  );
}

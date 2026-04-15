import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { Sparkles } from "lucide-react";
import UploadZone from "../components/UploadZone";
import { uploadPhotos } from "../lib/api";

export default function UploadPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleFiles = async (files: File[]) => {
    setLoading(true);
    try {
      const { user_id, uploaded_count } = await uploadPhotos(files);
      toast.success(`${uploaded_count} фото загружено`);
      navigate(`/styles/${user_id}`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12">
      {/* Header */}
      <div className="mb-10 text-center">
        <div className="inline-flex items-center gap-2 text-brand-500 mb-3">
          <Sparkles size={20} />
          <span className="text-sm font-medium uppercase tracking-widest">AI Фотосессия</span>
        </div>
        <h1 className="text-4xl font-bold tracking-tight">
          Идеальные фото для дейтинга
        </h1>
        <p className="mt-3 text-white/50 max-w-sm mx-auto">
          Загрузи 5–10 своих фото, выбери стили — и получи профессиональную фотосессию с твоим лицом
        </p>
      </div>

      <UploadZone onFilesReady={handleFiles} loading={loading} />

      {/* How it works */}
      <div className="mt-16 grid grid-cols-3 gap-4 max-w-lg text-center">
        {[
          { step: "1", label: "Загружаешь фото" },
          { step: "2", label: "Выбираешь стили" },
          { step: "3", label: "Получаешь фотосессию" },
        ].map(({ step, label }) => (
          <div key={step} className="flex flex-col items-center gap-2">
            <div className="w-9 h-9 rounded-full bg-brand-500/20 text-brand-500 font-bold flex items-center justify-center">
              {step}
            </div>
            <p className="text-white/50 text-sm">{label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

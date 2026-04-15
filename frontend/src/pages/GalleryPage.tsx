import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { ArrowLeft, Sparkles } from "lucide-react";
import Gallery from "../components/Gallery";
import { fetchGallery, GalleryImage } from "../lib/api";

export default function GalleryPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [images, setImages] = useState<GalleryImage[]>([]);

  useEffect(() => {
    if (!sessionId) return;
    fetchGallery(sessionId)
      .then(setImages)
      .catch(() => toast.error("Не удалось загрузить галерею"));
  }, [sessionId]);

  return (
    <div className="min-h-screen px-4 py-12 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 text-white/50 hover:text-white transition-colors"
        >
          <ArrowLeft size={18} /> Новая сессия
        </button>
        <div className="flex items-center gap-2 text-brand-500">
          <Sparkles size={16} />
          <span className="text-sm font-medium">Твоя фотосессия</span>
        </div>
      </div>

      <h1 className="text-3xl font-bold mb-6">Готово!</h1>

      {images.length > 0 ? (
        <Gallery images={images} />
      ) : (
        <div className="text-white/40 text-center py-20">Загружаем фото...</div>
      )}
    </div>
  );
}

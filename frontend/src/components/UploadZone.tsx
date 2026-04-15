import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, X, ImagePlus } from "lucide-react";

interface Props {
  onFilesReady: (files: File[]) => void;
  loading: boolean;
}

const MAX = 10;

export default function UploadZone({ onFilesReady, loading }: Props) {
  const [previews, setPreviews] = useState<{ file: File; url: string }[]>([]);

  const onDrop = useCallback((accepted: File[]) => {
    const combined = [...previews, ...accepted.map((f) => ({ file: f, url: URL.createObjectURL(f) }))];
    const clamped = combined.slice(0, MAX);
    setPreviews(clamped);
  }, [previews]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [".jpg", ".jpeg", ".png", ".webp"] },
    multiple: true,
    disabled: loading,
  });

  const remove = (idx: number) => {
    URL.revokeObjectURL(previews[idx].url);
    setPreviews((p) => p.filter((_, i) => i !== idx));
  };

  const handleSubmit = () => {
    if (previews.length >= 3) onFilesReady(previews.map((p) => p.file));
  };

  return (
    <div className="flex flex-col gap-6 w-full max-w-lg mx-auto">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-colors
          ${isDragActive ? "border-brand-500 bg-brand-500/10" : "border-white/20 hover:border-white/40"}`}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto mb-3 text-white/50" size={36} />
        <p className="text-white/70 text-sm">
          {isDragActive
            ? "Отпусти фотографии здесь"
            : "Перетащи или нажми — загрузи 5–10 фото с лицом"}
        </p>
        <p className="text-white/30 text-xs mt-1">JPG / PNG / WebP · до 10 МБ каждое</p>
      </div>

      {previews.length > 0 && (
        <div className="grid grid-cols-4 gap-2">
          <AnimatePresence>
            {previews.map(({ url }, i) => (
              <motion.div
                key={url}
                initial={{ opacity: 0, scale: 0.85 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="relative aspect-square rounded-xl overflow-hidden group"
              >
                <img src={url} alt="" className="w-full h-full object-cover" />
                <button
                  onClick={() => remove(i)}
                  className="absolute top-1 right-1 bg-black/60 rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X size={14} />
                </button>
              </motion.div>
            ))}
            {previews.length < MAX && (
              <motion.div
                {...(getRootProps() as any)}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="aspect-square rounded-xl border-2 border-dashed border-white/20 flex items-center justify-center cursor-pointer hover:border-white/40 transition-colors"
              >
                <ImagePlus size={20} className="text-white/30" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={previews.length < 3 || loading}
        className="w-full py-4 rounded-2xl font-semibold text-white bg-brand-500 hover:bg-brand-600
          disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95"
      >
        {loading ? "Загружаем..." : `Продолжить (${previews.length} фото)`}
      </button>

      {previews.length > 0 && previews.length < 3 && (
        <p className="text-center text-white/40 text-xs">Нужно минимум 3 фото</p>
      )}
    </div>
  );
}

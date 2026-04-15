import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Download, X, ChevronLeft, ChevronRight } from "lucide-react";
import type { GalleryImage } from "../lib/api";

interface Props {
  images: GalleryImage[];
}

export default function Gallery({ images }: Props) {
  const [lightbox, setLightbox] = useState<number | null>(null);

  const open = (i: number) => setLightbox(i);
  const close = () => setLightbox(null);
  const prev = () => setLightbox((i) => (i !== null ? Math.max(0, i - 1) : null));
  const next = () => setLightbox((i) => (i !== null ? Math.min(images.length - 1, i + 1) : null));

  const download = (img: GalleryImage) => {
    const a = document.createElement("a");
    a.href = img.url;
    a.download = img.filename;
    a.click();
  };

  const downloadAll = () => images.forEach(download);

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <p className="text-white/60 text-sm">{images.length} фото готово</p>
        <button
          onClick={downloadAll}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 text-sm font-medium transition-colors active:scale-95"
        >
          <Download size={16} /> Скачать все
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {images.map((img, i) => (
          <motion.div
            key={img.filename}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="relative aspect-square rounded-2xl overflow-hidden group cursor-pointer"
            onClick={() => open(i)}
          >
            <img src={img.url} alt="" className="w-full h-full object-cover transition-transform group-hover:scale-105" />
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
              <Download size={20} className="text-white opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </motion.div>
        ))}
      </div>

      {/* Lightbox */}
      <AnimatePresence>
        {lightbox !== null && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
            onClick={close}
          >
            <motion.img
              key={lightbox}
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              src={images[lightbox].url}
              alt=""
              className="max-h-full max-w-full rounded-2xl object-contain"
              onClick={(e) => e.stopPropagation()}
            />

            {/* Controls */}
            <button
              onClick={close}
              className="absolute top-4 right-4 bg-white/10 hover:bg-white/20 rounded-full p-2 transition-colors"
            >
              <X size={20} />
            </button>

            {lightbox > 0 && (
              <button
                onClick={(e) => { e.stopPropagation(); prev(); }}
                className="absolute left-4 bg-white/10 hover:bg-white/20 rounded-full p-2 transition-colors"
              >
                <ChevronLeft size={24} />
              </button>
            )}

            {lightbox < images.length - 1 && (
              <button
                onClick={(e) => { e.stopPropagation(); next(); }}
                className="absolute right-4 bg-white/10 hover:bg-white/20 rounded-full p-2 transition-colors"
              >
                <ChevronRight size={24} />
              </button>
            )}

            <button
              onClick={(e) => { e.stopPropagation(); download(images[lightbox]); }}
              className="absolute bottom-4 right-4 flex items-center gap-2 bg-brand-500 hover:bg-brand-600 rounded-xl px-4 py-2 text-sm font-medium transition-colors"
            >
              <Download size={16} /> Скачать
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

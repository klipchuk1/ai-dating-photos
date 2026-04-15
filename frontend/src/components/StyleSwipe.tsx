/**
 * Tinder-like swipe UI for style selection.
 * Swipe right = like (add to selection), swipe left = skip.
 * Touch + mouse drag supported via pointer events.
 */
import { useState, useRef, useCallback } from "react";
import { motion, useMotionValue, useTransform, AnimatePresence } from "framer-motion";
import { Heart, X, Check, RotateCcw } from "lucide-react";
import type { StyleOption } from "../lib/api";

interface Props {
  styles: StyleOption[];
  onDone: (selected: string[]) => void;
}

const SWIPE_THRESHOLD = 100; // px to register a swipe

export default function StyleSwipe({ styles, onDone }: Props) {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [gone, setGone] = useState(false); // animating out

  const x = useMotionValue(0);
  const rotate = useTransform(x, [-200, 200], [-25, 25]);
  const likeOpacity = useTransform(x, [20, 80], [0, 1]);
  const nopeOpacity = useTransform(x, [-80, -20], [1, 0]);
  const dragStartX = useRef(0);

  const current = styles[currentIdx];
  const remaining = styles.length - currentIdx;
  const isLast = currentIdx >= styles.length - 1;

  const advance = useCallback(
    (liked: boolean) => {
      if (gone) return;
      setGone(true);
      if (liked && current) {
        setSelected((s) => [...s, current.id]);
      }
      setTimeout(() => {
        setCurrentIdx((i) => i + 1);
        x.set(0);
        setGone(false);
      }, 300);
    },
    [gone, current, x]
  );

  const handleDragEnd = () => {
    const val = x.get();
    if (Math.abs(val) > SWIPE_THRESHOLD) {
      advance(val > 0);
    } else {
      x.set(0);
    }
  };

  const handleFinish = () => {
    if (selected.length === 0) return;
    onDone(selected);
  };

  // All cards swiped
  if (currentIdx >= styles.length) {
    return (
      <div className="flex flex-col items-center gap-6 py-10">
        <div className="text-5xl">🎉</div>
        <h2 className="text-2xl font-bold">Готово!</h2>
        <p className="text-white/60 text-center">
          Выбрано стилей: <span className="text-brand-500 font-semibold">{selected.length}</span>
        </p>
        {selected.length === 0 ? (
          <div className="flex flex-col gap-3 items-center">
            <p className="text-white/40 text-sm">Ни одного стиля не выбрано</p>
            <button
              onClick={() => { setCurrentIdx(0); setSelected([]); }}
              className="flex items-center gap-2 px-5 py-3 rounded-xl border border-white/20 hover:border-white/40 transition-colors"
            >
              <RotateCcw size={16} /> Начать заново
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4 w-full max-w-xs">
            <div className="flex flex-wrap gap-2 justify-center">
              {selected.map((id) => {
                const s = styles.find((st) => st.id === id);
                return s ? (
                  <span key={id} className="bg-brand-500/20 text-brand-500 text-xs px-3 py-1 rounded-full">
                    {s.name}
                  </span>
                ) : null;
              })}
            </div>
            <button
              onClick={handleFinish}
              className="w-full py-4 rounded-2xl bg-brand-500 hover:bg-brand-600 font-semibold transition-colors active:scale-95"
            >
              Генерировать фото
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-6 select-none">
      {/* Progress */}
      <div className="text-white/40 text-sm">
        {currentIdx + 1} / {styles.length} · выбрано: {selected.length}
      </div>

      {/* Card stack */}
      <div className="relative w-72 h-[420px]">
        {/* Background cards peek */}
        {[2, 1].map((offset) => {
          const peekIdx = currentIdx + offset;
          if (peekIdx >= styles.length) return null;
          return (
            <div
              key={peekIdx}
              className="absolute inset-0 rounded-3xl overflow-hidden bg-gray-800"
              style={{
                transform: `scale(${1 - offset * 0.04}) translateY(${offset * 10}px)`,
                zIndex: 10 - offset,
              }}
            >
              <img
                src={styles[peekIdx].preview_url}
                alt=""
                className="w-full h-full object-cover opacity-60"
                onError={(e) => (e.currentTarget.src = "/placeholder.jpg")}
              />
            </div>
          );
        })}

        {/* Active card */}
        <AnimatePresence>
          <motion.div
            key={current.id}
            className="absolute inset-0 rounded-3xl overflow-hidden bg-gray-800 cursor-grab active:cursor-grabbing shadow-2xl"
            style={{ x, rotate, zIndex: 20 }}
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.9}
            onDragStart={() => { dragStartX.current = x.get(); }}
            onDragEnd={handleDragEnd}
            animate={gone ? { x: x.get() > 0 ? 500 : -500, opacity: 0 } : {}}
            transition={{ duration: 0.25 }}
          >
            <img
              src={current.preview_url}
              alt={current.name}
              className="w-full h-full object-cover pointer-events-none"
              onError={(e) => (e.currentTarget.src = "/placeholder.jpg")}
            />

            {/* Gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />

            {/* NOPE badge */}
            <motion.div
              style={{ opacity: nopeOpacity }}
              className="absolute top-6 right-6 border-4 border-red-500 text-red-500 font-black text-2xl px-3 py-1 rounded-xl rotate-12"
            >
              NOPE
            </motion.div>

            {/* LIKE badge */}
            <motion.div
              style={{ opacity: likeOpacity }}
              className="absolute top-6 left-6 border-4 border-green-400 text-green-400 font-black text-2xl px-3 py-1 rounded-xl -rotate-12"
            >
              LIKE
            </motion.div>

            {/* Info */}
            <div className="absolute bottom-0 inset-x-0 p-5">
              <h3 className="font-bold text-xl">{current.name}</h3>
              <p className="text-white/70 text-sm mt-0.5">{current.description}</p>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Buttons */}
      <div className="flex items-center gap-6">
        <button
          onClick={() => advance(false)}
          className="w-14 h-14 rounded-full bg-white/10 hover:bg-red-500/20 border border-white/20 hover:border-red-500/50
            flex items-center justify-center transition-all active:scale-90"
        >
          <X size={24} className="text-white/60" />
        </button>

        <button
          onClick={() => advance(true)}
          className="w-16 h-16 rounded-full bg-brand-500 hover:bg-brand-600 shadow-lg shadow-brand-500/30
            flex items-center justify-center transition-all active:scale-90"
        >
          <Heart size={26} fill="white" className="text-white" />
        </button>

        {selected.length > 0 && isLast && (
          <button
            onClick={handleFinish}
            className="w-14 h-14 rounded-full bg-green-500 hover:bg-green-600
              flex items-center justify-center transition-all active:scale-90"
          >
            <Check size={22} />
          </button>
        )}
      </div>

      <p className="text-white/30 text-xs">← свайп влево · нравится →</p>
    </div>
  );
}

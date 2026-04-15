import { useEffect, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { toast } from "react-hot-toast";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Download,
  X,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Trophy,
} from "lucide-react";
import { getResult, PhotoOut } from "../lib/api";

interface RichPhoto extends PhotoOut {
  style_id: string;
}

// ── Similarity score badge ─────────────────────────────────────────────────────

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.65
      ? "bg-emerald-500/20 text-emerald-400 ring-emerald-500/30"
      : score >= 0.45
      ? "bg-amber-500/20 text-amber-400 ring-amber-500/30"
      : "bg-white/10 text-white/50 ring-white/10";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ring-1 ${color}`}>
      {pct}%
    </span>
  );
}

// ── Rank medal ─────────────────────────────────────────────────────────────────

const MEDALS = ["🥇", "🥈", "🥉", "4", "5", "6"];

function RankBadge({ rank }: { rank: number }) {
  const medal = MEDALS[rank] ?? String(rank + 1);
  const isEmoji = rank < 3;
  return (
    <div
      className={`absolute top-3 left-3 z-10 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
        ${isEmoji ? "bg-black/50 backdrop-blur-sm" : "bg-black/60 text-white/70 backdrop-blur-sm"}`}
    >
      {medal}
    </div>
  );
}

// ── Photo card ─────────────────────────────────────────────────────────────────

interface CardProps {
  photo: RichPhoto;
  rank: number;
  aspectClass: string;
  delay: number;
  onOpen: () => void;
  onDownload: () => void;
}

function PhotoCard({ photo, rank, aspectClass, delay, onOpen, onDownload }: CardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35, ease: "easeOut" }}
      className={`relative ${aspectClass} rounded-2xl overflow-hidden group cursor-pointer bg-gray-900`}
      onClick={onOpen}
    >
      <img
        src={photo.url}
        alt=""
        className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
      />

      {/* Gradient */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />

      {/* Rank */}
      <RankBadge rank={rank} />

      {/* Score badge (bottom left) */}
      <div className="absolute bottom-3 left-3">
        <ScoreBadge score={photo.similarity_score} />
      </div>

      {/* Download on hover */}
      <button
        onClick={(e) => { e.stopPropagation(); onDownload(); }}
        className="absolute bottom-3 right-3 w-8 h-8 rounded-full bg-white/10 hover:bg-brand-500
          backdrop-blur-sm flex items-center justify-center opacity-0 group-hover:opacity-100
          transition-all duration-200 active:scale-90"
      >
        <Download size={14} />
      </button>
    </motion.div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function ResultPage() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const jobIds: string[] = location.state?.jobIds ?? [];

  const [photos, setPhotos] = useState<RichPhoto[]>([]);
  const [loading, setLoading] = useState(true);
  const [lightbox, setLightbox] = useState<number | null>(null);

  // Fetch & aggregate ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (jobIds.length === 0) { navigate("/", { replace: true }); return; }

    (async () => {
      try {
        const results = await Promise.allSettled(jobIds.map((id) => getResult(id)));
        const all: RichPhoto[] = [];
        results.forEach((r) => {
          if (r.status !== "fulfilled") return;
          r.value.photos.forEach((p) => all.push({ ...p, style_id: r.value.style_id }));
        });
        all.sort((a, b) => b.similarity_score - a.similarity_score);
        setPhotos(all);
      } catch {
        toast.error("Не удалось загрузить результаты");
      } finally {
        setLoading(false);
      }
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Helpers ────────────────────────────────────────────────────────────────────
  const download = (photo: RichPhoto) => {
    const a = document.createElement("a");
    a.href = photo.url;
    a.download = photo.url.split("/").pop() ?? "photo.jpg";
    a.click();
  };

  const top6 = photos.slice(0, 6);
  const rest  = photos.slice(6);
  const hero  = photos[0] ?? null;

  const prevLightbox = () => setLightbox((i) => (i !== null ? Math.max(0, i - 1) : null));
  const nextLightbox = () => setLightbox((i) => (i !== null ? Math.min(photos.length - 1, i + 1) : null));

  // Keyboard navigation in lightbox
  useEffect(() => {
    if (lightbox === null) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft")  prevLightbox();
      if (e.key === "ArrowRight") nextLightbox();
      if (e.key === "Escape")     setLightbox(null);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [lightbox]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="max-w-3xl mx-auto px-4 py-10">

        {/* ── Header ── */}
        <div className="flex items-center justify-between mb-10">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 text-white/40 hover:text-white transition-colors text-sm"
          >
            <ArrowLeft size={16} /> Новая сессия
          </button>
          <div className="flex items-center gap-2 text-brand-500">
            <Sparkles size={15} />
            <span className="text-sm font-medium">AI Фотосессия</span>
          </div>
        </div>

        {loading ? (
          // ── Loading skeleton ──
          <div className="space-y-4">
            <div className="h-8 w-40 bg-white/5 rounded-xl animate-pulse" />
            <div className="aspect-[4/5] w-full bg-white/5 rounded-2xl animate-pulse" />
            <div className="grid grid-cols-3 gap-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="aspect-[3/4] bg-white/5 rounded-2xl animate-pulse" />
              ))}
            </div>
          </div>
        ) : photos.length === 0 ? (
          <div className="text-center py-32 text-white/30">Нет фото для отображения</div>
        ) : (
          <>
            {/* ── Title row ── */}
            <div className="flex items-end justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold tracking-tight">Твоя фотосессия</h1>
                <p className="text-white/40 text-sm mt-1">
                  {photos.length} фото&nbsp;·&nbsp;
                  {jobIds.length} {jobIds.length === 1 ? "стиль" : "стиля"}
                </p>
              </div>
              <button
                onClick={() => photos.forEach(download)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/8 hover:bg-white/12
                  border border-white/10 hover:border-white/20 text-sm font-medium transition-all active:scale-95"
              >
                <Download size={15} /> Скачать все
              </button>
            </div>

            {/* ── Hero — #1 photo ── */}
            {hero && (
              <div className="mb-3">
                <div className="flex items-center gap-2 mb-3">
                  <Trophy size={15} className="text-yellow-400" />
                  <span className="text-sm font-semibold text-yellow-400">Лучшее совпадение</span>
                  <ScoreBadge score={hero.similarity_score} />
                </div>
                <motion.div
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                  className="relative aspect-[3/4] w-full rounded-3xl overflow-hidden group cursor-pointer bg-gray-900"
                  onClick={() => setLightbox(0)}
                >
                  <img
                    src={hero.url}
                    alt="Best match"
                    className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />

                  {/* Medal */}
                  <div className="absolute top-4 left-4 bg-black/50 backdrop-blur-sm rounded-full w-10 h-10
                    flex items-center justify-center text-xl">🥇</div>

                  {/* Score + download overlay */}
                  <div className="absolute bottom-0 inset-x-0 p-5 flex items-end justify-between">
                    <div>
                      <p className="text-white/60 text-xs mb-1">Совпадение лица</p>
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-28 bg-white/20 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-emerald-400 rounded-full transition-all"
                            style={{ width: `${Math.round(hero.similarity_score * 100)}%` }}
                          />
                        </div>
                        <span className="text-white font-semibold text-sm">
                          {Math.round(hero.similarity_score * 100)}%
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); download(hero); }}
                      className="flex items-center gap-1.5 bg-white/10 hover:bg-brand-500 backdrop-blur-sm
                        rounded-xl px-3 py-2 text-sm font-medium transition-all active:scale-95"
                    >
                      <Download size={14} /> Скачать
                    </button>
                  </div>
                </motion.div>
              </div>
            )}

            {/* ── Top 6 grid (positions 2–6) ── */}
            {top6.length > 1 && (
              <div className="mt-3 mb-8">
                <p className="text-white/40 text-xs uppercase tracking-widest mb-3">
                  Топ-{top6.length}
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {top6.slice(1).map((photo, i) => (
                    <PhotoCard
                      key={photo.url}
                      photo={photo}
                      rank={i + 1}
                      aspectClass="aspect-[3/4]"
                      delay={0.05 + i * 0.06}
                      onOpen={() => setLightbox(i + 1)}
                      onDownload={() => download(photo)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* ── Divider ── */}
            {rest.length > 0 && (
              <div className="flex items-center gap-3 my-8">
                <div className="flex-1 h-px bg-white/8" />
                <span className="text-white/30 text-xs uppercase tracking-widest">
                  Все фото
                </span>
                <div className="flex-1 h-px bg-white/8" />
              </div>
            )}

            {/* ── Remaining photos grid ── */}
            {rest.length > 0 && (
              <div className="grid grid-cols-3 gap-2">
                {rest.map((photo, i) => (
                  <motion.div
                    key={photo.url}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 + i * 0.03 }}
                    className="relative aspect-square rounded-xl overflow-hidden group cursor-pointer bg-gray-900"
                    onClick={() => setLightbox(i + 6)}
                  >
                    <img
                      src={photo.url}
                      alt=""
                      className="absolute inset-0 w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors" />

                    {/* Mini score badge */}
                    <div className="absolute top-1.5 left-1.5">
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-semibold
                        ${photo.similarity_score >= 0.65
                          ? "bg-emerald-500/25 text-emerald-400"
                          : photo.similarity_score >= 0.45
                          ? "bg-amber-500/25 text-amber-400"
                          : "bg-white/10 text-white/50"
                        }`}>
                        {Math.round(photo.similarity_score * 100)}%
                      </span>
                    </div>

                    <button
                      onClick={(e) => { e.stopPropagation(); download(photo); }}
                      className="absolute bottom-1.5 right-1.5 w-7 h-7 rounded-lg bg-black/50 backdrop-blur-sm
                        flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity
                        hover:bg-brand-500 active:scale-90"
                    >
                      <Download size={12} />
                    </button>
                  </motion.div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Lightbox ────────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {lightbox !== null && photos[lightbox] && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
            onClick={() => setLightbox(null)}
          >
            {/* Image */}
            <motion.img
              key={lightbox}
              initial={{ scale: 0.92, opacity: 0 }}
              animate={{ scale: 1,    opacity: 1 }}
              exit={{    scale: 0.92, opacity: 0 }}
              transition={{ duration: 0.2 }}
              src={photos[lightbox].url}
              alt=""
              className="max-h-[90vh] max-w-[90vw] rounded-2xl object-contain shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            />

            {/* Close */}
            <button
              onClick={() => setLightbox(null)}
              className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20
                flex items-center justify-center transition-colors"
            >
              <X size={18} />
            </button>

            {/* Prev */}
            {lightbox > 0 && (
              <button
                onClick={(e) => { e.stopPropagation(); prevLightbox(); }}
                className="absolute left-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-white/10
                  hover:bg-white/20 flex items-center justify-center transition-colors"
              >
                <ChevronLeft size={22} />
              </button>
            )}

            {/* Next */}
            {lightbox < photos.length - 1 && (
              <button
                onClick={(e) => { e.stopPropagation(); nextLightbox(); }}
                className="absolute right-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-white/10
                  hover:bg-white/20 flex items-center justify-center transition-colors"
              >
                <ChevronRight size={22} />
              </button>
            )}

            {/* Bottom bar */}
            <div className="absolute bottom-0 inset-x-0 px-5 py-4 flex items-center justify-between
              bg-gradient-to-t from-black/80 to-transparent">
              <div className="flex items-center gap-3">
                <ScoreBadge score={photos[lightbox].similarity_score} />
                <span className="text-white/40 text-sm">
                  {lightbox + 1} / {photos.length}
                </span>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); download(photos[lightbox]); }}
                className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 rounded-xl
                  px-4 py-2 text-sm font-medium transition-colors active:scale-95"
              >
                <Download size={15} /> Скачать
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

import { motion } from "framer-motion";

interface Props {
  progress: number; // 0-100
  label?: string;
}

export default function ProgressBar({ progress, label }: Props) {
  return (
    <div className="w-full max-w-sm mx-auto">
      <div className="flex justify-between text-sm text-white/60 mb-2">
        <span>{label ?? "Генерация..."}</span>
        <span>{progress}%</span>
      </div>
      <div className="h-2 bg-white/10 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-brand-500 to-pink-400 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ ease: "easeOut", duration: 0.4 }}
        />
      </div>
    </div>
  );
}

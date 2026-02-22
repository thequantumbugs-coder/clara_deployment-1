import React from 'react';
import { motion } from 'motion/react';
import { useLanguage, Language } from '../context/LanguageContext';

const LANGUAGES: { name: Language; label: string }[] = [
  { name: 'English', label: 'English' },
  { name: 'Kannada', label: 'ಕನ್ನಡ' },
  { name: 'Hindi', label: 'हिन्दी' },
  { name: 'Tamil', label: 'தமிழ்' },
  { name: 'Telugu', label: 'తెలుగు' },
  { name: 'Malayalam', label: 'മലയാളം' },
];

export default function LanguageSelect({ onSelect }: { onSelect: (language: Language) => void }) {
  const { setLanguage, t } = useLanguage();

  const handleSelect = (lang: Language) => {
    setLanguage(lang);
    onSelect(lang);
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.05 }}
      className="w-full h-full flex flex-col items-center justify-center p-12"
    >
      <motion.h2
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="text-4xl font-display italic text-stone-100 mb-16 tracking-wide"
      >
        {t('selectLanguage')}
      </motion.h2>

      <div className="grid grid-cols-3 gap-8 w-full max-w-6xl">
        {LANGUAGES.map((lang, index) => (
          <motion.button
            key={lang.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => handleSelect(lang.name)}
            className="glass touch-button group relative overflow-hidden rounded-2xl flex flex-col items-center justify-center py-12 px-8 transition-all hover:border-neo-mint/30"
            data-testid={`language-${lang.name.toLowerCase()}`}
          >
            <div className="absolute inset-0 bg-neo-mint/0 group-active:bg-neo-mint/5 transition-colors" />
            
            <span className="text-3xl font-medium text-stone-100 mb-2">
              {lang.label}
            </span>
            <span className="text-sm tracking-widest uppercase text-stone-500 group-hover:text-neo-mint transition-colors">
              {lang.name}
            </span>

            {/* Subtle corner accent */}
            <div className="absolute top-4 right-4 w-2 h-2 rounded-full bg-white/5 group-hover:bg-neo-mint/40 transition-colors" />
          </motion.button>
        ))}
      </div>

      <div className="mt-24 text-stone-600 text-xs tracking-[0.4em] uppercase">
        Touch to begin your experience
      </div>
    </motion.div>
  );
}

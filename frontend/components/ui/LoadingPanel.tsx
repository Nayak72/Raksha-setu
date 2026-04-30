'use client';

export default function LoadingPanel() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-raksha-500/30 border-t-raksha-400 rounded-full animate-spin" />
        <div className="text-surface-500 text-sm">Loading...</div>
      </div>
    </div>
  );
}

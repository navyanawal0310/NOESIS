import React from 'react';
import { X, Tag, Database } from 'lucide-react';
import { Entity } from '../types';

interface EntityDetailModalProps {
  entity: Entity | null;
  onClose: () => void;
}

export const EntityDetailModal: React.FC<EntityDetailModalProps> = ({ entity, onClose }) => {
  if (!entity) return null;

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'PERSON':
        return 'text-sky-400 bg-sky-500/10 border-sky-500/30';
      case 'ORGANIZATION':
        return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
      case 'TECHNOLOGY':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
      case 'PROJECT':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
      case 'LOCATION':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
      default:
        return 'text-neutral-300 bg-neutral-800 border-neutral-700';
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-graphite-900 border border-graphite-700 rounded-lg max-w-lg w-full shadow-2xl p-6 font-mono relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-neutral-400 hover:text-neutral-200 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-4">
          <div className="w-9 h-9 rounded bg-graphite-800 border border-graphite-700 flex items-center justify-center">
            <Database className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-neutral-100">{entity.canonical_name}</h3>
            <span className={`text-[10px] uppercase px-2 py-0.5 rounded border inline-block mt-1 font-mono ${getTypeColor(entity.type)}`}>
              {entity.type}
            </span>
          </div>
        </div>

        <div className="space-y-4 text-xs">
          <div>
            <span className="text-neutral-400 block mb-1">Entity Identifier:</span>
            <div className="p-2 bg-graphite-950 rounded border border-graphite-800 text-amber-400 selection:bg-amber-500/30">
              {entity.id}
            </div>
          </div>

          {entity.description && (
            <div>
              <span className="text-neutral-400 block mb-1">Description / Role:</span>
              <div className="p-2.5 bg-graphite-950 rounded border border-graphite-800 text-neutral-300 font-sans leading-relaxed">
                {entity.description}
              </div>
            </div>
          )}

          {entity.aliases && entity.aliases.length > 0 && (
            <div>
              <span className="text-neutral-400 block mb-1">Known Aliases:</span>
              <div className="flex flex-wrap gap-1.5">
                {entity.aliases.map((alias, idx) => (
                  <span
                    key={idx}
                    className="flex items-center space-x-1 px-2 py-1 rounded bg-graphite-800 border border-graphite-700 text-neutral-300 text-[11px]"
                  >
                    <Tag className="w-3 h-3 text-neutral-400" />
                    <span>{alias}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="pt-2 border-t border-graphite-800 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded bg-graphite-800 hover:bg-graphite-700 text-neutral-200 text-xs transition-colors border border-graphite-700"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { Play, Plus, Trash2, CornerDownRight } from 'lucide-react';
import { Entity, EntityType, StructuredQueryPlan, TraversalStep } from '../types';

interface QueryBuilderProps {
  entities: Entity[];
  onExecute: (plan: StructuredQueryPlan) => void;
  loading: boolean;
}

const PRESET_QUERIES: Array<{ label: string; plan: StructuredQueryPlan }> = [
  {
    label: '3-Hop: Project Prometheus → Technologies',
    plan: {
      start_entity: 'ent_proj_prometheus',
      steps: [
        { predicate: 'WORKED_ON', direction: 'incoming' },
        { predicate: 'FOUNDED', direction: 'outgoing' },
        { predicate: 'DEVELOPED', direction: 'outgoing' },
      ],
      return_type: 'TECHNOLOGY',
      max_hops: 3,
    },
  },
  {
    label: '2-Hop: Nexus Institute Funded → Researchers',
    plan: {
      start_entity: 'ent_nexus_institute',
      steps: [
        { predicate: 'FUNDED', direction: 'outgoing' },
        { predicate: 'WORKED_ON', direction: 'incoming' },
      ],
      return_type: 'PERSON',
      max_hops: 2,
    },
  },
  {
    label: '1-Hop: Zurich Innovation Center → Organizations',
    plan: {
      start_entity: 'ent_zurich',
      steps: [{ predicate: 'LOCATED_IN', direction: 'incoming' }],
      return_type: 'ORGANIZATION',
      max_hops: 1,
    },
  },
  {
    label: 'Negative Control: Project Hyperion → Quantum Protocols',
    plan: {
      start_entity: 'ent_proj_hyperion',
      steps: [
        { predicate: 'WORKED_ON', direction: 'incoming' },
        { predicate: 'EMPLOYED_BY', direction: 'outgoing' },
        { predicate: 'DEVELOPED', direction: 'outgoing' },
      ],
      return_type: 'TECHNOLOGY',
      predicate_filter: 'DEVELOPED_QUANTUM',
      max_hops: 3,
    },
  },
];

const COMMON_PREDICATES = [
  'WORKED_ON',
  'FOUNDED',
  'DEVELOPED',
  'EMPLOYED_BY',
  'COLLABORATED_WITH',
  'FUNDED',
  'LOCATED_IN',
  'USES',
];

export const QueryBuilder: React.FC<QueryBuilderProps> = ({ entities, onExecute, loading }) => {
  const [startEntity, setStartEntity] = useState<string>('ent_proj_prometheus');
  const [steps, setSteps] = useState<TraversalStep[]>([
    { predicate: 'WORKED_ON', direction: 'incoming' },
    { predicate: 'FOUNDED', direction: 'outgoing' },
    { predicate: 'DEVELOPED', direction: 'outgoing' },
  ]);
  const [returnType, setReturnType] = useState<EntityType | ''>('TECHNOLOGY');
  const [maxHops, setMaxHops] = useState<number>(3);

  const handleApplyPreset = (presetPlan: StructuredQueryPlan) => {
    setStartEntity(presetPlan.start_entity);
    setSteps(presetPlan.steps);
    setReturnType(presetPlan.return_type || '');
    setMaxHops(presetPlan.max_hops);
  };

  const handleAddStep = () => {
    if (steps.length < 5) {
      setSteps([...steps, { predicate: 'DEVELOPED', direction: 'outgoing' }]);
      setMaxHops(Math.max(maxHops, steps.length + 1));
    }
  };

  const handleRemoveStep = (index: number) => {
    if (steps.length > 1) {
      setSteps(steps.filter((_, i) => i !== index));
    }
  };

  const handleStepChange = (index: number, field: keyof TraversalStep, value: any) => {
    const updated = [...steps];
    updated[index] = { ...updated[index], [field]: value };
    setSteps(updated);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const plan: StructuredQueryPlan = {
      start_entity: startEntity,
      steps: steps,
      return_type: returnType ? (returnType as EntityType) : undefined,
      max_hops: maxHops,
    };
    onExecute(plan);
  };

  return (
    <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-5 font-mono shadow-lg">
      {/* Preset Buttons */}
      <div className="mb-4">
        <span className="text-[11px] text-neutral-400 block mb-2 uppercase tracking-wider">
          Standard Benchmark Presets
        </span>
        <div className="flex flex-wrap gap-2">
          {PRESET_QUERIES.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleApplyPreset(preset.plan)}
              className="text-xs px-2.5 py-1 rounded bg-graphite-850 hover:bg-graphite-800 border border-graphite-700 text-neutral-300 hover:text-amber-400 transition-colors"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Start Entity & Return Type */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="md:col-span-2">
            <label className="text-[11px] text-neutral-400 block mb-1">Start Entity (Subject Origin)</label>
            <select
              value={startEntity}
              onChange={(e) => setStartEntity(e.target.value)}
              className="w-full bg-graphite-950 border border-graphite-700 rounded px-3 py-1.5 text-xs text-neutral-100 focus:outline-none focus:border-amber-500"
            >
              {entities.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.canonical_name} ({e.type} - {e.id})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[11px] text-neutral-400 block mb-1">Target Return Type</label>
            <select
              value={returnType}
              onChange={(e) => setReturnType(e.target.value as EntityType | '')}
              className="w-full bg-graphite-950 border border-graphite-700 rounded px-3 py-1.5 text-xs text-neutral-100 focus:outline-none focus:border-amber-500"
            >
              <option value="">Any Entity Type</option>
              <option value="TECHNOLOGY">TECHNOLOGY</option>
              <option value="PERSON">PERSON</option>
              <option value="ORGANIZATION">ORGANIZATION</option>
              <option value="PROJECT">PROJECT</option>
              <option value="LOCATION">LOCATION</option>
            </select>
          </div>
        </div>

        {/* Traversal Steps */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-neutral-400 uppercase tracking-wider flex items-center space-x-1.5">
              <CornerDownRight className="w-3.5 h-3.5 text-amber-400" />
              <span>Bounded Traversal Steps ({steps.length}/5 Hops)</span>
            </span>
            <button
              type="button"
              onClick={handleAddStep}
              disabled={steps.length >= 5}
              className="text-[11px] flex items-center space-x-1 px-2 py-0.5 rounded bg-graphite-850 hover:bg-graphite-800 border border-graphite-700 text-amber-400 disabled:opacity-40 transition-colors"
            >
              <Plus className="w-3 h-3" />
              <span>Add Hop</span>
            </button>
          </div>

          <div className="space-y-2">
            {steps.map((step, idx) => (
              <div
                key={idx}
                className="flex items-center space-x-2 bg-graphite-950 p-2.5 rounded border border-graphite-800 text-xs"
              >
                <span className="w-6 text-center text-neutral-500 font-bold">H{idx + 1}</span>

                <select
                  value={step.direction}
                  onChange={(e) => handleStepChange(idx, 'direction', e.target.value)}
                  className="bg-graphite-900 border border-graphite-700 rounded px-2 py-1 text-neutral-200 focus:outline-none focus:border-amber-500"
                >
                  <option value="outgoing">Outgoing (→)</option>
                  <option value="incoming">Incoming (←)</option>
                  <option value="both">Both (↔)</option>
                </select>

                <select
                  value={step.predicate}
                  onChange={(e) => handleStepChange(idx, 'predicate', e.target.value)}
                  className="flex-1 bg-graphite-900 border border-graphite-700 rounded px-2 py-1 text-amber-400 focus:outline-none focus:border-amber-500 font-semibold"
                >
                  {COMMON_PREDICATES.map((pred) => (
                    <option key={pred} value={pred}>
                      {pred}
                    </option>
                  ))}
                </select>

                {steps.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveStep(idx)}
                    className="p-1 rounded text-neutral-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Action Button */}
        <div className="flex justify-end pt-2 border-t border-graphite-800">
          <button
            type="submit"
            disabled={loading}
            className="flex items-center space-x-2 px-5 py-2 rounded bg-amber-500 hover:bg-amber-400 text-graphite-950 font-bold text-xs transition-colors shadow-lg disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{loading ? 'Executing Traversal...' : 'Execute Traversal Query'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};

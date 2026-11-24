import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { ZoomIn, ZoomOut, Maximize2, RefreshCw } from 'lucide-react';
import { Claim, Entity, GraphPayload } from '../types';
import { api } from '../services/api';

interface KnowledgeGraphExplorerProps {
  onSelectEntity: (entity: Entity) => void;
  onSelectClaim: (claim: Claim) => void;
  onSelectDocument: (docId: string) => void;
}

export const KnowledgeGraphExplorer: React.FC<KnowledgeGraphExplorerProps> = ({
  onSelectEntity,
  onSelectClaim,
  onSelectDocument,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const [graphData, setGraphData] = useState<GraphPayload | null>(null);
  const [layoutName, setLayoutName] = useState<string>('cose');
  const [showEvidence, setShowEvidence] = useState<boolean>(false);
  const [showDocuments, setShowDocuments] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  const loadGraph = async () => {
    setLoading(true);
    try {
      const data = await api.getGraph();
      setGraphData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraph();
  }, []);

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    // Filter elements based on display toggles
    const rawNodes = graphData.elements.nodes;
    const rawEdges = graphData.elements.edges;

    const filteredNodes = rawNodes.filter((n) => {
      if (n.data.type === 'Evidence' && !showEvidence) return false;
      if (n.data.type === 'Document' && !showDocuments) return false;
      return true;
    });

    const activeNodeIds = new Set(filteredNodes.map((n) => n.data.id));

    const filteredEdges = rawEdges.filter((e) => {
      return activeNodeIds.has(e.data.source) && activeNodeIds.has(e.data.target);
    });

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: {
        nodes: filteredNodes,
        edges: filteredEdges,
      },
      style: [
        // Default Node
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'color': '#d1d5db',
            'font-family': 'Inter, sans-serif',
            'font-size': '10px',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'background-color': '#475569',
            'width': 26,
            'height': 26,
            'border-width': 1.5,
            'border-color': '#334155',
          },
        },
        // Entities by classification
        {
          selector: 'node[type = "Entity"][entity_type = "PERSON"]',
          style: {
            'background-color': '#0284c7',
            'border-color': '#38bdf8',
            'shape': 'ellipse',
            'width': 30,
            'height': 30,
          },
        },
        {
          selector: 'node[type = "Entity"][entity_type = "ORGANIZATION"]',
          style: {
            'background-color': '#7e22ce',
            'border-color': '#c084fc',
            'shape': 'round-rectangle',
            'width': 34,
            'height': 34,
          },
        },
        {
          selector: 'node[type = "Entity"][entity_type = "TECHNOLOGY"]',
          style: {
            'background-color': '#059669',
            'border-color': '#34d399',
            'shape': 'hexagon',
            'width': 32,
            'height': 32,
          },
        },
        {
          selector: 'node[type = "Entity"][entity_type = "PROJECT"]',
          style: {
            'background-color': '#d97706',
            'border-color': '#fbbf24',
            'shape': 'diamond',
            'width': 36,
            'height': 36,
          },
        },
        {
          selector: 'node[type = "Entity"][entity_type = "LOCATION"]',
          style: {
            'background-color': '#e11d48',
            'border-color': '#fb7185',
            'shape': 'triangle',
            'width': 28,
            'height': 28,
          },
        },
        // Reified Claims
        {
          selector: 'node[type = "Claim"]',
          style: {
            'background-color': '#1e2126',
            'border-color': '#f59e0b',
            'border-width': 2,
            'shape': 'diamond',
            'width': 20,
            'height': 20,
            'font-size': '8px',
            'color': '#fbbf24',
          },
        },
        // Evidence Nodes
        {
          selector: 'node[type = "Evidence"]',
          style: {
            'background-color': '#334155',
            'border-color': '#64748b',
            'shape': 'round-tag',
            'width': 18,
            'height': 18,
            'font-size': '8px',
          },
        },
        // Document Nodes
        {
          selector: 'node[type = "Document"]',
          style: {
            'background-color': '#0f172a',
            'border-color': '#cbd5e1',
            'shape': 'barrel',
            'width': 26,
            'height': 26,
            'font-size': '9px',
          },
        },
        // Default Edges
        {
          selector: 'edge',
          style: {
            'width': 1.2,
            'line-color': '#334155',
            'target-arrow-color': '#64748b',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '7px',
            'font-family': 'monospace',
            'color': '#64748b',
            'text-rotation': 'autorotate',
            'text-background-color': '#121316',
            'text-background-opacity': 0.8,
            'text-background-padding': '2px',
          },
        },
        {
          selector: 'edge[rel_type = "CONTRADICTS"]',
          style: {
            'line-color': '#ef4444',
            'target-arrow-color': '#ef4444',
            'line-style': 'dashed',
            'width': 2,
            'color': '#f87171',
          },
        },
      ],
      layout: {
        name: layoutName,
        padding: 40,
        animate: false,
      } as any,
    });

    // Node click interactions
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const data = node.data();

      if (data.type === 'Entity') {
        api.getEntity(data.id).then((ent) => onSelectEntity(ent));
      } else if (data.type === 'Claim') {
        api.getClaim(data.id).then((clm: Claim) => onSelectClaim(clm));
      } else if (data.type === 'Document') {
        onSelectDocument(data.id);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [graphData, layoutName, showEvidence, showDocuments]);

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current?.fit();

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-3.5 font-mono flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-3">
          <span className="text-neutral-400">Layout:</span>
          <select
            value={layoutName}
            onChange={(e) => setLayoutName(e.target.value)}
            className="bg-graphite-950 border border-graphite-700 rounded px-2.5 py-1 text-neutral-200 focus:outline-none focus:border-amber-500"
          >
            <option value="cose">Force-Directed (CoSE)</option>
            <option value="concentric">Concentric</option>
            <option value="breadthfirst">Breadth-First Hierarchical</option>
            <option value="grid">Grid Matrix</option>
          </select>

          <span className="text-neutral-600">|</span>

          {/* Visibility Toggles */}
          <label className="flex items-center space-x-1.5 cursor-pointer text-neutral-300">
            <input
              type="checkbox"
              checked={showEvidence}
              onChange={(e) => setShowEvidence(e.target.checked)}
              className="accent-amber-500 rounded"
            />
            <span>Show Evidence Nodes</span>
          </label>

          <label className="flex items-center space-x-1.5 cursor-pointer text-neutral-300">
            <input
              type="checkbox"
              checked={showDocuments}
              onChange={(e) => setShowDocuments(e.target.checked)}
              className="accent-amber-500 rounded"
            />
            <span>Show Document Nodes</span>
          </label>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleZoomIn}
            className="p-1.5 rounded bg-graphite-850 hover:bg-graphite-800 border border-graphite-700 text-neutral-300 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-1.5 rounded bg-graphite-850 hover:bg-graphite-800 border border-graphite-700 text-neutral-300 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleFit}
            className="p-1.5 rounded bg-graphite-850 hover:bg-graphite-800 border border-graphite-700 text-neutral-300 transition-colors"
            title="Fit to Screen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={loadGraph}
            className="p-1.5 rounded bg-graphite-850 hover:bg-graphite-800 border border-graphite-700 text-amber-400 transition-colors"
            title="Refresh Graph"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Cytoscape Canvas */}
      <div className="relative bg-graphite-950 border border-graphite-800 rounded-lg overflow-hidden h-[680px]">
        {loading && (
          <div className="absolute inset-0 bg-graphite-950/70 backdrop-blur-sm z-10 flex items-center justify-center font-mono text-xs text-neutral-400">
            Loading Knowledge Graph Substrate...
          </div>
        )}
        <div ref={containerRef} className="w-full h-full" />

        {/* Legend */}
        <div className="absolute bottom-3 left-3 bg-graphite-900/90 border border-graphite-800 rounded p-2.5 font-mono text-[10px] space-y-1 backdrop-blur shadow-lg z-10">
          <span className="text-neutral-400 font-semibold block uppercase mb-1">Entity Ontology</span>
          <div className="flex items-center space-x-2"><span className="w-2.5 h-2.5 rounded-full bg-sky-400" /><span>PERSON</span></div>
          <div className="flex items-center space-x-2"><span className="w-2.5 h-2.5 rounded-sm bg-purple-400" /><span>ORGANIZATION</span></div>
          <div className="flex items-center space-x-2"><span className="w-2.5 h-2.5 bg-emerald-400" style={{ clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)' }} /><span>TECHNOLOGY</span></div>
          <div className="flex items-center space-x-2"><span className="w-2.5 h-2.5 rotate-45 bg-amber-400" /><span>PROJECT</span></div>
          <div className="flex items-center space-x-2"><span className="w-2.5 h-2.5 bg-rose-400" style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }} /><span>LOCATION</span></div>
          <div className="flex items-center space-x-2 pt-1 border-t border-graphite-800"><span className="w-2.5 h-2.5 border border-amber-400 bg-graphite-900 rotate-45" /><span>CLAIM (Reified)</span></div>
        </div>
      </div>
    </div>
  );
};

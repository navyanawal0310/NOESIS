import React, { useEffect, useState } from 'react';
import {
  FileText,
  Hash,
  Calendar,
  CheckCircle2,
  Search,
  ShieldCheck,
} from 'lucide-react';
import { Document } from '../types';
import { api } from '../services/api';

interface SourceVaultProps {
  initialDocumentId?: string | null;
}

export const SourceVault: React.FC<SourceVaultProps> = ({ initialDocumentId }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [highlightOffsets, setHighlightOffsets] = useState<[number, number] | null>(null);
  const [searchFilter, setSearchFilter] = useState<string>('');

  useEffect(() => {
    api
      .getDocuments()
      .then((docs) => {
        setDocuments(docs);
        if (initialDocumentId) {
          const match = docs.find((d) => d.id === initialDocumentId);
          if (match) setSelectedDoc(match);
          else if (docs.length > 0) setSelectedDoc(docs[0]);
        } else if (docs.length > 0) {
          setSelectedDoc(docs[0]);
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [initialDocumentId]);

  const filteredDocs = documents.filter(
    (d) =>
      d.id.toLowerCase().includes(searchFilter.toLowerCase()) ||
      d.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
      d.raw_text.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const renderHighlightedText = (text: string, offsets: [number, number] | null) => {
    if (!offsets) return text;
    const [start, end] = offsets;
    if (start < 0 || end > text.length || start >= end) return text;

    const before = text.slice(0, start);
    const target = text.slice(start, end);
    const after = text.slice(end);

    return (
      <>
        {before}
        <mark className="bg-amber-500/25 text-amber-200 border-b-2 border-amber-400 px-0.5 rounded font-medium">
          {target}
        </mark>
        {after}
      </>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 font-mono text-xs">
      {/* Document Sidebar (4 cols) */}
      <div className="lg:col-span-4 space-y-3">
        <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-3">
          <div className="relative mb-3">
            <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Filter synthetic documents..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full bg-graphite-950 border border-graphite-700 rounded pl-8 pr-3 py-1.5 text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-amber-500 text-xs"
            />
          </div>

          <div className="space-y-1.5 max-h-[620px] overflow-y-auto pr-1">
            {loading ? (
              <div className="p-4 text-center text-neutral-500">Loading documents...</div>
            ) : (
              filteredDocs.map((doc) => {
                const isSelected = selectedDoc?.id === doc.id;
                return (
                  <div
                    key={doc.id}
                    onClick={() => {
                      setSelectedDoc(doc);
                      setHighlightOffsets(null);
                    }}
                    className={`p-3 rounded cursor-pointer transition-colors border ${
                      isSelected
                        ? 'bg-amber-500/10 border-amber-500/40 text-neutral-100'
                        : 'bg-graphite-950 hover:bg-graphite-850 border-graphite-800 text-neutral-400'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-amber-400">{doc.id}</span>
                      <span className="text-[10px] uppercase px-1.5 py-0.2 rounded bg-graphite-800 text-neutral-400 border border-graphite-700">
                        {doc.source_type}
                      </span>
                    </div>
                    <p className="font-sans font-medium text-xs text-neutral-200 line-clamp-2">
                      {doc.title}
                    </p>
                    <div className="flex items-center space-x-2 text-[10px] text-neutral-500 mt-2 font-mono">
                      <span>{doc.publication_date || '2023'}</span>
                      <span>•</span>
                      <span>{doc.raw_text.length} chars</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Document Reader (8 cols) */}
      <div className="lg:col-span-8 space-y-4">
        {selectedDoc ? (
          <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-6 shadow-xl space-y-5">
            {/* Header info */}
            <div>
              <div className="flex items-center space-x-2 text-[11px] text-amber-400 mb-1">
                <FileText className="w-4 h-4" />
                <span>SYNTHETIC SOURCE DOSSIER</span>
                <span className="px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px]">
                  BENCHMARK
                </span>
              </div>
              <h2 className="text-lg font-bold text-neutral-100 font-sans tracking-tight">
                {selectedDoc.title}
              </h2>

              <div className="flex flex-wrap items-center gap-4 text-[11px] text-neutral-400 mt-2 pt-2 border-t border-graphite-800">
                <div className="flex items-center space-x-1">
                  <Hash className="w-3.5 h-3.5 text-neutral-500" />
                  <span>ID: <strong className="text-neutral-200">{selectedDoc.id}</strong></span>
                </div>
                <div className="flex items-center space-x-1">
                  <Calendar className="w-3.5 h-3.5 text-neutral-500" />
                  <span>Date: {selectedDoc.publication_date || 'N/A'}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Hash: {selectedDoc.content_hash.slice(0, 16)}...</span>
                </div>
              </div>
            </div>

            {/* Document Text Viewer */}
            <div className="bg-graphite-950 border border-graphite-855 rounded-lg p-5 font-sans text-sm text-neutral-200 leading-relaxed whitespace-pre-wrap selection:bg-amber-500/30">
              {renderHighlightedText(selectedDoc.raw_text, highlightOffsets)}
            </div>

            {/* Quotation Verification Footnote */}
            <div className="p-3 bg-graphite-950 rounded border border-graphite-800 flex items-start space-x-2 text-[11px] text-neutral-400 font-sans">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-neutral-300 font-medium">Exact Text Provenance Verification Guarantee</p>
                <p className="mt-0.5 text-neutral-400 leading-relaxed">
                  Every evidence record mapped to {selectedDoc.id} is verified at character offsets against this raw text.
                  Quotation matching confirms exact lexical presence in source text, while semantic correctness is maintained via the claim graph.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-12 text-center text-neutral-500">
            Select a document from the vault to inspect its source text and provenance records.
          </div>
        )}
      </div>
    </div>
  );
};

"use client";

import React, { useState } from "react";
import {
  Upload,
  FileText,
  CheckCircle,
  AlertTriangle,
  Sparkles,
  Loader2,
  FileSpreadsheet,
  FileCode,
  ShieldCheck,
} from "lucide-react";
import { ApiClient } from "@/lib/apiClient";
import { SupplierQuote } from "@/types/procurement";

interface UploadScreenProps {
  isBackendLive: boolean;
  onExtractionComplete: (suppliers: SupplierQuote[]) => void;
}

export function UploadScreen({ isBackendLive, onExtractionComplete }: UploadScreenProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [parseResult, setParseResult] = useState<any>(null);
  const [extractedSuppliers, setExtractedSuppliers] = useState<SupplierQuote[] | null>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "csv", "xlsx", "xls"].includes(ext || "")) {
      alert("Unsupported file format. Please upload PDF, CSV, or XLSX supplier quotations.");
      return;
    }
    setSelectedFile(file);
    setParseResult(null);
    setExtractedSuppliers(null);
  };

  const runExtraction = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setProgress(20);

    // Simulate progress steps
    const timer = setInterval(() => {
      setProgress((old) => (old >= 90 ? 90 : old + 20));
    }, 300);

    try {
      // Step 1: Upload and parse document
      const parsed = await ApiClient.uploadDocument(selectedFile);
      setParseResult(parsed);
      setProgress(70);

      // Step 2: Run Gemma claim extraction
      const extractRes = await ApiClient.extractClaims(parsed.filename, parsed.raw_text, !isBackendLive);
      setProgress(100);
      clearInterval(timer);

      setExtractedSuppliers(extractRes.suppliers);
      onExtractionComplete(extractRes.suppliers);
    } catch (err) {
      clearInterval(timer);
      alert("Extraction processing error: " + String(err));
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8 text-slate-800">
      {/* Upload Banner */}
      <div className="bg-white p-8 rounded-2xl border border-slate-200/80 shadow-sm space-y-6">
        <div>
          <h3 className="text-xl font-bold text-slate-900 tracking-tight">
            Upload Supplier Quotation Document
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            Upload PDF, CSV, or XLSX price quotes. Gemma 4 will extract structured supplier data,
            flag missing fields, and ground claims in source page excerpts.
          </p>
        </div>

        {/* Drag & Drop Area */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all ${
            dragActive
              ? "border-blue-500 bg-blue-50/50"
              : "border-slate-300 hover:border-slate-400 bg-slate-50/50"
          }`}
        >
          <div className="w-16 h-16 rounded-2xl bg-blue-100 text-blue-600 flex items-center justify-center mx-auto mb-4">
            <Upload className="w-8 h-8" />
          </div>
          <h4 className="text-base font-semibold text-slate-800">
            Drag and drop your quotation file here
          </h4>
          <p className="text-xs text-slate-400 mt-1">Supports PDF, CSV, and XLSX formats up to 25MB</p>

          <label className="mt-6 inline-block px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs cursor-pointer shadow-md shadow-blue-600/30 transition-colors">
            Browse Computer
            <input
              type="file"
              accept=".pdf,.csv,.xlsx,.xls"
              onChange={(e) => e.target.files && handleFileSelect(e.target.files[0])}
              className="hidden"
            />
          </label>
        </div>

        {/* Selected File Details */}
        {selectedFile && (
          <div className="p-4 rounded-xl bg-slate-100/80 border border-slate-200 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-blue-600">
                {selectedFile.name.endsWith(".csv") ? (
                  <FileCode className="w-5 h-5 text-emerald-600" />
                ) : selectedFile.name.endsWith(".xlsx") ? (
                  <FileSpreadsheet className="w-5 h-5 text-green-600" />
                ) : (
                  <FileText className="w-5 h-5 text-blue-600" />
                )}
              </div>
              <div>
                <p className="text-sm font-bold text-slate-900">{selectedFile.name}</p>
                <p className="text-xs text-slate-500">
                  {(selectedFile.size / 1024).toFixed(1)} KB • Ready for extraction
                </p>
              </div>
            </div>

            <button
              onClick={runExtraction}
              disabled={isProcessing}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold text-xs shadow-md shadow-blue-600/30 hover:opacity-95 transition-opacity disabled:opacity-50 flex items-center space-x-2"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Extracting Claims...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Run Gemma Extraction</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* Progress Indicator */}
        {isProcessing && (
          <div className="space-y-2 pt-2">
            <div className="flex justify-between text-xs font-semibold text-slate-600">
              <span>Extracting Supplier Quotation Claims & Source Citations...</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 transition-all duration-300 rounded-full"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>

      {/* Extracted Supplier Results Preview */}
      {extractedSuppliers && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h4 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-emerald-500" />
              Extraction Results ({extractedSuppliers.length} Supplier Quotes Extracted)
            </h4>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-100 text-blue-800">
              {isBackendLive ? "Live Gemma 4 Extraction" : "Simulated Demo Result"}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {extractedSuppliers.map((s) => (
              <div
                key={s.supplier_id}
                className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4"
              >
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div>
                    <h5 className="font-bold text-slate-900 text-base">{s.supplier_name}</h5>
                    <p className="text-xs text-slate-400">ID: {s.supplier_id}</p>
                  </div>
                  <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    ₹{s.unit_price} / unit
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-slate-50 p-2.5 rounded-lg">
                    <span className="text-slate-400 block">MOQ</span>
                    <span className="font-semibold text-slate-800">{s.moq ?? "Unspecified"}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg">
                    <span className="text-slate-400 block">Monthly Capacity</span>
                    <span className="font-semibold text-slate-800">{s.capacity ?? "Unspecified"} units</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg">
                    <span className="text-slate-400 block">Lead Time</span>
                    <span className="font-semibold text-slate-800">
                      {s.delivery_days ? `${s.delivery_days} days` : "Ambiguous"}
                    </span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg">
                    <span className="text-slate-400 block">Freight Charge</span>
                    <span className="font-semibold text-slate-800">
                      {s.transport_cost ? `₹${s.transport_cost}` : "Missing (Omitted)"}
                    </span>
                  </div>
                </div>

                {/* Missing & Conflict Tags */}
                {s.missing_fields.length > 0 && (
                  <div className="flex items-center space-x-2 text-xs text-amber-700 bg-amber-50 p-2.5 rounded-lg border border-amber-200">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    <span>Missing Fields: {s.missing_fields.join(", ")}</span>
                  </div>
                )}

                {/* Claim Excerpts */}
                <div className="space-y-1.5 pt-2">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Grounded Source Excerpts
                  </span>
                  {s.claims.slice(0, 2).map((c, idx) => (
                    <div key={idx} className="p-2 rounded bg-slate-50 text-[11px] text-slate-600 border border-slate-150 italic">
                      "{c.source_excerpt}"
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

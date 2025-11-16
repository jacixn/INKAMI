"use client";

import axios from "axios";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";

import LoadingOrbit from "./LoadingOrbit";

const dropHints = [
  "ZIP • PDF • PNG • JPG",
  "Auto-splits long scrolls",
  "Images deleted after processing"
];

export default function UploadWizard() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isHovering, setIsHovering] = useState(false);

  const sizeText = useMemo(() => {
    const total = files.reduce((acc, file) => acc + file.size, 0);
    if (!total) return "0 MB";
    return `${(total / (1024 * 1024)).toFixed(2)} MB`;
  }, [files]);

  const previewList = files.slice(0, 3);
  const extras = files.length - previewList.length;
  const preflight = files.length ? Math.min(35 + files.length * 4, 90) : 15;
  const progress = isUploading ? Math.min(preflight + 10, 96) : preflight;

  function handleFiles(list: FileList | null) {
    if (!list?.length) {
      setFiles([]);
      return;
    }
    setFiles(Array.from(list));
    setError(null);
    setIsHovering(false);
  }

  async function handleUpload() {
    if (!files.length || isUploading) return;
    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));

      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const response = await axios.post(`${apiUrl}/api/chapters`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      const chapterId = response.data?.chapter_id ?? response.data?.id;
      if (!chapterId) {
        throw new Error("Invalid server response");
      }

      router.push(`/chapters/${chapterId}`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Upload failed. Try again.";
      setError(message);
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <section className="glass-panel flex flex-col gap-6 p-6">
      <motion.div
        className={`rounded-3xl border border-dashed p-8 text-center transition ${
          isHovering ? "border-white/60 bg-white/10" : "border-white/20 bg-white/5"
        }`}
        whileHover={{ scale: 1.01 }}
        onClick={() => inputRef.current?.click()}
        onDragEnter={(event) => {
          event.preventDefault();
          setIsHovering(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setIsHovering(false);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          event.dataTransfer.dropEffect = "copy";
        }}
        onDrop={(event) => {
          event.preventDefault();
          handleFiles(event.dataTransfer.files);
        }}
      >
        <p className="text-sm text-white/80">
          Drop a chapter archive or browse your device.
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-3 text-xs text-white/60">
          {dropHints.map((hint) => (
            <span
              key={hint}
              className="rounded-full border border-white/15 px-4 py-1 backdrop-blur"
            >
              {hint}
            </span>
          ))}
        </div>
        <button
          type="button"
          className="mx-auto mt-6 inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-black shadow-lg shadow-purple-500/30"
          onClick={() => inputRef.current?.click()}
        >
          Browse files
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".zip,.pdf,image/*"
          multiple
          hidden
          onChange={(event) => handleFiles(event.target.files)}
        />
      </motion.div>

      {files.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-black/40 p-4 text-left">
          <p className="text-xs uppercase tracking-[0.3em] text-white/50">
            Selected batch
          </p>
          <p className="mt-2 text-xl font-semibold text-white">
            {files.length} file(s) · {sizeText}
          </p>
          <ul className="mt-3 space-y-1 text-sm text-white/70">
            {previewList.map((file) => (
              <li key={file.name}>{file.name}</li>
            ))}
            {extras > 0 && <li>+{extras} more</li>}
          </ul>
        </div>
      )}

      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs text-white/60">
          <span>Preflight check</span>
          <span>{progress}%</span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-gradient-to-r from-sky-400 via-purple-400 to-pink-400 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          disabled={isUploading || !files.length}
          className="flex flex-1 items-center justify-center gap-3 rounded-full bg-gradient-to-r from-blue-400 to-purple-500 px-4 py-4 text-sm font-semibold text-white transition enabled:hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          onClick={handleUpload}
        >
          {isUploading && <LoadingOrbit size={32} />}
          {isUploading ? "Uploading & queuing..." : "Start processing"}
        </button>
        <button
          type="button"
          className="rounded-full border border-white/20 px-4 py-3 text-sm text-white/80"
          onClick={() => setFiles([])}
          disabled={!files.length || isUploading}
        >
          Clear
        </button>
      </div>

      {error && (
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
          {error}
        </p>
      )}

      <p className="text-xs text-white/50">
        Files stay encrypted in transit and auto-delete once narration is ready.
      </p>
    </section>
  );
}


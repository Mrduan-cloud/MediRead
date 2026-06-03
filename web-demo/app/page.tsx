"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  SAMPLES,
  type IndicatorStatus,
  type RiskTier,
  type SampleReport,
} from "@/lib/samples";

type Phase = "select" | "analyzing" | "done";

const TIER_STYLE: Record<RiskTier, { text: string; chip: string; dot: string }> = {
  正常: { text: "text-emerald-300", chip: "bg-emerald-500/10 border-emerald-500/30", dot: "bg-emerald-400" },
  轻度偏离: { text: "text-sky-300", chip: "bg-sky-500/10 border-sky-500/30", dot: "bg-sky-400" },
  关注观察: { text: "text-amber-300", chip: "bg-amber-500/10 border-amber-500/30", dot: "bg-amber-400" },
  建议复查: { text: "text-orange-300", chip: "bg-orange-500/10 border-orange-500/30", dot: "bg-orange-400" },
  建议就医: { text: "text-rose-300", chip: "bg-rose-500/10 border-rose-500/30", dot: "bg-rose-400" },
};

const ANALYZE_STEPS = ["OCR 文字识别", "版式区域解析", "指标结构化抽取", "风险研判与建议"];

function statusMeta(s: IndicatorStatus): { label: string; cls: string } {
  if (s === "high") return { label: "↑ 偏高", cls: "text-rose-300 bg-rose-500/10 border-rose-500/20" };
  if (s === "low") return { label: "↓ 偏低", cls: "text-amber-300 bg-amber-500/10 border-amber-500/20" };
  return { label: "正常", cls: "text-neutral-400 bg-white/[0.04] border-white/10" };
}

function TierChip({ tier }: { tier: RiskTier }) {
  const s = TIER_STYLE[tier];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${s.chip} ${s.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {tier}
    </span>
  );
}

export default function Page() {
  const [phase, setPhase] = useState<Phase>("select");
  const [report, setReport] = useState<SampleReport | null>(null);
  const [step, setStep] = useState(0);
  const [fromUpload, setFromUpload] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const start = useCallback((r: SampleReport, viaUpload = false) => {
    setReport(r);
    setFromUpload(viaUpload);
    setStep(0);
    setPhase("analyzing");
  }, []);

  useEffect(() => {
    if (phase !== "analyzing") return;
    if (step >= ANALYZE_STEPS.length) {
      const t = setTimeout(() => setPhase("done"), 320);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setStep((s) => s + 1), 480);
    return () => clearTimeout(t);
  }, [phase, step]);

  const reset = () => {
    setPhase("select");
    setReport(null);
    setStep(0);
    setFromUpload(false);
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="mx-auto w-full max-w-3xl px-5 pb-24 pt-10 sm:pt-16">
        <Hero />
        <div className="mt-10 rounded-2xl border border-white/10 bg-white/[0.02] p-1.5 shadow-2xl shadow-black/40">
          <div className="rounded-xl bg-neutral-950/60 p-5 sm:p-7">
            {phase === "select" && (
              <SelectStage
                onPick={(r) => start(r)}
                onUpload={() => fileRef.current?.click()}
              />
            )}
            {phase === "analyzing" && report && <AnalyzeStage report={report} step={step} />}
            {phase === "done" && report && (
              <ResultStage report={report} fromUpload={fromUpload} onReset={reset} />
            )}
          </div>
        </div>
        <Footer />
      </main>

      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        className="hidden"
        onChange={() => start(SAMPLES[SAMPLES.length - 1], true)}
      />
    </div>
  );
}

function Nav() {
  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-neutral-950/70 backdrop-blur-xl">
      <div className="mx-auto flex h-14 w-full max-w-3xl items-center justify-between px-5">
        <div className="flex items-center gap-2.5">
          <span className="grid h-6 w-6 place-items-center rounded-md bg-white text-[13px] font-bold text-black">M</span>
          <span className="text-sm font-semibold tracking-tight text-white">MediRead</span>
          <span className="ml-1 rounded-full border border-white/15 px-2 py-0.5 text-[11px] text-neutral-400">
            演示模式
          </span>
        </div>
        <a
          href="https://github.com/Mrduan-cloud/MediRead"
          target="_blank"
          rel="noreferrer"
          className="text-sm text-neutral-400 transition hover:text-white"
        >
          GitHub ↗
        </a>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="text-center">
      <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs text-neutral-400">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
        PaddleOCR · 版式识别 · 指标抽取 · 风险分级
      </div>
      <h1 className="bg-gradient-to-b from-white to-neutral-400 bg-clip-text text-4xl font-semibold tracking-tight text-transparent sm:text-5xl">
        AI 体检报告智能解读
      </h1>
      <p className="mx-auto mt-4 max-w-xl text-balance text-[15px] leading-relaxed text-neutral-400">
        上传体检报告,自动完成 OCR 解析、指标结构化抽取,并给出按 4 级口径的风险研判与就医建议。
      </p>
    </section>
  );
}

function SelectStage({ onPick, onUpload }: { onPick: (r: SampleReport) => void; onUpload: () => void }) {
  return (
    <div className="animate-fade-up">
      <button
        onClick={onUpload}
        className="group flex w-full flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-white/15 bg-white/[0.015] py-10 transition hover:border-white/30 hover:bg-white/[0.03]"
      >
        <span className="grid h-11 w-11 place-items-center rounded-full border border-white/10 bg-white/5 text-neutral-300 transition group-hover:scale-105">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 16V4M12 4l-4 4M12 4l4 4" />
            <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
          </svg>
        </span>
        <span className="text-sm text-neutral-300">拖拽 PDF / 图片报告到此,或点击上传</span>
        <span className="text-xs text-neutral-500">演示模式下将以样例数据呈现解读</span>
      </button>

      <div className="my-6 flex items-center gap-3 text-xs text-neutral-600">
        <span className="h-px flex-1 bg-white/10" />
        或选择一份脱敏样例
        <span className="h-px flex-1 bg-white/10" />
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {SAMPLES.map((r) => (
          <button
            key={r.id}
            onClick={() => onPick(r)}
            className="group flex flex-col items-start gap-2 rounded-xl border border-white/10 bg-white/[0.02] p-4 text-left transition hover:-translate-y-0.5 hover:border-white/25 hover:bg-white/[0.04]"
          >
            <span className="text-sm font-medium text-white">{r.title}</span>
            <span className="text-xs text-neutral-500">{r.category}</span>
            <span className="mt-1">
              <TierChip tier={r.interpretation.overallTier} />
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function AnalyzeStage({ report, step }: { report: SampleReport; step: number }) {
  return (
    <div className="animate-fade-up py-6">
      <p className="mb-6 text-center text-sm text-neutral-400">
        正在解读 <span className="text-neutral-200">{report.title}</span> …
      </p>
      <ol className="mx-auto max-w-sm space-y-3">
        {ANALYZE_STEPS.map((label, i) => {
          const done = i < step;
          const active = i === step;
          return (
            <li key={label} className="flex items-center gap-3">
              <span
                className={`grid h-6 w-6 place-items-center rounded-full border text-[11px] transition ${
                  done
                    ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                    : active
                      ? "border-white/40 bg-white/10 text-white"
                      : "border-white/10 bg-white/[0.02] text-neutral-600"
                }`}
              >
                {done ? "✓" : i + 1}
              </span>
              <span className={`text-sm ${done ? "text-neutral-300" : active ? "text-white" : "text-neutral-600"}`}>
                {label}
              </span>
              {active && (
                <span className="ml-auto flex gap-1">
                  <Dot delay="0ms" />
                  <Dot delay="150ms" />
                  <Dot delay="300ms" />
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-400"
      style={{ animationDelay: delay }}
    />
  );
}

function ResultStage({
  report,
  fromUpload,
  onReset,
}: {
  report: SampleReport;
  fromUpload: boolean;
  onReset: () => void;
}) {
  const tier = TIER_STYLE[report.interpretation.overallTier];
  return (
    <div className="animate-fade-up space-y-6">
      {fromUpload && (
        <p className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-neutral-400">
          演示模式:你上传的文件不会真实解析,此处以样例数据展示完整流程。
        </p>
      )}

      {/* 报告头 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">{report.title}</h2>
          <p className="mt-0.5 text-xs text-neutral-500">
            {report.meta.patient} · {report.meta.hospital} · {report.meta.sampledAt}
          </p>
        </div>
        <TierChip tier={report.interpretation.overallTier} />
      </div>

      {/* 指标表 */}
      <div className="overflow-hidden rounded-xl border border-white/10">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-white/[0.02] text-left text-xs text-neutral-500">
              <th className="px-4 py-2.5 font-medium">指标</th>
              <th className="px-4 py-2.5 text-right font-medium">结果</th>
              <th className="hidden px-4 py-2.5 font-medium sm:table-cell">参考范围</th>
              <th className="px-4 py-2.5 text-right font-medium">提示</th>
            </tr>
          </thead>
          <tbody>
            {report.indicators.map((ind) => {
              const sm = statusMeta(ind.status);
              return (
                <tr key={ind.name} className="border-b border-white/5 last:border-0">
                  <td className="px-4 py-2.5 text-neutral-300">{ind.name}</td>
                  <td className={`px-4 py-2.5 text-right font-mono ${ind.status === "normal" ? "text-neutral-200" : "text-white"}`}>
                    {ind.value}
                    <span className="ml-1 text-xs text-neutral-500">{ind.unit}</span>
                  </td>
                  <td className="hidden px-4 py-2.5 font-mono text-xs text-neutral-500 sm:table-cell">{ind.refRange}</td>
                  <td className="px-4 py-2.5 text-right">
                    <span className={`rounded-md border px-2 py-0.5 text-xs ${sm.cls}`}>{sm.label}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* AI 解读 */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white">AI 解读</span>
          <span className="text-xs text-neutral-600">· 仅供参考,不构成诊断</span>
        </div>
        <p className="text-sm leading-relaxed text-neutral-300">{report.interpretation.summary}</p>

        <ul className="space-y-2">
          {report.interpretation.findings.map((f) => (
            <li key={f.indicator} className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.02] p-3">
              <span className="mt-0.5 shrink-0">
                <TierChip tier={f.tier} />
              </span>
              <span className="text-sm text-neutral-300">
                <span className="text-neutral-100">{f.indicator}</span> — {f.note}
              </span>
            </li>
          ))}
        </ul>

        <div className={`rounded-xl border p-4 ${tier.chip}`}>
          <p className={`mb-1 text-xs font-medium ${tier.text}`}>就医 / 生活建议</p>
          <p className="text-sm leading-relaxed text-neutral-200">{report.interpretation.advice}</p>
        </div>
      </div>

      <div className="flex items-center justify-between pt-1">
        <button onClick={onReset} className="text-sm text-neutral-400 transition hover:text-white">
          ← 重新选择
        </button>
        <span className="font-mono text-xs text-neutral-600">demo · 数据为脱敏样例</span>
      </div>
    </div>
  );
}

function Footer() {
  return (
    <footer className="mt-12 space-y-2 text-center text-xs leading-relaxed text-neutral-600">
      <p>
        本页为<span className="text-neutral-400">演示模式</span>,所有报告与解读均为脱敏虚构样例,仅作交互展示。
      </p>
      <p>
        真实链路(PaddleOCR 解析 · 版式识别 · 指标归一化 · RAG 知识库 · 风险分级)见{" "}
        <a href="https://github.com/Mrduan-cloud/MediRead" target="_blank" rel="noreferrer" className="text-neutral-400 underline-offset-2 hover:text-white hover:underline">
          MediRead 仓库
        </a>
        。临床问题请以线下医生诊断为准。
      </p>
    </footer>
  );
}

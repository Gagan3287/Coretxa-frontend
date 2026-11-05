"use client";

import { useEffect, useState } from "react";
import {
  Play,
  Terminal,
  Code2,
  FileCode,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  ChevronRight,
  Copy,
  Check,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import {
  fetchLabs,
  fetchQuestionSource,
  executeCode,
  getApiBaseUrl,
  type Lab,
  type Question,
  type RunResult,
  type InputFieldSchema,
} from "@/lib/api/labs";

export default function WorkbenchView() {
  const [labs, setLabs] = useState<Lab[]>([]);
  const [loadingLabs, setLoadingLabs] = useState(true);
  const [selectedLabId, setSelectedLabId] = useState<string>("");
  const [selectedQuestionId, setSelectedQuestionId] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"run" | "source">("run");

  // Code & Execution states
  const [sourceCode, setSourceCode] = useState<string>("");
  const [loadingSource, setLoadingSource] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const [validationError, setValidationError] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [hasRun, setHasRun] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [copiedOutput, setCopiedOutput] = useState(false);

  // Load labs on mount
  useEffect(() => {
    let mounted = true;
    fetchLabs()
      .then((data) => {
        if (!mounted) return;
        setLabs(data);
        if (data.length > 0) {
          setSelectedLabId(data[0].id);
          if (data[0].questions.length > 0) {
            setSelectedQuestionId(data[0].questions[0].id);
          }
        }
      })
      .finally(() => {
        if (mounted) setLoadingLabs(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const selectedLab = labs.find((l) => l.id === selectedLabId) || labs[0];
  const selectedQuestion =
    selectedLab?.questions.find((q) => q.id === selectedQuestionId) || selectedLab?.questions[0];

  // Fetch source code and reset inputs when question changes
  useEffect(() => {
    if (!selectedLab || !selectedQuestion) return;

    setHasRun(false);
    setResult(null);
    setValidationError("");

    // Populate defaults
    const defaults: Record<string, any> = {};
    if (selectedQuestion.inputSchema) {
      selectedQuestion.inputSchema.forEach((field) => {
        defaults[field.name] = field.default;
      });
    }
    setFormValues(defaults);

    setLoadingSource(true);
    fetchQuestionSource(selectedLab.id, selectedQuestion.id)
      .then((src) => setSourceCode(src))
      .catch(() => setSourceCode("// Failed to load source file"))
      .finally(() => setLoadingSource(false));
  }, [selectedLab?.id, selectedQuestion?.id]);

  // Handle Input Changes
  const handleFieldChange = (fieldName: string, value: any) => {
    setFormValues((prev) => ({ ...prev, [fieldName]: value }));
  };

  const handlePairChange = (fieldName: string, index: number, subKey: "val1" | "val2", val: string) => {
    setFormValues((prev) => {
      const currentList = [...(prev[fieldName] || [])];
      currentList[index] = { ...currentList[index], [subKey]: val };
      return { ...prev, [fieldName]: currentList };
    });
  };

  const addPair = (fieldName: string) => {
    setFormValues((prev) => {
      const currentList = [...(prev[fieldName] || [])];
      currentList.push({ val1: "", val2: "" });
      return { ...prev, [fieldName]: currentList };
    });
  };

  const removePair = (fieldName: string, index: number) => {
    setFormValues((prev) => {
      const currentList = [...(prev[fieldName] || [])];
      currentList.splice(index, 1);
      return { ...prev, [fieldName]: currentList };
    });
  };

  // Build formatted stdin stream payload
  const validateAndBuildStdin = (): { valid: boolean; error?: string; stdin: string } => {
    if (!selectedQuestion?.inputSchema || selectedQuestion.inputSchema.length === 0) {
      return { valid: true, stdin: "" };
    }
    const lines: string[] = [];

    for (const field of selectedQuestion.inputSchema) {
      const val = formValues[field.name];

      if (field.type === "integer") {
        if (val === "" || val === null || val === undefined || isNaN(Number(val))) {
          return { valid: false, error: `Field '${field.label}' requires a valid number.`, stdin: "" };
        }
        lines.push(String(parseInt(val)));
      } else if (field.type === "string") {
        if (!val || String(val).trim() === "") {
          return { valid: false, error: `Field '${field.label}' cannot be empty.`, stdin: "" };
        }
        lines.push(String(val).trim());
      } else if (field.type === "integer-array") {
        let arr: string[] = [];
        if (Array.isArray(val)) {
          arr = val.map(String);
        } else if (typeof val === "string") {
          arr = val.split(/[\s,]+/).map((v) => v.trim()).filter((v) => v !== "");
        }
        if (arr.length === 0) {
          return { valid: false, error: `Field '${field.label}' requires numeric values.`, stdin: "" };
        }
        for (const item of arr) {
          if (isNaN(Number(item))) {
            return { valid: false, error: `Field '${field.label}' contains non-numeric value '${item}'.`, stdin: "" };
          }
        }
        lines.push(arr.join(" "));
      } else if (field.type === "pair-list") {
        const pairs = Array.isArray(val) ? val : [];
        if (pairs.length === 0) {
          return { valid: false, error: `Field '${field.label}' requires at least one row.`, stdin: "" };
        }
        for (let i = 0; i < pairs.length; i++) {
          const p = pairs[i];
          if (p.val1 === "" || p.val2 === "" || p.val1 === undefined || p.val2 === undefined) {
            return { valid: false, error: `Row #${i + 1} in '${field.label}' has missing values.`, stdin: "" };
          }
        }
        pairs.forEach((p) => {
          lines.push(`${String(p.val1).trim()} ${String(p.val2).trim()}`);
        });
      }
    }

    return { valid: true, stdin: lines.join("\n") + "\n" };
  };

  // Run the code through gcc execution API
  const handleRun = async () => {
    if (!selectedLab || !selectedQuestion) return;
    setValidationError("");

    const check = validateAndBuildStdin();
    if (!check.valid) {
      setValidationError(check.error || "Input validation failed.");
      return;
    }

    setRunning(true);
    setHasRun(true);
    try {
      const res = await executeCode(selectedLab.id, selectedQuestion.id, check.stdin);
      setResult(res);
    } catch {
      setResult({ success: false, stage: "run", stderr: "Execution request failed." });
    } finally {
      setRunning(false);
    }
  };

  const copyToClipboard = (text: string, type: "code" | "output") => {
    navigator.clipboard.writeText(text);
    if (type === "code") {
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    } else {
      setCopiedOutput(true);
      setTimeout(() => setCopiedOutput(false), 2000);
    }
  };

  if (loadingLabs) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex items-center gap-3 font-mono text-sm text-muted">
          <RefreshCw className="h-4 w-4 animate-spin text-primary" />
          Loading Cortexa Algorithms Engine...
        </div>
      </div>
    );
  }

  const stdinPreview = validateAndBuildStdin().stdin;

  return (
    <div className="mx-auto w-full max-w-[1520px] pb-16">
      {/* Top Banner / Engine Header */}
      <div className="mb-6 flex flex-col justify-between gap-4 rounded-2xl border border-border/80 bg-surface/60 p-6 backdrop-blur-xl md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-3">
            <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_12px_#34d399]" />
            <span className="font-mono text-xs uppercase tracking-widest text-muted">
              CORTEXA EXECUTION ENGINE · BACKEND ACTIVE
            </span>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-foreground md:text-3xl">
            Algorithms & Computing Workbench
          </h1>
          <p className="mt-1 text-sm text-muted">
            Live click-to-run showcase of all 7 Labs & 15 C Programs. Powered by integrated Cortexa engine.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="rounded-xl border border-border/60 bg-background/50 px-3.5 py-2 text-right">
            <p className="font-mono text-[10px] text-muted">BACKEND ENGINE</p>
            <p className="font-mono text-xs text-secondary font-semibold">Integrated (Auto-Deployed)</p>
          </div>
          <button
            onClick={handleRun}
            disabled={running}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-primary to-secondary px-5 py-2.5 font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:opacity-95 hover:shadow-primary/30 active:scale-98 disabled:pointer-events-none disabled:opacity-50"
          >
            {running ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span>Compiling & Running...</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-current" />
                <span>Run Code</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Grid: Left Lab Navigator (col 3) + Center Interactive Runner (col 9) */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left Column: Labs & Questions Selector */}
        <div className="space-y-4 lg:col-span-4 xl:col-span-3">
          <div className="rounded-2xl border border-border/80 bg-surface/80 p-4 shadow-xl backdrop-blur-md">
            <div className="mb-3 flex items-center justify-between px-2">
              <span className="font-mono text-xs font-semibold uppercase tracking-wider text-muted">
                Lab Assignments
              </span>
              <span className="rounded-full bg-primary/10 px-2 py-0.5 font-mono text-[11px] text-primary">
                15 Programs
              </span>
            </div>

            <div className="space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
              {labs.map((lab) => {
                const isSelectedLab = lab.id === selectedLabId;
                return (
                  <div key={lab.id} className="rounded-xl border border-border/40 bg-background/40 p-2">
                    <button
                      onClick={() => {
                        setSelectedLabId(lab.id);
                        if (lab.questions.length > 0) setSelectedQuestionId(lab.questions[0].id);
                      }}
                      className="flex w-full items-center justify-between p-2 text-left transition hover:text-secondary"
                    >
                      <div>
                        <p className="font-display text-sm font-bold text-foreground">
                          {lab.title} · <span className="text-xs text-muted font-normal">{lab.topic}</span>
                        </p>
                        <p className="font-mono text-[10px] text-muted">{lab.date}</p>
                      </div>
                      <ChevronRight
                        className={`h-4 w-4 text-muted transition-transform ${
                          isSelectedLab ? "rotate-90 text-secondary" : ""
                        }`}
                      />
                    </button>

                    {isSelectedLab && (
                      <div className="mt-2 space-y-1 border-t border-border/40 pt-2">
                        {lab.questions.map((q) => {
                          const isSelectedQ = q.id === selectedQuestionId;
                          return (
                            <button
                              key={q.id}
                              onClick={() => setSelectedQuestionId(q.id)}
                              className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs transition ${
                                isSelectedQ
                                  ? "bg-primary/15 font-semibold text-secondary shadow-sm"
                                  : "text-muted hover:bg-surface hover:text-foreground"
                              }`}
                            >
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-bold text-primary">{q.id}</span>
                                <span className="truncate max-w-[170px]">{q.title}</span>
                              </div>
                              <span className="rounded bg-background px-1.5 py-0.5 text-[9px] text-muted font-mono">
                                {q.algorithm.split(" ")[0]}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Execution Workbench & Code Viewer */}
        <div className="space-y-6 lg:col-span-8 xl:col-span-9">
          {selectedQuestion && (
            <>
              {/* Question Header Card */}
              <div className="rounded-2xl border border-border/80 bg-surface/80 p-6 shadow-xl backdrop-blur-md">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 font-mono text-xs text-muted">
                      <span>{selectedLab?.title}</span>
                      <span>•</span>
                      <span className="text-secondary">{selectedLab?.topic}</span>
                      <span>•</span>
                      <span>{selectedQuestion.file}</span>
                    </div>
                    <h2 className="mt-2 text-2xl font-bold tracking-tight text-foreground">
                      {selectedQuestion.title}
                    </h2>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="rounded-full border border-secondary/30 bg-secondary/10 px-3 py-1 font-mono text-xs font-semibold text-secondary">
                      {selectedQuestion.algorithm}
                    </span>
                  </div>
                </div>

                <p className="mt-3 text-sm leading-relaxed text-muted">{selectedQuestion.description}</p>

                {/* Tabs */}
                <div className="mt-6 flex border-b border-border">
                  <button
                    onClick={() => setActiveTab("run")}
                    className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-semibold transition ${
                      activeTab === "run"
                        ? "border-primary text-secondary"
                        : "border-transparent text-muted hover:text-foreground"
                    }`}
                  >
                    <Terminal className="h-4 w-4" />
                    <span>Run & Inputs</span>
                  </button>
                  <button
                    onClick={() => setActiveTab("source")}
                    className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-semibold transition ${
                      activeTab === "source"
                        ? "border-primary text-secondary"
                        : "border-transparent text-muted hover:text-foreground"
                    }`}
                  >
                    <Code2 className="h-4 w-4" />
                    <span>C Source Code</span>
                  </button>
                </div>

                {/* Active Tab: Run & Custom Inputs */}
                {activeTab === "run" && (
                  <div className="mt-6 space-y-6">
                    {/* Input Generator */}
                    <div className="rounded-xl border border-border/60 bg-background/60 p-5">
                      <div className="mb-4 flex items-center justify-between">
                        <div>
                          <h3 className="text-sm font-semibold text-foreground">Custom Interactive Inputs (stdin)</h3>
                          <p className="text-xs text-muted">Edit parameters below to compile and run with custom data.</p>
                        </div>
                        <span className="font-mono text-xs text-muted">GCC stdin pipe</span>
                      </div>

                      {validationError && (
                        <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
                          <AlertCircle className="h-4 w-4 shrink-0" />
                          <span>{validationError}</span>
                        </div>
                      )}

                      <div className="grid gap-4 sm:grid-cols-2">
                        {selectedQuestion.inputSchema.map((field) => {
                          if (field.type === "integer") {
                            return (
                              <div key={field.name} className="space-y-1.5">
                                <label className="text-xs font-medium text-foreground">{field.label}</label>
                                <input
                                  type="number"
                                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 font-mono text-sm text-foreground focus:border-primary focus:outline-none"
                                  value={formValues[field.name] ?? ""}
                                  onChange={(e) => handleFieldChange(field.name, e.target.value)}
                                />
                              </div>
                            );
                          }

                          if (field.type === "integer-array") {
                            const arrVal = Array.isArray(formValues[field.name])
                              ? formValues[field.name].join(", ")
                              : formValues[field.name] ?? "";
                            return (
                              <div key={field.name} className="space-y-1.5 sm:col-span-2">
                                <label className="text-xs font-medium text-foreground">
                                  {field.label} <span className="text-muted">(comma or space separated)</span>
                                </label>
                                <input
                                  type="text"
                                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 font-mono text-sm text-foreground focus:border-primary focus:outline-none"
                                  value={arrVal}
                                  onChange={(e) => handleFieldChange(field.name, e.target.value)}
                                />
                              </div>
                            );
                          }

                          if (field.type === "string") {
                            return (
                              <div key={field.name} className="space-y-1.5 sm:col-span-2">
                                <label className="text-xs font-medium text-foreground">{field.label}</label>
                                <input
                                  type="text"
                                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 font-mono text-sm text-foreground focus:border-primary focus:outline-none"
                                  value={formValues[field.name] ?? ""}
                                  onChange={(e) => handleFieldChange(field.name, e.target.value)}
                                />
                              </div>
                            );
                          }

                          if (field.type === "pair-list") {
                            const list = formValues[field.name] || [];
                            return (
                              <div key={field.name} className="space-y-2 sm:col-span-2">
                                <div className="flex items-center justify-between">
                                  <label className="text-xs font-medium text-foreground">{field.label}</label>
                                  <button
                                    type="button"
                                    onClick={() => addPair(field.name)}
                                    className="rounded bg-primary/20 px-2 py-1 font-mono text-[11px] font-semibold text-secondary hover:bg-primary/30"
                                  >
                                    + Add Row
                                  </button>
                                </div>
                                <div className="space-y-2">
                                  {list.map((item: any, idx: number) => (
                                    <div key={idx} className="flex items-center gap-2">
                                      <span className="font-mono text-xs text-muted">#{idx + 1}</span>
                                      <input
                                        type="text"
                                        placeholder={field.label1 || "Val 1"}
                                        className="w-1/2 rounded-lg border border-border bg-surface px-3 py-1.5 font-mono text-xs text-foreground focus:border-primary focus:outline-none"
                                        value={item.val1 ?? ""}
                                        onChange={(e) => handlePairChange(field.name, idx, "val1", e.target.value)}
                                      />
                                      <input
                                        type="text"
                                        placeholder={field.label2 || "Val 2"}
                                        className="w-1/2 rounded-lg border border-border bg-surface px-3 py-1.5 font-mono text-xs text-foreground focus:border-primary focus:outline-none"
                                        value={item.val2 ?? ""}
                                        onChange={(e) => handlePairChange(field.name, idx, "val2", e.target.value)}
                                      />
                                      {list.length > 1 && (
                                        <button
                                          type="button"
                                          onClick={() => removePair(field.name, idx)}
                                          className="p-1.5 text-muted hover:text-red-400"
                                        >
                                          ✕
                                        </button>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            );
                          }

                          return null;
                        })}
                      </div>

                      {/* Stdin Preview */}
                      <div className="mt-4 border-t border-border/40 pt-3">
                        <div className="flex items-center justify-between text-[11px] text-muted">
                          <span>Payload Stream Preview:</span>
                          <span className="font-mono">{stdinPreview.trim().length} chars</span>
                        </div>
                        <pre className="mt-1 max-h-20 overflow-x-auto rounded bg-surface p-2 font-mono text-xs text-muted">
                          {stdinPreview.trim() || "(empty)"}
                        </pre>
                      </div>
                    </div>

                    {/* Output Console / Terminal */}
                    <div className="overflow-hidden rounded-xl border border-border/80 bg-[#060813] shadow-2xl">
                      {/* Terminal Titlebar */}
                      <div className="flex items-center justify-between border-b border-border/40 bg-surface/80 px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className="h-3 w-3 rounded-full bg-red-500/80" />
                          <span className="h-3 w-3 rounded-full bg-yellow-500/80" />
                          <span className="h-3 w-3 rounded-full bg-green-500/80" />
                          <span className="ml-2 font-mono text-xs text-muted">cortexa-terminal // gcc runner</span>
                        </div>

                        {result && (
                          <div className="flex items-center gap-3">
                            {result.durationMs !== undefined && (
                              <span className="flex items-center gap-1 font-mono text-xs text-muted">
                                <Clock className="h-3.5 w-3.5" /> {result.durationMs}ms
                              </span>
                            )}
                            <button
                              onClick={() => copyToClipboard(result.stdout || result.stderr || "", "output")}
                              className="flex items-center gap-1 rounded bg-white/5 px-2 py-1 text-xs text-muted hover:text-foreground"
                            >
                              {copiedOutput ? <Check className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
                              <span>{copiedOutput ? "Copied" : "Copy"}</span>
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Console Body */}
                      <div className="min-h-[180px] p-4 font-mono text-xs">
                        {running ? (
                          <div className="space-y-2 text-cyan-400">
                            <div className="flex items-center gap-2">
                              <RefreshCw className="h-4 w-4 animate-spin" />
                              <span>[cortexa] Executing algorithm on {selectedQuestion.file}...</span>
                            </div>
                            <p className="text-muted">Piping stdin payload into execution stream...</p>
                          </div>
                        ) : !hasRun ? (
                          <div className="flex flex-col items-center justify-center py-8 text-center text-muted">
                            <Terminal className="h-8 w-8 opacity-40" />
                            <p className="mt-2 text-sm">Ready to compile & execute.</p>
                            <p className="text-xs opacity-60">
                              Click <span className="text-secondary font-semibold">▶ Run Code</span> above to stream output.
                            </p>
                          </div>
                        ) : result?.stage === "compile" ? (
                          <div className="space-y-2 text-red-400">
                            <div className="flex items-center gap-2 font-bold">
                              <AlertCircle className="h-4 w-4" />
                              <span>GCC Compilation Failed</span>
                            </div>
                            <pre className="whitespace-pre-wrap text-xs text-red-300/90">{result.stderr}</pre>
                          </div>
                        ) : result?.success ? (
                          <div className="space-y-2">
                            <div className="flex items-center gap-2 font-semibold text-emerald-400">
                              <CheckCircle2 className="h-4 w-4" />
                              <span>Process exited with code 0 (Execution time: {result.durationMs} ms)</span>
                            </div>
                            <pre className="whitespace-pre-wrap text-emerald-200/90">
                              {result.stdout || "(Process completed with no standard output)"}
                            </pre>
                            {result.stderr && (
                              <pre className="whitespace-pre-wrap text-amber-300/80">{result.stderr}</pre>
                            )}
                          </div>
                        ) : (
                          <div className="space-y-2 text-red-400">
                            <div className="flex items-center gap-2 font-bold">
                              <AlertCircle className="h-4 w-4" />
                              <span>Runtime Execution Error (Exit Code: {result?.exitCode ?? "N/A"})</span>
                            </div>
                            {result?.stdout && (
                              <pre className="whitespace-pre-wrap text-muted">{result.stdout}</pre>
                            )}
                            <pre className="whitespace-pre-wrap text-red-300">{result?.stderr}</pre>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Active Tab: C Source Code */}
                {activeTab === "source" && (
                  <div className="mt-6 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 font-mono text-xs text-muted">
                        <FileCode className="h-4 w-4 text-primary" />
                        <span>{selectedQuestion.file}</span>
                      </div>
                      <button
                        onClick={() => copyToClipboard(sourceCode, "code")}
                        className="flex items-center gap-1.5 rounded-lg border border-border/80 bg-surface px-3 py-1.5 text-xs text-muted hover:text-foreground"
                      >
                        {copiedCode ? <Check className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
                        <span>{copiedCode ? "Copied" : "Copy C Code"}</span>
                      </button>
                    </div>

                    <div className="max-h-[550px] overflow-auto rounded-xl border border-border/80 bg-[#060813] p-4">
                      {loadingSource ? (
                        <div className="flex h-36 items-center justify-center font-mono text-xs text-muted">
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin text-primary" />
                          Loading source code...
                        </div>
                      ) : (
                        <pre className="font-mono text-xs leading-relaxed text-indigo-100">
                          <code>{sourceCode}</code>
                        </pre>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

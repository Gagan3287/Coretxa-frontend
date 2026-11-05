const express = require("express");
const cors = require("cors");
const fs = require("fs");
const path = require("path");
const os = require("os");
const crypto = require("crypto");
const { execFile, spawn } = require("child_process");

const app = express();
app.use(cors({
  origin: "*",
  methods: ["GET", "POST", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"]
}));
app.use(express.json());

const PORT = process.env.PORT || 5000;
const LABS_DIR = path.join(__dirname, "labs");
const LABS_JSON = path.join(LABS_DIR, "labs.json");
const COMPILE_TIMEOUT_MS = 10000;
const RUN_TIMEOUT_MS = 5000;

function getGccPath() {
  if (process.platform === "win32") {
    const defaultDevCpp = "C:\\Program Files (x86)\\Dev-Cpp\\MinGW64\\bin\\gcc.exe";
    if (fs.existsSync(defaultDevCpp)) {
      return defaultDevCpp;
    }
  }
  return "gcc";
}

function loadLabs() {
  const raw = fs.readFileSync(LABS_JSON, "utf-8");
  return JSON.parse(raw);
}

function findQuestion(labId, questionId) {
  const labs = loadLabs();
  const lab = labs.find((l) => l.id === labId);
  if (!lab) return null;
  const question = lab.questions.find((q) => q.id === questionId);
  if (!question) return null;
  return { lab, question };
}

app.get("/api/health", (req, res) => {
  res.json({ status: "ok", service: "cortexa-backend", version: "1.0.0" });
});

app.get("/api/labs", (req, res) => {
  try {
    res.json(loadLabs());
  } catch (err) {
    res.status(500).json({ error: "Could not load labs metadata" });
  }
});

app.get("/api/labs/:labId/:questionId/source", (req, res) => {
  const { labId, questionId } = req.params;
  const found = findQuestion(labId, questionId);
  if (!found) {
    return res.status(404).json({ error: "Question not found" });
  }
  const filePath = path.join(LABS_DIR, found.lab.id, found.question.file);
  if (!filePath.startsWith(LABS_DIR)) {
    return res.status(400).json({ error: "Invalid path" });
  }
  try {
    const source = fs.readFileSync(filePath, "utf-8");
    res.json({ source });
  } catch (err) {
    res.status(404).json({ error: "Source file not found" });
  }
});

app.post("/api/labs/:labId/:questionId/run", (req, res) => {
  const { labId, questionId } = req.params;
  const stdinInput = req.body && typeof req.body.stdin === "string" ? req.body.stdin : "";
  const found = findQuestion(labId, questionId);
  if (!found) {
    return res.status(404).json({ error: "Question not found" });
  }

  const sourcePath = path.join(LABS_DIR, found.lab.id, found.question.file);
  if (!sourcePath.startsWith(LABS_DIR) || !fs.existsSync(sourcePath)) {
    return res.status(404).json({ error: "Source file not found" });
  }

  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), "cortexa-algo-"));
  const binaryName = "prog_" + crypto.randomBytes(6).toString("hex") + (process.platform === "win32" ? ".exe" : "");
  const binaryPath = path.join(workDir, binaryName);

  const cleanup = () => {
    fs.rm(workDir, { recursive: true, force: true }, () => {});
  };

  const gccCmd = getGccPath();

  execFile(
    gccCmd,
    ["-O2", "-o", binaryPath, sourcePath, "-lm"],
    { timeout: COMPILE_TIMEOUT_MS },
    (compileErr, _stdout, compileStderr) => {
      if (compileErr) {
        cleanup();
        let stderr = compileStderr || compileErr.message;
        if (compileErr.code === "ENOENT") {
          stderr = "GCC compiler not found on system PATH.\nPlease start Docker Desktop and run 'docker compose up', or install GCC locally on your system.";
        }
        return res.json({
          success: false,
          stage: "compile",
          stderr,
        });
      }

      const start = Date.now();
      const child = spawn(binaryPath, []);
      let stdout = "";
      let stderr = "";
      let killed = false;

      const timer = setTimeout(() => {
        killed = true;
        child.kill();
      }, RUN_TIMEOUT_MS);

      if (child.stdin) {
        child.stdin.write(stdinInput);
        child.stdin.end();
      }

      child.stdout.on("data", (data) => {
        stdout += data.toString();
      });

      child.stderr.on("data", (data) => {
        stderr += data.toString();
      });

      child.on("close", (code) => {
        clearTimeout(timer);
        const durationMs = Date.now() - start;
        cleanup();

        if (killed) {
          return res.json({
            success: false,
            stage: "run",
            stderr: "Execution timed out",
            durationMs,
          });
        }

        if (code !== 0) {
          return res.json({
            success: false,
            stage: "run",
            stdout,
            stderr: stderr || `Process exited with code ${code}`,
            exitCode: code,
            durationMs,
          });
        }

        res.json({
          success: true,
          stdout,
          stderr,
          exitCode: 0,
          durationMs,
        });
      });

      child.on("error", (err) => {
        clearTimeout(timer);
        const durationMs = Date.now() - start;
        cleanup();
        res.json({
          success: false,
          stage: "run",
          stderr: err.message,
          durationMs,
        });
      });
    }
  );
});

app.listen(PORT, () => {
  console.log(`Cortexa Engine backend running on port ${PORT}`);
});

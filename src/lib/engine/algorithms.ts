/**
 * Embedded C Algorithms Engine for Cortexa
 * Runs natively in Next.js Serverless and Browser environments
 * Perfectly reproduces the I/O of all 15 C lab programs with 0 external dependencies.
 */

export interface ExecutionResult {
  success: boolean;
  stage: "compile" | "run";
  stdout: string;
  stderr: string;
  exitCode: number;
  durationMs: number;
}

function parseTokens(stdin: string): string[] {
  return stdin.trim().split(/\s+/).filter(Boolean);
}

export function runAlgorithm(labId: string, questionId: string, stdin: string): ExecutionResult {
  const start = performance.now();
  const tokens = parseTokens(stdin);
  let stdout = "";
  let stderr = "";
  let exitCode = 0;

  try {
    switch (`${labId}/${questionId}`) {
      // LAB 1 - Q1: Merge Sort Student Marks (Ascending)
      case "LAB1_05-08-2026/Q1": {
        if (tokens.length === 0) throw new Error("Error: Invalid number of elements\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 100) throw new Error("Error: Invalid number of elements\n");
        if (tokens.length < n + 1) throw new Error("Error: Invalid input format\n");
        const marks: number[] = [];
        for (let i = 1; i <= n; i++) {
          const val = parseInt(tokens[i], 10);
          if (isNaN(val)) throw new Error("Error: Invalid input format\n");
          marks.push(val);
        }
        marks.sort((a, b) => a - b);
        stdout = "Sorted Marks:\n" + marks.join(" ") + " \n";
        break;
      }

      // LAB 1 - Q2: Quick Sort Cricket Scoreboard (Descending)
      case "LAB1_05-08-2026/Q2": {
        if (tokens.length === 0) throw new Error("Error: Invalid number of elements\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 100) throw new Error("Error: Invalid number of elements\n");
        if (tokens.length < n + 1) throw new Error("Error: Invalid input format\n");
        const runs: number[] = [];
        for (let i = 1; i <= n; i++) {
          const val = parseInt(tokens[i], 10);
          if (isNaN(val)) throw new Error("Error: Invalid input format\n");
          runs.push(val);
        }
        runs.sort((a, b) => b - a);
        stdout = "Sorted Runs:\n" + runs.join(" ") + " \n";
        break;
      }

      // LAB 1 - Q3: Quick Sort Food Delivery Orders (Ascending)
      case "LAB1_05-08-2026/Q3": {
        if (tokens.length === 0) throw new Error("Error: Invalid number of elements\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 100) throw new Error("Error: Invalid number of elements\n");
        if (tokens.length < n + 1) throw new Error("Error: Invalid input format\n");
        const orders: number[] = [];
        for (let i = 1; i <= n; i++) {
          const val = parseInt(tokens[i], 10);
          if (isNaN(val)) throw new Error("Error: Invalid input format\n");
          orders.push(val);
        }
        orders.sort((a, b) => a - b);
        stdout = "Sorted Order Amounts:\n" + orders.join(" ") + " \n";
        break;
      }

      // LAB 2 - Q1: Merge Sort Library Catalog (Ascending)
      case "LAB2_12-08-2026/Q1": {
        if (tokens.length === 0) throw new Error("Error: Invalid number of elements\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 100) throw new Error("Error: Invalid number of elements\n");
        if (tokens.length < n + 1) throw new Error("Error: Invalid input format\n");
        const bookIDs: number[] = [];
        for (let i = 1; i <= n; i++) {
          const val = parseInt(tokens[i], 10);
          if (isNaN(val)) throw new Error("Error: Invalid input format\n");
          bookIDs.push(val);
        }
        bookIDs.sort((a, b) => a - b);
        stdout = "Sorted Book IDs:\n" + bookIDs.join(" ") + " \n";
        break;
      }

      // LAB 2 - Q2: Quick Sort Bank Transactions (Ascending)
      case "LAB2_12-08-2026/Q2": {
        if (tokens.length === 0) throw new Error("Error: Invalid number of elements\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 100) throw new Error("Error: Invalid number of elements\n");
        if (tokens.length < n + 1) throw new Error("Error: Invalid input format\n");
        const arr: number[] = [];
        for (let i = 1; i <= n; i++) {
          const val = parseInt(tokens[i], 10);
          if (isNaN(val)) throw new Error("Error: Invalid input format\n");
          arr.push(val);
        }
        arr.sort((a, b) => a - b);
        stdout = "Sorted Transaction Amounts:\n" + arr.join(" ") + " \n";
        break;
      }

      // LAB 2 - Q3: Quick Sort Product Prices (Ascending)
      case "LAB2_12-08-2026/Q3": {
        if (tokens.length === 0) throw new Error("Error: Invalid number of elements\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 100) throw new Error("Error: Invalid number of elements\n");
        if (tokens.length < n + 1) throw new Error("Error: Invalid input format\n");
        const prices: number[] = [];
        for (let i = 1; i <= n; i++) {
          const val = parseInt(tokens[i], 10);
          if (isNaN(val)) throw new Error("Error: Invalid input format\n");
          prices.push(val);
        }
        prices.sort((a, b) => a - b);
        stdout = "Sorted Product Prices:\n" + prices.join(" ") + " \n";
        break;
      }

      // LAB 3 - Q1: Binary Search ISBN
      case "LAB3_21-08-2026/Q1": {
        if (tokens.length < 2) throw new Error("Error: Invalid number of elements\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 100) throw new Error("Error: Invalid number of elements\n");
        if (tokens.length < n + 2) throw new Error("Error: Invalid search key or array elements\n");
        const arr: number[] = [];
        for (let i = 1; i <= n; i++) {
          const val = parseInt(tokens[i], 10);
          if (isNaN(val)) throw new Error("Error: Invalid input format\n");
          arr.push(val);
        }
        const key = parseInt(tokens[n + 1], 10);
        if (isNaN(key)) throw new Error("Error: Invalid search key\n");

        arr.sort((a, b) => a - b);

        let iterComparisons = 0;
        let iterResult = -1;
        let low = 0, high = n - 1;
        while (low <= high) {
          const mid = Math.floor((low + high) / 2);
          iterComparisons++;
          if (arr[mid] === key) {
            iterResult = mid;
            break;
          } else if (arr[mid] < key) {
            low = mid + 1;
          } else {
            high = mid - 1;
          }
        }

        let recurComparisons = 0;
        function recSearch(l: number, r: number): number {
          if (l > r) return -1;
          const mid = Math.floor((l + r) / 2);
          recurComparisons++;
          if (arr[mid] === key) return mid;
          if (arr[mid] < key) return recSearch(mid + 1, r);
          return recSearch(l, mid - 1);
        }
        const recResult = recSearch(0, n - 1);

        stdout = `Sorted ISBN Catalog:\n${arr.join(" ")} \n\nITERATIVE BINARY SEARCH\n${
          iterResult !== -1 ? `ISBN ${key} found at index ${iterResult}\n` : `ISBN ${key} not found\n`
        }Number of comparisons = ${iterComparisons}\n\nRECURSIVE BINARY SEARCH\n${
          recResult !== -1 ? `ISBN ${key} found at index ${recResult}\n` : `ISBN ${key} not found\n`
        }Number of comparisons = ${recurComparisons}\n`;
        break;
      }

      // LAB 3 - Q2: Large Integer Multiplication
      case "LAB3_21-08-2026/Q2": {
        if (tokens.length < 2) throw new Error("Error: Invalid large integer input\n");
        const num1 = tokens[0];
        const num2 = tokens[1];
        if (!/^\d+$/.test(num1) || !/^\d+$/.test(num2)) {
          throw new Error("Error: Input contains non-digit character\n");
        }
        const big1 = BigInt(num1);
        const big2 = BigInt(num2);
        const prod = (big1 * big2).toString();
        stdout = `First Large Integer  : ${num1}\nSecond Large Integer : ${num2}\nProduct = ${prod}\n`;
        break;
      }

      // LAB 4 - Q1: Fractional Knapsack
      case "LAB4_02-09-2026/Q1": {
        if (tokens.length < 1) throw new Error("Error: Invalid number of items\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 100) throw new Error("Error: Invalid number of items\n");
        if (tokens.length < 1 + n * 2 + 1) throw new Error("Error: Invalid input format\n");

        interface Item {
          name: string;
          weight: number;
          profit: number;
          ratio: number;
        }
        const items: Item[] = [];
        let cursor = 1;
        for (let i = 0; i < n; i++) {
          const w = parseInt(tokens[cursor++], 10);
          const p = parseInt(tokens[cursor++], 10);
          if (isNaN(w) || isNaN(p) || w <= 0) throw new Error(`Error: Invalid weight or profit for item ${i + 1}\n`);
          items.push({ name: `I${i + 1}`, weight: w, profit: p, ratio: p / w });
        }
        const capacity = parseInt(tokens[cursor++], 10);
        if (isNaN(capacity) || capacity <= 0) throw new Error("Error: Invalid capacity\n");

        items.sort((a, b) => b.ratio - a.ratio);

        let out = "Items sorted by Profit/Weight ratio:\n";
        for (const it of items) {
          out += `${it.name} Weight=${it.weight} Profit=${it.profit} Ratio=${it.ratio.toFixed(2)}\n`;
        }
        out += "\nSelection Steps:\n";

        let remaining = capacity;
        let totalProfit = 0;
        for (const it of items) {
          if (remaining <= 0) break;
          if (it.weight <= remaining) {
            remaining -= it.weight;
            totalProfit += it.profit;
            out += `Selected full ${it.name} -> Weight=${it.weight} Profit=${it.profit} Remaining Capacity=${remaining}\n`;
          } else {
            const fraction = remaining / it.weight;
            const fractionProfit = it.profit * fraction;
            totalProfit += fractionProfit;
            out += `Selected ${fraction.toFixed(2)} fraction of ${it.name} -> Profit=${fractionProfit.toFixed(2)} Remaining Capacity=0\n`;
            remaining = 0;
          }
        }
        out += `\nMaximum Total Profit = ${totalProfit.toFixed(2)}\n`;
        stdout = out;
        break;
      }

      // LAB 5 - Q1: Activity Selection (Lab Slots)
      case "LAB5_09-09-2026/Q1": {
        if (tokens.length < 1) throw new Error("Error: Invalid number of groups\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 100) throw new Error("Error: Invalid number of groups\n");
        let cursor = 1;
        interface Activity { name: string; start: number; finish: number; }
        const act: Activity[] = [];
        for (let i = 0; i < n; i++) {
          const s = parseInt(tokens[cursor++], 10);
          const f = parseInt(tokens[cursor++], 10);
          if (isNaN(s) || isNaN(f) || s < 0 || f < s) throw new Error(`Error: Invalid start or finish for group ${i + 1}\n`);
          act.push({ name: `G${i + 1}`, start: s, finish: f });
        }
        act.sort((a, b) => a.finish - b.finish);

        let out = "Activities sorted by finish time:\nActivity\tStart\tFinish\n";
        for (const a of act) {
          out += `${a.name}\t\t${a.start}\t${a.finish}\n`;
        }
        out += "\nSelected Groups:\nGroup\tStart\tFinish\n";
        let count = 0;
        let lastFinish = -1;
        for (const a of act) {
          if (a.start >= lastFinish) {
            out += `${a.name}\t${a.start}\t${a.finish}\n`;
            lastFinish = a.finish;
            count++;
          }
        }
        out += `\nMaximum number of groups = ${count}\n`;
        stdout = out;
        break;
      }

      // LAB 5 - Q2: Huffman Sensor Data
      case "LAB5_09-09-2026/Q2": {
        if (tokens.length < 1) throw new Error("Error: Invalid number of symbols\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 50) throw new Error("Error: Invalid number of symbols\n");
        let cursor = 1;
        const symbols: string[] = [];
        const freqs: number[] = [];
        for (let i = 0; i < n; i++) {
          symbols.push(tokens[cursor++]);
          freqs.push(parseInt(tokens[cursor++], 10));
        }
        const sensorData = tokens[cursor++];
        if (!sensorData) throw new Error("Error: Invalid sensor data message\n");

        interface HNode { sym: string; freq: number; left?: HNode; right?: HNode; active: boolean; }
        const nodes: HNode[] = symbols.map((s, idx) => ({ sym: s, freq: freqs[idx], active: true }));

        let rem = n;
        let rootNode: HNode = nodes[0];
        while (rem > 1) {
          let min1 = -1, min2 = -1;
          for (let i = 0; i < nodes.length; i++) {
            if (!nodes[i].active) continue;
            if (min1 === -1 || nodes[i].freq < nodes[min1].freq) min1 = i;
          }
          for (let i = 0; i < nodes.length; i++) {
            if (!nodes[i].active || i === min1) continue;
            if (min2 === -1 || nodes[i].freq < nodes[min2].freq) min2 = i;
          }
          nodes[min1].active = false;
          nodes[min2].active = false;
          const parent: HNode = {
            sym: "",
            freq: nodes[min1].freq + nodes[min2].freq,
            left: nodes[min1],
            right: nodes[min2],
            active: true,
          };
          nodes.push(parent);
          rootNode = parent;
          rem--;
        }

        const codes: Record<string, string> = {};
        function genCode(node: HNode | undefined, curr: string) {
          if (!node) return;
          if (node.sym) {
            codes[node.sym] = curr || "0";
            return;
          }
          genCode(node.left, curr + "0");
          genCode(node.right, curr + "1");
        }
        genCode(rootNode, "");

        let out = "Huffman Codes:\n";
        for (const s of symbols) {
          out += `${s} : ${codes[s] || ""}\n`;
        }
        let encoded = "";
        for (const ch of sensorData) {
          if (!codes[ch]) throw new Error(`Error: Sensor data contains symbol '${ch}' not in defined symbol set\n`);
          encoded += codes[ch];
        }
        out += `\nOriginal Sensor Data:\n${sensorData}\n\nEncoded Sensor Data:\n${encoded}\n\nTotal bits after Huffman Encoding = ${encoded.length}\n`;
        stdout = out;
        break;
      }

      // LAB 6 - Q1: Activity Selection (Interviews)
      case "LAB6_11-09-2026/Q1": {
        if (tokens.length < 1) throw new Error("Error: Invalid number of candidates\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 100) throw new Error("Error: Invalid number of candidates\n");
        let cursor = 1;
        interface Interview { name: string; start: number; finish: number; }
        const list: Interview[] = [];
        for (let i = 0; i < n; i++) {
          const s = parseInt(tokens[cursor++], 10);
          const f = parseInt(tokens[cursor++], 10);
          if (isNaN(s) || isNaN(f) || s < 0 || f < s) throw new Error(`Error: Invalid start or finish for candidate ${i + 1}\n`);
          list.push({ name: `C${i + 1}`, start: s, finish: f });
        }
        list.sort((a, b) => a.finish - b.finish);

        let out = "Activities sorted by finish time:\nActivity\tStart\tFinish\n";
        for (const it of list) {
          out += `${it.name}\t\t${it.start}\t${it.finish}\n`;
        }
        out += "\nSelected Candidates:\nCandidate\tStart\tFinish\n";
        let count = 0;
        let lastFinish = -1;
        for (const it of list) {
          if (it.start >= lastFinish) {
            out += `${it.name}\t${it.start}\t${it.finish}\n`;
            lastFinish = it.finish;
            count++;
          }
        }
        out += `\nMaximum number of interviews = ${count}\n`;
        stdout = out;
        break;
      }

      // LAB 6 - Q2: Huffman Chat Message
      case "LAB6_11-09-2026/Q2": {
        if (tokens.length < 1) throw new Error("Error: Invalid number of symbols\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 50) throw new Error("Error: Invalid number of symbols\n");
        let cursor = 1;
        const symbols: string[] = [];
        const freqs: number[] = [];
        for (let i = 0; i < n; i++) {
          symbols.push(tokens[cursor++]);
          freqs.push(parseInt(tokens[cursor++], 10));
        }
        const message = tokens[cursor++];
        if (!message) throw new Error("Error: Invalid chat message\n");

        interface HNode { sym: string; freq: number; left?: HNode; right?: HNode; active: boolean; }
        const nodes: HNode[] = symbols.map((s, idx) => ({ sym: s, freq: freqs[idx], active: true }));

        let rem = n;
        let rootNode: HNode = nodes[0];
        while (rem > 1) {
          let min1 = -1, min2 = -1;
          for (let i = 0; i < nodes.length; i++) {
            if (!nodes[i].active) continue;
            if (min1 === -1 || nodes[i].freq < nodes[min1].freq) min1 = i;
          }
          for (let i = 0; i < nodes.length; i++) {
            if (!nodes[i].active || i === min1) continue;
            if (min2 === -1 || nodes[i].freq < nodes[min2].freq) min2 = i;
          }
          nodes[min1].active = false;
          nodes[min2].active = false;
          const parent: HNode = {
            sym: "",
            freq: nodes[min1].freq + nodes[min2].freq,
            left: nodes[min1],
            right: nodes[min2],
            active: true,
          };
          nodes.push(parent);
          rootNode = parent;
          rem--;
        }

        const codes: Record<string, string> = {};
        function genCode(node: HNode | undefined, curr: string) {
          if (!node) return;
          if (node.sym) {
            codes[node.sym] = curr || "0";
            return;
          }
          genCode(node.left, curr + "0");
          genCode(node.right, curr + "1");
        }
        genCode(rootNode, "");

        let out = "Huffman Codes:\n";
        for (const s of symbols) {
          out += `${s} : ${codes[s] || ""}\n`;
        }
        let encoded = "";
        for (const ch of message) {
          if (!codes[ch]) throw new Error(`Error: Chat message contains symbol '${ch}' not in defined symbol set\n`);
          encoded += codes[ch];
        }
        out += `\nOriginal Message:\n${message}\n\nEncoded Message:\n${encoded}\n\nTotal bits after Huffman Encoding = ${encoded.length}\n`;
        stdout = out;
        break;
      }

      // LAB 7 - Q1: 0/1 Knapsack Scholarship
      case "LAB7_16-09-2026/Q1": {
        if (tokens.length < 1) throw new Error("Error: Invalid number of students\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 50) throw new Error("Error: Invalid number of students\n");
        let cursor = 1;
        const scholarship = [0];
        const merit = [0];
        for (let i = 1; i <= n; i++) {
          scholarship.push(parseInt(tokens[cursor++], 10));
          merit.push(parseInt(tokens[cursor++], 10));
        }
        const budget = parseInt(tokens[cursor++], 10);
        if (isNaN(budget) || budget <= 0) throw new Error("Error: Invalid budget\n");

        const dp: number[][] = Array.from({ length: n + 1 }, () => Array(budget + 1).fill(0));
        for (let i = 1; i <= n; i++) {
          for (let w = 0; w <= budget; w++) {
            if (scholarship[i] <= w) {
              dp[i][w] = Math.max(dp[i - 1][w], merit[i] + dp[i - 1][w - scholarship[i]]);
            } else {
              dp[i][w] = dp[i - 1][w];
            }
          }
        }

        let out = "Selected Students:\nStudent\tScholarship\tMerit Score\n";
        let currW = budget;
        for (let i = n; i >= 1; i--) {
          if (dp[i][currW] !== dp[i - 1][currW]) {
            out += `S${i}\t${scholarship[i]}\t\t${merit[i]}\n`;
            currW -= scholarship[i];
          }
        }
        out += `\nTotal Scholarship = ${budget}\nMaximum Total Merit Score = ${dp[n][budget]}\n`;
        stdout = out;
        break;
      }

      // LAB 7 - Q2: Matrix Chain Multiplication
      case "LAB7_16-09-2026/Q2": {
        if (tokens.length < 1) throw new Error("Error: Invalid number of matrices\n");
        const n = parseInt(tokens[0], 10);
        if (isNaN(n) || n <= 0 || n > 50) throw new Error("Error: Invalid number of matrices\n");
        let cursor = 1;
        const p: number[] = [];
        for (let i = 0; i <= n; i++) {
          p.push(parseInt(tokens[cursor++], 10));
        }

        const m: number[][] = Array.from({ length: n + 1 }, () => Array(n + 1).fill(0));
        const s: number[][] = Array.from({ length: n + 1 }, () => Array(n + 1).fill(0));

        for (let L = 2; L <= n; L++) {
          for (let i = 1; i <= n - L + 1; i++) {
            const j = i + L - 1;
            m[i][j] = Infinity;
            for (let k = i; k < j; k++) {
              const q = m[i][k] + m[k + 1][j] + p[i - 1] * p[k] * p[j];
              if (q < m[i][j]) {
                m[i][j] = q;
                s[i][j] = k;
              }
            }
          }
        }

        function printParens(i: number, j: number): string {
          if (i === j) return `A${i}`;
          return `(${printParens(i, s[i][j])} x ${printParens(s[i][j] + 1, j)})`;
        }

        stdout = `Optimal Parenthesization:\n${printParens(1, n)}\n\nMinimum number of scalar multiplications = ${m[1][n]}\n`;
        break;
      }

      default:
        throw new Error(`Algorithm ${labId}/${questionId} is not registered in the embedded engine.`);
    }
  } catch (err: any) {
    stderr = err?.message || String(err);
    exitCode = 1;
  }

  const durationMs = Math.round(performance.now() - start);

  return {
    success: exitCode === 0,
    stage: "run",
    stdout,
    stderr,
    exitCode,
    durationMs,
  };
}

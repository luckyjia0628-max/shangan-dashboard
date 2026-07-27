const express = require('express');
const path = require('path');
const fs = require('fs');
const app = express();
const PORT = process.env.PORT || 3000;

const DATA_FILE = path.join(__dirname, 'data.json');

app.use(express.json({ limit: '1mb' }));
app.use(express.static(__dirname));

/* ---------- data API ---------- */
app.get('/api/data', (_req, res) => {
  try {
    if (fs.existsSync(DATA_FILE)) {
      const raw = fs.readFileSync(DATA_FILE, 'utf-8');
      const data = JSON.parse(raw);
      return res.json(data);
    }
    res.json({});
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/data', (req, res) => {
  try {
    const payload = { ...req.body, _updated: new Date().toISOString() };
    fs.writeFileSync(DATA_FILE, JSON.stringify(payload, null, 2), 'utf-8');
    res.json({ ok: true, updated: payload._updated });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

/* ---------- health ---------- */
app.get('/api/health', (_req, res) => res.json({ ok: true }));

/* ---------- start ---------- */
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🧭 上岸作战台 running on http://0.0.0.0:${PORT}`);
});

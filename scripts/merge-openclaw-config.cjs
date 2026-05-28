#!/usr/bin/env node
'use strict';

const fs = require('fs');

const configPath = process.argv[2];
if (!configPath) {
  console.error('Usage: node merge-openclaw-config.cjs <path-to-openclaw.json>');
  process.exit(1);
}

const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const raw = process.env.MANAGER_TELEGRAM_CHAT_IDS || process.env.MANAGER_TELEGRAM_CHAT_ID || '';
const ids = raw
  .split(/[,;]/)
  .map((s) => s.trim())
  .filter((s) => /^\d+$/.test(s));

cfg.channels = cfg.channels || {};
cfg.channels.telegram = cfg.channels.telegram || {};
cfg.channels.telegram.direct = cfg.channels.telegram.direct || {};

for (const id of ids) {
  cfg.channels.telegram.direct[String(id)] = { enabled: false };
}

if (!cfg.commands) cfg.commands = {};
cfg.commands.ownerAllowFrom = ids.map((id) => `telegram:${id}`);

fs.writeFileSync(configPath, JSON.stringify(cfg, null, 2));

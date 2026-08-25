module.exports = {
  apps: [{
    name: "ser-api-service",
    script: "venv/bin/uvicorn",
    args: "server:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'",
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: "2G",
    min_uptime: "10s",
    max_restarts: 10,
    restart_delay: 5000,
    env: {
      SENTIVOX_ENV: "production",
      PYTHONUNBUFFERED: "1"
    },
    error_file: "./logs/pm2-err.log",
    out_file: "./logs/pm2-out.log",
    merge_logs: true,
    time: true,
    kill_timeout: 10000
  }]
};

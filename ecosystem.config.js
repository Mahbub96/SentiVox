module.exports = {
  apps: [{
    name: "ser-api-service",
    script: "venv/bin/uvicorn",
    args: "server:app --host 127.0.0.1 --port 8000 --workers 4",
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: "2G",
    env: {
      NODE_ENV: "production",
      PYTHONUNBUFFERED: "1"
    },
    error_file: "./logs/pm2-err.log",
    out_file: "./logs/pm2-out.log",
    time: true
  }]
};

#!/bin/bash
set -e

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Initialize database
python -c "from bot import init_db; init_db()"

# Set webhook with secret
if [ -n "$WEBHOOK_URL" ] && [ -n "$WEBHOOK_SECRET" ]; then
    curl -s -F "url=$WEBHOOK_URL" -F "secret_token=$WEBHOOK_SECRET" "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook"
    echo "Webhook set successfully"
fi

# Start Gunicorn in background
gunicorn -c gunicorn.conf.py bot:app &
GUNICORN_PID=$!

# Start reminders in background
python reminders.py &
REMINDERS_PID=$!

echo "Bot PID: $GUNICORN_PID"
echo "Reminders PID: $REMINDERS_PID"

# Keep script alive
trap "kill $GUNICORN_PID $REMINDERS_PID 2>/dev/null; exit" INT TERM
wait

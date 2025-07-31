#!/bin/bash
# JamBandNerd Cron Setup Script
# This script sets up a cron job to run the daily pipeline at 3 PM Eastern Time

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_PATH="$(which python3)"
CRON_TIME="0 15 * * *"  # 3 PM daily (adjust for your timezone)
LOG_FILE="$PROJECT_DIR/logs/automation/cron.log"

echo "🔧 JamBandNerd Cron Setup"
echo "=========================="
echo "Project Directory: $PROJECT_DIR"
echo "Python Path: $PYTHON_PATH"
echo "Schedule: Daily at 3 PM"
echo ""

# Create logs directory
mkdir -p "$PROJECT_DIR/logs/automation"

# Create the cron job command
CRON_COMMAND="cd $PROJECT_DIR && $PYTHON_PATH automation/daily_pipeline.py >> $LOG_FILE 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "automation/daily_pipeline.py"; then
    echo "⚠️  Existing JamBandNerd cron job found. Removing..."
    crontab -l 2>/dev/null | grep -v "automation/daily_pipeline.py" | crontab -
fi

# Add the new cron job
echo "➕ Adding new cron job..."
(crontab -l 2>/dev/null; echo "$CRON_TIME $CRON_COMMAND") | crontab -

# Verify the cron job was added
echo ""
echo "✅ Cron job added successfully!"
echo "Current crontab:"
echo "=================="
crontab -l | grep "automation/daily_pipeline.py"
echo ""

# Display next run times
echo "📅 Next scheduled runs:"
echo "======================="
python3 -c "
import datetime
from croniter import croniter

now = datetime.datetime.now()
cron = croniter('$CRON_TIME', now)
for i in range(3):
    next_run = cron.get_next(datetime.datetime)
    print(f'  {next_run.strftime(\"%Y-%m-%d %H:%M:%S %Z\")}')
" 2>/dev/null || echo "  Install 'croniter' package to see next run times: pip install croniter"

echo ""
echo "📝 Notes:"
echo "========="
echo "- Logs will be written to: $LOG_FILE"
echo "- To remove the cron job: crontab -e (then delete the line)"
echo "- To view cron logs: tail -f $LOG_FILE"
echo "- Make sure your .env file is properly configured"
echo ""
echo "🎉 Setup complete! The pipeline will run daily at 3 PM."

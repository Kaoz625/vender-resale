#!/bin/bash
# Sets up the nightly research cron job for Vender Resale
# Run once: bash scripts/setup_cron.sh

SCRIPT="/Users/markususche/Desktop/Vender Resale/scripts/nightly_research.py"
LOG="/Users/markususche/Desktop/Vender Resale/research/logs/cron.log"
PYTHON=$(which python3)

# Cron line: runs at 2:00am every night
CRON_LINE="0 2 * * * $PYTHON \"$SCRIPT\" >> \"$LOG\" 2>&1"

# Check if already installed
if crontab -l 2>/dev/null | grep -q "nightly_research.py"; then
    echo "Cron job already installed."
    crontab -l | grep "nightly_research"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "Cron job installed:"
    echo "  $CRON_LINE"
fi

echo ""
echo "To run manually right now:"
echo "  python3 \"$SCRIPT\""
echo ""
echo "To view logs:"
echo "  tail -f \"$LOG\""
echo ""
echo "To remove the cron job:"
echo "  crontab -l | grep -v nightly_research | crontab -"

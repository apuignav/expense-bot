#!/bin/bash
now=$(date +"%Y %b %d %H:%M:%S")
echo "Starting expense bot on $now"
python3 /home/osmc/src/expense-bot/expensebot/cli.py -c /home/osmc/.expensebotrc
exit
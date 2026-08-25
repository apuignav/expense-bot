#!/bin/bash
now=$(date +"%Y %b %d %H:%M:%S")
echo "Starting expense bot on $now"
cd /home/osmc/src/expense-bot || exit 1
exec /usr/bin/python3 -m expensebot.cli -c /home/osmc/.expensebotrc

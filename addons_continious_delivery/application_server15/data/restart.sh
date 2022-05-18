#!/bin/sh

RESTART_COMMAND="${1}"
CONFIG_FILES="${2}"

START_CMD=$(echo $RESTART_COMMAND | sed "s/restart/start/")
STOP_CMD=$(echo $RESTART_COMMAND | sed "s/restart/stop/")

# Trying to stop Odoo for 1 minute...
$STOP_CMD  & sleep 1m  # parallel execution

for CONFIG in $CONFIG_FILES
do
  CONFIG_FOR_SEARCH="config=${CONFIG}"
  # Checking if Odoo server process is running
  if ps aux | grep "$CONFIG_FOR_SEARCH" | grep -v grep
  then
      echo "Failed to stop Odoo server. Processes to be killed:"
      ODOO_PROCESSES=$(ps aux | grep "$CONFIG_FOR_SEARCH" | grep -v grep)
      echo "$ODOO_PROCESSES"
      # Kill Odoo Processes
      ps aux | grep "$CONFIG_FOR_SEARCH" | grep -v grep | awk '{print $2}' | xargs kill -9
      echo "Done killing."
  else
      echo "Odoo server stopped successfully."
  fi
done

$START_CMD  # Start Odoo server

exit 0

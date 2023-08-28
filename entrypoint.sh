#!/bin/bash

set -e

exec python3 sched.py &
exec python3 app.py
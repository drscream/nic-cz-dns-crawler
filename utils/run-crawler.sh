#!/bin/bash

# Example script that copies the domain list over from
# a remote machine and runs the crawler controller
# and workers in a tmux session.

set -e
eval "$(keychain --eval --agents ssh id_ecdsa)"
date=$(date +%Y%m%d)

cd ~
mkdir -p ~/domain-lists
mkdir -p ~/results
scp -C -i ~/.ssh/id_ecdsa "user@host:/path/to/domain/list-${date}.txt" ~/domain-lists/

tmux new -s crawler -d
tmux rename-window -t crawler dns-crawler
tmux send-keys -t crawler "cd ~/dns-crawler/" C-m
tmux send-keys -t crawler "source .venv/bin/activate" C-m
tmux send-keys -t crawler "pip install -U hstspreload" C-m
tmux send-keys -t crawler "dns-crawler-controller ~/domain-lists/list-${date}.txt > ~/results/${date}" C-m

sleep 15;

tmux new-window -t crawler
tmux rename-window -t crawler workers
tmux send-keys -t crawler "cd ~/dns-crawler/" C-m
tmux send-keys -t crawler "source .venv/bin/activate" C-m
tmux send-keys -t crawler "dns-crawler-workers 64" C-m

exit 0
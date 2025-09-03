#!/bin/bash

# Check if the argument for JOBS is provided (first arg)
if [ -z "$1" ]; then
    JOBS=8
else
    JOBS=$1  # Number of jobs specified by user
fi

# Check if the user has provided a test prompt list (second argument)
if [ -z "$2" ]; then
    INPUT_FILE="test_prompt_list"
else
    INPUT_FILE=$2
fi

CHAT_WS_ENDPOINT=ws://localhost:9500/chatstream

parallel \
  --joblog "stats_benchmark${JOBS}.log" \
  --progress \
  --jobs ${JOBS} \
  "python testws.py --url ${CHAT_WS_ENDPOINT} --prompt {}" < "${INPUT_FILE}"

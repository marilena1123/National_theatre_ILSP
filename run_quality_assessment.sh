#!/bin/bash

CHAT_WS_ENDPOINT=ws://localhost:9500/chatstream

if [ -z "$1" ]; then
    INPUT_FILE="quality_assessment_prompts.txt"
else
    INPUT_FILE=$1
fi

OUTPUT_CSV=${2:-"quality_assessment_results.csv"}

# Check if input file exists
if [ ! -f "${INPUT_FILE}" ]; then
    echo "Input file not found: ${INPUT_FILE}"
    exit 1
fi

# Prepare the output CSV file
echo "prompt,result" > "${OUTPUT_CSV}"

# Read each line from the input file
while IFS= read -r prompt; do
    # Call the python script and capture the output
    result=$(python testws.py --url "${CHAT_WS_ENDPOINT}" --prompt "${prompt}")
    
    # wait 2s to avoid timeouts
    sleep 2
    # Escape pipes in the output for CSV format
    escaped_result=$(echo "${result}" | sed 's/|/\\|/g')

    # Write the prompt and result to the CSV
    echo "\"${prompt}\"|\"${escaped_result}\"" >> "${OUTPUT_CSV}"
done < "${INPUT_FILE}"

echo "Processing complete. Output written to ${OUTPUT_CSV}"

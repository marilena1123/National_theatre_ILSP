curl -X 'POST' \
  'http://localhost:9500/chat' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d "{
  \"query\": \"$1\"
}"

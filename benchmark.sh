INPUT=$1

JOBS=8

parallel \
  --joblog stats_benchmark${JOBS}.log \
  --progress \
  --jobs ${JOBS} \
 "bash req.sh {}" < test_prompt_list


#!/bin/bash
# Watch logs from both servers in real-time

echo "=== AutoUGC Server Logs ==="
echo ""
echo "FastAPI Backend: http://localhost:8000"
echo "Next.js Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "================================================"

# Show both log files with labels
tail -f \
  /private/tmp/claude-501/-Users-yagna-Desktop-autougc/tasks/b6151df.output \
  /private/tmp/claude-501/-Users-yagna-Desktop-autougc/tasks/bd80bc8.output \
  2>/dev/null

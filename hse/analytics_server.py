from flask import Flask, Response, render_template_string
from flask_cors import CORS
import json
import time

METRICS_PATH = "live_metrics.json"

app = Flask("sovereign_analytics")
CORS(app)

TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Sovereign Live Metrics</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h2>Sovereign Live Metrics</h2>
  <div>
    <p>Instances: <span id="instances">0</span></p>
    <p>Total turns: <span id="turns">0</span></p>
    <p>Feature coverage: <pre id="coverage"></pre></p>
  </div>
  <script>
    const evtSource = new EventSource("/stream");
    evtSource.onmessage = function(e) {
      const data = JSON.parse(e.data);
      document.getElementById("instances").innerText = data.instances;
      document.getElementById("turns").innerText = data.total_turns;
      document.getElementById("coverage").innerText = JSON.stringify(data.feature_coverage, null, 2);
    };
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(TEMPLATE)

def stream_metrics():
    def event_stream():
        last = ""
        while True:
            try:
                with open(METRICS_PATH, "r", encoding="utf-8") as f:
                    s = f.read()
                if s != last:
                    last = s
                    yield f"data: {s}\n\n"
            except FileNotFoundError:
                yield f"data: {json.dumps({'instances':0,'total_turns':0,'feature_coverage':{}})}\n\n"
            time.sleep(1.0)
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/stream")
def stream():
    return stream_metrics()

def start_server(port=5006):
    app.run(host="0.0.0.0", port=port, threaded=True)

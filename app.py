"""The Fit Physician recipe-guide renderer service.
POST /generate  { client selections as JSON }  ->  branded PDF
Optional header X-Auth must match SHARED_SECRET env var (recommended)."""
import io, os
from flask import Flask, request, send_file, jsonify
from generate import generate_guide

app = Flask(__name__)

@app.get("/")
def health():
    return "The Fit Physician recipe renderer is running."

@app.post("/generate")
def generate():
    secret = os.environ.get("SHARED_SECRET", "")
    if secret and request.headers.get("X-Auth", "") != secret:
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True, silent=True) or {}
    try:
        pdf = generate_guide(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    fn = (str(data.get("first_name", "")).strip() + "_" + str(data.get("last_name", "")).strip()).strip("_") or "Recipe"
    return send_file(io.BytesIO(pdf), mimetype="application/pdf",
                     as_attachment=True, download_name=fn + "_Recipe_Guide.pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

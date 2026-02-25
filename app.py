"""
AI Voice Cloning TTS — Local App using Coqui XTTS-v2

Endpoints:
  GET  /              → Web UI
  GET  /health        → Health check
  POST /api/tts       → Clone voice → returns WAV file
  POST /api/tts/base64→ Clone voice → returns base64 JSON
"""

from flask import Flask, request, jsonify, send_file, render_template_string
import os, uuid, base64, torch

# Accept Coqui license automatically (needed for Docker)
os.environ["COQUI_TOS_AGREED"] = "1"

from TTS.api import TTS

app = Flask(__name__)
os.makedirs("outputs", exist_ok=True)

# ---------------- LOAD MODEL ----------------
print("⏳ Loading XTTS-v2 model (first run downloads ~2GB)...")
device = "cuda" if torch.cuda.is_available() else "cpu"
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
print(f"✅ Model loaded on {device}")

# ---------------- WEB UI ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>AI Voice Cloner</title>
<style>
body{
  font-family:Arial, Helvetica, sans-serif;
  background:#0f1117;
  color:white;
  display:flex;
  justify-content:center;
  align-items:center;
  height:100vh;
}
.card{
  background:#1a1d26;
  padding:25px;
  border-radius:14px;
  width:420px;
  box-shadow:0 10px 25px rgba(0,0,0,0.4);
}
h2{margin-top:0}
select, textarea, input, button{
  width:100%;
  margin-top:12px;
  padding:11px;
  border-radius:8px;
  border:none;
  font-size:14px;
}
textarea{resize:vertical; min-height:110px;}
button{
  background:#5b9cff;
  color:white;
  font-weight:bold;
  cursor:pointer;
}
button:hover{background:#3f86ff;}
small{color:#aaa}
</style>
</head>
<body>

<div class="card">
  <h2>🎙 AI Voice Cloner</h2>

  <label>Upload Voice Sample</label>
  <input type="file" id="voice" accept=".wav,.mp3,.ogg,.flac">

  <label>Select Language</label>
  <select id="language">
    <option value="en">English</option>
    <option value="hi">Hindi</option>
    <option value="kn">Kannada</option>
    <option value="ta">Tamil</option>
    <option value="te">Telugu</option>
    <option value="ml">Malayalam</option>
    <option value="bn">Bengali</option>
    <option value="mr">Marathi</option>
  </select>

  <textarea id="text" placeholder="Type text here..."></textarea>

  <button onclick="generate()">Generate Voice</button>

  <small>Tip: Use 10-30 sec clean voice sample for best results.</small>

  <audio id="audio" controls style="display:none;margin-top:15px;"></audio>
</div>

<script>
async function generate(){
  const text = document.getElementById('text').value.trim();
  const voice = document.getElementById('voice').files[0];
  const language = document.getElementById('language').value;
  const audio = document.getElementById('audio');

  if(!text){
    alert("Enter text");
    return;
  }

  if(!voice){
    alert("Upload voice sample");
    return;
  }

  const fd = new FormData();
  fd.append("text", text);
  fd.append("voice", voice);
  fd.append("language", language);

  const res = await fetch("/api/tts", { method:"POST", body:fd });

  if(!res.ok){
    alert("Error generating voice");
    return;
  }

  const blob = await res.blob();
  audio.src = URL.createObjectURL(blob);
  audio.style.display="block";
}
</script>

</body>
</html>
"""

# ---------------- HELPER ----------------
def run_tts(text: str, voice_storage, language: str) -> str:
    """
    Save voice sample → run XTTS → return output wav path
    """
    ext = os.path.splitext(voice_storage.filename)[-1] or ".wav"
    temp_voice = f"outputs/tmp_{uuid.uuid4().hex}{ext}"
    voice_storage.save(temp_voice)

    output_path = f"outputs/out_{uuid.uuid4().hex}.wav"

    try:
        tts.tts_to_file(
            text=text,
            speaker_wav=temp_voice,
            language=language,
            file_path=output_path
        )
    finally:
        if os.path.exists(temp_voice):
            os.remove(temp_voice)

    return output_path

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "device": device,
        "model": "xtts_v2"
    })

@app.route("/api/tts", methods=["POST"])
def api_tts():
    text = request.form.get("text", "").strip()
    language = request.form.get("language", "en")
    voice = request.files.get("voice")

    if not text:
        return jsonify({"error": "Text required"}), 400
    if not voice:
        return jsonify({"error": "Voice sample required"}), 400

    try:
        out = run_tts(text, voice, language)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return send_file(out, mimetype="audio/wav",
                     as_attachment=True,
                     download_name="voice.wav")

@app.route("/api/tts/base64", methods=["POST"])
def api_tts_base64():
    text = request.form.get("text", "").strip()
    language = request.form.get("language", "en")
    voice = request.files.get("voice")

    if not text or not voice:
        return jsonify({"error": "text & voice required"}), 400

    try:
        out = run_tts(text, voice, language)
        with open(out, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        os.remove(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "ok",
        "format": "wav",
        "encoding": "base64",
        "audio": b64
    })

# ---------------- RUN ----------------
if __name__ == "__main__":
    print("\n✅ Open UI: http://localhost:5000")
    print("✅ Health : http://localhost:5000/health\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
"""
Kannada Voice Cloning TTS — Local App using Coqui XTTS-v2
Endpoints:
  GET  /              → Web UI
  GET  /health        → Health check
  POST /api/tts       → Clone voice → returns WAV file
  POST /api/tts/base64→ Clone voice → returns base64 JSON
"""

from flask import Flask, request, jsonify, send_file, render_template_string
import os, uuid, base64, torch

# ── Auto-accept Coqui TOS (required for Docker / non-interactive environments) ─
os.environ["COQUI_TOS_AGREED"] = "1"

from TTS.api import TTS

app = Flask(__name__)
os.makedirs("outputs", exist_ok=True)

# ── Load model once at startup ─────────────────────────────────────────────────
print("⏳ Loading XTTS-v2 model... (first run downloads ~2GB)")
device = "cuda" if torch.cuda.is_available() else "cpu"
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
print(f"✅ Model loaded on {device}!")

HTML = """<!DOCTYPE html>
<html lang="kn">
<head>
<meta charset="UTF-8">
<title>ಕನ್ನಡ ವಾಯ್ಸ್ ಕ್ಲೋನ್</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Kannada:wght@300;400;600;700&display=swap');
  *{margin:0;padding:0;box-sizing:border-box;}
  body{font-family:'Noto Sans Kannada',sans-serif;background:#0a0a0f;color:#e8e0d0;
    min-height:100vh;display:flex;align-items:center;justify-content:center;}
  body::before{content:'';position:fixed;inset:0;
    background:radial-gradient(ellipse at 30% 20%,#1a0a2e 0%,transparent 60%),
               radial-gradient(ellipse at 70% 80%,#0a1a2e 0%,transparent 60%);z-index:0;}
  .container{position:relative;z-index:1;width:100%;max-width:640px;padding:2rem;}
  .header{text-align:center;margin-bottom:2.5rem;}
  .header h1{font-size:2.4rem;font-weight:700;
    background:linear-gradient(135deg,#c8a96e,#e8d5a3,#c8a96e);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
  .header p{color:#7a7060;font-size:.9rem;letter-spacing:.05em;margin-top:.4rem;}
  .card{background:rgba(255,255,255,.04);border:1px solid rgba(200,169,110,.15);
    border-radius:16px;padding:2rem;backdrop-filter:blur(10px);}
  .slabel{font-size:.75rem;font-weight:600;letter-spacing:.12em;color:#c8a96e;
    text-transform:uppercase;margin-bottom:.75rem;}
  .upload{border:2px dashed rgba(200,169,110,.3);border-radius:10px;padding:1.5rem;
    text-align:center;cursor:pointer;transition:all .3s;margin-bottom:1.5rem;position:relative;}
  .upload:hover{border-color:rgba(200,169,110,.6);background:rgba(200,169,110,.05);}
  .upload input{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;}
  .upload .icon{font-size:2rem;margin-bottom:.5rem;}
  .upload .ulbl{color:#a09080;font-size:.9rem;}
  .upload.ok .ulbl{color:#c8a96e;}
  textarea{width:100%;background:rgba(255,255,255,.05);border:1px solid rgba(200,169,110,.2);
    border-radius:10px;color:#e8e0d0;font-family:'Noto Sans Kannada',sans-serif;font-size:1rem;
    padding:1rem;resize:vertical;min-height:120px;outline:none;transition:border-color .3s;margin-bottom:1.5rem;}
  textarea:focus{border-color:rgba(200,169,110,.5);}
  textarea::placeholder{color:#5a5040;}
  button{width:100%;padding:1rem;background:linear-gradient(135deg,#c8a96e,#e8d5a3);
    border:none;border-radius:10px;color:#0a0a0f;font-family:'Noto Sans Kannada',sans-serif;
    font-size:1rem;font-weight:700;cursor:pointer;transition:all .3s;}
  button:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(200,169,110,.3);}
  button:disabled{opacity:.5;cursor:not-allowed;transform:none;}
  .status{margin-top:1.5rem;padding:1rem;border-radius:10px;text-align:center;display:none;}
  .status.loading{display:block;background:rgba(200,169,110,.1);border:1px solid rgba(200,169,110,.2);
    color:#c8a96e;animation:pulse 1.5s infinite;}
  .status.success{display:block;background:rgba(80,200,120,.1);border:1px solid rgba(80,200,120,.2);color:#80e0a0;}
  .status.error{display:block;background:rgba(200,80,80,.1);border:1px solid rgba(200,80,80,.2);color:#e09090;}
  audio{width:100%;margin-top:1rem;border-radius:8px;accent-color:#c8a96e;}
  @keyframes pulse{0%,100%{opacity:1;}50%{opacity:.6;}}
  .wave{display:flex;justify-content:center;gap:4px;margin-bottom:.5rem;}
  .wave span{width:4px;height:20px;background:#c8a96e;border-radius:2px;animation:wave 1s infinite;}
  .wave span:nth-child(2){animation-delay:.1s;}.wave span:nth-child(3){animation-delay:.2s;}
  .wave span:nth-child(4){animation-delay:.3s;}.wave span:nth-child(5){animation-delay:.4s;}
  @keyframes wave{0%,100%{transform:scaleY(.4);}50%{transform:scaleY(1);}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>ಧ್ವನಿ ಕ್ಲೋನ್</h1>
    <p>KANNADA VOICE CLONING · LOCAL · PRIVATE</p>
  </div>
  <div class="card">
    <div class="slabel">ನಿಮ್ಮ ಧ್ವನಿ ಮಾದರಿ (Your Voice Sample)</div>
    <div class="upload" id="uploadBox">
      <input type="file" id="voiceFile" accept=".wav,.mp3,.ogg,.flac">
      <div class="icon">🎙️</div>
      <div class="ulbl" id="uploadLabel">WAV / MP3 ಫೈಲ್ ಆಯ್ಕೆ ಮಾಡಿ (5 sec – 2 min)</div>
    </div>
    <div class="slabel">ಪಠ್ಯ ನಮೂದಿಸಿ (Enter Kannada Text)</div>
    <textarea id="textInput" placeholder="ಇಲ್ಲಿ ಕನ್ನಡ ಪಠ್ಯ ಟೈಪ್ ಮಾಡಿ..."></textarea>
    <button id="btn" onclick="generate()">🔊 ಧ್ವನಿ ರಚಿಸಿ (Generate Voice)</button>
    <div class="status" id="status">
      <div class="wave"><span></span><span></span><span></span><span></span><span></span></div>
      ಧ್ವನಿ ರಚಿಸಲಾಗುತ್ತಿದೆ...
    </div>
    <audio id="audio" controls style="display:none"></audio>
  </div>
</div>
<script>
  document.getElementById('voiceFile').addEventListener('change', e => {
    if(e.target.files[0]){
      document.getElementById('uploadLabel').textContent='✅ '+e.target.files[0].name;
      document.getElementById('uploadBox').classList.add('ok');
    }
  });
  async function generate(){
    const text=document.getElementById('textInput').value.trim();
    const file=document.getElementById('voiceFile').files[0];
    const status=document.getElementById('status');
    const btn=document.getElementById('btn');
    const audio=document.getElementById('audio');
    if(!text){alert('ದಯವಿಟ್ಟು ಪಠ್ಯ ನಮೂದಿಸಿ!');return;}
    if(!file){alert('ದಯವಿಟ್ಟು ಧ್ವನಿ ಮಾದರಿ ಆಯ್ಕೆ ಮಾಡಿ!');return;}
    btn.disabled=true;status.className='status loading';audio.style.display='none';
    const fd=new FormData();fd.append('text',text);fd.append('voice',file);
    try{
      const res=await fetch('/api/tts',{method:'POST',body:fd});
      if(!res.ok){const e=await res.json();throw new Error(e.error);}
      audio.src=URL.createObjectURL(await res.blob());
      audio.style.display='block';
      status.className='status success';
      status.innerHTML='✅ ಧ್ವನಿ ಯಶಸ್ವಿಯಾಗಿ ರಚಿಸಲಾಗಿದೆ!';
    }catch(err){status.className='status error';status.innerHTML='❌ ದೋಷ: '+err.message;}
    btn.disabled=false;
  }
</script>
</body>
</html>"""


# ── Helper ────────────────────────────────────────────────────────────────────
def run_tts(text: str, voice_storage) -> str:
    """Save voice sample, run TTS, return output path."""
    ext = os.path.splitext(voice_storage.filename)[-1] or ".wav"
    tmp = f"outputs/tmp_{uuid.uuid4().hex}{ext}"
    voice_storage.save(tmp)
    out = f"outputs/out_{uuid.uuid4().hex}.wav"
    try:
        tts.tts_to_file(text=text, speaker_wav=tmp, language="kn", file_path=out)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return out


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/health")
def health():
    """Health check — useful for Docker / load balancers."""
    return jsonify({"status": "ok", "device": device, "model": "xtts_v2"})


@app.route("/api/tts", methods=["POST"])
def api_tts():
    """
    Clone your voice and return a WAV audio file.

    Request  : multipart/form-data
      text   (str)  — Kannada text to synthesise
      voice  (file) — Your voice sample WAV/MP3/OGG (5 sec – 2 min)

    Response : audio/wav
    """
    text = request.form.get("text", "").strip()
    voice = request.files.get("voice")
    if not text:
        return jsonify({"error": "Field 'text' is required"}), 400
    if not voice:
        return jsonify({"error": "Field 'voice' (audio file) is required"}), 400
    try:
        out = run_tts(text, voice)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return send_file(out, mimetype="audio/wav", as_attachment=True,
                     download_name="cloned_voice.wav")


@app.route("/api/tts/base64", methods=["POST"])
def api_tts_base64():
    """
    Clone your voice and return JSON with base64-encoded audio.

    Request  : multipart/form-data
      text   (str)  — Kannada text to synthesise
      voice  (file) — Your voice sample WAV/MP3/OGG (5 sec – 2 min)

    Response : application/json
      { "status": "ok", "format": "wav", "encoding": "base64", "audio": "<base64>" }
    """
    text = request.form.get("text", "").strip()
    voice = request.files.get("voice")
    if not text:
        return jsonify({"error": "Field 'text' is required"}), 400
    if not voice:
        return jsonify({"error": "Field 'voice' (audio file) is required"}), 400
    try:
        out = run_tts(text, voice)
        with open(out, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        os.remove(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"status": "ok", "format": "wav", "encoding": "base64", "audio": b64})


if __name__ == "__main__":
    print("\n✅  Web UI      →  http://localhost:5000")
    print("✅  Health      →  GET  http://localhost:5000/health")
    print("✅  API (WAV)   →  POST http://localhost:5000/api/tts")
    print("✅  API (JSON)  →  POST http://localhost:5000/api/tts/base64\n")
    app.run(host="0.0.0.0", debug=False, port=5000)
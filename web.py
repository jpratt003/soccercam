#!/usr/bin/env python3
"""Flask web app to control CameraRecorder and manage recorded files.

Usage:
  pip install -r requirements.txt
  python3 web.py

Open http://<pi-ip>:5000 in a browser.
"""
from flask import Flask, jsonify, request, render_template_string, send_from_directory, abort
import threading
import os
import time
from pathlib import Path
import shutil
import subprocess
from record import CameraRecorder

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

import logging
logging.basicConfig(level=logging.INFO)
logging.info(f"web.py loaded; project_dir={PROJECT_DIR}")
logging.info(f"ffmpeg available: {shutil.which('ffmpeg') is not None}")
logging.info(f"PATH={os.environ.get('PATH')}")
logging.info(f"web user={os.environ.get('USER')} uid={os.geteuid()}")

app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>SoccerCam Recorder</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; }
      .badge { display:inline-block; padding:0.3rem 0.6rem; border-radius:0.25rem; color:#fff; font-weight:bold; }
      .badge.running { background:#28a745; }
      .badge.stopped { background:#dc3545; }
      button { font-size: 1rem; padding: 0.4rem 0.8rem; margin-right: 0.5rem; }
      input { margin-right: 0.5rem; }
      #status { margin-top: 1rem; white-space: pre-wrap; }
      table { border-collapse: collapse; margin-top: 1rem; }
      th, td { border: 1px solid #ccc; padding: 0.3rem 0.6rem; }
      .meta { margin-top: 0.5rem; }
    </style>
  </head>
  <body>
    <h1>SoccerCam Recorder</h1>
    <div>
      <label>Output dir: <input id="directory" value="videos"></label>
      <label>Left filename: <input id="left_name" value="left_camera.mp4"></label>
      <label>Right filename: <input id="right_name" value="right_camera.mp4"></label>
      <label>Duration (minutes, empty = indefinite): <input id="duration" size="6"></label>
    </div>
    <div style="margin-top: 1rem;">
      <button id="start">Start Recording</button>
      <button id="stop">Stop Recording</button>
      <button id="refresh_files">Refresh Files</button>

    </div>

    <div id="status">
      <div id="running_badge" class="badge stopped">Loading...</div>
      <div class="meta" id="status_meta"></div>
      <div class="meta" id="countdown"></div>
      <div class="meta" id="error_meta" style="color:#c00; font-weight:bold;"></div>
      <div class="meta" id="ffmpeg_meta" style="color:#444;"></div>
      <div class="meta" id="power_meta" style="color:#a00; font-weight:bold;"></div>
      <div class="meta" id="power_lines" style="color:#a00; white-space: pre-wrap; font-family: monospace; font-size: 0.9rem;"></div>
      <div class="meta" id="write_meta" style="color:#006; font-weight:bold;"></div> 
    </div> 

    <div id="files"></div>

    <script>
      let remainingSeconds = null;
      let countdownInterval = null;

      // Global handlers to surface JS errors into the UI
      window.addEventListener('error', (ev)=>{
        console.error('Global error', ev);
        try{
          const msg = ev && ev.message ? ev.message : (ev && ev.error ? String(ev.error) : 'Unknown script error');
          const em = document.getElementById('error_meta');
          if (em) em.textContent = 'Global error: ' + msg;
          const badge = document.getElementById('running_badge');
          if (badge) { badge.textContent = 'Error'; badge.classList.add('stopped'); badge.classList.remove('running'); }
        }catch(e){ /* ignore */ }
      });
      window.addEventListener('unhandledrejection', (ev)=>{
        console.error('Unhandled rejection', ev);
        try{
          const em = document.getElementById('error_meta');
          if (em) em.textContent = 'Unhandled promise rejection';
        }catch(e){}
      });

      function formatSeconds(s){
        if (s == null) return '';
        s = Math.max(0, Math.floor(s));
        const h = Math.floor(s/3600);
        const m = Math.floor((s%3600)/60);
        const sec = s%60;
        if (h>0) return `${h}h ${m}m ${sec}s`;
        return `${m}m ${sec}s`;
      }

      function startCountdown(){
        if (countdownInterval) clearInterval(countdownInterval);
        countdownInterval = setInterval(()=>{
          if (remainingSeconds == null) {
            document.getElementById('countdown').textContent = '';
            return;
          }
          if (remainingSeconds <= 0){
            document.getElementById('countdown').textContent = 'Ending soon...';
            remainingSeconds = 0;
            return;
          }
          document.getElementById('countdown').textContent = 'Remaining: ' + formatSeconds(remainingSeconds);
          remainingSeconds -= 1;
        }, 1000);
      }

      // helper: fetch with timeout
      async function fetchWithTimeout(url, opts = {}, timeout = 3000){
        const controller = new AbortController();
        const signal = controller.signal;
        const t = setTimeout(()=> controller.abort(), timeout);
        try{
          const resp = await fetch(url, {...opts, signal});
          clearTimeout(t);
          return resp;
        }catch(e){
          clearTimeout(t);
          throw e;
        }
      }

      async function updateStatus(){
        console.debug('updateStatus start');
        try {
          const r = await fetchWithTimeout('/status', {}, 3000);
          if (!r.ok) throw new Error('Status fetch failed: ' + r.status);
          let s;
          try{
            s = await r.json();
          }catch(parseErr){
            const txt = await r.text().catch(()=>'<no body>');
            console.error('Failed to parse /status JSON', parseErr, txt);
            throw new Error('Invalid JSON from /status: ' + (parseErr.message||parseErr) + ' — ' + txt.slice(0,200));
          }
          const badge = document.getElementById('running_badge');
          const meta = document.getElementById('status_meta');
          const err = document.getElementById('error_meta');
          const pwr = document.getElementById('power_meta');

          if (s.running){
            badge.textContent = 'Recording';
            badge.classList.add('running');
            badge.classList.remove('stopped');
          } else {
            badge.textContent = 'Stopped';
            badge.classList.add('stopped');
            badge.classList.remove('running');
          }
          meta.textContent = `Dir: ${s.output_dir || ''}\nLeft: ${s.output1 || ''}\nRight: ${s.output2 || ''}\nDuration: ${s.duration_minutes || ''}`;
          err.textContent = s.last_error || '';
          if (s.undervoltage_recent){
            pwr.textContent = '⚠️ Recent undervoltage detected. See logs.';
          } else {
            pwr.textContent = '';
          }

          document.getElementById('start').disabled = s.running;
          document.getElementById('stop').disabled = !s.running;

          if (s.remaining_seconds != null){
            remainingSeconds = s.remaining_seconds;
          } else {
            remainingSeconds = null;
          }
          startCountdown();
        } catch (e) {
          console.error('updateStatus failed', e);
          const badge = document.getElementById('running_badge');
          badge.textContent = 'Error';
          badge.classList.add('stopped');
          badge.classList.remove('running');
          document.getElementById('error_meta').textContent = 'Status error: ' + (e.message || e);
          // keep trying periodically
        }
      }

      async function listFiles(){
        console.debug('listFiles start');
        try {
          const directory = document.getElementById('directory').value || 'videos';
          const r = await fetchWithTimeout('/files?directory=' + encodeURIComponent(directory), {}, 3000);
          if (!r.ok) throw new Error('Files fetch failed: ' + r.status);
          let list;
          try{
            list = await r.json();
          }catch(parseErr){
            const txt = await r.text().catch(()=>'<no body>');
            console.error('Failed to parse /files JSON', parseErr, txt);
            const container = document.getElementById('files');
            container.innerHTML = '<p>Error listing files: Invalid JSON from server</p><pre style="white-space:pre-wrap; max-height:6em; overflow:auto;">'+txt.slice(0,500)+'</pre>';
            return;
          }
          const container = document.getElementById('files');
          if (!Array.isArray(list)){
            container.innerHTML = '<p>Error listing files</p>';
            return;
          }
          if (list.length === 0){
            container.innerHTML = '<p>No files found in ' + directory + '</p>';
            return;
          }
          let html = '<table><thead><tr><th>Name</th><th>Size</th><th>Modified</th><th>Download</th></tr></thead><tbody>';
          for (const f of list){
            html += '<tr>' +
                    '<td>' + f.name + '</td>' +
                    '<td>' + f.size + '</td>' +
                    '<td>' + f.mtime + '</td>' +
                    '<td><a href="/download?directory=' + encodeURIComponent(directory) + '&filename=' + encodeURIComponent(f.name) + '">Download</a></td>' +
                    '</tr>';
          }
          html += '</tbody></table>';
          container.innerHTML = html;
        } catch (e) {
          console.error('listFiles failed', e);
          const container = document.getElementById('files');
          container.innerHTML = '<p>Error listing files: ' + (e.message || e) + '</p>';
        }
      }

      document.getElementById('start').addEventListener('click', async ()=>{
        const duration = document.getElementById('duration').value;
        const directory = document.getElementById('directory').value || 'videos';
        const left = document.getElementById('left_name').value || 'left_camera.mp4';
        const right = document.getElementById('right_name').value || 'right_camera.mp4';
        await fetch('/start', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({duration: duration ? Number(duration) : null, directory, left, right})
        });
        setTimeout(()=>{ updateStatus(); listFiles(); }, 200);
      });

      document.getElementById('stop').addEventListener('click', async ()=>{
        await fetch('/stop', {method: 'POST'});
        setTimeout(()=>{ updateStatus(); listFiles(); }, 200);
      });

      document.getElementById('refresh_files').addEventListener('click', async ()=>{
        listFiles();
      });



      window.addEventListener('load', ()=>{
        console.debug('DOM loaded; starting status/file refresh loop');
        updateStatus();
        listFiles();
        setInterval(()=>{ updateStatus(); listFiles(); }, 5000);
      });
    </script>
  </body>
</html>
"""


class RecordingManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        self.cam1 = CameraRecorder(camera_id=0, hflip=False, vflip=False)
        self.cam2 = CameraRecorder(camera_id=1, hflip=False, vflip=False)
        self.cam1.configure()
        self.cam2.configure()
        self.output_dir = 'videos'
        self.output1 = None
        self.output2 = None
        self.start_time = None
        self.duration_minutes = None
        self.last_error = None
        # watcher removed; keep minimal state

    def _build_directories(self, output_dir, out1='left_camera.mp4', out2='right_camera.mp4'):
        os.makedirs(output_dir, exist_ok=True)
        output1_path = os.path.join(output_dir, out1)
        output2_path = os.path.join(output_dir, out2)
        # Create new CameraRecorder instances that point to the target files
        self.output_dir = output_dir
        self.output1 = output1_path
        self.output2 = output2_path

    def start(self, duration_minutes=None, left_name='left_camera.mp4', right_name='right_camera.mp4'):
        with self.lock:
            if self.running:
                return False, 'Already running'

            # Build cameras with requested filenames
            self._build_directories(self.output_dir, out1=left_name, out2=right_name)

            try:
                self.cam1.start_recording(self.output1)
                self.cam2.start_recording(self.output2)

                # give ffmpeg a moment to spawn if it's going to
                time.sleep(0.5)
                # keep start logging minimal
                logging.info('Recording processes started')

            except Exception as exc:
                self.last_error = f'Failed to start recording: {exc}'
                try:
                    if self.cam1:
                        self.cam1.stop()
                except Exception:
                    pass
                try:
                    if self.cam2:
                        self.cam2.stop()
                except Exception:
                    pass
                return False, self.last_error

            # Clear previous errors on successful start
            self.last_error = None
            self.running = True
            self.stop_event.clear()
            self.start_time = time.time()
            self.duration_minutes = duration_minutes

            if duration_minutes:
                # Run a thread that will stop recording after the duration
                def timed_stop():
                    finished = self.stop_event.wait(duration_minutes * 60)
                    if not finished:
                        self.stop()
                self.thread = threading.Thread(target=timed_stop, daemon=True)
                self.thread.start()

            return True, 'Recording started' 

    def stop(self):
        print("\nStopping recording and shutting down cameras...")
        with self.lock:
            if not self.running:
                return False, 'Not running'
            try:
                if self.cam1:
                    self.cam1.stop_recording()
            except Exception:
                pass
            try:
                if self.cam2:
                    self.cam2.stop_recording()
            except Exception:
                pass

            try:
                if self.cam1:
                    self.cam1.stop()
                if self.cam2:
                    self.cam2.stop()
            except Exception:
                pass
            self.running = False
            self.stop_event.set()
            # Clear timing info
            self.start_time = None
            self.duration_minutes = None
            return True, 'Stopped'

    def status(self):
        remaining = None
        if self.running and self.start_time and self.duration_minutes:
            elapsed = time.time() - self.start_time
            total = (self.duration_minutes or 0) * 60
            remaining = int(max(0, total - elapsed))
        # include recent undervoltage lines (best-effort)
        underv = ''
        try:
            underv = subprocess.check_output("dmesg -T | grep -i undervoltage | tail -n 5", shell=True, text=True, stderr=subprocess.DEVNULL)
        except Exception:
            underv = ''
        return {
            'running': self.running,
            'output1': self.output1,
            'output2': self.output2,
            'output_dir': self.output_dir,
            'start_time': self.start_time,
            'duration_minutes': self.duration_minutes,
            'remaining_seconds': remaining,
            'last_error': self.last_error,
            'undervoltage_recent': bool(underv.strip()),
            'undervoltage_lines': underv.strip().splitlines(),
        }

manager = RecordingManager()


def safe_directory(user_dir: str) -> str:
    """Return an absolute path inside PROJECT_DIR for a given user-supplied directory."""
    # Treat user_dir as relative to project dir if not absolute
    if os.path.isabs(user_dir):
        candidate = os.path.abspath(user_dir)
    else:
        candidate = os.path.abspath(os.path.join(PROJECT_DIR, user_dir))
    # Prevent directory traversal outside the project
    if not candidate.startswith(PROJECT_DIR):
        raise ValueError('Directory not allowed')
    return candidate


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/start', methods=['POST'])
def start():
    data = request.get_json() or {}
    duration = data.get('duration')
    directory = data.get('directory', 'videos') or 'videos'
    left = data.get('left') or data.get('left_name') or 'left_camera.mp4'
    right = data.get('right') or data.get('right_name') or 'right_camera.mp4'

    try:
        manager.output_dir = safe_directory(directory)
    except ValueError:
        return jsonify({'ok': False, 'msg': 'Invalid directory'}), 400

    logging.info(f"Start request: dir={directory} left={left} right={right} duration={duration}")
    ok, msg = manager.start(duration_minutes=duration, left_name=left, right_name=right)
    logging.info(f"Start result: ok={ok} msg={msg}")
    if manager.last_error:
        logging.error(f"Last error after start: {manager.last_error}")
    return jsonify({'ok': ok, 'msg': msg, 'status': manager.status()})


@app.route('/stop', methods=['POST'])
def stop():
    logging.info('Stop request')
    ok, msg = manager.stop()
    logging.info(f"Stop result: ok={ok} msg={msg}")
    return jsonify({'ok': ok, 'msg': msg, 'status': manager.status()})


@app.route('/status', methods=['GET'])
def status():
    return jsonify(manager.status())


@app.route('/debug', methods=['GET'])
def debug():
    info = {
        'PATH': os.environ.get('PATH'),
        'ffmpeg_path': shutil.which('ffmpeg'),
        'ffmpeg_available': shutil.which('ffmpeg') is not None,
        'user': os.environ.get('USER'),
        'uid': os.geteuid(),
    }
    return jsonify(info)


@app.route('/files', methods=['GET'])
def files():
    directory = request.args.get('directory', 'videos')
    try:
        base = safe_directory(directory)
    except ValueError:
        return jsonify([])
    if not os.path.isdir(base):
        return jsonify([])
    entries = []
    for name in sorted(os.listdir(base), key=lambda n: os.path.getmtime(os.path.join(base, n)), reverse=True):
        full = os.path.join(base, name)
        if os.path.isfile(full):
            entries.append({
                'name': name,
                'size': os.path.getsize(full),
                'mtime': time.ctime(os.path.getmtime(full)),
            })
    return jsonify(entries)


# /test_write endpoint removed — directory access debug tools cleaned up


@app.route('/download')
def download():
    directory = request.args.get('directory', 'videos')
    filename = request.args.get('filename')
    if not filename:
        abort(400)
    try:
        base = safe_directory(directory)
    except ValueError:
        abort(400)
    # Prevent path traversal in filename
    if os.path.basename(filename) != filename:
        abort(400)
    if not os.path.exists(os.path.join(base, filename)):
        abort(404)
    return send_from_directory(base, filename, as_attachment=True)


if __name__ == '__main__':
    logging.info('Starting SoccerCam web server on 0.0.0.0:5000')
    logging.info(f"WorkingDirectory={PROJECT_DIR}")
    app.run(host='0.0.0.0', port=5000, debug=False)

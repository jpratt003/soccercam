#!/usr/bin/env python3
import subprocess, time, requests, os

proc = subprocess.Popen(["python3","web.py"], cwd="/home/jpratt/soccercam", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
time.sleep(3)
print('Server started')
res = requests.post('http://localhost:5000/start', json={'duration':5,'directory':'videos/test_web','left':'web_m_lb.mp4','right':'web_m_rb.mp4'}, timeout=5)
print('start', res.status_code, res.text)
for i in range(8):
    out = subprocess.run(['ps','aux'], capture_output=True, text=True)
    ff = [l for l in out.stdout.splitlines() if 'ffmpeg' in l]
    print(f'{i+1}s ffmpeg count', len(ff))
    for l in ff:
        print('  ', l)
    time.sleep(1)
res2 = requests.post('http://localhost:5000/stop', timeout=5)
print('stop', res2.status_code, res2.text)
print('exists', os.path.exists('videos/test_web/web_m_lb.mp4'), os.path.exists('videos/test_web/web_m_rb.mp4'))
print('files', os.listdir('videos/test_web'))
proc.terminate()
proc.wait(timeout=5)

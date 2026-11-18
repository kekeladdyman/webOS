import re, sys, json, subprocess, time, html
cats = sys.argv[1:]
out = json.load(open("catalog.json")) if __import__("os").path.exists("catalog.json") else {}
H = ["-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36", "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "-H", "Accept-Language: en-US,en;q=0.9"]
for c in cats:
    for page in (1, 2):
        url = f"https://mixkit.co/free-sound-effects/{c}/" + (f"?page={page}" if page > 1 else "")
        r = subprocess.run(["curl", "-sS", "--compressed", "-m", "30", "-w", "\n%{http_code}", url] + H, capture_output=True, text=True, errors="ignore")
        body, code = r.stdout.rsplit("\n", 1)
        if code != "200": print(c, page, "http", code); time.sleep(8); continue
        blocks = body.split('data-controller="audio-player"')[1:]
        n = 0
        for b in blocks:
            m = re.search(r'preview-url-value="([^"]+)"', b); i = re.search(r'item-id-value="(\d+)"', b)
            t = re.search(r'item-grid-card__title[^>]*>\s*([^<]+?)\s*<', b); d = re.search(r'data-test-id="duration">\s*([\d:]+)', b)
            if m and i and t:
                out[i.group(1)] = dict(title=html.unescape(t.group(1)), dur=d.group(1) if d else "", url=m.group(1), cat=out.get(i.group(1), {}).get("cat", []) + [c]); n += 1
        print(c, page, n, "items"); time.sleep(3.5)
        if n < 30: break
json.dump(out, open("catalog.json", "w"), indent=0)
print("total", len(out))

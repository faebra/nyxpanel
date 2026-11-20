#!/usr/bin/env python3
"""Nyx extension JS obfuscator — sensitive-string encoding + rename + minify."""
import re, base64, random, string, json, shutil, zipfile, tempfile, sys
from pathlib import Path
try:
    from jsmin import jsmin
except ImportError:
    def jsmin(s):
        return re.sub(r"\s+", " ", s)

PRESERVE = set("""chrome browser cookies getAll storage local session tabs query create remove
sendMessage onMessage addListener runtime onInstalled onStartup id getURL lastError
scripting executeScript world MAIN target tabId func downloads download filename
conflictAction saveAs url alarms clear get set bookmarks history search activeTab
fetch Promise async await then catch finally JSON parse stringify Math random floor Date
console log error warn setTimeout setInterval clearTimeout document window localStorage
sessionStorage location navigator String Number Boolean Array Object Map Set RegExp
true false null undefined this new typeof instanceof return function var let const if else
for while do switch case break continue try catch throw class extends super import export
default from of in length push pop map filter find forEach includes join split slice concat
indexOf toString valueOf keys values name value domain path secure httpOnly expirationDate
type data eid headers method body status ok text undefined NaN Infinity arguments eval
POST GET Content-Type application json""".split())

def rnd_name(n=8):
    first = random.choice(string.ascii_lowercase)
    rest = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n-1))
    return first + rest

def b64(s):
    return base64.b64encode(s.encode("utf-8")).decode("ascii")

SENSITIVE = re.compile(
    r'("(?:https?://[^"]{8,}|[A-Za-z0-9_\\-]{20,}|/[a-z]+/[a-zA-Z0-9_/\\-]+)"|'
    r"'(?:https?://[^']{8,}|[A-Za-z0-9_\\-]{20,}|/[a-z]+/[a-zA-Z0-9_/\\-]+)')"
)

def protect_sensitive(src: str):
    strings = []
    def repl(m):
        inner = m.group(0)[1:-1]
        idx = len(strings)
        strings.append(inner)
        return "__S[%d]" % idx
    out = SENSITIVE.sub(repl, src)
    if not strings:
        return src
    encoded = [b64(s) for s in strings]
    decoder = (
        "var __S=(function(){var a=%s;var d=function(s){try{return decodeURIComponent(escape(atob(s)))}"
        "catch(e){try{return atob(s)}catch(e2){return s}}};var o=[];for(var i=0;i<a.length;i++)o.push(d(a[i]));return o})();"
    ) % json.dumps(encoded)
    return decoder + "\n" + out

def rename_funcs(src: str):
    candidates = set(re.findall(r"\\b(?:async\\s+)?function\\s+([A-Za-z_][A-Za-z0-9_]*)", src))
    candidates |= set(re.findall(r"\\b(?:const|let|var)\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*(?:async\\s*)?(?:function|\\()", src))
    mapping = {}
    for c in candidates:
        if c in PRESERVE or c.startswith("__") or len(c) < 4:
            continue
        mapping[c] = rnd_name(random.randint(7, 12))
    for old in sorted(mapping, key=len, reverse=True):
        src = re.sub(r"\\b%s\\b" % re.escape(old), mapping[old], src)
    return src

def strip_comments(src):
    src = re.sub(r"/\\*[\\s\\S]*?\\*/", "", src)
    src = re.sub(r"(?m)//.*?$", "", src)
    return src

def obfuscate_js(src: str) -> str:
    src = strip_comments(src)
    src = protect_sensitive(src)
    src = rename_funcs(src)
    a, b = rnd_name(6), rnd_name(6)
    junk = "var %s=0;function %s(x){return x&&%s?x:%s;}" % (a, b, a, a)
    src = "(function(){%s;%s})();" % (junk, src)
    return jsmin(src)

def process_extension(src_dir: Path, out_zip: Path):
    work = Path(tempfile.mkdtemp(prefix="nyx_obf_"))
    try:
        for p in src_dir.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(src_dir)
            dest = work / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if p.suffix == ".js":
                raw = p.read_text(encoding="utf-8", errors="replace")
                dest.write_text(obfuscate_js(raw), encoding="utf-8")
                print("  %s" % rel)
            else:
                shutil.copy2(p, dest)
        if out_zip.exists():
            out_zip.unlink()
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for p in work.rglob("*"):
                if p.is_file():
                    z.write(p, str(p.relative_to(work)))
        print("wrote", out_zip, out_zip.stat().st_size)
    finally:
        shutil.rmtree(work, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python nyx_obf.py <ext_folder> <out.zip>")
        sys.exit(1)
    process_extension(Path(sys.argv[1]), Path(sys.argv[2]))

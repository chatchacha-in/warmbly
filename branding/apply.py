#!/usr/bin/env python3
"""Apply the Chat Chacha brand to a Warmbly source tree, at build time.

    python3 branding/apply.py <warmbly-source-dir> <branding-dir>

Run by .github/workflows/chatchacha-images.yml against a clean checkout of an
upstream release, so upstream code is never edited in git and every release can
be re-branded the same way. It changes what people see, never code identifiers:
"Warmbly" is replaced only as a whole word, so names like WarmblyCloudSetting
are untouched. Every targeted patch names the text it expects; if upstream
moved it, the script fails loudly instead of shipping a half-branded build.
"""
import json
import os
import re
import shutil
import subprocess
import sys

repo, bdir = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
cfg = json.load(open(os.path.join(bdir, "brand.json"), encoding="utf-8"))
NAME, ASSISTANT = cfg["name"], cfg["assistant"]
problems: list[str] = []
stats: dict[str, int] = {}

# "Warmbly" as a whole word, except "Warmbly Cloud": that is Warmbly's own hosted
# service, its entry points are hidden below, and renaming it would misdescribe it.
WORD = re.compile(r"(?<![A-Za-z0-9_$])Warmbly(?![A-Za-z0-9_$])(?! Cloud)")
REMIE = re.compile(r"(?<![A-Za-z0-9_$])Remie(?![A-Za-z0-9_$])")
TEXT_EXT = (".ts", ".tsx", ".html", ".css", ".json", ".webmanifest")


def path(rel: str) -> str:
    return os.path.join(repo, rel)


def read(p: str) -> str:
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def write(p: str, s: str) -> None:
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def is_test(p: str) -> bool:
    return ".test." in p or ".spec." in p or "__tests__" in p or os.sep + "test" + os.sep in p


def patch(rel: str, old: str, new: str) -> None:
    """Replace one exact anchor, or record a problem if upstream changed it."""
    p = path(rel)
    s = read(p)
    if old not in s:
        problems.append(f"{rel}: expected text not found: {old[:70]!r}")
        return
    write(p, s.replace(old, new, 1))
    stats["targeted patches"] = stats.get("targeted patches", 0) + 1


def patch_regex(rel: str, pattern: str, repl: str, flags: int = 0) -> None:
    p = path(rel)
    s = read(p)
    s2, n = re.subn(pattern, repl, s, count=1, flags=flags)
    if n == 0:
        problems.append(f"{rel}: pattern not found: {pattern[:70]!r}")
        return
    write(p, s2)
    stats["targeted patches"] = stats.get("targeted patches", 0) + 1


# 1. Visible text in the three frontends (dashboard, admin panel, public forms).
for root in ("web/src", "admin/src", "forms/src"):
    for dp, _dirs, files in os.walk(path(root)):
        for fn in files:
            p = os.path.join(dp, fn)
            if not fn.endswith(TEXT_EXT) or is_test(p):
                continue
            s = read(p)
            s2, n1 = WORD.subn(NAME, s)
            n2 = 0
            if root == "web/src":
                s2, n2 = REMIE.subn(ASSISTANT, s2)
            if n1 or n2:
                write(p, s2)
                stats["brand words replaced"] = stats.get("brand words replaced", 0) + n1
                stats["assistant renamed"] = stats.get("assistant renamed", 0) + n2

for rel in ("web/index.html", "admin/index.html", "forms/index.html"):
    if os.path.exists(path(rel)):
        s = read(path(rel))
        s2, n = WORD.subn(NAME, s)
        if n:
            write(path(rel), s2)
            stats["brand words replaced"] = stats.get("brand words replaced", 0) + n

# 2. Emails the platform sends (login codes, invites, notifications, the admin test mail).
GO_STRING = re.compile(r'"(?:[^"\\\n]|\\.)*"|`[^`]*`')
for root in ("internal/notify", "internal/api/handler/admin_mail.go"):
    targets = []
    if os.path.isfile(path(root)):
        targets = [path(root)]
    else:
        for dp, _dirs, files in os.walk(path(root)):
            targets += [os.path.join(dp, f) for f in files if f.endswith(".go") and not f.endswith("_test.go")]
    for p in targets:
        s = read(p)
        count = 0

        def in_literal(m: re.Match) -> str:
            global count
            lit = m.group(0)
            new, n = WORD.subn(NAME, lit)
            count += n
            return new

        count = 0
        s2 = GO_STRING.sub(in_literal, s)
        if count:
            write(p, s2)
            stats["email strings replaced"] = stats.get("email strings replaced", 0) + count

# 3. Colour: the dashboard's accent is Tailwind's sky scale, so repaint that scale.
pal = cfg["palette_sky"]
theme = "\n/* Chat Chacha brand: the dashboard accent is Tailwind's sky scale, repainted. */\n@theme {\n"
theme += "".join(f"  --color-sky-{k}: {v};\n" for k, v in pal.items())
theme += "}\n"
css = path("web/src/global.css")
write(css, read(css) + theme)
SKY_HEX = {"#f0f9ff": "50", "#e0f2fe": "100", "#bae6fd": "200", "#7dd3fc": "300", "#38bdf8": "400",
           "#0ea5e9": "500", "#0284c7": "600", "#0369a1": "700", "#075985": "800", "#0c4a6e": "900",
           "#082f49": "950"}
hex_re = re.compile("|".join(re.escape(h) for h in SKY_HEX), re.IGNORECASE)
for root in ("web/src", "web/index.html", "web/public/site.webmanifest"):
    targets = [path(root)] if os.path.isfile(path(root)) else [
        os.path.join(dp, f) for dp, _d, fs in os.walk(path(root)) for f in fs if f.endswith(TEXT_EXT)]
    for p in targets:
        if is_test(p):
            continue
        s = read(p)
        s2, n = hex_re.subn(lambda m: pal[SKY_HEX[m.group(0).lower()]], s)
        if n:
            write(p, s2)
            stats["hex colours repainted"] = stats.get("hex colours repainted", 0) + n

# 4. Logo: the mark everywhere is the company logo image.
os.makedirs(path("web/public/brand"), exist_ok=True)
logo = os.path.join(bdir, "assets", "logo.png")
shutil.copyfile(logo, path("web/public/brand/logo.png"))
patch("web/src/components/svg.tsx", "export const Logo = (", "export const UpstreamLogo = (")
svg = path("web/src/components/svg.tsx")
write(svg, read(svg) + (
    "\n// Chat Chacha brand: the mark is the company logo image (see branding/apply.py).\n"
    "export const Logo = ({ className }: { className: string }) => (\n"
    '    <img src="/brand/logo.png" alt="" className={className} style={{ height: "auto" }} />\n'
    ");\n"))

# 5. Favicons and app icons, generated from the logo.
def find_imagemagick() -> str | None:
    # "convert" on Windows is a disk tool, so only trust a binary that says it is ImageMagick.
    for name in ("magick", "convert"):
        exe = shutil.which(name)
        if not exe:
            continue
        try:
            out = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=20).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        if "ImageMagick" in out:
            return exe
    return None


magick = find_imagemagick()
if not magick:
    problems.append("ImageMagick not found: favicons not generated")
else:
    pub = path("web/public")
    for size, name in ((16, "favicon-16x16.png"), (32, "favicon-32x32.png"), (48, "favicon-48x48.png"),
                       (96, "favicon-96x96.png"), (180, "apple-touch-icon.png"),
                       (192, "web-app-manifest-192x192.png"), (512, "web-app-manifest-512x512.png")):
        subprocess.run([magick, logo, "-resize", f"{size}x{size}", "-background", "none", "-gravity", "center",
                        "-extent", f"{size}x{size}", os.path.join(pub, name)], check=True)
    subprocess.run([magick, logo, "-background", "none", "-define", "icon:auto-resize=48,32,16",
                    os.path.join(pub, "favicon.ico")], check=True)
    stats["icons generated"] = 8

manifest = path("web/public/site.webmanifest")
m = json.loads(read(manifest))
m.update(name=NAME, short_name=NAME, description=cfg["description"],
         theme_color=cfg["theme_color"], background_color=cfg["background_color"])
write(manifest, json.dumps(m, indent=2) + "\n")

# 6. Upsells for Warmbly's own hosted plans and its Cloud warmup pool.
tour = "web/src/components/app/tour/ProductTour.tsx"
patch(tour, "const slides = TOUR_SLIDES;",
      'const slides = TOUR_SLIDES.filter((s) => s.chapter.id !== "plans");')
patch(tour, 'if (!jumped && slide.chapter.id !== "plans") {',
      'if (!jumped && slide.chapter.id !== "plans" && slides.some((s) => s.chapter.id === "plans")) {')
patch_regex("web/src/components/app/emails/CloudPoolBanner.tsx",
            r"(export default function CloudPoolBanner\([^)]*\)[^{]*\{)",
            r"\1\n    return null; // Chat Chacha brand: no Warmbly Cloud promotion.")
patch_regex("web/src/app/app/settings/layout.tsx",
            r'\n[ \t]*\{ path: "warmbly-cloud",[^\n]*', "")

# Report.
for k, v in sorted(stats.items()):
    print(f"  {k}: {v}")
if problems:
    print("\nBranding problems (upstream moved something this script relies on):")
    for p in problems:
        print("  - " + p)
    sys.exit(1)
print("Branding applied.")

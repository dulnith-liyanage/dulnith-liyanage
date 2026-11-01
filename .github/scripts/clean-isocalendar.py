#!/usr/bin/env python3
import os
import sys
import re
import glob
import xml.dom.minidom

def find_input_file(candidate=None):
    if candidate and os.path.exists(candidate):
        return candidate
    search_paths = [
        "/metrics_renders/isocalendar.raw.svg",
        "/metrics_renders/isocalendar.svg",
        "metrics_renders/isocalendar.raw.svg",
        "metrics_renders/isocalendar.svg",
        "isocalendar.raw.svg",
        "isocalendar.svg"
    ]
    for p in search_paths:
        if os.path.exists(p):
            return p
    # Try searching for any svg in metrics_renders
    matches = glob.glob("**/metrics_renders/*.svg", recursive=True) + glob.glob("/metrics_renders/*.svg")
    if matches:
        return matches[0]
    return candidate

def clean_isocalendar(input_path, output_path):
    resolved_in = find_input_file(input_path)
    if not resolved_in or not os.path.exists(resolved_in):
        print(f"Error: input file {input_path} not found.")
        sys.exit(1)

    with open(resolved_in, "r", encoding="utf-8") as f:
        content = f.read()

    # Locate inner SVG if wrapped inside lowlighter/metrics HTML/foreignObject
    svg_start = content.find('<svg version="1.1"')
    if svg_start == -1:
        # Check if already a pure inner SVG or standard SVG
        svg_start = content.find("<svg")

    svg_end = content.find("</svg>\n            </section>")
    if svg_end != -1:
        svg_end += 6
    else:
        svg_end = content.rfind("</svg>") + 6

    inner = content[svg_start:svg_end]
    dom = xml.dom.minidom.parseString(inner)

    # Compute bounding box of all paths in the SVG
    def get_bbox(node, cur_tx=0.0, cur_ty=0.0, cur_sx=1.0, cur_sy=1.0):
        pts = []
        tx, ty = cur_tx, cur_ty
        sx, sy = cur_sx, cur_sy
        if node.nodeType == node.ELEMENT_NODE:
            tr = node.getAttribute("transform")
            if tr:
                sm = re.search(r"scale\(([-\d\.]+)(?:,\s*([-\d\.]+))?\)", tr)
                if sm:
                    scx = float(sm.group(1))
                    scy = float(sm.group(2)) if sm.group(2) else scx
                    sx *= scx
                    sy *= scy
                tm = re.search(r"translate\(([-\d\.]+),\s*([-\d\.]+)\)", tr)
                if tm:
                    tx += float(tm.group(1)) * sx
                    ty += float(tm.group(2)) * sy
            if node.tagName == "path":
                d = node.getAttribute("d")
                coords = re.findall(r"([-\d\.]+)[,\s]+([-\d\.]+)", d)
                for x, y in coords:
                    pts.append((tx + float(x) * sx, ty + float(y) * sy))
            for child in node.childNodes:
                pts.extend(get_bbox(child, tx, ty, sx, sy))
        return pts

    pts = get_bbox(dom.documentElement)
    if not pts:
        print("Warning: No path coordinates found, keeping original file.")
        if resolved_in != output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
        return

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    pad_x = 6.0
    pad_y = 6.0
    min_x = min(xs) - pad_x
    min_y = min(ys) - pad_y
    width = (max(xs) - min(xs)) + 2 * pad_x
    height = (max(ys) - min(ys)) + 2 * pad_y

    inner_body = content[content.find(">", svg_start) + 1 : svg_end - 6].strip()

    clean_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x:.1f} {min_y:.1f} {width:.1f} {height:.1f}" width="100%" height="100%">
{inner_body}
</svg>
'''
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(clean_svg)

    print(f"Cleaned calendar saved to {output_path} (viewBox='{min_x:.1f} {min_y:.1f} {width:.1f} {height:.1f}')")

if __name__ == "__main__":
    in_file = sys.argv[1] if len(sys.argv) > 1 else "isocalendar.svg"
    out_file = sys.argv[2] if len(sys.argv) > 2 else "isocalendar.svg"
    clean_isocalendar(in_file, out_file)

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoS Deliverable Packager - packages complete product deliverable per hardware target.

Every build releases:
  1. EoS source code for the product (all 7 repos)
  2. Generated SDK (toolchain, sysroot)
  3. Cross-compiled libraries (eos, eboot, eai, eni, eipc)
  4. Bootable rootfs image
  5. eApps binaries
  6. Documentation (manifest, release notes)

Output: eos-{target}-v{version}-deliverable.zip
"""
import os
import json
import shutil
import zipfile
import sys
from datetime import datetime, timezone

try:
    from ebuild.sdk_generator import TARGET_ARCH, get_target_info
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sdk_generator import TARGET_ARCH, get_target_info

SOURCE_REPOS = {
    "eos":     {"dirs": ["core","hal","kernel","drivers","debug","services","systems",
                         "power","net","toolchains","include","products"],
                "files": ["CMakeLists.txt","build.yaml","README.md","LICENSE"]},
    "eboot":   {"dirs": ["core","hal","boards","crypto","include"],
                "files": ["CMakeLists.txt","build.yaml","README.md","LICENSE"]},
    "eai":     {"dirs": ["core","runtime","tools","orchestrator","ebot","include"],
                "files": ["CMakeLists.txt","build.yaml","README.md","LICENSE"]},
    "eni":     {"dirs": ["core","providers","platform","include"],
                "files": ["CMakeLists.txt","build.yaml","README.md","LICENSE"]},
    "eipc":    {"dirs": ["core","protocol","security","transport","services","cmd","sdk"],
                "files": ["go.mod","go.sum","README.md","LICENSE"]},
    "ebuild":  {"dirs": ["ebuild","examples"],
                "files": ["setup.py","pyproject.toml","README.md","LICENSE"]},
        "eApps": {"dirs": ["src","include","gui","tests"],
                "files": ["CMakeLists.txt","pyproject.toml","README.md","LICENSE"]},
}


def collect_source(workspace, out_src, target, info):
    collected = 0
    for repo, spec in SOURCE_REPOS.items():
        repo_path = os.path.join(workspace, repo)
        if not os.path.isdir(repo_path):
            continue
        repo_out = os.path.join(out_src, repo)
        os.makedirs(repo_out, exist_ok=True)
        for fname in spec.get("files", []):
            src = os.path.join(repo_path, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(repo_out, fname))
                collected += 1
        for dname in spec.get("dirs", []):
            src_dir = os.path.join(repo_path, dname)
            if os.path.isdir(src_dir):
                dst_dir = os.path.join(repo_out, dname)
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns(
                                    "*.o","*.obj","*.a","*.lib","*.exe",
                                    "*.pyc","__pycache__",".git","build",
                                    "*.cpio.gz","*.tar.gz","*.zip"))
                collected += 1
    product_cfg = os.path.join(out_src, "eos_product_config.h")
    with open(product_cfg, "w") as f:
        f.write("/* Auto-generated EoS product config for %s */\n" % target)
        f.write("#ifndef EOS_PRODUCT_CONFIG_H\n#define EOS_PRODUCT_CONFIG_H\n\n")
        f.write('#define EOS_TARGET_NAME     "%s"\n' % target)
        f.write('#define EOS_TARGET_ARCH     "%s"\n' % info["arch"])
        f.write('#define EOS_TARGET_CPU      "%s"\n' % info["cpu"])
        f.write('#define EOS_TARGET_TRIPLET  "%s"\n' % info["triplet"])
        f.write('#define EOS_TARGET_VENDOR   "%s"\n' % info["vendor"])
        f.write('#define EOS_TARGET_SOC      "%s"\n' % info["soc"])
        f.write('#define EOS_TARGET_CLASS    "%s"\n' % info["class"])
        f.write('#define EOS_DEFAULT_IP      "192.168.1.100"\n')
        f.write('#define EOS_EBOT_PORT       8420\n')
        f.write("\n#endif /* EOS_PRODUCT_CONFIG_H */\n")
    collected += 1
    return collected


def package_deliverable(target, version="0.1.0", build_dir="build",
                        output_base="dist", workspace=None):
    info = get_target_info(target)
    if workspace is None:
        workspace = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
    out = os.path.join(output_base, "eos-%s-v%s" % (target, version))
    dirs = ["sdk","source","image","docs",
            "eosuite/bin","eosuite/lib","eosuite/include","eosuite/etc",
            "libs/eos","libs/eboot","libs/eai","libs/eni","libs/eipc"]
    for d in dirs:
        os.makedirs(os.path.join(out, d), exist_ok=True)

    # Manifest
    now = datetime.now(timezone.utc)
    manifest = {
        "product": "eos-%s" % target, "version": version,
        "date": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": {"name": target, "arch": info["arch"], "cpu": info["cpu"],
                   "triplet": info["triplet"], "vendor": info["vendor"],
                   "soc": info["soc"], "class": info["class"]},
        "components": {"eos":"0.5.0","eboot":"0.3.0","eai":"0.1.0",
                       "eni":"0.1.0","eipc":"0.1.0","eosuite":"0.1.0"},
        "network": {"default_ip":"192.168.1.100","ebot_port":8420},
        "sdk": {"toolchain":"sdk/toolchain.cmake","sysroot":"sdk/sysroot/"},
        "image": "image/eos-image-%s.cpio.gz" % target,
        "source": "source/",
    }
    with open(os.path.join(out,"manifest.json"),"w") as f:
        json.dump(manifest, f, indent=2)

    # Source code
    src_count = collect_source(workspace, os.path.join(out,"source"), target, info)
    print("  Source: %d items collected from workspace" % src_count)

    # SDK
    sdk_src = os.path.join(build_dir, "eos-sdk-%s" % target)
    if os.path.exists(sdk_src):
        shutil.copytree(sdk_src, os.path.join(out,"sdk"), dirs_exist_ok=True)

    # Libraries
    for comp in ["eos","eboot","eai","eni"]:
        bd = os.path.join(build_dir, comp, "build")
        if os.path.exists(bd):
            for r,_,files in os.walk(bd):
                for fn in files:
                    if fn.endswith((".a",".lib")):
                        shutil.copy2(os.path.join(r,fn), os.path.join(out,"libs",comp))
    eipc_bd = os.path.join(build_dir,"eipc","sdk","c","build")
    if os.path.exists(eipc_bd):
        for r,_,files in os.walk(eipc_bd):
            for fn in files:
                if fn.endswith(".a"):
                    shutil.copy2(os.path.join(r,fn), os.path.join(out,"libs","eipc"))

    # eApps (entire suite)
    eosuite_bd = os.path.join(build_dir, "eosuite")
    if os.path.exists(eosuite_bd):
        for r,_,files in os.walk(eosuite_bd):
            for fn in files:
                fp = os.path.join(r,fn)
                if fn.endswith((".a",".lib")):
                    shutil.copy2(fp, os.path.join(out,"eosuite","lib"))
                elif fn.endswith(".h"):
                    shutil.copy2(fp, os.path.join(out,"eosuite","include"))
                elif os.access(fp, os.X_OK) or fn in ("ebot","ebot.exe",
                        "eos_integration_test","eos_integration_test.exe",
                        "eosuite","eosuite.exe"):
                    shutil.copy2(fp, os.path.join(out,"eosuite","bin"))
    conf_path = os.path.join(out,"eosuite","etc","ebot.conf")
    with open(conf_path,"w") as f:
        f.write("# Ebot config for %s\nhost=192.168.1.100\nport=8420\ntimeout=30\nmodel=phi-mini-q4\n" % target)

    # Image
    img = os.path.join(build_dir, "eos-image-%s.cpio.gz" % target)
    if os.path.exists(img):
        shutil.copy2(img, os.path.join(out,"image"))

    # Generated source
    gen = os.path.join(build_dir, "_generated")
    if os.path.exists(gen):
        for fn in os.listdir(gen):
            if fn.endswith((".h",".yaml",".yml",".cmake",".ld")):
                shutil.copy2(os.path.join(gen,fn), os.path.join(out,"source"))

    # Documentation
    with open(os.path.join(out,"docs","RELEASE.txt"),"w") as f:
        f.write("EoS Release %s\nTarget: %s (%s %s)\nArch: %s (%s)\nTriplet: %s\nClass: %s\nDate: %s\n" % (
            version, target, info["vendor"], info["soc"], info["arch"], info["cpu"],
            info["triplet"], info["class"], now.isoformat()))
    with open(os.path.join(out,"docs","README.md"),"w") as f:
        f.write("# EoS Deliverable - %s %s (%s)\n\n" % (info["vendor"], info["soc"], target))
        f.write("Version: %s | Architecture: %s (%s)\n\n" % (version, info["arch"], info["cpu"]))
        f.write("## Contents\n\n| Directory | Description |\n|---|---|\n")
        f.write("| source/ | EoS source code (all 8 repos + product config) |\n")
        f.write("| sdk/ | Target SDK (toolchain.cmake, sysroot) |\n")
        f.write("| libs/ | Cross-compiled libraries |\n")
        f.write("| eosuite/ | eApps binaries + config |\n")
        f.write("| image/ | Bootable rootfs |\n")
        f.write("| manifest.json | Build metadata |\n\n")
        f.write("## Quick Start\n\n```bash\nsource sdk/environment-setup\n")
        f.write("cmake -B build -DCMAKE_TOOLCHAIN_FILE=$CMAKE_TOOLCHAIN_FILE\ncmake --build build\n```\n\n")
        f.write("## Rebuild from Source\n\n```bash\ncd source/eos && cmake -B build && cmake --build build\n```\n")

    # ZIP
    zname = "eos-%s-v%s-deliverable.zip" % (target, version)
    zpath = os.path.join(output_base, zname)
    with zipfile.ZipFile(zpath,"w",zipfile.ZIP_DEFLATED) as zf:
        for r,_,files in os.walk(out):
            for fn in files:
                fp = os.path.join(r,fn)
                zf.write(fp, os.path.relpath(fp, output_base))
    sz = os.path.getsize(zpath) / (1024*1024)
    print("Deliverable: %s (%.1f MB)" % (zpath, sz))
    print("  Target:  %s (%s %s)" % (target, info["vendor"], info["soc"]))
    print("  Arch:    %s (%s)" % (info["arch"], info["cpu"]))
    print("  Content: manifest.json + source/ + sdk/ + libs/ + image/ + eosuite/ + docs/")
    return zpath


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="EoS Deliverable Packager")
    p.add_argument("--target", required=True,
                   help="Target hardware: " + ", ".join(sorted(TARGET_ARCH.keys())))
    p.add_argument("--version", default="0.1.0")
    p.add_argument("--build-dir", default="build")
    p.add_argument("--output", default="dist")
    p.add_argument("--workspace", default=None,
                   help="EoS workspace root (auto-detect if omitted)")
    a = p.parse_args()
    package_deliverable(a.target, a.version, a.build_dir, a.output, a.workspace)

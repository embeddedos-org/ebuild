"""Generate per-segment narration using edge-tts (US English neural voice)."""
import asyncio
import json
import edge_tts
from mutagen.mp3 import MP3

# en-US-GuyNeural = neutral male US voice (Silicon Valley style)
VOICE = "en-US-GuyNeural"
RATE = "+0%"  # natural pace

SEGMENTS = [
    {"id": "intro", "text": "Introducing ebuild. The embedded build system for EoS."},
    {"id": "f1", "text": "Feature one. Cross-Compilation Toolchains. Target ARM, RISC-V, and x86 from a single host with automatic toolchain management."},
    {"id": "f2", "text": "Feature two. Incremental Builds. Content-addressed caching rebuilds only changed targets, cutting build times by 90 percent."},
    {"id": "f3", "text": "Feature three. Dependency Resolution. DAG-based resolver handles diamond dependencies and circular includes automatically."},
    {"id": "arch", "text": "Under the hood, ebuild is built with C, Make, CMake, and LLVM. The architecture flows from Parser, to Resolver, to Scheduler, to Compiler, to Linker."},
    {"id": "cta", "text": "ebuild. Open source and production ready. Visit github dot com slash embeddedos-org slash ebuild."}
]


async def generate():
    durations = {}
    audio_files = []

    for seg in SEGMENTS:
        filename = f"seg_{seg['id']}.mp3"
        communicate = edge_tts.Communicate(seg["text"], VOICE, rate=RATE)
        await communicate.save(filename)
        dur = MP3(filename).info.length
        durations[seg["id"]] = round(dur + 0.5, 1)
        audio_files.append(filename)
        print(f"  {seg['id']}: {dur:.1f}s -> padded {durations[seg['id']]}s")

    with open("durations.json", "w") as f:
        json.dump(durations, f, indent=2)

    # Concatenate
    import subprocess
    with open("concat_list.txt", "w") as f:
        for af in audio_files:
            f.write(f"file '{af}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "concat_list.txt", "-c", "copy", "narration.mp3"
    ], check=True)

    total = sum(durations.values())
    print(f"\nVoice: {VOICE}")
    print(f"Total narration: {total:.1f}s")
    print(f"Durations: {json.dumps(durations)}")


asyncio.run(generate())

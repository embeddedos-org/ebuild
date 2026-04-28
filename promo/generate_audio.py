"""Generate narration audio using Google Text-to-Speech."""
from gtts import gTTS

NARRATION = (
    "Introducing ebuild. The embedded build system for EoS. Feature one: Cross-compilation toolchains target any architecture from a single host. Feature two: Incremental builds compile only what changed, saving hours of build time. Feature three: Automatic dependency resolution manages complex embedded project graphs. ebuild. Open source and production ready. Visit github dot com slash embeddedos-org slash ebuild."
)

tts = gTTS(text=NARRATION, lang="en", slow=False)
tts.save("narration.mp3")
print(f"Generated narration.mp3 ({len(NARRATION)} chars)")

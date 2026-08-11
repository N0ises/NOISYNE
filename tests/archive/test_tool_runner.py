from brain.tool_runner import run_tool

audio = "tests/assets/test.wav"

tools = [
    "pitch_detection",
    "lufs_meter",
    "spectrum_analysis",
    "bpm_detection",
    "key_detection",
]

for tool in tools:

    print("=" * 60)
    print(tool.upper())
    print("=" * 60)

    result = run_tool(tool, audio)

    print(result)
    print()
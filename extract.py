import json

def find_pages():
    with open('/home/mostafa/.gemini/antigravity/brain/b810017e-554a-4b7d-a63e-2d8692f57226/.system_generated/logs/transcript_full.jsonl') as f:
        for line in f:
            try:
                data = json.loads(line)
                if 'tool_calls' in data:
                    for call in data['tool_calls']:
                        if 'TargetFile' in call['args']:
                            fname = call['args']['TargetFile']
                            if 'Page.jsx' in fname:
                                print(f"Step {data['step_index']}: {fname}")
            except Exception as e:
                pass

find_pages()

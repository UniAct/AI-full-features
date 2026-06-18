import json
import os
import subprocess

# 1. Reset frontend from zip
subprocess.run("rm -rf frontend/src/pages/DocumentsPage.jsx frontend/src/components/common/ScopeSelector.jsx", shell=True)
subprocess.run("unzip -o uniact-frontend.zip -d uniact-frontend_tmp && cp -r uniact-frontend_tmp/uniact-frontend/* frontend/ && rm -rf uniact-frontend_tmp", shell=True)
subprocess.run("rm -rf frontend/src/pages/DataPage.jsx frontend/src/pages/IndexPage.jsx", shell=True)

# 2. Replay all edits up to step 1999
with open('/home/mostafa/.gemini/antigravity/brain/b810017e-554a-4b7d-a63e-2d8692f57226/.system_generated/logs/transcript_full.jsonl') as f:
    for line in f:
        data = json.loads(line)
        if data['step_index'] >= 2000:
            break
            
        if 'tool_calls' in data:
            for call in data['tool_calls']:
                args = call['args']
                if 'TargetFile' not in args:
                    continue
                path = args['TargetFile']
                if 'frontend' not in path:
                    continue
                    
                # Fix path
                if path.startswith('/home/mostafa/Documents/UniAct-rag-app-fixed/'):
                    rel_path = path[len('/home/mostafa/Documents/UniAct-rag-app-fixed/'):]
                else:
                    rel_path = path
                    
                try:
                    if call['name'] == 'write_to_file':
                        os.makedirs(os.path.dirname(rel_path), exist_ok=True)
                        with open(rel_path, 'w') as out:
                            out.write(args['CodeContent'])
                            
                    elif call['name'] == 'replace_file_content':
                        if os.path.exists(rel_path):
                            with open(rel_path, 'r') as file:
                                content = file.read()
                            content = content.replace(args['TargetContent'], args['ReplacementContent'], 1)
                            with open(rel_path, 'w') as out:
                                out.write(content)
                            
                    elif call['name'] == 'multi_replace_file_content':
                        if os.path.exists(rel_path):
                            with open(rel_path, 'r') as file:
                                content = file.read()
                            
                            chunks = args['ReplacementChunks']
                            if isinstance(chunks, str):
                                chunks = json.loads(chunks)
                                
                            for c in chunks:
                                content = content.replace(c['TargetContent'], c['ReplacementContent'], 1)
                            with open(rel_path, 'w') as out:
                                out.write(content)
                except Exception as e:
                    print(f"Error at step {data['step_index']} for {rel_path}: {e}")

print("Rebuild complete!")

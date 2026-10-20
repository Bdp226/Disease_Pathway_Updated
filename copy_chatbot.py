import re

src = r'c:\Users\z005b8nt\Downloads\Digitization-of-Disease-Pathways-main-20260721T095451Z-1-001\Digitization-of-Disease-Pathways-main\main.py'
dst = r'c:\Users\z005b8nt\Downloads\Digitization-of-Disease-Pathways-main (1)-20260724T044225Z-1-001\Digitization-of-Disease-Pathways-main (1)\main.py'

with open(src, 'r', encoding='utf-8') as f:
    src_content = f.read()

# Extract Chat endpoint
chat_idx = src_content.find('# \u2500\u2500\u2500\n# FEATURE 5: AI ASSISTANT')
if chat_idx == -1:
    chat_idx = src_content.find('# FEATURE 5: AI ASSISTANT')

if chat_idx != -1:
    chat_code = src_content[chat_idx:]
    # Append to destination
    with open(dst, 'r', encoding='utf-8') as f:
        dst_content = f.read()
    
    if 'FEATURE 5: AI ASSISTANT' not in dst_content:
        # Also need to make sure StreamingResponse is imported
        if 'StreamingResponse' not in dst_content:
            dst_content = dst_content.replace('from fastapi.responses import JSONResponse', 'from fastapi.responses import JSONResponse, StreamingResponse')
            
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(dst_content + "\n\n" + chat_code)
        print("Chatbot endpoints copied!")
    else:
        print("Chatbot endpoints already exist in destination.")
else:
    print("Could not find chatbot code in source.")

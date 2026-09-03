import pathlib

p = pathlib.Path("cyberai/llm_gateway/litellm/INTEGRATION.md")
raw = p.read_text(encoding="utf-8-sig")

raw = raw.replace("cd platform/llm-gateway/litellm", "cd cyberai/llm_gateway/litellm")
# Remove the stray 'n' after the closing code fences (corruption remnant)
raw = raw.replace("```\nn\n", "```\n\n")

p.write_text(raw, encoding="utf-8")
print("fixed:", p)
print("---")
print(raw)

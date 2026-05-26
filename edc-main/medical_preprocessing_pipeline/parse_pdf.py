import asyncio
from llama_cloud import AsyncLlamaCloud

async def main():
    # Khởi tạo client với API key của bạn
    client = AsyncLlamaCloud(api_key="llx-otjLluLLJPjbXAIGk1KCxvHfM0aJxMXgML4A6kmvffWpjs0D")

    pdf_path = "./PIIS1530891X23000344.pdf"

    # Upload
    print(f"Uploading {pdf_path}...")
    file_obj = await client.files.create(file=pdf_path, purpose="parse")
    print(f"File uploaded successfully. File ID: {file_obj.id}")

    # Parse
    print("Parsing file. This may take a moment...")
    result = await client.parsing.parse(
        file_id=file_obj.id,
        tier="agentic_plus",
        version="latest",
        expand=["markdown_full", "text_full"],
    )

    # Lưu kết quả
    markdown_path = "PIIS1530891X23000344.md"
    text_path = "PIIS1530891X23000344.txt"

    with open(markdown_path, "w", encoding="utf-8") as f:
        if result.markdown_full:
            f.write(result.markdown_full)
        
    with open(text_path, "w", encoding="utf-8") as f:
        if result.text_full:
            f.write(result.text_full)
        
    print(f"Parsing completed! Outputs saved to {markdown_path} and {text_path}")

if __name__ == "__main__":
    asyncio.run(main())

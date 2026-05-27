import os
import openai

def test_mimo():
    api_key = os.environ.get("XIAOMI_API_KEY", "")
    print(f"XIAOMI_API_KEY present in environment: {bool(api_key)}")
    if not api_key:
        print("Please set your XIAOMI_API_KEY in your environment before running this script.")
        return

    client = openai.OpenAI(
        base_url="https://token-plan-sgp.xiaomimimo.com/v1",
        api_key=api_key,
    )
    
    # Test different model name variants
    variants = ["MiMo-V2.5-Pro", "mimo-v2.5-pro", "xiaomi/mimo-v2.5-pro"]
    for model_name in variants:
        print(f"\n--- Testing model variant: '{model_name}' ---")
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "Hello, who are you? Reply in one sentence."}],
                temperature=0,
                max_tokens=100
            )
            content = response.choices[0].message.content
            print(f"Success! Response: '{content}'")
        except Exception as e:
            print(f"Failed with exception: {e}")

if __name__ == "__main__":
    test_mimo()

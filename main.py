import os
import base64
import httpx
from typing import AsyncIterable
import fastapi_poe as fp
from fastapi import FastAPI
import uvicorn

# ==========================================
# ⚙️ কনফিগারেশন
# ==========================================
POE_ACCESS_KEY = "2ioixw7wQlgGkk5vNFdf5I0zaoN8QeQv"
BOT_NAME = "Quater"

# আপনার Hugging Face স্পেসের Ngrok লিঙ্ক
NGROK_API_URL = "https://earache-huntsman-undertow.ngrok-free.dev/generate"

# ==========================================
# 🤖 POE BOT CLASS (Fixed with Auth)
# ==========================================
class QuaterBridgeBot(fp.PoeBot):
    
    # 🎯 বট ক্লাসে Access Key পাস করা হলো যাতে অ্যাটাচমেন্ট পারমিশন পায়
    def __init__(self, access_key: str):
        super().__init__(access_key=access_key)

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(allow_attachments=True)

    async def get_response(self, request: fp.QueryRequest) -> AsyncIterable[fp.PartialResponse]:
        user_prompt = request.query[-1].content
        yield fp.PartialResponse(text="🎨 ছবি তৈরি হচ্ছে, অনুগ্রহ করে ১২-১৫ সেকেন্ড অপেক্ষা করুন...\n\n")

        try:
            # Ngrok-এ কল পাঠানো
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    NGROK_API_URL,
                    json={"prompt": user_prompt},
                    headers={
                        "Content-Type": "application/json",
                        "ngrok-skip-browser-warning": "true"
                    }
                )
                
                data = response.json()

                if data.get("status") == "success":
                    base64_data = data["image_base64"]
                    # Base64 থেকে ডাটা আলাদা করা
                    base64_string = base64_data.split(",")[1] if "," in base64_data else base64_data
                    image_bytes = base64.b64decode(base64_string)

                    # ১. Poe API তে সরাসরি ছবি অ্যাটাচ করা
                    await self.post_message_attachment(
                        message_id=request.message_id,
                        file_data=image_bytes,
                        filename="quater_image.png",
                        is_inline=True
                    )
                    
                    # ২. চ্যাটে ছবি নিশ্চিত করা
                    yield fp.PartialResponse(text="✨ আপনার ছবি নিচে তৈরি হয়ে গেছে!\n")
                else:
                    error_msg = data.get("message", "Generation failed")
                    yield fp.PartialResponse(text=f"❌ ছবি তৈরিতে সমস্যা হয়েছে: {error_msg}")

        except httpx.ReadTimeout:
            yield fp.PartialResponse(text="❌ টাইমআউট! Hugging Face Space হয়তো ব্যস্ত বা স্লিপ মোডে আছে।")
        except Exception as e:
            yield fp.PartialResponse(text=f"❌ কানেকশন এরর: {str(e)}")

# ==========================================
# 🌐 FASTAPI APP
# ==========================================
# Bot ইনিশিয়ালাইজেশনে Access Key যুক্ত করা হলো
bot = QuaterBridgeBot(access_key=POE_ACCESS_KEY)
app = fp.make_app(bot, access_key=POE_ACCESS_KEY, bot_name=BOT_NAME)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

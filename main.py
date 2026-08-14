import os
import base64
import httpx
from typing import AsyncIterable
import fastapi_poe as fp
from fastapi import FastAPI
import uvicorn

# ==========================================
# ⚙️ কনফিগারেশন (আপনার তথ্য)
# ==========================================
POE_ACCESS_KEY = "2ioixw7wQlgGkk5vNFdf5I0zaoN8QeQv"
BOT_NAME = "Quater"

# আপনার Hugging Face স্পেসের Ngrok API লিঙ্ক
NGROK_API_URL = "https://earache-huntsman-undertow.ngrok-free.dev/generate"

# ==========================================
# 🤖 POE BOT CLASS (The Bridge)
# ==========================================
class QuaterBridgeBot(fp.PoeBot):
    
    # ১. Poe-র হ্যান্ডশেক/পিং পাস করার জন্য
    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(allow_attachments=True)

    # ২. ইউজারের মেসেজ রিসিভ ও প্রসেস করা
    async def get_response(self, request: fp.QueryRequest) -> AsyncIterable[fp.PartialResponse]:
        
        # ইউজার কী ছবি বানাতে চায় তা বের করা
        user_prompt = request.query[-1].content
        yield fp.PartialResponse(text="🎨 ছবি তৈরি হচ্ছে, অনুগ্রহ করে ১২-১৫ সেকেন্ড অপেক্ষা করুন...\n\n")

        try:
            # Render থেকে আপনার Ngrok (HF Space)-এ রিকুয়েস্ট পাঠানো
            # timeout=60 দেওয়া হয়েছে কারণ ছবি বানাতে ১৫ সেকেন্ড লাগে
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    NGROK_API_URL,
                    json={"prompt": user_prompt},
                    headers={
                        "Content-Type": "application/json",
                        "ngrok-skip-browser-warning": "true"  # 🎯 Ngrok-এর ওয়ার্নিং পেজ বাইপাস করার ম্যাজিক!
                    }
                )
                
                data = response.json()

                # যদি HF Space থেকে সাকসেস মেসেজ আসে
                if data.get("status") == "success":
                    # Base64 ডাটা থেকে "data:image/png;base64," অংশটুকু বাদ দিয়ে আসল কোড নেওয়া
                    base64_string = data["image_base64"].split(",")[1]
                    image_bytes = base64.b64decode(base64_string)

                    # Poe-তে ছবি আপলোড করে দেওয়া
                    await self.post_message_attachment(
                        message_id=request.message_id,
                        file_data=image_bytes,
                        filename="quater_image.png",
                        is_inline=True
                    )
                    yield fp.PartialResponse(text="✨ আপনার ছবি প্রস্তুত!")
                else:
                    error_msg = data.get("message", "Unknown error")
                    yield fp.PartialResponse(text=f"❌ ছবি জেনারেট করতে সমস্যা হয়েছে: {error_msg}")

        except httpx.ReadTimeout:
            yield fp.PartialResponse(text="❌ সার্ভার টাইমআউট! Hugging Face Space হয়তো স্লিপ মোডে আছে বা লোড বেশি।")
        except Exception as e:
            yield fp.PartialResponse(text=f"❌ কানেকশন এরর: {str(e)}")

# ==========================================
# 🌐 FASTAPI APP SETUP
# ==========================================
# Poe-র জন্য অ্যাপ তৈরি
app = fp.make_app(QuaterBridgeBot(), access_key=POE_ACCESS_KEY, bot_name=BOT_NAME)

# Render-এর জন্য লোকাল টেস্টিং ব্লক
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
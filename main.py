import os
import base64
import uuid
import httpx
from typing import AsyncIterable
import fastapi_poe as fp
from fastapi.staticfiles import StaticFiles
import uvicorn

# ==========================================
# ⚙️ কনফিগারেশন
# ==========================================
POE_ACCESS_KEY = "2ioixw7wQlgGkk5vNFdf5I0zaoN8QeQv"
BOT_NAME = "Quater"
NGROK_API_URL = "https://earache-huntsman-undertow.ngrok-free.dev/generate"
RENDER_BASE_URL = "https://quater-bridge.onrender.com"

# Render-এ ছবি সেভ রাখার ফোল্ডার
IMAGE_DIR = "static_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# ==========================================
# 🤖 POE BOT CLASS (Markdown Image Enabled)
# ==========================================
class QuaterBridgeBot(fp.PoeBot):
    
    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(allow_attachments=True)

    async def get_response(self, request: fp.QueryRequest) -> AsyncIterable[fp.PartialResponse]:
        user_prompt = request.query[-1].content
        
        # ১. প্রসেসিং স্ট্যাটাস
        yield fp.PartialResponse(text="🎨 Rendering image... Please allow ~12 seconds.\n\n")

        try:
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
                    base64_string = base64_data.split(",", 1)[1] if "," in base64_data else base64_data
                    image_bytes = base64.b64decode(base64_string)

                    # ২. ছবিটি Render-এ সেভ করা
                    filename = f"{uuid.uuid4().hex}.png"
                    filepath = os.path.join(IMAGE_DIR, filename)
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)

                    # ৩. ছবির লাইভ পাবলিক লিঙ্ক তৈরি
                    image_url = f"{RENDER_BASE_URL}/images/{filename}"

                    # ৪. Poe-তে সরাসরি মার্কডাউন ছবি পাঠানো (স্ক্রিনে সাথে সাথে ডিসপ্লে করবে)
                    markdown_image = f"![Generated Image]({image_url})\n\n"
                    yield fp.PartialResponse(text=f"{markdown_image}✨ Image generated successfully.\n\n*Powered by Quater AI 🔮*")

                    # ব্যাকআপ অ্যাটাচমেন্ট
                    try:
                        await self.post_message_attachment(
                            message_id=request.message_id,
                            download_url=image_url,
                            filename=filename,
                            is_inline=True
                        )
                    except Exception:
                        pass

                else:
                    error_msg = data.get("message", "Generation failed")
                    yield fp.PartialResponse(text=f"⚠️ Generation failed: {error_msg}\n\nPlease try again.")

        except httpx.ReadTimeout:
            yield fp.PartialResponse(text="⏳ Server timeout: The generation engine is taking longer than expected. Please try again.")
        except Exception as e:
            yield fp.PartialResponse(text=f"⚠️ Connection error: {str(e)}")

# ==========================================
# 🌐 FASTAPI APP & STATIC ROUTE
# ==========================================
bot = QuaterBridgeBot()
app = fp.make_app(bot, access_key=POE_ACCESS_KEY)

# Render-এ ছবি দেখানোর জন্য পাবলিক রাউট মাউন্ট করা হলো
app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

import os
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

# Render-এ ছবি ডিসপ্লে করার ফোল্ডার
IMAGE_DIR = "static_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# ==========================================
# 🤖 POE BOT CLASS (Receives Link & Serves to Poe)
# ==========================================
class QuaterBridgeBot(fp.PoeBot):
    
    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(allow_attachments=True)

    async def get_response(self, request: fp.QueryRequest) -> AsyncIterable[fp.PartialResponse]:
        user_prompt = request.query[-1].content
        yield fp.PartialResponse(text="🖌️ Creating... Hold for 12 seconds 👇...\n\n")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # ১. Hugging Face থেকে ছবির লাইভ লিঙ্ক চাওয়া
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
                    # Hugging Face থেকে আসা সরাসরি ছবির লিঙ্ক
                    hf_image_url = data["image_url"]

                    # ২. রেন্ডার সেই লিঙ্ক থেকে ছবিটি এনে নিজের কাছে দ্রুত সেভ করা
                    img_response = await client.get(
                        hf_image_url,
                        headers={"ngrok-skip-browser-warning": "true"}
                    )
                    
                    filename = f"{uuid.uuid4().hex}.png"
                    filepath = os.path.join(IMAGE_DIR, filename)
                    with open(filepath, "wb") as f:
                        f.write(img_response.content)

                    # ৩. Poe-তে সরাসরি মার্কডাউন ছবি পাঠানো
                    poe_image_url = f"{RENDER_BASE_URL}/images/{filename}"
                    markdown_image = f"![Generated Image]({poe_image_url})\n\n"
                    yield fp.PartialResponse(text=f"{markdown_image}🎉 Here Your Image 👆.\n\n*Powered by Quater AI 🎖️.*")

                    try:
                        await self.post_message_attachment(
                            message_id=request.message_id,
                            download_url=poe_image_url,
                            filename=filename,
                            is_inline=True
                        )
                    except Exception:
                        pass

                else:
                    error_msg = data.get("message", "Generation failed")
                    yield fp.PartialResponse(text=f"⚠️ Generation failed: {error_msg}\n\nPlease try again.")

        except httpx.ReadTimeout:
            yield fp.PartialResponse(text="⏳ Server timeout: Generation engine is busy. Please try again.")
        except Exception as e:
            yield fp.PartialResponse(text=f"⚠️ Connection error: {str(e)}")

# ==========================================
# 🌐 FASTAPI APP
# ==========================================
bot = QuaterBridgeBot()
app = fp.make_app(bot, access_key=POE_ACCESS_KEY)
app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

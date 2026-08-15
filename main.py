import os
import base64
import httpx
from typing import AsyncIterable
import fastapi_poe as fp
import uvicorn

# ==========================================
# ⚙️ Configuration
# ==========================================
POE_ACCESS_KEY = "2ioixw7wQlgGkk5vNFdf5I0zaoN8QeQv"
NGROK_API_URL = "https://earache-huntsman-undertow.ngrok-free.dev/generate"

# ==========================================
# 🤖 Poe Bot Class
# ==========================================
class QuaterBridgeBot(fp.PoeBot):
    
    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(allow_attachments=True)

    async def get_response(self, request: fp.QueryRequest) -> AsyncIterable[fp.PartialResponse]:
        user_prompt = request.query[-1].content
        
        # Premium & Sleek Generation Status
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

                    # Attach image directly to Poe chat
                    await self.post_message_attachment(
                        message_id=request.message_id,
                        file_data=image_bytes,
                        filename="quater_image.png",
                        is_inline=True
                    )
                    
                    # Clean completion signature
                    yield fp.PartialResponse(text="✨ Image generated successfully.\n\n*Powered by Quater AI 🔮*")
                else:
                    error_msg = data.get("message", "Generation failed")
                    yield fp.PartialResponse(text=f"⚠️ Generation failed: {error_msg}\n\nPlease try again.")

        except httpx.ReadTimeout:
            yield fp.PartialResponse(text="⏳ Server timeout: The generation engine is taking longer than expected. Please try again.")
        except Exception as e:
            yield fp.PartialResponse(text=f"⚠️ Connection error: {str(e)}")

# ==========================================
# 🌐 FastAPI App (Clean Authentication)
# ==========================================
bot = QuaterBridgeBot()
app = fp.make_app(bot, access_key=POE_ACCESS_KEY)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

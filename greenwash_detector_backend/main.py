import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import pytesseract

app = FastAPI()

TEMP_UPLOAD_FOLDER = "temp_uploads"
os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)

# Tesseract OCR'ın kurulu olduğu yolu belirtin (gerekirse güncelleyin)
# İşletim sisteminize göre doğru yolu yazdığınızdan emin olun
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'# Windows örneği


@app.get("/")
async def root():
    return {"message": "FastAPI sunucusu çalışıyor. POST /analyze_image ile görsel yükleyin."}

@app.post("/analyze_image")
async def analyze_image(file: UploadFile = File(...)):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Sadece JPEG ve PNG formatındaki görseller desteklenmektedir.")
    try:
        image = Image.open(file.file)
        extracted_text = pytesseract.image_to_string(image, lang='eng') # 'tur' Türkçe için
        file_path = os.path.join(TEMP_UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        return {"filename": file.filename, "extracted_text": extracted_text, "saved_path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR işlemi sırasında bir hata oluştu: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
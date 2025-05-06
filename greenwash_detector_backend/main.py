import os
import io
import numpy as np
import cv2
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import pytesseract
import google.generativeai as genai
import langdetect
import re

# API Anahtarı ve model
api_key = "AIzaSyDxMDqEOn920L3W22DaezYiyVLUvo-t7Ag"
genai.configure(api_key=api_key)
model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-001")

# Tesseract yolu (Windows)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Geçici yükleme klasörü
TEMP_UPLOAD_FOLDER = "temp_uploads"
os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)

# FastAPI ve CORS ayarları
app = FastAPI()

def parse_analysis(analysis_text):
    blocks = {
        "ozet": "",
        "supheli_ifadeler": [],
        "skor": None,
        "skor_aciklama": "",
        "tavsiye": []
    }

    current_key = None
    buffer = []

    for line in analysis_text.splitlines():
        line = line.strip()
        if re.match(r"[-•]?\s*(Özet|Sonuç)\s*:", line, re.IGNORECASE):
            if current_key == "tavsiye":
                blocks["tavsiye"] = [l.strip("-*• ") for l in buffer if l.strip()]
            current_key = "ozet"
            buffer = [line.split(":", 1)[-1].strip()]
        elif re.match(r"[-•]?\s*Şüpheli İfadeler\s*:", line, re.IGNORECASE):
            if current_key == "ozet":
                blocks["ozet"] = " ".join(buffer).strip()
            current_key = "supheli_ifadeler"
            buffer = []
        elif re.match(r"[-•]?\s*Greenwashing Skoru", line, re.IGNORECASE):
            if current_key == "supheli_ifadeler":
                blocks["supheli_ifadeler"] = [l.strip("-*• ") for l in buffer if l.strip()]
            current_key = "skor"
            buffer = []
            match = re.search(r"(\d+)\s*\((.*?)\)", line)
            if match:
                blocks["skor"] = int(match.group(1))
                blocks["skor_aciklama"] = match.group(2).strip()
        elif re.match(r"[-•]?\s*Tavsiye\s*:", line, re.IGNORECASE):
            current_key = "tavsiye"
            buffer = []
        elif current_key:
            buffer.append(line)

    if current_key == "tavsiye":
        blocks["tavsiye"] = [l.strip("-*• ") for l in buffer if l.strip()]
    return blocks

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Statik dosyaları (JS, CSS, görseller vs.) sunmak için
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Görsel ön işleme fonksiyonu
def preprocess_image(image_bytes, Kenar_algılama=False, use_sobel=False, Esitleme_Hist_Kullan=False, Median_blur_kullan=False, Gauss_blur_kullan=False):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        open_cv_image = np.array(image)
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
        processed_image = gray

        if Gauss_blur_kullan:
            processed_image = cv2.GaussianBlur(processed_image, (5, 5), 0)

        if Median_blur_kullan:
            processed_image = cv2.medianBlur(processed_image, 5)

        if Esitleme_Hist_Kullan:
            processed_image = cv2.equalizeHist(processed_image)

        if Kenar_algılama:
            processed_image = cv2.Canny(processed_image, 100, 200)

        if use_sobel:
            sobelx = cv2.Sobel(processed_image, cv2.CV_64F, 1, 0, ksize=5)
            sobely = cv2.Sobel(processed_image, cv2.CV_64F, 0, 1, ksize=5)
            processed_image = cv2.magnitude(sobelx, sobely)
            processed_image = cv2.normalize(processed_image, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)

        _, thresh = cv2.threshold(processed_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return Image.fromarray(thresh), open_cv_image

    except Exception as e:
        print("Görsel ön işlem hatası:", e)
        raise e
        return None, None

# Görsel analiz endpoint'i
@app.post("/analyze-image")


async def analyze_image(
    file: UploadFile = File(...),
    Kenar_algılama: bool = Form(False),
    use_sobel: bool = Form(False),
    Esitleme_Hist_Kullan: bool = Form(False),
    Median_blur_kullan: bool = Form(False),
    Gauss_blur_kullan: bool = Form(False),
):
    try:
        contents = await file.read()

        # Görseli kaydet
        file_path = os.path.join(TEMP_UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            f.write(contents)

        # Görseli işle
        processed_image, original_image_np = preprocess_image(
            contents,
            Kenar_algılama=Kenar_algılama,
            use_sobel=use_sobel,
            Esitleme_Hist_Kullan=Esitleme_Hist_Kullan,
            Median_blur_kullan=Median_blur_kullan,
            Gauss_blur_kullan=Gauss_blur_kullan,
        )
        if processed_image is None:
            return JSONResponse(content={"error": "Görsel işlenemedi."}, status_code=400)

        # OCR
        try:
            extracted_text = pytesseract.image_to_string(processed_image, lang="eng+tur")
            if not extracted_text.strip() or len(extracted_text) < 10:
                detected_lang = langdetect.detect(extracted_text)
                ocr_lang = "eng+tur" if detected_lang in ["en", "tr"] else "eng"
                extracted_text = pytesseract.image_to_string(processed_image, lang=ocr_lang)
        except Exception:
            extracted_text = ""

        # Eğer metin yeterli değilse: doğrudan analiz yap
        if not extracted_text.strip() or len(extracted_text) < 10:
            pil_image = Image.fromarray(cv2.cvtColor(original_image_np, cv2.COLOR_BGR2RGB))
            prompt = """
            Görseli analiz et. Yeşil renklerin yoğunluğu, doğa görsellerinin varlığı, sertifika logoları gibi unsurları değerlendirerek greenwashing potansiyeli hakkında yorum yap. Anlamlı metin bulunamadı.
            """
            response = model.generate_content([prompt, pil_image])
            return {
                "filename": file.filename,
                "saved_path": file_path,
                "extracted_text": "Anlamlı metin bulunamadı.",
                "analysis": {
                    "ozet": response.text if hasattr(response, "text") else str(response),
                    "supheli_ifadeler": "",
                    "skor": None,
                    "skor_aciklama": "",
                    "tavsiye": ""
                }
            }

        # Metin varsa analiz yap
        prompt = f"""
        Aşağıdaki ürün açıklamasını ve görseldeki metni analiz et. Bu metinde greenwashing olup olmadığını değerlendir.

        Greenwashing taktikleri:
        - Belirsiz iddialar (ör: "çevre dostu", "doğal").
        - Alakasız erdemler.
        - Daha az kötü olma iddiası.
        - Yanıltıcı görseller/etiketler.
        - Kanıtlanmamış iddialar.
        - Gizli zararları gizleme.
        - Açık yalanlar.

        Metin: "{extracted_text}"

        Lütfen sadece aşağıdaki formatta açıkça yanıt ver:

        - Özet: ...
        - Şüpheli İfadeler:
        - ...
        - Greenwashing Skoru (0-100): ... (kısa açıklama)
        - Tavsiye:
        - ...
        """

        response = model.generate_content(prompt)
        analysis_text = response.text if hasattr(response, "text") else str(response)
        print("GEMINI YANITI:\n", analysis_text)  # return'den önceye aldım

        parsed = parse_analysis(analysis_text)

        return {
            "filename": file.filename,
            "saved_path": file_path.replace("\\", "/"),
            "extracted_text": extracted_text,
            "analysis": {
                "ozet": parsed["ozet"],
                "supheli_ifadeler": parsed["supheli_ifadeler"],
                "skor": parsed["skor"],
                "skor_aciklama": parsed["skor_aciklama"],
                "tavsiye": parsed["tavsiye"],
                "sonuc": (
                    "Bu ürün açıklaması, yüksek olasılıkla greenwashing içermektedir."
                    if parsed["skor"] and parsed["skor"] >= 70
                    else "Bu ürün açıklaması greenwashing içermeyebilir."
                )
            },
            "analysis_raw": analysis_text
        }

        print("GEMINI YANITI:\n", analysis_text)  # Hata ayıklama

        # Eğer yanıt boşsa:
        if not analysis_text or len(analysis_text.strip()) < 20:
            return {
                "filename": file.filename,
                "saved_path": file_path,
                "extracted_text": extracted_text,
                "analysis": {
                    "ozet": "Gemini modeli yanıt üretemedi.",
                    "supheli_ifadeler": "",
                    "skor": None,
                    "skor_aciklama": "",
                    "tavsiye": ""
                },
                "analysis_raw": analysis_text
            }

        # Yanıtı ayrıştır
        ozet = ""
        supheli_ifadeler = ""
        skor = None
        skor_aciklama = ""
        tavsiye = ""

        ozet_match = re.search(r"(?:Özet|Sonuç):\s*(.+?)(?=\n-\s*(Şüpheli|Greenwashing Skoru|Tavsiye)|\Z)", analysis_text, re.DOTALL)
        if ozet_match:
            ozet = ozet_match.group(1).strip()

        supheli_ifadeler_match = re.search(r"-\s*Şüpheli İfadeler:\s*(.+?)(?=\n-\s*Greenwashing Skoru|\Z)", analysis_text, re.DOTALL)
        if supheli_ifadeler_match:
            supheli_ifadeler = supheli_ifadeler_match.group(1).strip()

        skor_match = re.search(r"Greenwashing Skoru \(0-100\):\s*(\d+)\s*\((.*?)\)", analysis_text, re.DOTALL)
        if skor_match:
            skor = int(skor_match.group(1))
            skor_aciklama = skor_match.group(2).strip()

        tavsiye_match = re.search(r"-\s*Tavsiye:\s*(.+)", analysis_text, re.DOTALL)
        if tavsiye_match:
            tavsiye = tavsiye_match.group(1).strip()


        return {
            "filename": file.filename,
            "saved_path": file_path.replace("\\", "/"),
            "extracted_text": extracted_text,
            "analysis": {
                "ozet": ozet,
                "supheli_ifadeler": [
                    line.strip("- ").strip() for line in supheli_ifadeler.split("\n") if line.strip()
                ],
                "skor": skor,
                "skor_aciklama": skor_aciklama,
                "tavsiye": [
                    line.strip("* ").strip() for line in tavsiye.split("\n") if line.strip()
                ],
                "sonuc": (
                    "Bu ürün açıklaması, yüksek olasılıkla greenwashing içermektedir."
                    if skor and skor >= 70
                    else "Bu ürün açıklaması greenwashing içermeyebilir."
                )
            }
        }


    except Exception as e:
        return JSONResponse(content={"error": f"Sunucu hatası: {str(e)}"}, status_code=500)


# index.html(root)
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

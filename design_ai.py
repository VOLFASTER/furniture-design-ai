from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from enum import Enum
from typing import Dict, List, Optional
import uvicorn
import os
import json
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import uuid
import openai
import requests
from PIL import Image, ImageDraw
from io import BytesIO

# OpenAI API anahtarını buraya ekleyin
openai.api_key = "YOUR_API_KEY_HERE"

# FastAPI uygulamasını oluştur
app = FastAPI(title="Mobilya Tasarım Sistemi")

# Templates ve static dosyaları yapılandır
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Loglama yapılandırması
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            'app.log',
            maxBytes=1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)

# Enum sınıfları
class MaterialType(str, Enum):
    WOOD = "wood"
    METAL = "metal"
    FABRIC = "fabric"
    LEATHER = "leather"
    GLASS = "glass"

class FurnitureType(str, Enum):
    TABLE = "table"
    CHAIR = "chair"
    CABINET = "cabinet"
    SOFA = "sofa"

class LightingType(str, Enum):
    NATURAL = "natural"
    STUDIO = "studio"
    WARM = "warm"
    COOL = "cool"
    DRAMATIC = "dramatic"

class CameraAngle(str, Enum):
    FRONT = "front"
    PERSPECTIVE = "perspective"
    TOP = "top"
    ISOMETRIC = "isometric"

class RenderQuality(str, Enum):
    DRAFT = "draft"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"

# Pydantic modelleri
class MaterialProperties(BaseModel):
    material_type: MaterialType
    sub_type: str
    color: str
    texture: Optional[str] = None
    finish: Optional[str] = None

class RenderSettings(BaseModel):
    lighting_type: LightingType
    camera_angle: CameraAngle
    quality: RenderQuality
    background_color: Optional[str] = "#FFFFFF"
    shadow_softness: Optional[float] = 0.5
    ambient_occlusion: Optional[bool] = True
    exposure: Optional[float] = 1.0

class DesignRequest(BaseModel):
    furniture_type: FurnitureType
    dimensions: Dict[str, float]
    material: MaterialProperties
    render_settings: RenderSettings

class DesignResponse(BaseModel):
    id: str
    preview_url: str
    render_url: str
    technical_url: str
    model_url: str

def create_test_image(width: int, height: int, text: str, error_text: str) -> bytes:
    """Test görüntüsü oluştur"""
    try:
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        draw.text((width/2-100, height/2-50), text, fill='black')
        draw.text((width/2-100, height/2+50), error_text, fill='red')
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except Exception as e:
        logger.error(f"Test görüntüsü oluşturma hatası: {str(e)}")
        return b""

async def generate_furniture_image(
    furniture_type: str,
    material: str,
    view: str,
    dimensions: Dict[str, float],
    color: str,
    finish: str
) -> bytes:
    """DALL-E ile mobilya görüntüsü oluştur"""
    try:
        logger.debug(f"Görüntü oluşturma başladı: {furniture_type} - {view}")
        dimensions_text = f"{dimensions['length']}cm x {dimensions['width']}cm x {dimensions['height']}cm"
        
        prompt = f"""Create a photorealistic {view} view of a {furniture_type} with these exact specifications:
        - Material: {material}
        - Dimensions: {dimensions_text}
        - Color: {color}
        - Finish: {finish}
        The image should be a high-quality product photo on a white background."""
        
        logger.debug(f"DALL-E Prompt: {prompt}")
        
        try:
            response = openai.Image.create(
                prompt=prompt,
                n=1,
                size="1024x1024",
                response_format="url"
            )
            logger.debug(f"DALL-E yanıtı: {response}")
            
            image_url = response['data'][0]['url']
            logger.debug(f"Görüntü URL'i: {image_url}")
            
            image_response = requests.get(image_url)
            logger.debug(f"Görüntü indirme durumu: {image_response.status_code}")
            
            if image_response.status_code == 200:
                return image_response.content
            else:
                raise Exception(f"Görüntü indirilemedi: {image_response.status_code}")
                
        except Exception as api_error:
            logger.error(f"DALL-E API hatası: {str(api_error)}")
            return create_test_image(
                1024, 1024,
                f"{furniture_type}\n{view}\n{dimensions_text}",
                f"Test görüntüsü - API hatası"
            )
            
    except Exception as e:
        logger.error(f"Genel hata: {str(e)}")
        return create_test_image(
            1024, 1024,
            "Hata",
            f"Görüntü oluşturulamadı: {str(e)}"
        )

@app.get("/")
async def home(request: Request):
    """Ana sayfa"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/design/", response_model=DesignResponse)
async def create_design(design: DesignRequest):
    """Yeni tasarım oluştur"""
    try:
        design_id = str(uuid.uuid4())
        design_dir = f"static/designs/{design_id}"
        os.makedirs(design_dir, exist_ok=True)
        
        views = ['front', 'perspective', 'top']
        for view in views:
            image_data = await generate_furniture_image(
                furniture_type=design.furniture_type.value,
                material=f"{design.material.material_type.value} {design.material.sub_type}",
                view=view,
                dimensions=design.dimensions,
                color=design.material.color,
                finish=design.material.finish or "standard"
            )
            
            filepath = f"static/previews/{design_id}_{view}.png"
            with open(filepath, "wb") as f:
                f.write(image_data)
            logger.info(f"Görüntü kaydedildi: {filepath}")
        
        render_path = f"{design_dir}/render.png"
        with open(render_path, "wb") as f:
            f.write(image_data)
        
        with open(f"{design_dir}/design.json", "w", encoding="utf-8") as f:
            json.dump(design.dict(), f, ensure_ascii=False, indent=2)
        
        return DesignResponse(
            id=design_id,
            preview_url=f"/static/previews/{design_id}_front.png",
            render_url=f"/static/designs/{design_id}/render.png",
            technical_url=f"/static/designs/{design_id}/technical.pdf",
            model_url=f"/static/models/{design_id}.obj"
        )
    
    except Exception as e:
        logger.error(f"Tasarım oluşturma hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/preview/{design_id}")
async def preview_design(request: Request, design_id: str):
    """Tasarım önizleme sayfası"""
    try:
        design_path = f"static/designs/{design_id}/design.json"
        if not os.path.exists(design_path):
            raise HTTPException(status_code=404, detail="Tasarım bulunamadı")
        
        with open(design_path, "r", encoding="utf-8") as f:
            design_data = json.load(f)
        
        previews = [
            {
                "angle": view,
                "image_url": f"/static/previews/{design_id}_{view}.png"
            }
            for view in ['front', 'perspective', 'top']
        ]
        
        return templates.TemplateResponse(
            "preview.html",
            {
                "request": request,
                "title": f"Tasarım Önizleme - {design_id}",
                "previews": previews,
                "dimensions": design_data["dimensions"],
                "material": design_data["material"],
                "show_dimensions": True,
                "show_materials": True
            }
        )
    
    except Exception as e:
        logger.error(f"Önizleme hatası: {str(e)}")
        raise HTTPException(status_code=500, detail="Önizleme oluşturulamadı")

# Uygulamayı başlat
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

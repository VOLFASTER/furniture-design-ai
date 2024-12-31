from PIL import Image, ImageDraw, ImageFont
import os

def create_error_image():
    """Hata durumunda gösterilecek varsayılan görüntüyü oluştur"""
    try:
        # Görüntü boyutları
        width = 1024
        height = 1024
        
        # Yeni bir görüntü oluştur
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Metin ayarları
        main_text = "Görüntü Yüklenemedi"
        sub_text = "Lütfen tekrar deneyin"
        
        # Basit font kullan (özel font olmadan)
        main_font_size = 48
        sub_font_size = 32
        
        # Ana metin için pozisyon hesapla
        main_text_x = width // 2
        main_text_y = height // 2 - 50
        
        # Alt metin için pozisyon hesapla
        sub_text_x = width // 2
        sub_text_y = height // 2 + 50
        
        # Metinleri çiz
        draw.text(
            (main_text_x, main_text_y),
            main_text,
            fill='red',
            anchor="mm"  # Metni merkeze hizala
        )
        
        draw.text(
            (sub_text_x, sub_text_y),
            sub_text,
            fill='gray',
            anchor="mm"  # Metni merkeze hizala
        )
        
        # Uyarı ikonu çiz (basit bir daire)
        icon_radius = 40
        icon_x = width // 2
        icon_y = height // 2 - 150
        draw.ellipse(
            [
                icon_x - icon_radius,
                icon_y - icon_radius,
                icon_x + icon_radius,
                icon_y + icon_radius
            ],
            outline='red',
            width=5
        )
        
        # Ünlem işareti çiz
        draw.text(
            (icon_x, icon_y),
            "!",
            fill='red',
            anchor="mm"
        )
        
        # static/images klasörünü oluştur
        os.makedirs('static/images', exist_ok=True)
        
        # Görüntüyü kaydet
        image.save('static/images/error.png')
        print("Hata görüntüsü başarıyla oluşturuldu: static/images/error.png")
        
    except Exception as e:
        print(f"Hata görüntüsü oluşturulurken bir hata oluştu: {str(e)}")

if __name__ == "__main__":
    create_error_image()

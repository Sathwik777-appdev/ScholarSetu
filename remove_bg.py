from PIL import Image

def remove_white_bg(input_path, output_path, tolerance=220):
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    for item in datas:
        # Check if pixel is close to white
        if item[0] > tolerance and item[1] > tolerance and item[2] > tolerance:
            # Change all white (also shades of whites)
            # pixels to transparent
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img.save(output_path, "PNG")

remove_white_bg("apps/console/public/hero-logo.jpg", "apps/console/public/hero-logo.png")

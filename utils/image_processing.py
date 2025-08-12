from PIL import Image

ALL_IMAGE_FORMAT_LIST = ['rgb', 'RGB', 'gif', 'GIF', 'pbm', 'PBM', 'pgm', 'PGM', 'ppm', 'PPM', 'tiff', 'TIFF', 'rast', 'RAST', 'xbm', 'XBM', 'jpeg', 'JPEG', 'jpg', 'JPG', 'bmp', 'BMP', 'png', 'PNG', 'webp', 'WEBP' , 'exr', 'EXR']

def resize_image(img_list):
    for imge in img_list:
        max_width, max_height = 750, 1000
        path = imge.path
        try:
            image = Image.open(path)
            width, height = image.size
            if width > max_width or height > max_height:
                if width > height:
                    w_h = (1000, 750)
                elif height > width:
                    w_h = (750, 1000)
                img = image.resize(w_h)
                img.save(path)
        except Exception:
            pass

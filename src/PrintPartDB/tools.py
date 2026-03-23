import os
import time 

import numpy as np

import PIL
from PIL.Image import Image, Resampling

from niimprint import PrinterClient, BluetoothTransport, SerialTransport

from PyPartDB import PartDB
from pdf2image import convert_from_bytes


def url_to_id(url: str) -> tuple:
    """
    Takes PartDB api url, and finds the elementType and elementId, returns as tuple.
    """
    ELEMENT_TYPES = [
        "part",
        "category",
        "project",
        "label"
    ]

    url_sectioned = url.split("/")

    for element_type in ELEMENT_TYPES:
        if element_type in url_sectioned:
            found_type_index = url_sectioned.index(element_type)
            if found_type_index < len(url_sectioned):
                return (element_type, url_sectioned[found_type_index + 1])
                
    return None
        
def label_to_PILs(api: PartDB, profileId: int, elementIds: list, elementType: str, dpi=300) -> list[Image]:
    """
    Creates an 
    """
    pdf = api.postLabelGenerationRequest(profileId, elementIds, elementType)

    return [image for image in convert_from_bytes(pdf, dpi=dpi)]

def label_to_file(api: PartDB, output_dir, profileId: int, elementIds: list, elementType: str = "part", dpi=300, format: str = "PNG"):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    for element in elementIds:
        pdf = api.postLabelGenerationRequest(profileId, [element], elementType)
        if type(pdf) != bytes:
            print("failed")
            continue
        image: list[Image] = convert_from_bytes(pdf, dpi=dpi)
        image[0].save(os.path.join(output_dir, f"{element}.{format}"), format)

def list_category_names(api: PartDB) -> list:
    """
    Quick method to display (id, name, full_path) of categories.
    """
    categories = []
    for category in sorted(api.getCategories(), key=lambda d: d['full_path']):
        categories.append((category["id"], category["name"], category["full_path"]))
    return categories

def list_part_names_in_category(api: PartDB, category_id: str) -> list:
    pass


def trim_whitespace(img, threshold=240) -> Image:
    import numpy as np
    arr = np.array(img)
    mask = (arr < threshold).any(axis=2)
    coords = np.argwhere(mask)
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1
    return img.crop((x0, y0, x1, y1))

def add_non_uniform_padding(img: Image, left=0, top=0, right=0, bottom=0, color=(255,255,255)) -> Image:
    width, height = img.size
    new_width = width + left + right
    new_height = height + top + bottom
    padded_img = PIL.Image.new(img.mode, (new_width, new_height), color)
    padded_img.paste(img, (left, top))
    return padded_img

def center_image(image, new_width, new_height):
    width, height = image.size   # Get dimensions

    left = round((width - new_width)/2)
    top = round((height - new_height)/2)
    x_right = round(width - new_width) - left
    x_bottom = round(height - new_height) - top
    right = width - x_right
    bottom = height - x_bottom

    # Crop the center of the image
    return image.crop((left, top, right, bottom))

def print_partdb_labels(api: PartDB, printer: PrinterClient, paper_height_mm: float, paper_width_mm:float, paper_height_px:int, profileId: int, elementIds: list, elementType: str = "part", efficient_whitespace:bool = True):
    for image in label_to_PILs(api, profileId, elementIds, elementType):
        paper_ratio = paper_width_mm/paper_height_mm
        max_px_width = paper_height_px
        max_px_height = int(paper_ratio * max_px_width)
        
        # rotate, because it's coming out sideways - makes sense
        # sorry if some of the other dimension calls are wrong because of this.
        image = image.rotate(-90, expand=True)

        # stupid little call that trims the ends because PartDB struggles with small px designs.
        if efficient_whitespace:
            image = trim_whitespace(image)
            image = add_non_uniform_padding(image, top=20)

        # Resize to make sure we're not hitting edges.
        if image.height > max_px_width:
            increase_ratio = max_px_height/image.height
            image = image.resize((int(image.width*increase_ratio), int(image.height*increase_ratio)))

        if image.width > max_px_height:
            increase_ratio = max_px_width/image.width
            image = image.resize((int(image.width*increase_ratio), int(image.height*increase_ratio)))

        printer.print_image(image, 3)

def print_label_from_url(api: PartDB, printer: PrinterClient, url: str, paper_height_mm: float, paper_width_mm:float, paper_height_px:int, profileId: int, efficient_whitespace:bool = True) -> Image:
    result = url_to_id(url)
    if result == None:
        return
    elementType, elementId = result

    print_partdb_labels(
        api=api, 
        printer=printer, 
        paper_height_mm=paper_height_mm, 
        paper_width_mm=paper_width_mm, 
        paper_height_px=paper_height_px, 
        profileId=profileId, 
        elementIds=[elementId], 
        elementType=elementType, 
        efficient_whitespace=False
    )
